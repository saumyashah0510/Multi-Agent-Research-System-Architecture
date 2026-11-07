"""Unit tests for Agent 05: Full-Text PDF Extractor Node.

Assignee Task (Issue AI-06):
- Test that pdf_extractor_node extracts sections from approved papers
- Test fallback to abstract when PDF URL is missing or download fails
- Test empty approved_papers list handling
"""

from typing import Any, Dict, Optional

import pytest
from app.agents.nodes.pdf_extractor_node import pdf_extractor_node


@pytest.mark.asyncio
async def test_pdf_extractor_extracts_sections_for_approved_papers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approved papers get their section dictionaries, keyed by arxiv_id."""

    calls: list[Dict[str, Optional[str]]] = []

    async def mock_download(
        pdf_url: str,
        cache_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        calls.append({"pdf_url": pdf_url, "cache_key": cache_key})
        return {
            "raw_text": "full text",
            "sections": {
                "abstract": "We present a VQE algorithm.",
                "methods": "We construct a Hamiltonian.",
                "results": "Achieved 94.2% accuracy.",
                "limitations": "Decoherence limits scaling.",
                "related_work": "Not a standard section, should be dropped.",
            },
        }

    monkeypatch.setattr(
        "app.agents.nodes.pdf_extractor_node.download_and_extract_pdf",
        mock_download,
    )

    state = {
        "approved_papers": [
            {
                "arxiv_id": "2301.12345",
                "title": "VQE Paper",
                "abstract": "Fallback abstract.",
            }
        ]
    }

    result = await pdf_extractor_node(state)

    assert result["current_step"] == "pdf_extraction_completed"

    sections = result["extracted_pdf_contents"]["2301.12345"]
    assert sections["methods"] == "We construct a Hamiltonian."
    assert sections["results"] == "Achieved 94.2% accuracy."
    assert sections["limitations"] == "Decoherence limits scaling."
    assert "related_work" not in sections

    assert calls == [
        {
            "pdf_url": "https://arxiv.org/pdf/2301.12345.pdf",
            "cache_key": "2301.12345",
        }
    ]


@pytest.mark.asyncio
async def test_pdf_extractor_falls_back_to_abstract_on_invalid_url() -> None:
    """An unsafe/invalid pdf_url falls back to the paper's abstract."""

    state = {
        "approved_papers": [
            {
                "arxiv_id": "9999.00000",
                "title": "Paywalled Paper",
                "abstract": "Only the abstract is available.",
                "pdf_url": "http://169.254.169.254/latest/meta-data/",
            }
        ]
    }

    result = await pdf_extractor_node(state)

    assert result["current_step"] == "pdf_extraction_completed"
    assert result["extracted_pdf_contents"] == {
        "9999.00000": {"abstract": "Only the abstract is available."}
    }


@pytest.mark.asyncio
async def test_pdf_extractor_handles_empty_approved_papers() -> None:
    """Empty or missing approved_papers returns an empty result without errors."""

    for state in ({"approved_papers": []}, {}):
        result = await pdf_extractor_node(state)

        assert result == {
            "extracted_pdf_contents": {},
            "current_step": "pdf_extraction_completed",
        }


@pytest.mark.asyncio
async def test_pdf_extractor_preserves_full_sections_on_duplicate_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If a duplicate paper key fell back to abstract, keep the full-text sections."""

    call_count = 0

    async def mock_download(
        pdf_url: str,
        cache_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "raw_text": "full text",
                "sections": {
                    "abstract": "Full abstract.",
                    "methods": "Detailed methods.",
                },
            }
        # Second call fails
        return {"raw_text": "", "sections": {}}

    monkeypatch.setattr(
        "app.agents.nodes.pdf_extractor_node.download_and_extract_pdf",
        mock_download,
    )

    state = {
        "approved_papers": [
            {
                "arxiv_id": "2301.11111",
                "title": "Quantum Paper",
                "abstract": "Fallback abstract.",
            },
            {
                "arxiv_id": "2301.11111",
                "title": "Quantum Paper Copy",
                "abstract": "Fallback abstract.",
            },
        ]
    }

    result = await pdf_extractor_node(state)
    sections = result["extracted_pdf_contents"]["2301.11111"]
    assert "methods" in sections
    assert sections["methods"] == "Detailed methods."


@pytest.mark.asyncio
async def test_download_and_extract_pdf_rejects_html_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If a publisher returns HTML instead of PDF, reject and return empty sections."""
    from app.services.pdf_service import download_and_extract_pdf

    async def mock_download_pdf(url: str) -> bytes:
        return b"<!DOCTYPE html><html><body>Error or Landing Page</body></html>"

    monkeypatch.setattr("app.services.pdf_service._download_pdf", mock_download_pdf)

    res = await download_and_extract_pdf("https://example.com/paper.pdf", cache_key="1234.5678")
    assert res["raw_text"] == ""
    assert res["sections"] == {}
