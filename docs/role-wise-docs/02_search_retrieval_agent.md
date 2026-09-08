# Role Workbook: Member 2 - Academic Search & Retrieval Agent

## 📋 Role Overview & Scope
- **Role:** Search & Academic API Agent Developer.
- **Goal:** Build search client integration with arXiv, Semantic Scholar, and Crossref APIs. Handle query expansion, rate limiting, and paper metadata normalization.
- **Owned Files:**
  - `backend/app/agents/search_agent.py`
  - `backend/app/services/academic_apis/arxiv_client.py`
  - `backend/app/services/academic_apis/semantic_scholar_client.py`
  - `backend/tests/test_search_agent.py`

---

## 🎯 Step-by-Step Task Breakdown
1. Query Expansion & Optimization (convert user topic into academic query strings).
2. Fetch paper metadata (title, authors, abstract, published year, PDF URL, citations count).
3. Fallback handling (if arXiv fails, query Semantic Scholar).
4. Unit tests in `backend/tests/test_search_agent.py` with mock HTTP API responses.
