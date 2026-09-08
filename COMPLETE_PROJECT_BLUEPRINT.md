# 🎓 Multi-Agent Academic Research & Literature Review Assistant
## Complete Project Blueprint, Website Flow, System Architecture & Role Guide

> **100% Free & Open-Source Verification:** This entire project is designed to run at **$0 cost**. All APIs (arXiv, Semantic Scholar, Crossref), databases (PostgreSQL + pgvector in Docker), caching (Redis in Docker), embeddings (`sentence-transformers`), LLM options (Groq free tier / Gemini free API / local Ollama), and frameworks are 100% free open-source tools.

---

## 🌐 PART 1: How the Website Works (User Journey & UI Flow)

Imagine an end-user opening the application in their browser. Here is the step-by-step experience:

```
 ┌──────────────────────────┐      ┌──────────────────────────┐      ┌──────────────────────────┐
 │  STEP 1: SUBMIT TOPIC    │      │ STEP 2: HUMAN REVIEW UI  │      │ STEP 3: READ SYNTHESIS   │
 │ User enters research     │ ───> │ User views paper cards,  │ ───> │ User views literature    │
 │ topic & search scope     │      │ approves/flags papers    │      │ review report & matrix   │
 └──────────────────────────┘      └──────────────────────────┘      └─────────────┬────────────┘
                                                                                   │
                                                                                   ▼
                                                                     ┌──────────────────────────┐
                                                                     │  STEP 4: RAG CHAT Q&A    │
                                                                     │ User asks questions over │
                                                                     │ literature in chat box   │
                                                                     └──────────────────────────┘
```

### Step 1: Research Topic Submission
1. The user opens the website homepage.
2. They type a research topic (e.g., *"Transformers in Medical Image Segmentation"*).
3. They select options (e.g., search limit: 10 papers, target citation style: APA).
4. They click **Start Literature Review**.

### Step 2: Human-in-the-Loop Review Dashboard
1. The backend automatically queries academic APIs, fetches paper metadata, and downloads PDFs.
2. The pipeline **pauses** automatically, and the UI presents an interactive **Paper Review Dashboard**.
3. The user sees 10 paper cards displaying: Title, Authors, Publication Year, Abstract, and PDF Link.
4. The user clicks **Approve ✅** on 6 relevant papers and **Reject ❌** on 4 irrelevant ones.
5. The user clicks **Proceed with Approved Papers**.

### Step 3: Automated Literature Review & Report Generation
1. The system resumes execution on the 6 approved papers.
2. The user sees a real-time progress bar while the AI agents summarize key findings, synthesize contradictory evidence, and build citation bibliographies.
3. The user is presented with a formatted **Literature Review Report** containing:
   - **Paper Summaries Table** (Methodology, Dataset, Findings, Limitations).
   - **Synthesis Matrix** (Points of Agreement vs Contradictory Claims across papers).
   - **Open Research Gaps** (Unanswered questions highlighted by authors).
   - **Formatted References** (APA, IEEE, Harvard, BibTeX) with a **Download Report (PDF / Markdown / BibTeX)** button.

### Step 4: Interactive RAG Q&A Chat
1. Beneath the report, an interactive **RAG Chat Window** appears.
2. The user can type follow-up questions (e.g., *"Which paper used the BraTS 2023 dataset and achieved the highest Dice score?"*).
3. The RAG Chat agent searches the vectorized PDF chunks and returns precise answers with inline citations.

---

## ⚙️ PART 2: How the System Works Internally (Under the Hood)

Behind the web interface, **LangGraph** coordinates a stateful multi-agent state machine where data flows cleanly from node to node:

```
                       ┌────────────────────────┐
                       │  User Inputs Research  │
                       │    Topic & Scope       │
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │ 1. Search & Fetch Node │
                       │ (arXiv, Semantic Schol)│
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │ 2. Ingestion RAG Node  │
                       │ (PDF Parsing, Embeds)  │
                       └───────────┬────────────┘
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │ ⏸️ HUMAN-IN-THE-LOOP INTERRUPT    │
                 │ State pauses for user paper review│
                 └─────────────────┬─────────────────┘
                                   │ (Approved Papers Only)
                                   ▼
                       ┌────────────────────────┐
                       │  3. Summarizer Agent   │
                       │ (Method, Data, Findings│
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │   4. Synthesis Agent   │
                       │ (Agreements & Gaps)    │
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │   5. Citation Agent    │
                       │ (BibTeX, APA, IEEE)    │
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │ 6. Interactive RAG Chat│
                       │  (Q&A Vector Search)   │
                       └────────────────────────┘
```

