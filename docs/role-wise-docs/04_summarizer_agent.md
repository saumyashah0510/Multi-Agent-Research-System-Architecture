# Role Workbook: Member 4 - Summarizer Agent & Structured Outputs

## 📋 Role Overview & Scope
- **Role:** Summarizer Agent & Prompt Engineer.
- **Goal:** Process each user-approved paper to extract research methodology, datasets, key quantitative findings, and acknowledged limitations into strict Pydantic JSON schemas.
- **Owned Files:**
  - `backend/app/agents/summarizer_agent.py`
  - `backend/app/prompts/summarizer_prompts.py`
  - `backend/app/schemas/summary_schema.py`
  - `backend/tests/test_summarizer_agent.py`

---

## 🎯 Step-by-Step Task Breakdown
1. Design structured Pydantic schema (`PaperSummary`: methodology, dataset, findings, limitations).
2. Prompt engineering with strict JSON output parsing to prevent hallucinations.
3. Unit tests verifying summary extraction on sample research papers in `backend/tests/test_summarizer_agent.py`.
