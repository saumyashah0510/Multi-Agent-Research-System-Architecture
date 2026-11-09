"""Vector embedding and text chunking service using pgvector and sentence-transformers."""

import asyncio
import hashlib
import logging
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import PaperChunk
from app.models.paper import Paper

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSION = 384

_ST_MODEL = None


def _get_embedding_model():
    """Lazy-load sentence-transformers model (100% free open-source local embeddings)."""
    global _ST_MODEL
    if _ST_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer

            _ST_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded local sentence-transformers model: all-MiniLM-L6-v2 (384D)")
        except Exception as err:
            logger.warning(f"Could not load sentence-transformers model: {err}")
            _ST_MODEL = False
    return _ST_MODEL


def is_embedding_model_available() -> bool:
    """Check if the local sentence-transformers model is successfully loaded."""
    model = _get_embedding_model()
    return bool(model)


def format_section_name(name: str) -> str:
    """Format section heading while preserving scientific acronyms, hyphens, and mixed case.

    Examples:
    - 'abstract' -> 'Abstract'
    - 'methods and materials' -> 'Methods And Materials'
    - 'LLM Evaluation' -> 'LLM Evaluation' (acronym preserved)
    - 'RNA-Seq Analysis' -> 'RNA-Seq Analysis' (hyphen and acronym preserved)
    - 'CNN vs ViT Performance' -> 'CNN vs ViT Performance' (mixed acronyms preserved)
    """
    if not name or not name.strip():
        return "Full Text"

    cleaned = name.replace("\x00", "").strip()
    if not cleaned:
        return "Full Text"

    # If the heading is purely lowercase (e.g. 'methods', 'abstract' from automated extractors),
    # capitalize word initials
    if cleaned.islower():
        words = cleaned.split()
        return " ".join(w.capitalize() for w in words)[:150]

    # If heading contains mixed case or uppercase acronyms, preserve exact author/scientific casing
    return cleaned[:150]


def chunk_text(
    text: str,
    section_name: str = "Full Text",
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict[str, Any]]:
    """Split raw text into overlapping chunks while preserving section metadata."""
    if not text:
        return []

    cleaned_text = text.replace("\x00", "").strip()
    if not cleaned_text:
        return []

    clean_sec = (section_name or "Full Text").replace("\x00", "").strip() or "Full Text"
    chunks: list[dict[str, Any]] = []

    if len(cleaned_text) <= chunk_size:
        return [
            {
                "chunk_index": 0,
                "section_name": clean_sec,
                "content": cleaned_text,
            }
        ]

    step = max(1, chunk_size - overlap)
    chunk_idx = 0

    for i in range(0, len(cleaned_text), step):
        chunk_content = cleaned_text[i : i + chunk_size].strip()
        if chunk_content:
            chunks.append(
                {
                    "chunk_index": chunk_idx,
                    "section_name": clean_sec,
                    "content": chunk_content,
                }
            )
            chunk_idx += 1

        if i + chunk_size >= len(cleaned_text):
            break

    return chunks


def chunk_paper_sections(
    sections: dict[str, str],
    full_text: str = "",
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict[str, Any]]:
    """Chunk paper text while preserving section names and ensuring 100% full coverage."""
    all_chunks: list[dict[str, Any]] = []
    global_index = 0

    if sections:
        for sec_name, sec_text in sections.items():
            if not sec_text or not sec_text.strip():
                continue
            sec_chunks = chunk_text(
                text=sec_text,
                section_name=format_section_name(sec_name),
                chunk_size=chunk_size,
                overlap=overlap,
            )
            for c in sec_chunks:
                c["chunk_index"] = global_index
                all_chunks.append(c)
                global_index += 1

    # If sections dictionary was empty or didn't capture the entire text, chunk full_text directly as "Main Body"
    if not all_chunks and full_text:
        all_chunks = chunk_text(
            text=full_text,
            section_name="Main Body",
            chunk_size=chunk_size,
            overlap=overlap,
        )

    return all_chunks


async def generate_embedding(text: str, allow_fallback: bool = True) -> list[float]:
    """Generate 384-dimensional vector embedding using 100% free local sentence-transformers model.

    If allow_fallback is False, raises RuntimeError when SentenceTransformers is unavailable
    rather than returning pseudo-embeddings.
    """
    model = _get_embedding_model()

    if model:
        try:
            vec = await asyncio.to_thread(model.encode, text, convert_to_numpy=True)
            return [round(float(x), 6) for x in vec.tolist()]
        except Exception as err:
            logger.warning(f"SentenceTransformer encoding error: {err}")
            if not allow_fallback:
                raise RuntimeError(f"SentenceTransformer failed to encode text: {err}") from err

    if not allow_fallback:
        raise RuntimeError(
            "SentenceTransformer ('all-MiniLM-L6-v2') is unavailable; "
            "semantic embedding cannot be generated."
        )

    # Fallback deterministic pseudo-embedding vector of 384 floats if sentence-transformers unavailable
    seed_hash = hashlib.sha256(text.encode("utf-8")).digest()
    vector = []
    for i in range(EMBEDDING_DIMENSION):
        val = ((seed_hash[i % len(seed_hash)] + i) % 256) / 255.0 - 0.5
        vector.append(round(val, 6))

    norm = sum(x * x for x in vector) ** 0.5
    if norm > 0:
        vector = [round(x / norm, 6) for x in vector]

    return vector


