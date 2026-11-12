"""Async PDF downloading and text extraction service with SSRF defense."""

import asyncio
import io
import logging
import re
import urllib.parse
from html.parser import HTMLParser
from typing import Any, Dict, Optional

import httpx
from pypdf import PdfReader

from app.core.config import settings
from app.core.guardrails import enforce_pdf_url_safety, validate_pdf_url

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10.0

S3_BUCKET = settings.AWS_S3_BUCKET
S3_PREFIX = "papers/"


SECTION_ALIASES = {
    "abstract": {
        "abstract",
        "summary",
    },
    "introduction": {
        "introduction",
        "background",
        "overview",
        "motivation",
    },
    "related_work": {
        "related work",
        "prior work",
        "literature review",
    },
    "preliminaries": {
        "preliminaries",
        "problem formulation",
        "definitions",
    },
    "methods": {
        "methods",
        "method",
        "methodology",
        "materials and methods",
        "materials & methods",
        "experimental methods",
        "system design",
        "architecture",
        "proposed method",
        "approach",
    },
    "results": {
        "results",
        "findings",
        "experiments",
        "evaluation",
        "experimental results",
    },
    "discussion": {
        "discussion",
        "analysis",
    },
    "limitations": {
        "limitations",
        "threats to validity",
        "drawbacks",
        "scope and limitations",
    },
    "future_work": {
        "future work",
        "future directions",
        "open challenges",
        "conclusions and future work",
    },
    "conclusion": {
        "conclusion",
        "conclusions",
        "discussion and conclusion",
    },
}


def _normalize_heading(text: str) -> str:
    """Normalize a possible section heading."""

    text = text.strip()
    text = re.sub(r"^\d+(?:\.\d+)*[\s.)-]+", "", text)
    text = re.sub(r"[^a-zA-Z0-9& ]+", "", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip().lower()


def _detect_section_heading(line: str) -> tuple[Optional[str], str]:
    """Return (canonical_section_name, trailing_content) for a recognized heading.

    Supports standalone headings (e.g. 'Methods') as well as inline headings
    with a colon or dash (e.g. 'Abstract: The emergence of...').
    """
    normalized = _normalize_heading(line)

    for section_name, aliases in SECTION_ALIASES.items():
        if normalized in aliases:
            return section_name, ""

    match = re.match(
        r"^(\d+(?:\.\d+)*[ \t.)-]*)?([a-zA-Z &]{3,30}?)(?::[ \t]*|[ \t]+[-–—][ \t]+)(.*)$",
        line,
    )
    if match:
        norm_prefix = _normalize_heading(match.group(2))
        for section_name, aliases in SECTION_ALIASES.items():
            if norm_prefix in aliases:
                return section_name, match.group(3).strip()

    return None, ""


def _extract_sections(raw_text: str) -> Dict[str, str]:
    """Extract common academic paper sections from raw PDF text."""

    sections: Dict[str, str] = {}

    current_section: str | None = None
    current_lines: list[str] = []

    def save_current_section() -> None:
        if current_section is None:
            return

        content = "\n".join(current_lines).replace("\x00", "").strip()

        if content:
            if current_section in sections:
                sections[current_section] += "\n" + content
            else:
                sections[current_section] = content

    clean_raw = (raw_text or "").replace("\x00", "")
    for line in clean_raw.splitlines():
        stripped_line = line.strip()

        if not stripped_line:
            if current_section is not None:
                current_lines.append("")
            continue

        detected_section, trailing_text = _detect_section_heading(stripped_line)

        if detected_section is not None:
            save_current_section()

            current_section = detected_section
            current_lines = [trailing_text] if trailing_text else []
            continue

        if current_section is not None:
            current_lines.append(stripped_line)

    save_current_section()

    return sections


def _extract_pdf_text(pdf_bytes: bytes, max_pages: int = 40) -> str:
    """Extract text from PDF pages up to max_pages to prevent memory exhaustion."""

    reader = PdfReader(io.BytesIO(pdf_bytes))

    page_texts: list[str] = []

    for idx, page in enumerate(reader.pages):
        if idx >= max_pages:
            break
        text = (page.extract_text() or "").replace("\x00", "")

        if text.strip():
            page_texts.append(text.strip())

    return "\n\n".join(page_texts).strip()


class _ArticleHTMLParser(HTMLParser):
    """Secure, zero-dependency HTML parser for Open Access article bodies."""

    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._ignore_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "nav", "header", "footer", "aside", "noscript"):
            self._ignore_stack.append(tag_lower)
        elif tag_lower in (
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "div",
            "section",
            "article",
            "br",
            "li",
        ):
            self._pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if self._ignore_stack and self._ignore_stack[-1] == tag_lower:
            self._ignore_stack.pop()
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "section", "article"):
            self._pieces.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignore_stack:
            self._pieces.append(data)

    def get_text(self) -> str:
        raw = "".join(self._pieces)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


