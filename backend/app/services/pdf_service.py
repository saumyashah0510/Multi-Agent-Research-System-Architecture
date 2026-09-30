"""Async PDF downloading and text extraction service."""

import io
import re
from typing import Any, Dict

import httpx
from pypdf import PdfReader

REQUEST_TIMEOUT = 10.0


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
    """Download PDF bytes asynchronously."""

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:
        response = await client.get(pdf_url)
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


async def download_and_extract_pdf(
    pdf_url: str,
) -> Dict[str, Any]:
    """Download a paper PDF and extract its text and key sections."""

    if not pdf_url or not pdf_url.strip():
        return {
            "raw_text": "",
            "sections": {},
        }

    try:
        pdf_bytes = await _download_pdf(pdf_url)

        if not pdf_bytes:
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

        sections = _extract_sections(raw_text)

        return {
            "raw_text": raw_text,
            "sections": sections,
        }

    except (
        httpx.HTTPError,
        OSError,
        ValueError,
    ):
        return {
            "raw_text": "",
            "sections": {},
        }
