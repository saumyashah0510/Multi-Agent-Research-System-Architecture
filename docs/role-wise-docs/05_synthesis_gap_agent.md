# Role Workbook: Member 5 - Synthesis & Literature Gap Analysis Agent

## 📋 Role Overview & Scope
- **Role:** Synthesis Engine & Literature Gap Analyst.
- **Goal:** Perform multi-document comparison to extract agreements, contradictory findings across papers, and unexplored research gaps.
- **Owned Files:**
  - `backend/app/agents/synthesis_agent.py`
  - `backend/app/services/synthesis_engine.py`
  - `backend/app/schemas/synthesis_schema.py`
  - `backend/tests/test_synthesis_agent.py`

---

## 🎯 Step-by-Step Task Breakdown
1. Multi-document cross-comparison algorithm (building comparative finding matrices).
2. Extracting:
   - **Agreements**: Where multiple papers reach identical conclusions.
   - **Contradictions**: Where findings clash (e.g. Paper A vs Paper B).
   - **Open Gaps**: Unanswered questions or unexplored domains.
3. Unit tests verifying synthesis matrix generation in `backend/tests/test_synthesis_agent.py`.
