# Multi-Agent Academic Research & Literature Review Assistant 🎓🤖

An autonomous, human-in-the-loop multi-agent AI pipeline designed to automate deep academic literature reviews.

---

## 🌟 System Architecture & Pipeline Flow

Instead of a simple prompt-response chatbot, this platform uses **LangGraph** to coordinate a team of specialized AI agents. Each agent handles a specific phase of research—from querying academic APIs to chunking PDFs, synthesizing contradictory findings, generating formatted citations, and hosting an interactive RAG chat over the collected literature.

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

## 🛠️ Tech Stack & Layer Mapping

| Layer | Tools / Technologies | Purpose in Project |
| :--- | :--- | :--- |
| **Orchestration & Agents** | Python, LangChain, LangGraph | Shared `ResearchState`, agent nodes, memory checkpointing, human-in-the-loop interrupts |
| **Backend API & Processing** | FastAPI, Redis, Celery | Async REST endpoints, task queues for PDF parsing, caching state runs |
| **Databases & Vector Storage** | PostgreSQL + pgvector, Redis | Relational data (papers, reviews) + vector store for RAG similarity search |
| **Data & Document Analytics** | NumPy, Pandas, PyPDF / Unstructured | PDF extraction, tabular metadata analysis, citation network analysis |
| **Frontend UI** | Next.js / React, Tailwind CSS | Dashboard for submitting topics, paper review interface, report viewer, RAG chat |
| **DevOps & Cloud** | Docker, Terraform, AWS (S3, EC2), GitHub Actions | Infrastructure as Code, S3 for PDF storage, CI/CD automated gatekeepers |
| **Testing & Quality** | Pytest, Bandit, Ruff, Black, Pre-Commit | Automated pre-commit hooks, static security scanning, 100% test coverage gate |

---

## ⚡ Quickstart Guide (Local Development Setup)

### 1. Prerequisites
- Python 3.11+ installed (`python --version`)
- Git installed (`git --version`)

### 2. Virtual Environment Setup
```bash
# Clone the repository
git clone https://github.com/saumyashah0510/Multi-Agent-Research-System-Architecture.git
cd Multi-Agent-Research-System-Architecture

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install development & quality gatekeeper tools
pip install -r requirements.txt

# Install local pre-commit hooks (Mandatory Security Step)
pre-commit install
```

### 3. Verification & Local Checks
```bash
# Run all pre-commit hooks locally across the repository
pre-commit run --all-files
```

---

## 🌿 Git Branch Naming Conventions

All team members must follow these branch naming rules:
- `feature/<name>` — New agents or core functionality
- `docs/<name>` — Documentation and team workbooks
- `fix/<name>` — Bug fixes or test resolutions
- `test/<name>` — Test suite additions
- `refactor/<name>` — Code restructures
- `ci/<name>` — CI/CD workflow updates

> ❌ **Direct pushes to `main` are strictly forbidden and blocked by GitHub branch protection.**

---

## 📄 Documentation Index
- [AGENTS.md](file:///c:/Users/OMEN/OneDrive/Desktop/Multi-Agent%20Research%20&%20Literature%20Review%20Assistant/AGENTS.md) — Persistent project rules & guidelines for AI assistants & human contributors.
