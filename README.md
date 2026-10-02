<div align="center">

# 🔬 Multi-Agent Academic Research Assistant

**Autonomous Human-in-the-Loop AI Pipeline for Deep Literature Reviews**

[![Live Demo](https://img.shields.io/badge/LIVE_DEMO-13.207.232.123%3A3000-2563EB?style=for-the-badge&logo=amazonaws&logoColor=white)](http://13.207.232.123:3000)
[![API Status](https://img.shields.io/badge/API_STATUS-HEALTHY-059669?style=for-the-badge&logo=fastapi&logoColor=white)](http://13.207.232.123:8000/api/v1/health)

![Python](https://img.shields.io/badge/PYTHON-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FASTAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LANGGRAPH-0.2%2B-FF6F00?style=for-the-badge&logo=langchain&logoColor=white)
![Gemini](https://img.shields.io/badge/GEMINI-3.1_FLASH_LITE-8E7CC3?style=for-the-badge&logo=google-gemini&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/POSTGRESQL-PGVECTOR-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/REDIS-5.0%2B-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![React](https://img.shields.io/badge/REACT-19.1%2B-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/VITE-6.3%2B-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Docker Compose](https://img.shields.io/badge/DOCKER_COMPOSE-V2-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GITHUB_ACTIONS-CD_PIPELINE-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)

</div>

---

An autonomous, human-in-the-loop multi-agent AI pipeline designed to automate deep academic literature reviews using LangGraph, FastAPI, PostgreSQL + `pgvector`, Redis, and React.

## 📌 Table of Contents
1. [Project Overview](#1-project-overview)
2. [Service Links](#2-service-links)
3. [Tech Stack](#3-tech-stack)
4. [Quick Start](#4-quick-start)
5. [Port Mapping](#5-port-mapping)
6. [Environment Setup](#6-environment-setup)
7. [System Features](#7-system-features)
8. [Role Documentation](#8-role-documentation)
9. [Architecture Diagrams](#9-architecture-diagrams)
10. [Repository Structure](#10-repository-structure)
11. [Open Questions & Code Mismatches](#11-open-questions--code-mismatches)

---

## 1. Project Overview

This project automates multi-source academic paper discovery, relevance screening, full-text PDF parsing, vector RAG retrieval, anti-hallucination citation verification, and structured report synthesis.

---

## 2. Service Links

| Service | Local | Live (AWS Elastic IP: 13.207.232.123) | Notes |
| :--- | :--- | :--- | :--- |
| **Web App Frontend** | [http://localhost:3000](http://localhost:3000) | [http://13.207.232.123:3000](http://13.207.232.123:3000) | React / Vite Single Page Application |
| **Backend API Base** | [http://localhost:8000/api/v1](http://localhost:8000/api/v1) | [http://13.207.232.123:8000/api/v1](http://13.207.232.123:8000/api/v1) | FastAPI base entry endpoint |
| **Swagger Interactive Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | [http://13.207.232.123:8000/docs](http://13.207.232.123:8000/docs) | OpenAPI interactive documentation |
| **Health Check API** | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) | [http://13.207.232.123:8000/api/v1/health](http://13.207.232.123:8000/api/v1/health) | Database and Redis connectivity check |
| **WebSocket Event Stream** | `ws://localhost:8000/api/v1/reviews/{id}/ws` | `ws://13.207.232.123:8000/api/v1/reviews/{id}/ws` | Real-time Redis Pub/Sub event broadcast |

---

## 3. Tech Stack

| Layer | Technology | Version / Specification |
| :--- | :--- | :--- |
| **AI Orchestration** | LangGraph | `>=0.2.0` |
| **LLM Engine** | Google Gemini | `gemini-3.1-flash-lite` |
| **Relevance Classifier** | Scikit-Learn (TF-IDF) | `>=1.4.0` |
| **Backend Framework** | FastAPI / Uvicorn | `>=0.110.0` / `>=0.28.0` |
| **Database ORM** | SQLAlchemy / AsyncPG | `>=2.0.0` / `>=0.29.0` |
| **Vector Database** | PostgreSQL + pgvector | `pgvector >=0.2.5` |
| **Cache & Event Pub/Sub**| Redis | `>=5.0.0` |
| **PDF Parser** | PyPDF / DefusedXML | `>=5.0.0` / `>=0.7.1` |
| **Frontend UI** | React / Vite | `^19.1.0` / `^6.3.5` |
| **Containerization** | Docker / Docker Compose | Multi-stage `python:3.11-slim` and `nginx:alpine` |
| **Cloud Infrastructure** | AWS EC2 / S3 / Terraform | Elastic IP `13.207.232.123` |

---

## 4. Quick Start

### a) Manual Setup (Without Docker)

#### Prerequisites
| Component | Requirement | Setup Notes |
| :--- | :--- | :--- |
| **Python** | Version `3.11` | Primary runtime for FastAPI and agent nodes |
| **Node.js** | Version `20+` | Node runtime for React / Vite frontend |
| **Database** | Neon PostgreSQL | Cloud connection string configured via `DATABASE_URL` |
| **Cache** | Upstash Redis | Remote TLS Redis connection string configured via `REDIS_URL` |

#### Environment Activation & Server Execution

**Linux / macOS**:
```bash
# 1. Start FastAPI Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Windows (PowerShell)**:
```powershell
# 1. Start FastAPI Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (React / Vite)**:
```bash
# 2. Start React Frontend
cd frontend
npm ci
npm run dev
```

### b) Docker Setup (Recommended)

```bash
# Build and start container stack in background
docker compose up --build -d

# View container logs in real time
docker compose logs -f

# Rebuild containers after code changes
docker compose build --no-cache

# Stop and remove containers
docker compose down
```

---

## 5. Port Mapping

| Service | Port | Manual Access URL | Docker Container Port |
| :--- | :--- | :--- | :--- |
| **Frontend Web App** | `3000` | [http://localhost:3000](http://localhost:3000) | `3000:3000` |
| **FastAPI Backend** | `8000` | [http://localhost:8000](http://localhost:8000) | `8000:8000` |
| **PostgreSQL Database**| `5432` | Remote Neon DB (`DATABASE_URL`) | External Pooler |
| **Redis Cache** | `6379` | Upstash Redis (`REDIS_URL`) | External TLS Endpoint |

---

## 6. Environment Setup

Reference [.env.example](.env.example) to configure environment variables:

```bash
# Application Settings
PROJECT_NAME="Multi-Agent Academic Research Assistant"
API_V1_STR="/api/v1"
ENVIRONMENT="development"

# Neon PostgreSQL Database Connection URL
DATABASE_URL="postgresql://neondb_owner:pass@ep-cool-db.aws.neon.tech/neondb?sslmode=require"

# Upstash Redis Cache URL
REDIS_URL="rediss://default:pass@cool-redis.upstash.io:6379"

# LLM API Key (Google Gemini)
GEMINI_API_KEY="AIzaSy..."

# Frontend API URL (Vite environment variable)
VITE_API_URL="http://localhost:8000/api/v1"
```

---

## 7. System Features

| Feature | Short Description | Document Link |
| :--- | :--- | :--- |
| **Query Expansion & Classification** | Deconstructs queries into sub-topics and routes to target academic domains. | [AI Architecture](docs/ai.md) |
| **Multi-Source Discovery** | Fetches papers from ArXiv, PubMed, OpenAlex, Crossref, bioRxiv/medRxiv with deduplication. | [AI Architecture](docs/ai.md) |
| **Relevance Screening** | Grades paper abstracts with Gemini LLM ($\ge 0.6$ score) and TF-IDF fallback. | [AI Architecture](docs/ai.md) |
| **Human-in-the-Loop Interrupt** | Interactive paper approval grid allowing user paper selection and query expansion loops. | [Frontend Docs](docs/frontend.md) |
| **Full-Text PDF Extraction** | Downloads open-access PDFs to S3 and parses structured sections (*Methods, Results, Limitations*). | [Backend Docs](docs/backend.md) |
| **`pgvector` RAG Storage** | Chunks text into passages and stores vector embeddings for semantic retrieval. | [Backend Docs](docs/backend.md) |
| **Methodology & Gap Analysis** | Extracts comparative experimental matrices and identifies unresolved research opportunities. | [AI Architecture](docs/ai.md) |
| **Citation Verification** | Cross-checks references against real DOIs/PMIDs to prevent LLM hallucinations. | [AI Architecture](docs/ai.md) |
| **5-Style Citation Export** | Formats citations in 5 standard styles: **APA, IEEE, MLA, Harvard, Chicago**. | [Frontend Docs](docs/frontend.md) |
| **User Authentication** | User session management linking research reviews to `user_id` foreign keys. | [Backend Docs](docs/backend.md) |
| **Structured Review Synthesis** | Generates structured JSON reports with executive summary, thematic clusters, matrix, and gaps. | [AI Architecture](docs/ai.md) |

---

## 8. Role Documentation

| Role | Link | Scope |
| :--- | :--- | :--- |
| **Frontend Engineer** | [Frontend Docs](docs/frontend.md) | React/Vite UI, Research Input, Approval Grid, Checkpoint Cards, 5 Citation Styles |
| **Backend Engineer** | [Backend Docs](docs/backend.md) | FastAPI routes, PostgreSQL models, Redis caching, PDF service, vector store |
| **AI / LangGraph Engineer** | [AI Docs](docs/ai.md) | AgentState schema, 9-agent nodes, Gemini structured output, graph orchestrator |
| **DevOps / Cloud Engineer** | [DevOps Docs](docs/devops.md) | AWS EC2, Elastic IP, Terraform, S3 storage, Docker Compose, GitHub Actions |

---

## 9. Architecture Diagrams

| Type | Link | What it covers |
| :--- | :--- | :--- |
| **Activity Diagram** | [Activity Diagram](docs/diagrams/activity.md) | Complete 9-agent execution flow, human interrupt, and domain routing |
| **Class Diagram** | [Class Diagram](docs/diagrams/class.md) | Database ORM models (`LiteratureReview`, `Paper`, `PaperChunk`, `User`) and Pydantic schemas |
| **Sequence Diagram** | [Sequence Diagram](docs/diagrams/sequence.md) | End-to-end API interaction, WebSocket checkpoint streaming, and database persistence |
| **State Diagram** | [State Diagram](docs/diagrams/state.md) | State machine transitions of `AgentState` from `pending` to `synthesis_completed` |

---

## 10. Repository Structure

```
.
├── .github/
│   └── workflows/          # GitHub Actions CD deployment pipeline (deploy.yml)
├── backend/
│   ├── app/
│   │   ├── agents/         # LangGraph AgentState, orchestrator, and node functions
│   │   ├── api/            # FastAPI route endpoints (health, reviews)
│   │   ├── core/           # Configuration settings and environment variables
│   │   ├── db/             # SQLAlchemy async engine, session, and base definitions
│   │   ├── models/         # ORM models (LiteratureReview, Paper, PaperChunk, User, Log)
│   │   ├── schemas/        # Pydantic data validation schemas
│   │   └── services/       # External search, PDF parser, Redis, and vector services
│   ├── tests/              # Pytest backend test suite
│   ├── Dockerfile          # Backend container definition (python:3.11-slim)
│   └── requirements.txt    # Python dependencies manifest
├── docs/
│   ├── assets/             # Architecture images and diagrams
│   ├── diagrams/           # Activity, Class, Sequence, and State diagram guides
│   ├── planning/           # Sprint 2 & 3 master implementation plan
│   ├── ai.md               # AI Multi-Agent system specification
│   ├── backend.md          # Backend API & database documentation
│   ├── devops.md           # AWS cloud infrastructure & Terraform guides
│   └── frontend.md         # React frontend UI documentation
├── frontend/
│   ├── src/                # React application components and pages
│   ├── Dockerfile          # Frontend multi-stage Nginx container definition
│   └── package.json        # Frontend Node.js dependencies
├── terraform/              # AWS EC2, Elastic IP, and Security Group IaC scripts
├── .env.example            # Environment variables template
├── docker-compose.yml      # Multi-container service definition
└── pyproject.toml          # Ruff and Pytest project configuration
```

---

## 11. Open Questions & Code Mismatches

| Topic | Codebase Value | Implementation Plan Value | Action Required |
| :--- | :--- | :--- | :--- |
| **Frontend API Env Variable** | `VITE_API_URL` in [frontend/src/lib/api.ts](frontend/src/lib/api.ts#L3) | `NEXT_PUBLIC_API_URL` in [.env.example](.env.example) | **Action Required**: Update [.env.example](.env.example) to use `VITE_API_URL` as frontend is built with Vite. |
| **Embedding Vector Dimension** | `Vector(384)` in [backend/app/models/chunk.py](backend/app/models/chunk.py#L28) | `1536-dimensional vector embeddings` | **Action Required**: Align vector dimension to 1536 when updating embedding generator model. |
| **Vector Passage Chunk Size** | `chunk_size=1000`, `overlap=200` in [backend/app/services/vector_service.py](backend/app/services/vector_service.py#L25) | `500-token passages with 50-token overlap` | **Action Required**: Update `vector_service.py` default chunk parameters to 500 tokens. |
| **Paper Approval Endpoint Path** | `POST /api/v1/reviews/approve` in [backend/app/api/v1/health.py](backend/app/api/v1/health.py#L76) | `POST /api/v1/reviews/{id}/approve` | **Action Required**: Refactor paper approval route into `backend/app/api/v1/reviews.py`. |
| **Unused Environment Variable** | `OPENAI_API_KEY` in [.env.example](.env.example) | Gemini LLM Engine | **Action Required**: Remove `OPENAI_API_KEY` from `.env.example` as backend uses `GEMINI_API_KEY`. |