1. **Shared Graph State (`ResearchState`)**: Every node reads and updates a central state dictionary containing `topic`, `retrieved_papers`, `approved_papers`, `summaries`, `synthesis_report`, `citations`, and `chat_history`.
2. **Interrupt Mechanics (`interrupt_before=["human_review"]`)**: LangGraph checkpoints state into Redis/MemorySaver before `human_review`. When the user submits approvals via REST API, the checkpointer loads the state and resumes execution seamlessly.
3. **Vector RAG Pipeline**: PDF text is split into 500-token chunks with 50-token overlaps, embedded via HuggingFace `sentence-transformers`, and stored in PostgreSQL with HNSW indexes for sub-millisecond similarity search.

---

## 🛠️ PART 3: Flexible & Changeable Tech Stack ($0 Cost)

All technologies listed below are **100% free** and can be swapped based on team preference:

| Component | Default Free Option | Changeable Alternatives |
| :--- | :--- | :--- |
| **Agent Orchestration** | **LangGraph + LangChain** (Python) | AutoGen, CrewAI, LlamaIndex Workflows |
| **Backend API** | **FastAPI** (Python 3.11) | Flask, Django REST, Express.js |
| **Frontend UI** | **React / Next.js** (Tailwind CSS) | Streamlit, Vue.js, Vite React |
| **LLM Inference** | **Groq API Free Tier / Gemini Free API** | Local Ollama (Llama 3 / Mistral), Hugging Face Inference |
| **Embeddings Model** | **HuggingFace `sentence-transformers`** | OpenAI `text-embedding-3-small`, FastEmbed |
| **Database & Vector DB** | **PostgreSQL + pgvector** (via Docker) | Neon free tier, Supabase free tier, ChromaDB, Qdrant |
| **State Cache** | **Redis** (via Docker) | Upstash Redis, Local In-Memory Dict |
| **PDF Extraction** | **PyPDF / pypdf** | Unstructured, pdfplumber, PyMuPDF |
| **Container & CI/CD** | **Docker Compose + GitHub Actions** | Local Python venv, Render free tier |

---

## 👥 PART 4: Role-Wise Breakdown & Task Allocation

To accommodate both **Domain Specialist Teams** and **10-Member Task Teams**, here are the two clean breakdown structures:

---

### Option A: 5-Domain Specialist Breakdown (High-Level Roles)

```
 ┌───────────────────────────┐      ┌───────────────────────────┐
 │   1. FRONTEND DEVELOPER   │      │   2. BACKEND & API DEV    │
 │ (UI Dashboard, Paper Cards│      │ (FastAPI REST Routes,     │
 │  Review Buttons, Chat UI) │      │  Session State, Endpoints)│
 └─────────────┬─────────────┘      └─────────────┬─────────────┘
               │                                  │
 ┌─────────────▼─────────────┐      ┌─────────────▼─────────────┐
 │  3. DATABASE & VECTOR ENG │      │ 4. AI AGENTS & LANGGRAPH  │
 │ (PostgreSQL+pgvector,     │      │ (Search, Ingestion,       │
 │  Redis Caching, Models)   │      │  Summarizer, Synthesis)   │
 └───────────────────────────┘      └─────────────┬─────────────┘
                                                  │
                                    ┌─────────────▼─────────────┐
                                    │ 5. DEVOPS & QA ENGINEER   │
                                    │ (Docker Compose, CI/CD,   │
                                    │  Pre-commit, Pytest)      │
                                    └───────────────────────────┘
```

#### 👤 Domain Role 1: Frontend UI Developer (The Face)
- **Primary Goal:** Build the web dashboard for research topic input, paper review cards, report viewing, and interactive RAG chat.
- **Owned Scope:** `frontend/` (Next.js / React app or Streamlit UI).
- **Deliverables:** Topic form component, Paper review card grid with Approve/Reject toggles, Report markdown renderer, Chat drawer component.

#### 👤 Domain Role 2: Backend API Developer (The Connector)
- **Primary Goal:** Build FastAPI REST API routes connecting the Frontend UI to the LangGraph AI orchestrator.
- **Owned Scope:** `backend/app/api/`.
- **Deliverables:** `POST /api/v1/research/start`, `POST /api/v1/research/review`, `GET /api/v1/research/{id}/status`, `POST /api/v1/chat/query`.

#### 👤 Domain Role 3: AI Agents & LangGraph Specialist (The Brain)
- **Primary Goal:** Build the LangGraph state machine workflow and individual AI agent nodes.
- **Owned Scope:** `backend/app/graph/`, `backend/app/agents/`, `backend/app/prompts/`.
- **Deliverables:** Shared `ResearchState`, Human-in-the-loop interrupt mechanics, Search agent, Summarizer agent, Synthesis matrix engine, Citation formatter agent.

#### 👤 Domain Role 4: Database & Vector Engineer (The Memory)
- **Primary Goal:** Architect PostgreSQL schemas, pgvector vector storage, and Redis caching.
- **Owned Scope:** `backend/app/models/`, `backend/app/core/db.py`, `backend/app/core/redis.py`, `backend/app/services/vector_store.py`.
- **Deliverables:** SQLAlchemy ORM models, HNSW vector indexing, similarity search service, Redis state checkpointer.

