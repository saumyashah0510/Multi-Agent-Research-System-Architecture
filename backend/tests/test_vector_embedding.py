"""Comprehensive regression and unit tests for Agent 06: Vector Chunking and pgvector Embedding Node.

Audit Corrections & Regression Tests (Issue #60 / Audit):
1. Ambiguous title resolution:
   - Duplicate normalized titles are marked ambiguous.
   - Titles differing only in punctuation/whitespace are marked ambiguous.
   - Ambiguous title + valid arXiv ID resolves via arXiv ID.
   - Ambiguous title + valid DOI resolves via DOI.
   - Ambiguous title without stronger identifier safely skipped.
   - Three papers with identical title all marked ambiguous.
   - Duplicate titles in different reviews do not create cross-review ambiguity.
2. Numeric dictionary key resolution:
   - Key "1" does not resolve unrelated Paper.id = 1.
   - Key "42" with no metadata safely skipped.
   - Explicit valid content["paper_id"] resolved after review validation.
   - Explicit content["paper_id"] from another review rejected.
   - Numeric key alongside valid arXiv ID resolves via arXiv ID.
3. Section heading preservation:
   - Acronyms ("LLM", "CNN", "RNA-Seq", "COVID-19", "GPT-4") preserved.
   - All-lowercase headings ("abstract", "methods") capitalized to title case.
4. Chunking boundary tests:
   - 0, 1, 49, 50, 499, 500, 501, 550, 551, 1000, 1001 characters.
5. Idempotency, concurrency, and rollback:
   - Sequential retry replaces existing chunks without duplication.
   - Row-level lock (with_for_update) executed on paper replacement.
6. Fail-fast error when model unavailable:
   - No pseudo-embeddings allowed to masquerade as semantic embeddings.
"""

import hashlib
from typing import Any, List
from unittest.mock import patch

import pytest
from app.agents.nodes.vector_embedding_node import (
    _build_paper_index,
    _normalize_identifier,
    _normalize_title,
    _strip_version,
    vector_embedding_node,
)
from app.agents.state import AgentState
from app.models.chunk import PaperChunk
from app.models.paper import Paper
from app.services.vector_service import (
    EMBEDDING_DIMENSION,
    chunk_paper_sections,
    chunk_text,
    format_section_name,
)


class MockSentenceTransformer:
    """Mock SentenceTransformer model generating deterministic 384D unit vectors."""

    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
        single = isinstance(texts, str)
        text_list = [texts] if single else texts

        vectors = []
        for t in text_list:
            h = hashlib.sha256(t.encode("utf-8")).digest()
            vec = [round(((h[i % len(h)] + i) % 256) / 255.0 - 0.5, 6) for i in range(384)]
            norm = sum(x * x for x in vec) ** 0.5
            if norm > 0:
                vec = [round(x / norm, 6) for x in vec]
            vectors.append(vec)

        return vectors[0] if single and not convert_to_numpy else vectors


@pytest.fixture(autouse=True)
def mock_sentence_transformer_unit(request):
    """Autouse fixture to mock SentenceTransformer for lightweight, offline unit tests."""
    # Skip mock for dedicated integration test that tests real model inference
    if "integration" in request.node.name:
        yield
        return

    mock_model = MockSentenceTransformer()
    with patch("app.services.vector_service._get_embedding_model", return_value=mock_model):
        with patch("app.services.vector_service.is_embedding_model_available", return_value=True):
            with patch(
                "app.agents.nodes.vector_embedding_node.is_embedding_model_available",
                return_value=True,
            ):
                yield


class MockAsyncSession:
    """Mock AsyncSession for isolating database persistence in unit tests."""

    def __init__(self, papers: List[Paper] = None):
        self.papers = papers or []
        self.added_chunks: List[PaperChunk] = []
        self.executed_stmts: List[Any] = []
        self.flushed = False
        self.committed = False
        self.with_for_update_called = False

    async def execute(self, stmt):
        self.executed_stmts.append(stmt)
        stmt_str = str(stmt).lower()

        if "with_for_update" in stmt_str or "for update" in stmt_str:
            self.with_for_update_called = True

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


# ==============================================================================
# 1. Ambiguous Paper Title Resolution Tests
# ==============================================================================