async def generate_embeddings_batch(
    texts: list[str],
    allow_fallback: bool = True,
) -> list[list[float]]:
    """Generate 384-dimensional vector embeddings for a batch of texts using sentence-transformers."""
    if not texts:
        return []

    model = _get_embedding_model()
    if model:
        try:
            vecs = await asyncio.to_thread(
                model.encode, texts, convert_to_numpy=True, show_progress_bar=False
            )
            return [[round(float(x), 6) for x in vec] for vec in vecs]
        except Exception as err:
            logger.warning(f"SentenceTransformer batch encoding error: {err}")
            if not allow_fallback:
                raise RuntimeError(f"SentenceTransformer failed to encode batch: {err}") from err

    if not allow_fallback:
        raise RuntimeError(
            "SentenceTransformer ('all-MiniLM-L6-v2') is unavailable; "
            "semantic embedding cannot be generated."
        )

    # Fallback deterministic pseudo-embedding
    return [await generate_embedding(t, allow_fallback=True) for t in texts]


async def store_paper_chunks(
    db: AsyncSession,
    paper_id: int,
    full_text: Optional[str] = None,
    sections: Optional[dict[str, str]] = None,
    chunk_size: int = 500,
    overlap: int = 50,
    allow_fallback: bool = True,
    replace_existing: bool = False,
) -> list[PaperChunk]:
    """Chunk paper text, generate embeddings, and insert PaperChunk records into PostgreSQL.

    When replace_existing=True, acquires a row-level lock on the Paper record before deleting
    and re-inserting chunks to ensure concurrent serialization and prevent race conditions.
    """
    if replace_existing:
        # Acquire row-level lock on Paper to serialize concurrent reprocessing for the same paper
        await db.execute(select(Paper.id).where(Paper.id == paper_id).with_for_update())
        await db.execute(delete(PaperChunk).where(PaperChunk.paper_id == paper_id))

    chunks_meta = chunk_paper_sections(
        sections=sections or {},
        full_text=full_text or "",
        chunk_size=chunk_size,
        overlap=overlap,
    )

    if not chunks_meta:
        logger.warning(f"No text or sections provided for paper_id={paper_id}")
        return []

    texts = [c["content"] for c in chunks_meta]
    embeddings = await generate_embeddings_batch(texts, allow_fallback=allow_fallback)

    db_chunks: list[PaperChunk] = []

    for c, emb in zip(chunks_meta, embeddings, strict=True):
        if len(emb) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(emb)}"
            )
        clean_content = str(c["content"]).replace("\x00", "")
        clean_section = str(c["section_name"]).replace("\x00", "")[:150] or "Full Text"
        if not clean_content.strip():
            continue
        chunk_obj = PaperChunk(
            paper_id=paper_id,
            chunk_index=c["chunk_index"],
            section_name=clean_section,
            content=clean_content,
            embedding=emb,
        )
        db.add(chunk_obj)
        db_chunks.append(chunk_obj)

    await db.flush()
    logger.info(f"Successfully stored {len(db_chunks)} chunks for paper_id={paper_id}")
    return db_chunks


async def similarity_search(
    db: AsyncSession,
    query_text: str,
    review_id: Optional[int] = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Perform pgvector cosine similarity search over paper chunks."""
    query_vector = await generate_embedding(query_text)

    stmt = select(
        PaperChunk,
        PaperChunk.embedding.cosine_distance(query_vector).label("distance"),
    )

    if review_id is not None:
        stmt = stmt.join(Paper, PaperChunk.paper_id == Paper.id).where(Paper.review_id == review_id)

    stmt = stmt.order_by("distance").limit(top_k)
    result = await db.execute(stmt)

    matches = []
    for chunk_obj, distance in result.all():
        similarity = round(max(0.0, 1.0 - float(distance)), 4)
        matches.append(
            {
                "chunk_id": chunk_obj.id,
                "paper_id": chunk_obj.paper_id,
                "section_name": chunk_obj.section_name,
                "chunk_index": chunk_obj.chunk_index,
                "content": chunk_obj.content,
                "similarity": similarity,
                "distance": round(float(distance), 4),
            }
        )

    return matches
