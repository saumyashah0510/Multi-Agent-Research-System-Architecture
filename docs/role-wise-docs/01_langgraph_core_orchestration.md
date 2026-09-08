# Role Workbook: Member 1 - LangGraph Core State & Graph Orchestration

## 📋 Role Overview & Scope
- **Role:** Lead Graph Orchestrator & State Machine Architect.
- **Goal:** Design the central `ResearchState` schema, build the LangGraph workflow graph, manage memory persistence, and implement the Human-in-the-Loop review interrupt.
- **Owned Files:**
  - `backend/app/graph/state.py`
  - `backend/app/graph/workflow.py`
  - `backend/tests/test_graph.py`

---

## 🎯 Step-by-Step Task Breakdown

### Task 1: Define `ResearchState` Schema (`backend/app/graph/state.py`)
- Store user research topic, query string, retrieved papers list, user-approved papers list, per-paper summaries dictionary, synthesis report, citations formatted list, and error tracking log.

### Task 2: Build LangGraph Workflow (`backend/app/graph/workflow.py`)
- Create state graph nodes: `search_node`, `ingestion_node`, `human_review`, `summarizer_node`, `synthesis_node`, `citation_node`.
- Configure `interrupt_before=["human_review"]` so execution pauses until user paper approval is received.
- Add checkpointer (MemorySaver / Redis checkpointer).

### Task 3: Unit Testing (`backend/tests/test_graph.py`)
- Write tests verifying state initialization, state updates across nodes, and graph interruption on `human_review`.
