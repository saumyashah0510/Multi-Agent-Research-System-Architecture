# Role Workbook: Member 8 - FastAPI REST API & Interactive RAG Chat

## 📋 Role Overview & Scope
- **Role:** FastAPI Backend Engineer & RAG Chat Developer.
- **Goal:** Build REST API endpoints for starting research runs, human review review/flagging, progress polling, and the interactive RAG Q&A chat endpoint.
- **Owned Files:**
  - `backend/app/api/v1/research.py`
  - `backend/app/api/v1/chat.py`
  - `backend/app/agents/rag_chat_agent.py`
  - `backend/tests/test_api_endpoints.py`

---

## 🎯 Step-by-Step Task Breakdown
1. REST endpoints:
   - `POST /api/v1/research/start` (trigger research topic run)
   - `POST /api/v1/research/review` (submit user paper approvals/rejections)
   - `GET /api/v1/research/{run_id}/status` (poll agent workflow state)
   - `POST /api/v1/chat/query` (interactive RAG Q&A over literature vector store)
2. OpenAPI / Swagger documentation specs.
3. FastAPI endpoint integration tests in `backend/tests/test_api_endpoints.py`.