def extract_html_article_text(html_content: str) -> Dict[str, Any]:
    """Extract clean text and academic sections from an Open Access HTML article.

    Provides a zero-dependency fallback when publishers return full HTML web pages
    instead of raw PDF binaries.
    """
    if not html_content or not html_content.strip():
        return {"raw_text": "", "sections": {}}

    parser = _ArticleHTMLParser()
    try:
        parser.feed(html_content)
        raw_text = parser.get_text()
    except Exception as exc:  # noqa: BLE001
        logger.warning("HTML article parsing failed: %s", exc)
        return {"raw_text": "", "sections": {}}

    if not raw_text:
        return {"raw_text": "", "sections": {}}

    sections = _extract_sections(raw_text)
    return {"raw_text": raw_text, "sections": sections}


DEFAULT_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
}


def _normalize_doi(doi: Optional[str]) -> str:
    """Strip standard DOI URL prefixes and whitespace."""
    if not doi or not doi.strip():
        return ""
    clean = doi.strip()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix) :].strip()
    return clean


def _is_safe_pdf_url(url: Optional[str]) -> bool:
    """Validate that candidate URL meets SSRF policy and is not an anti-bot challenge domain or image asset."""
    if not url or not isinstance(url, str) or not url.strip().startswith("https://"):
        return False
    # Exclude known Proof-of-Work JS challenge endpoints that block automated HTTP clients
    if "pmc.ncbi.nlm.nih.gov" in url:
        return False

    clean_url = url.strip().lower().split("?")[0]
    # Filter out image/HTML assets mistakenly returned by commercial publishers as PDFs
    if clean_url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".html", ".htm")):
        return False
    if "ars.els-cdn.com" in clean_url or "/content/image/" in clean_url:
        return False

    validation = validate_pdf_url(url.strip())
    return validation.is_safe


async def _download_pdf(pdf_url: str) -> bytes:
    """Download PDF bytes asynchronously after enforcing SSRF URL safety on every redirect hop."""
    current_url = enforce_pdf_url_safety(pdf_url)
    max_hops = 5

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        for _ in range(max_hops):
            response = await client.get(
                current_url,
                headers=DEFAULT_BROWSER_HEADERS,
                follow_redirects=False,
            )
            if response.is_redirect:
                location = response.headers.get("Location")
                if not location:
                    response.raise_for_status()
                next_url = str(response.url.join(location))
                current_url = enforce_pdf_url_safety(next_url)
                continue
            response.raise_for_status()
            return response.content
        raise ValueError(f"Too many redirects downloading PDF from {pdf_url}")


def _get_s3_key(cache_key: str) -> str:
    """Return the deterministic S3 key for a given cache_key."""
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", cache_key):
        return f"{S3_PREFIX}arxiv/{cache_key}.pdf"
    if cache_key.startswith("pmid_") or cache_key.startswith("pubmed_"):
        clean_pmid = re.sub(r"[^A-Za-z0-9._-]", "_", cache_key)
        return f"{S3_PREFIX}pubmed/{clean_pmid}.pdf"
    if cache_key.startswith("doi_"):
        clean_doi = re.sub(r"[^A-Za-z0-9._-]", "_", cache_key[4:])
        return f"{S3_PREFIX}dois/{clean_doi}.pdf"
    import hashlib

    title_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:12]
    clean_title = re.sub(r"[^A-Za-z0-9._-]", "_", cache_key)[:40].strip("_")
    return f"{S3_PREFIX}titles/{clean_title}_{title_hash}.pdf"


