# 📁 Role-Wise Execution Workbooks Index

This directory contains individual, step-by-step role-wise workbooks for each task in the **Multi-Agent Academic Research & Literature Review Assistant** system.

---

## 👥 10-Member Role Allocation & Workbook Directory

| Task / Role | Responsible Member | Owned Module & Files | Detail Workbook |
| :--- | :--- | :--- | :--- |
| **01. LangGraph Core State & Graph Orchestration** | Member 1 (Lead Orchestrator) | `backend/app/graph/` | [01_langgraph_core_orchestration.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/01_langgraph_core_orchestration.md) |
| **02. Academic Search & Retrieval Agent** | Member 2 | `backend/app/agents/search_agent.py`, `backend/app/services/academic_apis/` | [02_search_retrieval_agent.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/02_search_retrieval_agent.md) |
| **03. Document Processing & Vector RAG Pipeline** | Member 3 | `backend/app/services/pdf_service.py`, `backend/app/services/vector_store.py` | [03_document_ingestion_rag.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/03_document_ingestion_rag.md) |
| **04. Summarizer Agent & Structured Outputs** | Member 4 | `backend/app/agents/summarizer_agent.py`, `backend/app/prompts/` | [04_summarizer_agent.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/04_summarizer_agent.md) |
| **05. Synthesis & Literature Gap Analysis Agent** | Member 5 | `backend/app/agents/synthesis_agent.py`, `backend/app/services/synthesis_engine.py` | [05_synthesis_gap_agent.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/05_synthesis_gap_agent.md) |
| **06. Citation & Bibliography Export Engine** | Member 6 | `backend/app/agents/citation_agent.py`, `backend/app/services/exporter.py` | [06_citation_bibliography_agent.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/06_citation_bibliography_agent.md) |
| **07. Database & Redis Caching Architect** | Member 7 | `backend/app/models/`, `backend/app/core/db.py`, `backend/app/core/redis.py` | [07_database_cache_architect.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/07_database_cache_architect.md) |
| **08. FastAPI REST Endpoints & Interactive RAG Chat** | Member 8 | `backend/app/api/`, `backend/app/agents/rag_chat_agent.py` | [08_fastapi_backend_rag_chat.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/08_fastapi_backend_rag_chat.md) |
| **09. Cloud Infrastructure, Docker & CI/CD** | Member 9 | `Dockerfile`, `docker-compose.yml`, `terraform/`, `.github/workflows/` | [09_devops_cloud_infra.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/09_devops_cloud_infra.md) |
| **10. Pytest Test Suites, Load Testing & Analytics** | Member 10 | `backend/tests/`, `locustfile.py`, `backend/app/analytics/` | [10_testing_analytics_viz.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/docs/role-wise-docs/10_testing_analytics_viz.md) |

---

## 📐 Directory Structure & Modification Rules

### 1. Source Code Location (`backend/app/`)
All application Python code **must** live inside `backend/app/`.
- **Can team members create subfolders inside `backend/app/`?** **Yes!** Developers can create sub-packages (e.g. `backend/app/services/pdf_parser/` or `backend/app/agents/sub_agents/`).
- **Rule:** Every new folder inside `backend/app/` **must** include an `__init__.py` file so Python treats it as a package.

### 2. Test Suite Location (`backend/tests/`)
All test files **must** live inside `backend/tests/`.
- **Naming Rule:** Every test file name **must start with `test_`** (e.g., `test_search_agent.py`, `test_vector_store.py`).
- **Why?** Pytest and our pre-commit hook are configured to automatically search `backend/tests/` for files starting with `test_`. If a file is named `search_test.py` or placed outside `backend/tests/`, Pytest will ignore it.

### 3. Modifying Top-Level Folders
- Top-level root folders (`backend/`, `docs/`, `.github/`) are standard across the project.
- Please do **not** rename or move `backend/app/` or `backend/tests/` because `pyproject.toml`, `.pre-commit-config.yaml`, and `.github/workflows/ci.yml` target these exact paths!
