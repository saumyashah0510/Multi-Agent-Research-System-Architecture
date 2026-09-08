# Role Workbook: Member 10 - Testing, Load Verification & Citation Analytics

## 📋 Role Overview & Scope
- **Role:** Lead QA Engineer & Data Analytics Specialist.
- **Goal:** Manage integration test coverage across all agents, conduct performance load testing using Locust for RAG endpoints, and build paper citation network visualizations.
- **Owned Files:**
  - `backend/tests/` (master test suite runner)
  - `locustfile.py`
  - `backend/app/analytics/citation_network.py`

---

## 🎯 Step-by-Step Task Breakdown
1. Pytest master test suite verification & coverage report generation (`pytest --cov=backend/app`).
2. Performance load testing with Locust for vector search and RAG chat endpoints (`locustfile.py`).
3. Citation network graph & paper topic cluster visualization (using Pandas, NetworkX, Matplotlib).
