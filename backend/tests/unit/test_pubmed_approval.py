from app.agents.nodes.human_interrupt_node import human_interrupt_node


def test_human_interrupt_node_matches_pubmed_and_doi(monkeypatch):
    # Mock screened papers from PubMed and Crossref
    screened_papers = [
        {
            "id": None,
            "title": "Deep Learning in Biomedicine",
            "authors": ["Alice Smith"],
            "abstract": "Test abstract 1",
            "pubmed_id": "38999123",
            "doi": "10.1016/j.biomed.2023.01.001",
            "source": "pubmed",
            "relevance_score": 0.95,
        },
        {
            "id": None,
            "title": "Crossref Neural Foundations",
            "authors": ["Bob Jones"],
            "abstract": "Test abstract 2",
            "pubmed_id": None,
            "doi": "10.1145/3318464.3389700",
            "source": "crossref",
            "relevance_score": 0.88,
        },
    ]

    state = {"screened_papers": screened_papers}

    # Case A: User approves by PubMed ID
    def mock_interrupt_pmid(payload):
        return {"user_decision": "continue", "approved_paper_ids": ["38999123"]}

    monkeypatch.setattr("app.agents.nodes.human_interrupt_node.interrupt", mock_interrupt_pmid)
    res = human_interrupt_node(state)
    assert len(res["approved_papers"]) == 1
    assert res["approved_papers"][0]["pubmed_id"] == "38999123"

    # Case B: User approves by DOI (with or without url prefix)
    def mock_interrupt_doi(payload):
        return {
            "user_decision": "continue",
            "approved_paper_ids": ["https://doi.org/10.1145/3318464.3389700"],
        }

    monkeypatch.setattr("app.agents.nodes.human_interrupt_node.interrupt", mock_interrupt_doi)
    res = human_interrupt_node(state)
    assert len(res["approved_papers"]) == 1
    assert res["approved_papers"][0]["doi"] == "10.1145/3318464.3389700"

    # Case C: User approves all
    def mock_interrupt_all(payload):
        return {
            "user_decision": "continue",
            "approved_paper_ids": ["38999123", "10.1145/3318464.3389700"],
        }

    monkeypatch.setattr("app.agents.nodes.human_interrupt_node.interrupt", mock_interrupt_all)
    res = human_interrupt_node(state)
    assert len(res["approved_papers"]) == 2

    # Case D: User approves by 1-based index
    def mock_interrupt_index(payload):
        return {
            "user_decision": "continue",
            "approved_paper_ids": ["1"],
        }

    monkeypatch.setattr("app.agents.nodes.human_interrupt_node.interrupt", mock_interrupt_index)
    res = human_interrupt_node(state)
    assert len(res["approved_papers"]) == 1
    assert res["approved_papers"][0]["pubmed_id"] == "38999123"

    # Case E: Fallback when unknown ID is passed
    def mock_interrupt_fallback(payload):
        return {
            "user_decision": "continue",
            "approved_paper_ids": ["unknown-id-123"],
        }

    monkeypatch.setattr("app.agents.nodes.human_interrupt_node.interrupt", mock_interrupt_fallback)
    res = human_interrupt_node(state)
    assert len(res["approved_papers"]) == 1
