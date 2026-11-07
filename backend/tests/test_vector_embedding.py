"""Unit tests for Agent 06: Vector Chunking and pgvector Embedding Node.

Assignee Task (Issue AI-07):
- Test that vector_embedding_node chunks sections into 500-char passages (50-char overlap)
- Test that generated embeddings have exactly 384 dimensions
- Test empty extracted_pdf_contents handling
- Test paper identity resolution by arXiv ID and title fallback
- Test safe handling of unresolvable papers (no orphaned chunks)
- Test enforcement that SentenceTransformers model must be available (no silent pseudo-embedding masquerading)
- Test fallback to Paper record abstract if extracted sections are missing
- Test cross-referencing approved_papers metadata for paper resolution
"""

from unittest.mock import patch

import pytest
from app.agents.nodes.vector_embedding_node import (
    _normalize_identifier,
    _normalize_title,
    _strip_version,
    vector_embedding_node,
)
from app.agents.state import AgentState
from app.models.chunk import PaperChunk
from app.models.paper import Paper
from app.services.vector_service import EMBEDDING_DIMENSION, chunk_paper_sections, chunk_text


class MockAsyncSession:
    """Mock AsyncSession for isolating database persistence in unit tests."""

    def __init__(self, papers=None):
        self.papers = papers or []
        self.added_chunks: list[PaperChunk] = []
        self.executed_stmts = []
        self.flushed = False
        self.committed = False

    async def execute(self, stmt):
        self.executed_stmts.append(stmt)

        class MockResult:
            def __init__(self, items):
                self._items = items

            def scalars(self):
                class MockScalars:
                    def __init__(self, items):
                        self._items = items

                    def all(self):
                        return self._items

                return MockScalars(self._items)

        return MockResult(self.papers)

    def add(self, obj):
        if isinstance(obj, PaperChunk):
            self.added_chunks.append(obj)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_empty_extracted_pdf_contents():
    """Verify that empty or None extracted_pdf_contents returns 0 chunks stored."""
    state_empty: AgentState = {
        "review_id": 1,
        "extracted_pdf_contents": {},
    }
    result = await vector_embedding_node(state_empty)
    assert result["current_step"] == "vector_embedding_completed"
    assert result["chunks_stored_count"] == 0

    state_none: AgentState = {
        "review_id": 1,
        "extracted_pdf_contents": None,
    }
    result_none = await vector_embedding_node(state_none)
    assert result_none["current_step"] == "vector_embedding_completed"
    assert result_none["chunks_stored_count"] == 0


@pytest.mark.asyncio
async def test_sentence_transformer_unavailable_raises_error():
    """Verify fail-fast error when SentenceTransformers model is unavailable."""
    state: AgentState = {
        "review_id": 1,
        "extracted_pdf_contents": {
            "2301.12345": {"abstract": "Sample text for chunking and embedding."}
        },
    }

    with patch(
        "app.agents.nodes.vector_embedding_node.is_embedding_model_available",
        return_value=False,
    ):
        with pytest.raises(RuntimeError, match="SentenceTransformer model .* is unavailable"):
            await vector_embedding_node(state)


