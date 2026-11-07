"""Tests for the PDF downloader and text extraction service."""

import io
import logging
from unittest.mock import AsyncMock

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


def test_extract_sections_with_inline_headings() -> None:
    """Test section detection with inline colon/dash headings."""
    text = """
    Abstract: The emergence of novel architectures in transformers.
    Second line of abstract.

    1. Introduction - Here we formulate the research question.
    More intro text.

    Methods: We executed benchmarks on GPU clusters.
    """
    sections = _extract_sections(text)

    assert "The emergence of novel architectures" in sections["abstract"]
    assert "Here we formulate the research question." in sections["introduction"]
    assert "We executed benchmarks on GPU clusters." in sections["methods"]


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


@pytest.mark.asyncio
async def test_download_and_extract_pdf_blocks_ssrf_url() -> None:
    """Test that SSRF / internal URLs are blocked and return empty payload safely."""
    # Attempting to fetch cloud metadata or internal IP must fail gracefully
    result = await download_and_extract_pdf("http://169.254.169.254/latest/meta-data/")

    assert result == {
        "raw_text": "",
        "sections": {},
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("cached_bytes", [b"%PDF-1.4 corrupt", b"", None])
async def test_unusable_cached_pdf_falls_back_to_download(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    cached_bytes: bytes | None,
) -> None:
    """A corrupt or missing cached PDF is replaced by a downloaded PDF."""
    pdf_bytes = create_test_pdf()
    download = AsyncMock(return_value=pdf_bytes)
    upload = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.services.pdf_service.get_pdf_from_s3", AsyncMock(return_value=cached_bytes)
    )
    monkeypatch.setattr("app.services.pdf_service._download_pdf", download)
    monkeypatch.setattr("app.services.pdf_service.cache_pdf_to_s3", upload)

    with caplog.at_level(logging.INFO, logger="app.services.pdf_service"):
        result = await download_and_extract_pdf("https://example.com/paper.pdf", cache_key="paper")

    download.assert_awaited_once_with("https://example.com/paper.pdf")
    upload.assert_awaited_once_with(pdf_bytes, "paper")
    assert result["sections"]["abstract"] == "This is the abstract of the paper."
    assert "Skipping network download" not in caplog.text
    if cached_bytes:
        assert "Cached PDF extraction failed for 'paper'" in caplog.text


@pytest.mark.asyncio
async def test_valid_cached_pdf_skips_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful cached extraction preserves the cache hit result."""
    pdf_bytes = create_test_pdf()
    download = AsyncMock()
    upload = AsyncMock()
    monkeypatch.setattr(
        "app.services.pdf_service.get_pdf_from_s3", AsyncMock(return_value=pdf_bytes)
    )
    monkeypatch.setattr("app.services.pdf_service._download_pdf", download)
    monkeypatch.setattr("app.services.pdf_service.cache_pdf_to_s3", upload)

    result = await download_and_extract_pdf("https://example.com/paper.pdf", cache_key="paper")

    assert result == {
        "raw_text": _extract_pdf_text(pdf_bytes),
        "sections": _extract_sections(_extract_pdf_text(pdf_bytes)),
    }
    download.assert_not_awaited()
    upload.assert_not_awaited()


def test_get_s3_key_formatting() -> None:
    """Test S3 key generation for arXiv, PubMed, DOI, and titles."""
    from app.services.pdf_service import _get_s3_key

    assert _get_s3_key("2305.18290") == "papers/2305.18290.pdf"
    assert _get_s3_key("pmid_42818104") == "papers/pubmed/pmid_42818104.pdf"
    assert _get_s3_key("pubmed_42818104") == "papers/pubmed/pubmed_42818104.pdf"
    assert _get_s3_key("doi_10.1038/s41586-021") == "papers/dois/10.1038_s41586-021.pdf"
    assert "papers/titles/" in _get_s3_key("Sample Paper Title Without IDs")


@pytest.mark.asyncio
async def test_resolve_pubmed_pdf_url_openalex_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test successful PubMed PDF resolution via OpenAlex works API."""
    from unittest.mock import MagicMock

    from app.services.pdf_service import resolve_pubmed_pdf_url

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "best_oa_location": {"pdf_url": "https://www.nature.com/articles/sample.pdf"}
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

    url = await resolve_pubmed_pdf_url("34265844", doi="10.1038/sample")
    assert url == "https://www.nature.com/articles/sample.pdf"


@pytest.mark.asyncio
async def test_resolve_pubmed_pdf_url_paywalled_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that a paywalled PubMed paper with no open access returns None."""
    from unittest.mock import MagicMock

    from app.services.pdf_service import resolve_pubmed_pdf_url

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "best_oa_location": None,
        "oa_locations": [],
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

    url = await resolve_pubmed_pdf_url("35000000", doi=None)
    assert url is None


@pytest.mark.asyncio
async def test_resolve_biorxiv_pdf_url_direct_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test successful bioRxiv resolution via direct HEAD check."""
    from unittest.mock import MagicMock

    from app.services.pdf_service import resolve_biorxiv_pdf_url

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/pdf"}

    mock_client = AsyncMock()
    mock_client.head = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

    url = await resolve_biorxiv_pdf_url("10.1101/2020.01.31.929042")
    assert url == "https://www.biorxiv.org/content/10.1101/2020.01.31.929042.full.pdf"


@pytest.mark.asyncio
async def test_resolve_biorxiv_pdf_url_empty_returns_none() -> None:
    """Empty or None DOI returns None immediately."""
    from app.services.pdf_service import resolve_biorxiv_pdf_url

    assert await resolve_biorxiv_pdf_url("") is None
    assert await resolve_biorxiv_pdf_url("   ") is None