#### 👤 Domain Role 5: DevOps & QA Engineer (The Shield)
- **Primary Goal:** Maintain repository security gatekeepers, Docker containerization, CI/CD pipelines, and Pytest test suites.
- **Owned Scope:** `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `backend/tests/`.
- **Deliverables:** Docker Compose configuration, passing GitHub Actions CI pipeline, master Pytest suite.

---

### Option B: 10-Task Granular Allocation (1 Task Per Member)

| Task / Role | Responsible Member | Owned Files & Scope | Core Deliverables |
| :--- | :--- | :--- | :--- |
| **01. LangGraph Core State Orchestrator** | Member 1 (Lead Orchestrator) | `backend/app/graph/state.py`<br>`backend/app/graph/workflow.py` | `ResearchState` schema, graph state machine, `interrupt_before=["human_review"]`. |
| **02. Academic Search & Retrieval Agent** | Member 2 | `backend/app/agents/search_agent.py`<br>`backend/app/services/academic_apis/` | arXiv & Semantic Scholar API clients, query expansion, metadata normalization. |
| **03. Document Processing & Vector RAG** | Member 3 | `backend/app/services/pdf_service.py`<br>`backend/app/services/vector_store.py` | PDF parsing, text cleaning, semantic chunking, pgvector embedding indexer. |
| **04. Summarizer Agent & Structured Output** | Member 4 | `backend/app/agents/summarizer_agent.py`<br>`backend/app/prompts/summarizer_prompts.py` | Structured Pydantic extraction (methodology, dataset, findings, limitations). |
| **05. Synthesis & Literature Gap Agent** | Member 5 | `backend/app/agents/synthesis_agent.py`<br>`backend/app/services/synthesis_engine.py` | Multi-document comparison matrix (agreements, contradictions, open research gaps). |
| **06. Citation Agent & Exporter Engine** | Member 6 | `backend/app/agents/citation_agent.py`<br>`backend/app/services/exporter.py` | Citation formatters (APA, IEEE, Harvard, BibTeX), PDF/Markdown/JSON exporter. |
| **07. Database & Redis Architect** | Member 7 | `backend/app/models/`<br>`backend/app/core/db.py`<br>`backend/app/core/redis.py` | PostgreSQL ORM schemas, pgvector HNSW index setup, Redis state cache. |
| **08. FastAPI REST Endpoints & RAG Chat** | Member 8 | `backend/app/api/`<br>`backend/app/agents/rag_chat_agent.py` | REST API routes (`/start`, `/review`, `/status`), RAG Q&A chat agent. |
| **09. Cloud Infra, Docker & CI/CD** | Member 9 | `Dockerfile`<br>`docker-compose.yml`<br>`.github/workflows/ci.yml` | Multi-stage Dockerfile, docker-compose stack, GitHub Actions CI automation. |
| **10. Pytest Suite, Load Tests & Analytics** | Member 10 | `backend/tests/`<br>`locustfile.py`<br>`backend/app/analytics/` | Master Pytest test runner, Locust performance load testing, paper network graphs. |

---

## 🛠️ Summary of Workspace Folder Structure

```
Multi-Agent-Research-System-Architecture/
├── .gitignore                          # Excludes venv, secrets (.env), caches
├── .pre-commit-config.yaml              # Local git hook security & quality gatekeeper
├── pyproject.toml                       # Tool settings (Ruff, Black, Pytest, Bandit)
├── requirements.txt                     # Base dev, security & testing dependencies
├── AGENTS.md                            # Persistent AI agent instructions & rules
├── README.md                            # GitHub repository homepage
├── COMPLETE_PROJECT_BLUEPRINT.md        # Master complete project blueprint (This File)
├── .github/
│   └── workflows/
│       └── ci.yml                       # GitHub Actions cloud CI pipeline
├── docs/
│   ├── architecture_blueprint.md        # Technical component blueprint
│   └── role-wise-docs/                  # Step-by-step workbooks for tasks 1 to 10
│       ├── README.md                    # Workbooks index
│       ├── 01_langgraph_core_orchestration.md
│       ├── 02_search_retrieval_agent.md
│       ├── 03_document_ingestion_rag.md
│       ├── 04_summarizer_agent.md
│       ├── 05_synthesis_gap_agent.md
│       ├── 06_citation_bibliography_agent.md
│       ├── 07_database_cache_architect.md
│       ├── 08_fastapi_backend_rag_chat.md
│       ├── 09_devops_cloud_infra.md
│       └── 10_testing_analytics_viz.md
└── backend/
    ├── app/                             # Core Python application package
    │   └── __init__.py
    └── tests/                           # Master test suite directory
        ├── __init__.py
        └── test_placeholder.py          # Pre-commit test runner verification
```