def test_duplicate_titles_marked_ambiguous():
    """Verify that two papers with identical normalized titles are marked ambiguous."""
    p1 = Paper(id=1, title="Survey on Deep Learning", arxiv_id="2101.00001", review_id=1)
    p2 = Paper(id=2, title="Survey on Deep Learning", arxiv_id="2101.00002", review_id=1)

    arxiv_map, _, _, title_map, _, ambiguous_titles = _build_paper_index([p1, p2])

    assert "survey on deep learning" in ambiguous_titles
    assert "survey on deep learning" not in title_map
    assert "2101.00001" in arxiv_map
    assert "2101.00002" in arxiv_map


def test_titles_differing_only_in_punctuation_marked_ambiguous():
    """Verify that titles differing only in punctuation/whitespace are marked ambiguous."""
    p1 = Paper(id=10, title="Quantum Computing: A Review!", arxiv_id="2201.00001", review_id=1)
    p2 = Paper(id=20, title="Quantum Computing - A Review", arxiv_id="2201.00002", review_id=1)

    _, _, _, title_map, _, ambiguous_titles = _build_paper_index([p1, p2])

    assert "quantum computing a review" in ambiguous_titles
    assert "quantum computing a review" not in title_map


@pytest.mark.asyncio
async def test_ambiguous_title_with_valid_arxiv_id_resolves():
    """Verify that when title is ambiguous, resolution succeeds using valid arXiv ID."""
    p1 = Paper(id=101, title="Machine Learning Foundations", arxiv_id="2301.11111", review_id=5)
    p2 = Paper(id=102, title="Machine Learning Foundations", arxiv_id="2301.22222", review_id=5)
    mock_db = MockAsyncSession(papers=[p1, p2])

    state: AgentState = {
        "review_id": 5,
        "extracted_pdf_contents": {
            "Machine Learning Foundations": {
                "arxiv_id": "2301.22222",  # Stronger identifier clarifies resolution
                "abstract": "Foundational overview of statistical learning algorithms.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    assert result["chunks_stored_count"] == 1
    assert mock_db.added_chunks[0].paper_id == 102


@pytest.mark.asyncio
async def test_ambiguous_title_with_valid_doi_resolves():
    """Verify that when title is ambiguous, resolution succeeds using valid DOI."""
    p1 = Paper(id=201, title="Robotics Review", doi="10.1000/1", review_id=3)
    p2 = Paper(id=202, title="Robotics Review", doi="10.1000/2", review_id=3)
    mock_db = MockAsyncSession(papers=[p1, p2])

    state: AgentState = {
        "review_id": 3,
        "extracted_pdf_contents": {
            "Robotics Review": {
                "doi": "10.1000/1",
                "methods": "Kinematics and motion planning algorithms.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    assert result["chunks_stored_count"] == 1
    assert mock_db.added_chunks[0].paper_id == 201


@pytest.mark.asyncio
async def test_ambiguous_title_without_stronger_identifier_skipped():
    """Verify that ambiguous title without stronger identifier is safely skipped."""
    p1 = Paper(id=301, title="Autonomous Agents", arxiv_id="2301.33333", review_id=4)
    p2 = Paper(id=302, title="Autonomous Agents", arxiv_id="2301.44444", review_id=4)
    mock_db = MockAsyncSession(papers=[p1, p2])

    state: AgentState = {
        "review_id": 4,
        "extracted_pdf_contents": {
            "Autonomous Agents": {
                "abstract": "Text without arXiv ID or DOI to disambiguate.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    # Must be safely skipped, never arbitrarily assigned to p1 or p2
    assert result["chunks_stored_count"] == 0
    assert len(mock_db.added_chunks) == 0


def test_three_papers_with_same_title_marked_ambiguous():
    """Verify that three papers sharing a title all remain marked ambiguous."""
    p1 = Paper(id=1, title="Graph Neural Networks", review_id=1)
    p2 = Paper(id=2, title="Graph Neural Networks", review_id=1)
    p3 = Paper(id=3, title="Graph Neural Networks", review_id=1)

    _, _, _, title_map, _, ambiguous_titles = _build_paper_index([p1, p2, p3])

    assert "graph neural networks" in ambiguous_titles
    assert "graph neural networks" not in title_map


@pytest.mark.asyncio
async def test_duplicate_title_across_different_reviews_no_ambiguity():
    """Verify that review-scoped queries prevent identical titles in different reviews from colliding."""
    # In review_id=1, there is only one paper with this title
    p_rev1 = Paper(id=50, title="Deep Reinforcement Learning", review_id=1)
    mock_db = MockAsyncSession(papers=[p_rev1])

    state: AgentState = {
        "review_id": 1,
        "extracted_pdf_contents": {
            "Deep Reinforcement Learning": {
                "abstract": "Policy gradients and Q-learning.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    assert result["chunks_stored_count"] == 1
    assert mock_db.added_chunks[0].paper_id == 50


# ==============================================================================
# 2. Numeric Key Resolution Removal Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_numeric_key_never_treated_as_database_id():
    """Verify that dictionary key '1' is never assumed to be Paper.id = 1."""
    # Paper in DB has id=1, but its title and arxiv_id do NOT match "1"
    p1 = Paper(id=1, title="Transformers in Vision", arxiv_id="2101.99999", review_id=8)
    mock_db = MockAsyncSession(papers=[p1])

    state: AgentState = {
        "review_id": 8,
        "extracted_pdf_contents": {
            "1": {  # Key is "1", representing an ordinal index, NOT database ID
                "abstract": "Extracted text without matching paper title or arxiv_id.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)

    # Must NOT resolve to Paper.id=1
    assert result["chunks_stored_count"] == 0
    assert len(mock_db.added_chunks) == 0


@pytest.mark.asyncio
async def test_numeric_key_42_with_no_metadata_skipped():
    """Verify that numeric key '42' with no metadata is safely skipped."""
    p42 = Paper(id=42, title="Specific Topic Paper", arxiv_id="2201.42424", review_id=9)
    mock_db = MockAsyncSession(papers=[p42])

    state: AgentState = {
        "review_id": 9,
        "extracted_pdf_contents": {"42": {"abstract": "Orphan content with no metadata."}},
    }

    result = await vector_embedding_node(state, db=mock_db)
    assert result["chunks_stored_count"] == 0
    assert len(mock_db.added_chunks) == 0


@pytest.mark.asyncio
async def test_explicit_valid_paper_id_in_content_resolves():
    """Verify that explicit content['paper_id'] resolves when it belongs to the review."""
    p = Paper(id=77, title="Valid Paper", arxiv_id="2001.00077", review_id=11)
    mock_db = MockAsyncSession(papers=[p])

    state: AgentState = {
        "review_id": 11,
        "extracted_pdf_contents": {
            "arbitrary_extractor_key": {
                "paper_id": 77,  # Explicit integer ID in content
                "methods": "Verified explicit paper ID in content payload.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)
    assert result["chunks_stored_count"] == 1
    assert mock_db.added_chunks[0].paper_id == 77


@pytest.mark.asyncio
async def test_explicit_paper_id_from_other_review_rejected():
    """Verify that explicit paper_id belonging to another review is rejected."""
    # Current review 10 only contains paper id=15
    p_rev10 = Paper(id=15, title="Review 10 Paper", review_id=10)
    mock_db = MockAsyncSession(papers=[p_rev10])

    state: AgentState = {
        "review_id": 10,
        "extracted_pdf_contents": {
            "some_key": {
                "paper_id": 999,  # Paper from a different review
                "abstract": "Attempting cross-review bypass via explicit paper_id.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)
    assert result["chunks_stored_count"] == 0
    assert len(mock_db.added_chunks) == 0


@pytest.mark.asyncio
async def test_numeric_key_alongside_valid_arxiv_id_resolves():
    """Verify that numeric extraction key with valid arxiv_id resolves via arXiv ID."""
    p = Paper(id=33, title="Neural ODEs", arxiv_id="1806.07366", review_id=6)
    mock_db = MockAsyncSession(papers=[p])

    state: AgentState = {
        "review_id": 6,
        "extracted_pdf_contents": {
            "9999": {  # Numeric key does not match id=33
                "arxiv_id": "1806.07366",  # Resolves via valid arXiv ID
                "abstract": "We introduce a new family of deep neural network models.",
            }
        },
    }

    result = await vector_embedding_node(state, db=mock_db)
    assert result["chunks_stored_count"] == 1
    assert mock_db.added_chunks[0].paper_id == 33


# ==============================================================================
# 3. Section Heading Preservation Tests
# ==============================================================================


def test_section_heading_acronyms_preserved():
    """Verify that scientific acronyms and mixed case in section headings are preserved."""
    assert format_section_name("LLM Evaluation") == "LLM Evaluation"
    assert format_section_name("RNA-Seq Analysis") == "RNA-Seq Analysis"
    assert format_section_name("CNN vs ViT Performance") == "CNN vs ViT Performance"
    assert format_section_name("COVID-19 Patient Cohort") == "COVID-19 Patient Cohort"
    assert format_section_name("GPT-4 Zero-Shot Results") == "GPT-4 Zero-Shot Results"
    assert format_section_name("Section 3.2: CRISPR-Cas9") == "Section 3.2: CRISPR-Cas9"


def test_lowercase_section_headings_capitalized():
    """Verify that purely lowercase section headings from automated extractors are title-cased."""
    assert format_section_name("abstract") == "Abstract"
    assert format_section_name("introduction") == "Introduction"
    assert format_section_name("methods and materials") == "Methods And Materials"
    assert format_section_name("results and discussion") == "Results And Discussion"
    assert format_section_name("limitations") == "Limitations"
    assert format_section_name("conclusion") == "Conclusion"


@pytest.mark.asyncio
async def test_chunk_paper_sections_preserves_acronym_headings():
    """Verify that chunk_paper_sections retains exact scientific acronyms."""
    sections = {
        "LLM Evaluation": "Evaluating large language models under uncertainty.",
        "RNA-Seq Methodology": "Sequencing pipelines using standard Illumina protocol.",
    }
    chunks = chunk_paper_sections(sections, chunk_size=500, overlap=50)

    section_names = {c["section_name"] for c in chunks}
    assert "LLM Evaluation" in section_names
    assert "RNA-Seq Methodology" in section_names


# ==============================================================================
# 4. Chunking Boundary Tests
# ==============================================================================


def test_chunking_boundaries_length_0():
    """Verify that length 0 returns empty chunk list."""
    assert chunk_text("", chunk_size=500, overlap=50) == []
    assert chunk_text("   \n\t ", chunk_size=500, overlap=50) == []


def test_chunking_boundaries_length_1_to_500():
    """Verify single chunk for text lengths <= 500 characters."""
    for length in (1, 49, 50, 499, 500):
        text = "X" * length
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert len(chunks[0]["content"]) == length
        assert chunks[0]["chunk_index"] == 0


def test_chunking_boundaries_length_501_to_551():
    """Verify two overlapping chunks for text lengths 501 through 551."""
    for length in (501, 550, 551):
        text = ("A" * 450) + ("O" * 50) + ("B" * (length - 500))
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 2, f"Failed for length={length}"
        assert len(chunks[0]["content"]) == 500
        assert len(chunks[1]["content"]) == length - 450
        assert chunks[0]["chunk_index"] == 0
        assert chunks[1]["chunk_index"] == 1
        # Overlap region check
        assert "O" * 50 in chunks[0]["content"]
        assert "O" * 50 in chunks[1]["content"]


def test_chunking_boundaries_length_1000_and_1001():
    """Verify three chunks for text lengths 1000 and 1001."""
    for length in (1000, 1001):
        text = "Z" * length
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 3, f"Failed for length={length}"
        assert len(chunks[0]["content"]) == 500
        assert len(chunks[1]["content"]) == 500
        assert len(chunks[2]["content"]) == length - 900


# ==============================================================================
# 5. Idempotency, Concurrency, and Error Handling Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_sequential_retry_idempotent():
    """Verify sequential node execution replaces existing chunks without duplication."""
    p = Paper(id=1, title="Idempotency Test Paper", arxiv_id="2401.00001", review_id=2)
    mock_db = MockAsyncSession(papers=[p])

    state: AgentState = {
        "review_id": 2,
        "extracted_pdf_contents": {
            "2401.00001": {
                "abstract": "First run abstract text.",
            }
        },
    }

    # Run 1
    res1 = await vector_embedding_node(state, db=mock_db)
    assert res1["chunks_stored_count"] == 1
    assert len(mock_db.added_chunks) == 1

    # Clear mock session added list to simulate existing DB state
    mock_db.added_chunks.clear()

    # Run 2 (retry)
    res2 = await vector_embedding_node(state, db=mock_db)
    assert res2["chunks_stored_count"] == 1
    assert len(mock_db.added_chunks) == 1
    assert mock_db.with_for_update_called is True


@pytest.mark.asyncio
async def test_sentence_transformer_unavailable_raises_fail_fast():
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
async def test_empty_extracted_pdf_contents_returns_zero():
    """Verify empty or None extracted_pdf_contents returns 0 chunks stored."""
    state_empty: AgentState = {"review_id": 1, "extracted_pdf_contents": {}}
    result = await vector_embedding_node(state_empty)
    assert result["current_step"] == "vector_embedding_completed"
    assert result["chunks_stored_count"] == 0

    state_none: AgentState = {"review_id": 1, "extracted_pdf_contents": None}
    result_none = await vector_embedding_node(state_none)
    assert result_none["current_step"] == "vector_embedding_completed"
    assert result_none["chunks_stored_count"] == 0


@pytest.mark.asyncio
async def test_embedding_dimensions_exactly_384():
    """Verify all persisted chunks have embeddings with exactly 384 dimensions."""
    db_paper = Paper(id=99, title="Dimension Test", arxiv_id="2401.99999", review_id=12)
    mock_db = MockAsyncSession(papers=[db_paper])

    state: AgentState = {
        "review_id": 12,
        "extracted_pdf_contents": {
            "2401.99999": {"abstract": "Validating output vector dimensions."}
        },
    }

    result = await vector_embedding_node(state, db=mock_db)
    assert result["chunks_stored_count"] == 1
    chunk = mock_db.added_chunks[0]
    assert len(chunk.embedding) == EMBEDDING_DIMENSION
    assert len(chunk.embedding) == 384


def test_normalization_helpers():
    """Unit tests for identifier and title normalization helpers."""
    assert _normalize_identifier("arXiv:2301.12345v3") == "2301.12345v3"
    assert _strip_version("2301.12345v3") == "2301.12345"
    assert _normalize_identifier("DOI:10.1000/182") == "10.1000/182"
    assert _normalize_identifier("PMID:12345678") == "12345678"
    assert _normalize_title("Attention Is All You Need!!!\n\t") == "attention is all you need"


@pytest.mark.asyncio
async def test_multiple_entries_same_paper_grouped_and_preserved():
    """Verify that multiple extracted entries resolving to the same paper are grouped
    before replacement, preserving sections across both entries and persisting chunks once.
    """
    db_paper = Paper(
        id=77,
        title="Federated Learning Survey",
        arxiv_id="2301.77777",
        review_id=5,
    )
    mock_db = MockAsyncSession(papers=[db_paper])

    # Two entries resolving to the same paper: one by arXiv ID, one by URL
    state: AgentState = {
        "review_id": 5,
        "extracted_pdf_contents": {
            "2301.77777": {
                "sections": {
                    "Introduction": "Federated learning enables collaborative model training."
                }
            },
            "https://arxiv.org/abs/2301.77777": {
                "sections": {
                    "Methodology": "Clients perform local SGD iterations and transmit parameter deltas."
                }
            },
        },
    }

    result = await vector_embedding_node(state, db=mock_db)
    assert result["current_step"] == "vector_embedding_completed"
    assert result["chunks_stored_count"] == 2

    # Verify both sections are present in stored chunks
    section_names = {c.section_name for c in mock_db.added_chunks}
    assert "Introduction" in section_names
    assert "Methodology" in section_names


# ==============================================================================
# 6. Dedicated Integration Test (Real SentenceTransformer Model)
# ==============================================================================


def test_real_sentence_transformer_integration():
    """Integration test verifying real all-MiniLM-L6-v2 inference when installed."""
    st = pytest.importorskip("sentence_transformers")
    model = st.SentenceTransformer("all-MiniLM-L6-v2")
    vec = model.encode(
        "Real sentence-transformers integration test sentence.", convert_to_numpy=True
    )
    assert len(vec) == 384
    norm = sum(x * x for x in vec) ** 0.5
    assert pytest.approx(norm, rel=1e-3) == 1.0