async def resolve_pubmed_pdf_url(
    pmid: str,
    doi: Optional[str] = None,
) -> Optional[str]:
    """Resolve an open-access full-text PDF URL for a PubMed paper.

    Queries OpenAlex works API by PMID, and Unpaywall API by DOI if available.
    Returns a verified HTTPS URL or None if paywalled/unavailable.
    """
    if not pmid or not pmid.strip():
        return None

    clean_pmid = pmid.strip()
    encoded_pmid = urllib.parse.quote(clean_pmid, safe="")
    headers = {"User-Agent": "mailto:team_review@daiict.ac.in"}

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
        # 1. Query OpenAlex by PMID
        try:
            openalex_url = f"https://api.openalex.org/works/pmid:{encoded_pmid}"
            resp = await client.get(openalex_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                best_oa = data.get("best_oa_location") or {}
                pdf_url = best_oa.get("pdf_url")
                if _is_safe_pdf_url(pdf_url):
                    return pdf_url
                for loc in data.get("locations", []):
                    cand = loc.get("pdf_url")
                    if _is_safe_pdf_url(cand):
                        return cand
        except Exception as exc:  # noqa: BLE001
            logger.debug("OpenAlex PMID resolution failed for %s: %s", clean_pmid, exc)

        # 2. Query Unpaywall if DOI is available
        clean_doi = _normalize_doi(doi) if doi else ""
        if clean_doi:
            try:
                encoded_doi = urllib.parse.quote(clean_doi, safe="/")
                unpaywall_url = (
                    f"https://api.unpaywall.org/v2/{encoded_doi}?email=team_review@daiict.ac.in"
                )
                resp = await client.get(unpaywall_url)
                if resp.status_code == 200:
                    data = resp.json()
                    best_oa = data.get("best_oa_location") or {}
                    pdf_url = best_oa.get("url_for_pdf")
                    if _is_safe_pdf_url(pdf_url):
                        return pdf_url

                    # Check secondary repository locations
                    for loc in data.get("oa_locations", []):
                        repo_pdf = loc.get("url_for_pdf")
                        if _is_safe_pdf_url(repo_pdf):
                            return repo_pdf
            except Exception as exc:  # noqa: BLE001
                logger.debug("Unpaywall DOI resolution failed for %s: %s", clean_doi, exc)

    return None


async def resolve_biorxiv_pdf_url(doi: str) -> Optional[str]:
    """Resolve an open-access full-text PDF URL for a bioRxiv preprint.

    Tries the direct Cold Spring Harbor canonical stream first, then falls back
    to OpenAlex and Unpaywall repository locations if direct access is restricted.
    """
    clean_doi = _normalize_doi(doi)
    if not clean_doi:
        return None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        )
    }

    # 1. Direct bioRxiv preprint stream
    direct_url = f"https://www.biorxiv.org/content/{clean_doi}.full.pdf"
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            resp = await client.head(direct_url, headers=headers)
            content_type = resp.headers.get("content-type", "").lower()
            if resp.status_code == 200 and "pdf" in content_type:
                return direct_url
    except Exception as exc:  # noqa: BLE001
        logger.debug("Direct bioRxiv HEAD check failed for %s: %s", clean_doi, exc)

    # 2. Fallback to OpenAlex / Unpaywall repository mirror
    try:
        encoded_doi = urllib.parse.quote(clean_doi, safe="/")
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            unpaywall_url = (
                f"https://api.unpaywall.org/v2/{encoded_doi}?email=team_review@daiict.ac.in"
            )
            resp = await client.get(unpaywall_url)
            if resp.status_code == 200:
                data = resp.json()
                for loc in data.get("oa_locations", []):
                    pdf_cand = loc.get("url_for_pdf")
                    if _is_safe_pdf_url(pdf_cand):
                        return pdf_cand
    except Exception as exc:  # noqa: BLE001
        logger.debug("bioRxiv mirror fallback failed for %s: %s", clean_doi, exc)

    return None


