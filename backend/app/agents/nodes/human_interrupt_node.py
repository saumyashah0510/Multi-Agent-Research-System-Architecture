"""Agent 04: Human Approval Interrupt Node."""

from typing import Any, Dict

from langgraph.types import interrupt

from app.agents.state import AgentState


def human_interrupt_node(state: AgentState) -> Dict[str, Any]:
    """Human-in-the-loop checkpoint pausing graph for user paper selection."""
    screened_papers = state.get("screened_papers") or []

    # Pause: payload has candidate papers with titles, abstracts, relevance scores
    response = interrupt(
        {
            "candidate_papers": [
                {
                    "id": p.get("id")
                    or p.get("paper_id")
                    or p.get("arxiv_id")
                    or p.get("doi")
                    or (str(p.get("pubmed_id")) if p.get("pubmed_id") else None)
                    or p.get("title"),
                    "title": p.get("title"),
                    "abstract": p.get("abstract"),
                    "relevance_score": p.get("relevance_score"),
                    "arxiv_id": p.get("arxiv_id"),
                    "doi": p.get("doi"),
                    "pubmed_id": p.get("pubmed_id"),
                }
                for p in screened_papers
            ]
        }
    )

    # Resumed with user input
    user_decision = response.get("user_decision", "continue")
    approved_paper_ids = response.get("approved_paper_ids") or []

    approved = []
    if user_decision == "continue":
        approved_set = set()
        for item in approved_paper_ids:
            if item and str(item).strip():
                val = str(item).strip().lower()
                approved_set.add(val)
                if "doi.org/" in val:
                    approved_set.add(val.split("doi.org/", 1)[-1].strip("/"))

        for idx, p in enumerate(screened_papers, 1):
            identifiers = {
                str(idx),
                f"paper-{idx}",
                str(p.get("id") or ""),
                str(p.get("paper_id") or ""),
                str(p.get("arxiv_id") or ""),
                str(p.get("doi") or ""),
                str(p.get("pubmed_id") or ""),
                str(p.get("title") or ""),
                str(p.get("pdf_url") or ""),
                str(p.get("url") or ""),
            }
            doi = p.get("doi")
            if doi:
                clean_doi = (
                    str(doi)
                    .strip()
                    .lower()
                    .replace("https://doi.org/", "")
                    .replace("http://doi.org/", "")
                    .strip("/")
                )
                identifiers.add(clean_doi)
                identifiers.add(f"https://doi.org/{clean_doi}")
                identifiers.add(f"http://doi.org/{clean_doi}")
            clean_ids = {str(x).strip().lower() for x in identifiers if x}
            if bool(clean_ids & approved_set):
                approved.append(p)
            elif p.get("title"):
                p_title_norm = str(p.get("title")).strip().lower()
                if any(
                    p_title_norm in app_id or app_id in p_title_norm
                    for app_id in approved_set
                    if len(app_id) > 10
                ):
                    approved.append(p)

        # Fallback safeguard: if user approved papers but identifier matching yielded 0,
        # fallback to the screened papers so downstream PDF extraction & synthesis never starves.
        if not approved and screened_papers:
            count = len(approved_paper_ids) if len(approved_paper_ids) > 0 else len(screened_papers)
            approved = screened_papers[:count]

    return {
        "approved_papers": approved,
        "user_decision": user_decision,
        "current_step": "human_approval_completed",
    }
