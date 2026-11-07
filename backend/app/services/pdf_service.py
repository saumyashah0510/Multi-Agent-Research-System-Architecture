"""Async PDF downloading and text extraction service with SSRF defense."""

import asyncio
import io
import logging
import re
from typing import Any, Dict, Optional

import httpx
from pypdf import PdfReader

from app.core.config import settings
from app.core.guardrails import enforce_pdf_url_safety

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


def _detect_section_heading(line: str) -> str | None:
    """Return the canonical section name for a recognized heading."""

    normalized = _normalize_heading(line)

    for section_name, aliases in SECTION_ALIASES.items():
        if normalized in aliases:
            return section_name

    return None


def _extract_sections(raw_text: str) -> Dict[str, str]:
    """Extract common academic paper sections from raw PDF text."""

    sections: Dict[str, str] = {}

    current_section: str | None = None
    current_lines: list[str] = []

    def save_current_section() -> None:
        if current_section is None:
            return

        content = "\n".join(current_lines).strip()

        if content:
            if current_section in sections:
                sections[current_section] += "\n" + content
            else:
                sections[current_section] = content

    for line in raw_text.splitlines():
        stripped_line = line.strip()

        if not stripped_line:
            if current_section is not None:
                current_lines.append("")
            continue

        detected_section = _detect_section_heading(stripped_line)

        if detected_section is not None:
            save_current_section()

            current_section = detected_section
            current_lines = []
            continue

        if current_section is not None:
            current_lines.append(stripped_line)

    save_current_section()

    return sections


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from every page of a PDF."""

    reader = PdfReader(io.BytesIO(pdf_bytes))

    page_texts: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            page_texts.append(text.strip())

    return "\n\n".join(page_texts).strip()


async def _download_pdf(pdf_url: str) -> bytes:
    """Download PDF bytes asynchronously after enforcing SSRF URL safety."""
    safe_url = enforce_pdf_url_safety(pdf_url)

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
        response = await client.get(safe_url)
        response.raise_for_status()

        content_type = response.headers.get(
            "content-type",
            "",
        ).lower()

        if content_type and "pdf" not in content_type:
            # Some academic repositories may return an incorrect or
            # missing content type, so the actual PDF content is still
            # accepted if it can be parsed successfully.
            pass

        return response.content


def _get_s3_key(cache_key: str) -> str:
    """Return the deterministic S3 key for a given cache_key."""
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", cache_key):
        return f"{S3_PREFIX}{cache_key}.pdf"
    import hashlib

    title_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:12]
    clean_title = re.sub(r"[^A-Za-z0-9._-]", "_", cache_key)[:40].strip("_")
    return f"{S3_PREFIX}titles/{clean_title}_{title_hash}.pdf"


async def get_pdf_from_s3(cache_key: str) -> Optional[bytes]:
    """Retrieve a cached PDF from S3 if it exists and AWS credentials are configured.

    Returns the raw bytes if found in S3, or None if not cached, credentials are
    missing, or on error.
    """
    access_key = settings.AWS_ACCESS_KEY_ID
    secret_key = settings.AWS_SECRET_ACCESS_KEY
    if not cache_key or not access_key or not secret_key:
        return None

    s3_key = _get_s3_key(cache_key)

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
        try:
            response = client.get_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=s3_key,
            )
            body = response["Body"].read()
            if body and body.startswith(b"%PDF"):
                return body
        except ClientError:
            return None
        except Exception as exc:  # noqa: BLE001 - cache read failure falls back to download
            logger.debug("S3 fetch failed for key '%s': %s", s3_key, exc)
            return None
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
                logger.info(
                    "Found cached PDF in S3 for '%s'. Skipping network download.", cache_key
                )
                raw_text = _extract_pdf_text(cached_bytes)
                if raw_text:
                    return {
                        "raw_text": raw_text,
                        "sections": _extract_sections(raw_text),
                    }

        # Enforce SSRF protection before downloading
        safe_url = enforce_pdf_url_safety(pdf_url)
        pdf_bytes = await _download_pdf(safe_url)

        if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
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

        if cache_key:
            await cache_pdf_to_s3(pdf_bytes, cache_key)

        raw_text = _extract_pdf_text(pdf_bytes)

        if not raw_text:
            return {
                "raw_text": "",
                "sections": {},
            }

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
