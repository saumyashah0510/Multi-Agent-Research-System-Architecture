"""Unit tests for LangGraph Checkpointer Factory (Issue BE-15)."""

import pytest
from app.agents.checkpointer import get_checkpointer
from app.agents.orchestrator import build_literature_review_graph
from langgraph.checkpoint.memory import MemorySaver


def test_checkpointer_force_memory():
    """Verify that force_memory=True returns a valid MemorySaver instance."""
    checkpointer = get_checkpointer(force_memory=True)
    assert isinstance(checkpointer, MemorySaver)


def test_orchestrator_compiles_with_custom_checkpointer():
    """Verify that build_literature_review_graph accepts and compiles with a custom checkpointer."""
    custom_saver = MemorySaver()
    compiled_graph = build_literature_review_graph(checkpointer=custom_saver)
    assert compiled_graph is not None
    assert hasattr(compiled_graph, "checkpointer")
    assert compiled_graph.checkpointer is custom_saver


@pytest.mark.skip(reason="Assignee will unskip upon implementing AsyncPostgresSaver in BE-15")
@pytest.mark.asyncio
async def test_postgres_checkpointer_snapshot_persistence():
    """Verify state snapshot writing and retrieval using AsyncPostgresSaver."""
    # Assignee will verify checkpoint save and load across pipeline thread IDs
    pass
