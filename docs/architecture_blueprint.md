# Conceptual Blueprint & System Architecture

This system is an autonomous, human-in-the-loop multi-agent AI pipeline designed to automate deep academic literature reviews.

Instead of a simple prompt-response chatbot, this platform uses **LangGraph** to coordinate a team of specialized AI agents. Each agent handles a specific phase of research—from querying academic APIs to chunking PDFs, synthesizing contradictory findings, generating formatted citations, and hosting an interactive RAG chat over the collected literature.

---

## 1. System Architecture & End-to-End Flow

```
                       ┌────────────────────────┐
                       │  User Inputs Research  │
                       │    Topic & Scope       │
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │  Search & Fetch Agent  │
                       │ (arXiv, Semantic Schol)│
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │ Ingestion & RAG Agent  │
                       │ (PDF parsing, Embeds)  │
                       └───────────┬────────────┘
                                   │
                                   ▼
                 ┌───────────────────────────────────┐
                 │ ⏸️ HUMAN-IN-THE-LOOP REVIEW STEP  │
                 │ User approves/flags relevant paper│
                 └─────────────────┬─────────────────┘
                                   │ (Approved Papers Only)
                                   ▼
                       ┌────────────────────────┐
                       │    Summarizer Agent    │
                       │ (Per-paper key findings│
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │    Synthesis Agent     │
                       │(Agreements, Gaps, Contr│
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │    Citation Agent      │
                       │(BibTeX, APA, IEEE form)│
                       └───────────┬────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │  Interactive RAG Chat  │
                       │  (Q&A over research)   │
                       └────────────────────────┘
```

---

## 2. Core System Components

### 1. LangGraph Orchestrator (The Agent Coordinator)
- **What it does:** Manages state across all agents. It acts as a central graph state machine where every paper, summary, vector ID, and user decision is stored in a shared `ResearchState`.
- **Key Feature (Human-in-the-Loop Interrupts):** When papers are fetched and indexed, the pipeline pauses cleanly (`interrupt_before=["human_review"]`). The user sees a list of retrieved papers with abstracts, clicks to flag/reject irrelevant ones, and triggers downstream execution.

### 2. Search & Retrieval Agent
- **What it does:** Converts user research topics into optimal academic search queries. Pulls metadata and PDFs via APIs like arXiv and Semantic Scholar.

### 3. Ingestion & RAG Agent
- **What it does:** Downloads paper PDFs, cleans raw text, splits them into semantic chunks, generates vector embeddings, and indexes them into PostgreSQL + pgvector.

### 4. Summarizer Agent
- **What it does:** Processes each approved paper to extract:
  - Primary research methodology & dataset used
  - Key quantitative findings & metrics
  - Limitations acknowledged by authors

### 5. Synthesis & Gap-Analysis Agent
- **What it does:** Cross-analyzes summaries across all papers to build a matrix of:
  - **Agreements:** Where multiple papers reach identical conclusions.
  - **Contradictions:** Where findings clash (e.g., Paper A claims method X outperforms Y, but Paper B claims the opposite).
  - **Research Gaps:** Unanswered questions or unexplored domains.

### 6. Citation & Bibliography Agent
- **What it does:** Formats all referenced papers into standardized styles (APA, IEEE, Harvard, BibTeX) and links inline citations back to source papers.

### 7. Interactive RAG Chat Agent
- **What it does:** Allows the user to ask follow-up questions about the literature review (e.g., *"What evaluation metrics did the papers in 2024 use?"*) using semantic search over the vectorized PDF chunks.

---

## 3. Technology Stack Mapping

| Layer | Tools Used | Purpose in Project |
| :--- | :--- | :--- |
| **Orchestration & Agents** | Python, LangChain, LangGraph | State graph, agent nodes, memory checkpointing, human-in-the-loop interrupts |
| **Backend API & Processing** | FastAPI (Python), Redis, Celery | Async API routes, job queues for long PDF parsing/embedding tasks, caching agent states |
| **Databases & Vectors** | PostgreSQL + pgvector, Redis | Relational data (papers, runs, reviews) + vector store for RAG similarity search |
| **Data & ML Processing** | NumPy, Pandas, scikit-learn, PyPDF | PDF text extraction, metadata tabular analysis, clustering paper topics |
| **Frontend UI** | React / Next.js or Streamlit | Dashboard for submitting topics, review UI for flagging papers, reading synthesized reports, and interactive chat |
| **Cloud & DevOps** | AWS (EC2, S3), Terraform, Docker, GitHub Actions | Infrastructure as Code (S3 for PDF storage, EC2 for background workers), containerized services |
| **Testing & Performance** | Pytest, Bandit, Ruff, Black, Pre-Commit | Unit/integration testing for agent state transitions, static security scanning, pre-commit gatekeepers |