async def resolve_unpaywall_pdf_url(doi: str) -> Optional[str]:
    """Resolve an open-access full-text PDF URL for a Crossref or external DOI.

    Queries Unpaywall API first, then falls back to OpenAlex DOI lookup.
    Returns a verified HTTPS PDF URL or None if paywalled/restricted.
    """
    clean_doi = _normalize_doi(doi)
    if not clean_doi:
        return None

    headers = {"User-Agent": "mailto:team_review@daiict.ac.in"}
    encoded_doi = urllib.parse.quote(clean_doi, safe="/")

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
        # 1. Query Unpaywall API
        try:
            unpaywall_url = (
                f"https://api.unpaywall.org/v2/{encoded_doi}?email=team_review@daiict.ac.in"
            )
            resp = await client.get(unpaywall_url)
            if resp.status_code == 200:
                data = resp.json()
                best_oa = data.get("best_oa_location") or {}
                pdf_url = best_oa.get("url_for_pdf")
                if _is_safe_pdf_url(pdf_url):
                    return pdf_url

                # Check secondary repository locations
                for loc in data.get("oa_locations", []):
                    cand = loc.get("url_for_pdf")
                    if _is_safe_pdf_url(cand):
                        return cand
        except Exception as exc:  # noqa: BLE001
            logger.debug("Unpaywall resolution failed for %s: %s", clean_doi, exc)

        # 2. Fallback to OpenAlex by DOI
        try:
            openalex_url = f"https://api.openalex.org/works/doi:{encoded_doi}"
            resp = await client.get(openalex_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                best_oa = data.get("best_oa_location") or {}
                pdf_url = best_oa.get("pdf_url")
                if _is_safe_pdf_url(pdf_url):
                    return pdf_url
                for loc in data.get("locations", []):
                    cand = loc.get("pdf_url")
                    if _is_safe_pdf_url(cand):
                        return cand
        except Exception as exc:  # noqa: BLE001
            logger.debug("OpenAlex DOI resolution failed for %s: %s", clean_doi, exc)

    return None


async def get_pdf_from_s3(cache_key: str) -> Optional[bytes]:
    """Retrieve a cached PDF from S3 if it exists and AWS credentials are configured.

    Returns the raw bytes if found in S3, or None if not cached, credentials are
    missing, or on error.
    """
    access_key = settings.AWS_ACCESS_KEY_ID
    secret_key = settings.AWS_SECRET_ACCESS_KEY
    if not cache_key or not access_key or not secret_key:
        return None

    primary_key = _get_s3_key(cache_key)
    legacy_key = (
        f"{S3_PREFIX}{cache_key}.pdf" if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", cache_key) else None
    )

    def _fetch() -> Optional[bytes]:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError

        s3_config = Config(
            connect_timeout=3,
            read_timeout=5,
            retries={"max_attempts": 1},
        )
        client_kwargs: Dict[str, Any] = {
            "region_name": settings.AWS_REGION,
            "config": s3_config,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        if settings.AWS_SESSION_TOKEN:
            client_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

        client = boto3.client("s3", **client_kwargs)

        keys_to_try = [primary_key]
        if legacy_key:
            keys_to_try.append(legacy_key)

        for s3_key in keys_to_try:
            try:
                response = client.get_object(
                    Bucket=settings.AWS_S3_BUCKET,
                    Key=s3_key,
                )
                body = response["Body"].read()
                if body and body.startswith(b"%PDF"):
                    return body
            except ClientError:
                continue
            except Exception as exc:  # noqa: BLE001 - cache read failure falls back to download
                logger.debug("S3 fetch failed for key '%s': %s", s3_key, exc)
                continue
        return None

    try:
        return await asyncio.to_thread(_fetch)
    except Exception:  # noqa: BLE001
        return None


async def cache_pdf_to_s3(pdf_bytes: bytes, cache_key: str) -> Optional[str]:
    """Cache a paper PDF to s3://{S3_BUCKET}/papers/{cache_key}.pdf.

    Returns the S3 URI on success. Returns None (never raises) if AWS keys are
    not configured, boto3 is unavailable, or the upload fails, so the pipeline
    simply continues with the PDF held in memory.
    """

    access_key = settings.AWS_ACCESS_KEY_ID
    secret_key = settings.AWS_SECRET_ACCESS_KEY
    session_token = settings.AWS_SESSION_TOKEN
    region = settings.AWS_REGION
    bucket = settings.AWS_S3_BUCKET

    if not pdf_bytes or not cache_key or not access_key or not secret_key:
        return None

    s3_key = _get_s3_key(cache_key)

    def _upload() -> None:
        import boto3
        from botocore.config import Config

        s3_config = Config(
            connect_timeout=3,
            read_timeout=5,
            retries={"max_attempts": 1},
        )

        client_kwargs: Dict[str, Any] = {
            "region_name": region,
            "config": s3_config,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }

        if session_token:
            client_kwargs["aws_session_token"] = session_token

        client = boto3.client("s3", **client_kwargs)
        client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )

    try:
        await asyncio.to_thread(_upload)
    except Exception as exc:  # noqa: BLE001 - caching must never break the pipeline
        logger.warning("S3 caching failed for '%s': %s", cache_key, exc)
        return None

    return f"s3://{bucket}/{s3_key}"


async def download_and_extract_pdf(
    pdf_url: str,
    cache_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Download a paper PDF and extract its text and key sections."""

    if not pdf_url or not pdf_url.strip():
        return {
            "raw_text": "",
            "sections": {},
        }

    try:
        # Check S3 cache first before network download to save bandwidth and avoid rate limits
        if cache_key:
            cached_bytes = await get_pdf_from_s3(cache_key)
            if cached_bytes:
                try:
                    raw_text = _extract_pdf_text(cached_bytes)
                except Exception as exc:  # noqa: BLE001 - corrupt cache falls back to download
                    logger.warning("Cached PDF extraction failed for '%s': %s", cache_key, exc)
                else:
                    if raw_text:
                        logger.info(
                            "Found cached PDF in S3 for '%s'. Skipping network download.", cache_key
                        )
                        return {
                            "raw_text": raw_text,
                            "sections": _extract_sections(raw_text),
                        }

        # Enforce SSRF protection before downloading
        safe_url = enforce_pdf_url_safety(pdf_url)
        pdf_bytes = await _download_pdf(safe_url)

        if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
            # Connect HTML fallback if the response is an Open Access HTML article
            if pdf_bytes and (
                pdf_bytes.lstrip().startswith(b"<!doctype html")
                or pdf_bytes.lstrip().startswith(b"<!DOCTYPE html")
                or pdf_bytes.lstrip().startswith(b"<html")
                or b"<article" in pdf_bytes[:500]
            ):
                try:
                    html_text = pdf_bytes.decode("utf-8", errors="replace")
                    html_data = extract_html_article_text(html_text)
                    if html_data.get("sections") and html_data.get("raw_text"):
                        logger.info("Extracted HTML article full text for '%s'", pdf_url)
                        return html_data
                except Exception as html_exc:  # noqa: BLE001
                    logger.debug("HTML extraction fallback failed for '%s': %s", pdf_url, html_exc)

            if pdf_bytes and not pdf_bytes.startswith(b"%PDF"):
                logger.warning(
                    "Downloaded content for '%s' is not a valid PDF (header: %s).",
                    pdf_url,
                    pdf_bytes[:16],
                )
            return {
                "raw_text": "",
                "sections": {},
            }

        raw_text = _extract_pdf_text(pdf_bytes)

        if not raw_text:
            return {
                "raw_text": "",
                "sections": {},
            }

        if cache_key:
            await cache_pdf_to_s3(pdf_bytes, cache_key)

        sections = _extract_sections(raw_text)

        return {
            "raw_text": raw_text,
            "sections": sections,
        }

    except (
        httpx.HTTPError,
        OSError,
        ValueError,
    ) as exc:
        logger.warning("PDF download or extraction failed for '%s': %s", pdf_url, exc)
        return {
            "raw_text": "",
            "sections": {},
        }
