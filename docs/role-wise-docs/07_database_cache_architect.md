# Role Workbook: Member 7 - Database & Redis Caching Architect

## 📋 Role Overview & Scope
- **Role:** Database, Vector Store & Redis Caching Architect.
- **Goal:** Design PostgreSQL schemas (users, research_runs, paper_metadata, synthesis_reports), configure pgvector HNSW indexes, and implement Redis state caching.
- **Owned Files:**
  - `backend/app/models/`
  - `backend/app/core/db.py`
  - `backend/app/core/redis.py`
  - `backend/tests/test_database.py`

---

## 🎯 Step-by-Step Task Breakdown
1. SQLAlchemy 2.0 ORM model definitions (`ResearchRun`, `PaperMetadata`, `SynthesisReport`, `ChatMessage`).
2. Pgvector extension initialization & HNSW vector index configuration.
3. Redis caching layer for agent runs and session checkpointer.
4. Database unit and integration tests in `backend/tests/test_database.py`.