@pytest.mark.asyncio
async def test_paper_resolution_by_arxiv_id():
    """Verify paper identity resolution matching arxiv_id (including version variants)."""
    db_paper = Paper(
        id=42,
        title="Attention Is All You Need",
        arxiv_id="1706.03762",
        review_id=1,
    )
    mock_db = MockAsyncSession(papers=[db_paper])

    state: AgentState = {
        "review_id": 1,
        "extracted_pdf_contents": {
            "arXiv:1706.03762v5": {
                "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.",
                "methods": "The Transformer allows for significantly more parallelization and can reach a new state of the art.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    assert result["current_step"] == "vector_embedding_completed"
    assert result["chunks_stored_count"] > 0
    assert len(mock_db.added_chunks) == result["chunks_stored_count"]

    # Ensure every single chunk is linked to the resolved Paper.id
    for chunk in mock_db.added_chunks:
        assert chunk.paper_id == 42
        assert len(chunk.embedding) == 384
        assert chunk.section_name in ["Abstract", "Methods"]


@pytest.mark.asyncio
async def test_paper_resolution_by_title_fallback():
    """Verify paper identity resolution falls back to normalized title matching."""
    db_paper = Paper(
        id=77,
        title="Deep Residual Learning for Image Recognition: A Comprehensive Study.",
        arxiv_id="1512.03385",
        review_id=5,
    )
    mock_db = MockAsyncSession(papers=[db_paper])

    # Key is title with different casing, punctuation, and extra whitespace
    key_title = "deep residual learning for image recognition a comprehensive study"
    state: AgentState = {
        "review_id": 5,
        "extracted_pdf_contents": {
            key_title: {
                "introduction": "Deeper neural networks are more difficult to train.",
                "results": "On the ImageNet classification dataset, we evaluate our residual nets.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    assert result["current_step"] == "vector_embedding_completed"
    assert result["chunks_stored_count"] > 0
    for chunk in mock_db.added_chunks:
        assert chunk.paper_id == 77
        assert len(chunk.embedding) == 384


@pytest.mark.asyncio
async def test_unresolvable_paper_safely_skipped():
    """Verify unresolvable paper keys are safely skipped without inserting orphaned chunks."""
    db_paper = Paper(
        id=10,
        title="Known Paper in Review",
        arxiv_id="2101.00001",
        review_id=3,
    )
    mock_db = MockAsyncSession(papers=[db_paper])

    state: AgentState = {
        "review_id": 3,
        "extracted_pdf_contents": {
            "unknown_ghost_paper_xyz": {
                "abstract": "This paper is not in the database and must not be persisted."
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    assert result["current_step"] == "vector_embedding_completed"
    assert result["chunks_stored_count"] == 0
    assert len(mock_db.added_chunks) == 0


@pytest.mark.asyncio
async def test_approved_papers_cross_reference_resolution():
    """Verify resolution via approved_papers metadata correlation when key differs from DB."""
    db_paper = Paper(
        id=105,
        title="Exact Match DB Title",
        arxiv_id="2305.12345",
        review_id=7,
    )
    mock_db = MockAsyncSession(papers=[db_paper])

    # Key in extracted contents is a variant title, but approved_papers links it to arxiv_id
    state: AgentState = {
        "review_id": 7,
        "approved_papers": [
            {
                "title": "Variant Title From Search",
                "arxiv_id": "2305.12345",
            }
        ],
        "extracted_pdf_contents": {
            "Variant Title From Search": {
                "methods": "Methodology excerpt text for testing approved_papers cross-reference."
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    assert result["chunks_stored_count"] == 1
    assert mock_db.added_chunks[0].paper_id == 105


@pytest.mark.asyncio
async def test_nested_sections_and_full_text():
    """Verify handling of extracted_pdf_contents structured as nested sections and full_text."""
    db_paper = Paper(
        id=55,
        title="Structured Paper",
        arxiv_id="2201.00001",
        review_id=2,
    )
    mock_db = MockAsyncSession(papers=[db_paper])

    state: AgentState = {
        "review_id": 2,
        "extracted_pdf_contents": {
            "2201.00001": {
                "sections": {
                    "methods": "We used deep reinforcement learning with actor-critic.",
                },
                "full_text": "Full paper text fallback if sections empty.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)
    assert result["chunks_stored_count"] >= 1
    assert mock_db.added_chunks[0].paper_id == 55
    assert mock_db.added_chunks[0].section_name == "Methods"


@pytest.mark.asyncio
async def test_fallback_to_paper_abstract_when_sections_empty():
    """Verify fallback to Paper.abstract if extracted content has no text."""
    db_paper = Paper(
        id=88,
        title="Paper With Abstract Only",
        arxiv_id="2005.14165",
        abstract="Language Models are Few-Shot Learners. We demonstrate that scaling up language models greatly improves task-agnostic few-shot performance.",
        review_id=9,
    )
    mock_db = MockAsyncSession(papers=[db_paper])

    state: AgentState = {
        "review_id": 9,
        "extracted_pdf_contents": {"2005.14165": {}},  # empty dictionary
    }

    result = await vector_embedding_node(state, db=mock_db)
    assert result["chunks_stored_count"] == 1
    assert mock_db.added_chunks[0].paper_id == 88
    assert mock_db.added_chunks[0].section_name == "Abstract"


@pytest.mark.asyncio
async def test_sliding_window_500_char_50_overlap():
    """Verify sliding window produces 500-character chunks with 50-character overlap."""
    # Create 950-character text: 0..499 and 450..949
    paragraph_1 = "A" * 450
    overlap_region = "OVERLAP_MARKER_TEST" + ("B" * (50 - len("OVERLAP_MARKER_TEST")))
    paragraph_2 = "C" * 450
    full_text = paragraph_1 + overlap_region + paragraph_2  # length = 450 + 50 + 450 = 950

    chunks = chunk_text(full_text, section_name="Methodology", chunk_size=500, overlap=50)

    assert len(chunks) == 2
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert len(chunks[0]["content"]) == 500
    assert len(chunks[1]["content"]) == 500
    assert "OVERLAP_MARKER_TEST" in chunks[0]["content"]
    assert "OVERLAP_MARKER_TEST" in chunks[1]["content"]


@pytest.mark.asyncio
async def test_section_metadata_and_consistent_indices():
    """Verify section metadata is preserved and chunk indices increment monotonically."""
    sections = {
        "abstract": "Short abstract under 500 characters.",
        "introduction": "Intro part 1 " * 40,  # ~520 chars -> 2 chunks
        "conclusion": "Final wrap up summary.",
    }

    chunks = chunk_paper_sections(sections, chunk_size=500, overlap=50)

    assert len(chunks) >= 4
    indices = [c["chunk_index"] for c in chunks]
    assert indices == list(range(len(chunks)))

    section_names = [c["section_name"] for c in chunks]
    assert "Abstract" in section_names
    assert "Introduction" in section_names
    assert "Conclusion" in section_names


@pytest.mark.asyncio
async def test_embedding_dimensions_exactly_384():
    """Verify all persisted chunks have embeddings with exactly 384 dimensions."""
    db_paper = Paper(
        id=99,
        title="Vector Dimension Test",
        arxiv_id="2401.99999",
        review_id=12,
    )
    mock_db = MockAsyncSession(papers=[db_paper])

    state: AgentState = {
        "review_id": 12,
        "extracted_pdf_contents": {
            "2401.99999": {
                "abstract": "Validating that allMiniLM embeddings always output 384 dimensions."
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    assert result["chunks_stored_count"] == 1
    chunk = mock_db.added_chunks[0]
    assert isinstance(chunk.embedding, list)
    assert len(chunk.embedding) == EMBEDDING_DIMENSION
    assert len(chunk.embedding) == 384


def test_normalization_helpers():
    """Unit tests for string identifier and title normalization helpers."""
    assert _normalize_identifier("arXiv:2301.12345v3") == "2301.12345v3"
    assert _strip_version("2301.12345v3") == "2301.12345"
    assert _normalize_identifier("DOI:10.1000/182") == "10.1000/182"
    assert _normalize_title("Attention Is All You Need!!!\n\t") == "attention is all you need"
