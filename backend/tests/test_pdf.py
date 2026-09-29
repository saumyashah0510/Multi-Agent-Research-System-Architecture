"""Tests for the PDF downloader and text extraction service."""

import io

import httpx
import pytest
from app.services.pdf_service import (
    _extract_pdf_text,
    _extract_sections,
    download_and_extract_pdf,
)


def create_test_pdf() -> bytes:
    """Create a minimal PDF containing academic section headings."""

    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()

    pdf = canvas.Canvas(buffer)

    lines = [
        "Abstract",
        "This is the abstract of the paper.",
        "",
        "Introduction",
        "This is the introduction.",
        "",
        "Methods",
        "These are the methods used in the study.",
        "",
        "Results",
        "These are the results.",
        "",
        "Conclusion",
        "This is the conclusion.",
    ]

    y_position = 800

    for line in lines:
        pdf.drawString(50, y_position, line)
        y_position -= 25

    pdf.save()

    return buffer.getvalue()


def test_extract_sections() -> None:
    """Test extraction of recognized academic sections."""

    text = """
    Abstract
    This is the abstract.

    Introduction
    This is the introduction.

    Methods
    These are the methods.

    Results
    These are the results.

    Conclusion
    This is the conclusion.
    """

    sections = _extract_sections(text)

    assert sections["abstract"] == "This is the abstract."
    assert sections["introduction"] == "This is the introduction."
    assert sections["methods"] == "These are the methods."
    assert sections["results"] == "These are the results."
    assert sections["conclusion"] == "This is the conclusion."


def test_extract_sections_with_numbered_headings() -> None:
    """Test section detection with numbered headings."""

    text = """
    1. Introduction
    Introduction content.

    2. Methods
    Methods content.

    3. Results
    Results content.

    4. Conclusion
    Conclusion content.
    """

    sections = _extract_sections(text)

    assert sections["introduction"] == "Introduction content."
    assert sections["methods"] == "Methods content."
    assert sections["results"] == "Results content."
    assert sections["conclusion"] == "Conclusion content."


def test_extract_pdf_text() -> None:
    """Test PDF page text extraction."""

    pdf_bytes = create_test_pdf()

    raw_text = _extract_pdf_text(pdf_bytes)

    assert "Abstract" in raw_text
    assert "Introduction" in raw_text
    assert "Methods" in raw_text
    assert "Results" in raw_text
    assert "Conclusion" in raw_text


@pytest.mark.asyncio
async def test_empty_url() -> None:
    """Test that an empty URL returns an empty payload."""

    result = await download_and_extract_pdf("")

    assert result == {
        "raw_text": "",
        "sections": {},
    }


@pytest.mark.asyncio
async def test_download_and_extract_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test the complete download and extraction flow."""

    pdf_bytes = create_test_pdf()

    async def mock_download(
        pdf_url: str,
    ) -> bytes:
        return pdf_bytes

    monkeypatch.setattr(
        "app.services.pdf_service._download_pdf",
        mock_download,
    )

    result = await download_and_extract_pdf("https://example.com/paper.pdf")

    assert "Abstract" in result["raw_text"]
    assert "abstract" in result["sections"]
    assert "introduction" in result["sections"]
    assert "methods" in result["sections"]
    assert "results" in result["sections"]
    assert "conclusion" in result["sections"]


@pytest.mark.asyncio
async def test_download_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test graceful handling of HTTP download failures."""

    async def mock_download(
        pdf_url: str,
    ) -> bytes:
        raise httpx.ConnectError("Connection failed")

    monkeypatch.setattr(
        "app.services.pdf_service._download_pdf",
        mock_download,
    )

    result = await download_and_extract_pdf("https://example.com/paper.pdf")

    assert result == {
        "raw_text": "",
        "sections": {},
    }
