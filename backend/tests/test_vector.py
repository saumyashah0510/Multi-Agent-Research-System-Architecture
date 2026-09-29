"""Unit & integration tests for vector embedding and text chunking service."""

import pytest
from app.db.session import AsyncSessionLocal
from app.models.chunk import PaperChunk
from app.models.paper import Paper
from app.models.review import LiteratureReview
from app.models.user import User
from app.services.vector_service import (
    EMBEDDING_DIMENSION,
    chunk_paper_sections,
    chunk_text,
    generate_embedding,
    similarity_search,
    store_paper_chunks,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def test_chunk_text_basic():
    """Test text chunking with sliding window and overlap."""
    sample_text = (
        "Artificial Intelligence (AI) and Machine Learning (ML) are transforming academic research. "
        "Literature review automation enables rapid extraction of methodology, key findings, and future scope. "
        "By utilizing vector embeddings and pgvector database indexing, multi-agent frameworks perform semantic RAG."
    )

    chunks = chunk_text(sample_text, section_name="Abstract", chunk_size=100, overlap=20)

    assert len(chunks) > 1
    assert chunks[0]["section_name"] == "Abstract"
    assert chunks[0]["chunk_index"] == 0
    assert len(chunks[0]["content"]) <= 100
    assert "Artificial Intelligence" in chunks[0]["content"]


def test_chunk_paper_sections():
    """Test chunking distinct paper sections while retaining headings."""
    sections = {
        "Abstract": "This paper presents a multi-agent framework for academic reviews.",
        "Methodology": "We employ FastAPI, LangGraph, and PostgreSQL with pgvector for semantic search.",
    }

    chunks = chunk_paper_sections(sections, chunk_size=50, overlap=10)

    assert len(chunks) >= 2
    section_names = {c["section_name"] for c in chunks}
    assert "Abstract" in section_names
    assert "Methodology" in section_names


@pytest.mark.asyncio
async def test_generate_embedding_fallback():
    """Test embedding generation length and unit normalization in offline fallback mode."""
    text = "pgvector semantic similarity search test query"
    vec = await generate_embedding(text)

    assert isinstance(vec, list)
    assert len(vec) == EMBEDDING_DIMENSION

    # Verify unit norm length ~1.0
    norm = sum(x * x for x in vec) ** 0.5
    assert pytest.approx(norm, rel=1e-3) == 1.0


@pytest.fixture
async def async_session():
    """Async session fixture for integration tests ensuring extension & tables exist."""
    from app.db.base import Base
    from app.db.session import engine
    from sqlalchemy import text

    try:
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        pytest.skip(f"PostgreSQL database connection unavailable: {e}")

    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_store_paper_chunks_and_similarity_search(async_session: AsyncSession):
    """Integration test storing paper chunks in DB and performing pgvector similarity search."""
    db_session = async_session

    # 1. Create User, Review, and Paper
    user = User(email="vector_test@example.com", hashed_password="hashed_secret_test")
    db_session.add(user)
    await db_session.flush()

    review = LiteratureReview(user_query="pgvector RAG review", status="completed")
    db_session.add(review)
    await db_session.flush()

    paper = Paper(
        title="Deep Learning for Autonomous Literature Review",
        abstract="Deep learning models coupled with pgvector vector stores enable automated literature review.",
        review_id=review.id,
    )
    db_session.add(paper)
    await db_session.flush()

    # 2. Store Chunks
    sections = {
        "Abstract": "Deep learning models coupled with pgvector vector stores enable automated literature review.",
        "Methodology": "We implement PostgreSQL pgvector cosine similarity search for multi-agent synthesis.",
    }

    chunks = await store_paper_chunks(
        db_session, paper_id=paper.id, sections=sections, chunk_size=100, overlap=20
    )

    assert len(chunks) >= 2

    # Verify database persistence
    stmt = select(PaperChunk).where(PaperChunk.paper_id == paper.id)
    res = await db_session.execute(stmt)
    db_saved = res.scalars().all()
    assert len(db_saved) == len(chunks)

    # 3. Perform Similarity Search
    results = await similarity_search(
        db_session, query_text="PostgreSQL pgvector similarity search", review_id=review.id, top_k=2
    )

    assert len(results) > 0
    assert results[0]["paper_id"] == paper.id
    assert "similarity" in results[0]
    assert results[0]["similarity"] >= 0.0
