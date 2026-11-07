"""AI Safety and Input Guardrails module.

Provides enterprise-grade defense against:
1. Adversarial prompt injections, system prompt leak attempts, and jailbreaks.
2. Malformed, oversized, or empty research queries.
3. Server-Side Request Forgery (SSRF) and malicious redirects in academic PDF fetching.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

MIN_QUERY_LENGTH = 5
MAX_QUERY_LENGTH = 1000

# High-confidence prompt injection, jailbreak, and system extraction signatures
PROMPT_INJECTION_PATTERNS = [
    # Instruction override / forget prompts
    re.compile(
        r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|system)\s+(?:instructions|prompts|rules|commands)\b",
        re.IGNORECASE,
    ),
    # System prompt extraction
    re.compile(
        r"\b(?:reveal|output|display|show|print|leak|repeat)\s+(?:your\s+)?(?:system\s+prompt|initial\s+instructions|core\s+prompt|developer\s+mode)\b",
        re.IGNORECASE,
    ),
    # Persona hijacking & Jailbreaks (DAN, unrestricted, developer mode)
    re.compile(
        r"\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(?:an?\s+)?(?:DAN|unrestricted|jailbroken|unfiltered|free\s+AI|evil)\b",
        re.IGNORECASE,
    ),
    # Safety bypass commands
    re.compile(
        r"\b(?:without|bypass|disable|turn\s+off|override)\s+(?:safety|guardrails|filters|content\s+moderation|ethical\s+guidelines)\b",
        re.IGNORECASE,
    ),
    # HTML / Script injection attempt inside academic queries
    re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
]

# Trusted academic domains allowed for automated full-text PDF retrieval
TRUSTED_ACADEMIC_DOMAINS = {
    "arxiv.org",
    "export.arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "openalex.org",
    "semanticscholar.org",
    "nature.com",
    "sciencedirect.com",
    "springer.com",
    "ieeexplore.ieee.org",
    "dl.acm.org",
    "frontiersin.org",
    "plos.org",
    "mdpi.com",
    "pnas.org",
    "europepmc.org",
    "unpaywall.org",
    "cell.com",
    "wiley.com",
    "tandfonline.com",
    "oup.com",
    "nih.gov",
}

# Blocked loopback / internal / private IP representations
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # IPv4 loopback
    ipaddress.ip_network("10.0.0.0/8"),  # RFC 1918 private
    ipaddress.ip_network("172.16.0.0/12"),  # RFC 1918 private
    ipaddress.ip_network("192.168.0.0/16"),  # RFC 1918 private
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / AWS & Cloud Metadata
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",  # nosec: B104
    "metadata.google.internal",
    "169.254.169.254",
    "instance-data",
}


# ---------------------------------------------------------------------------
# Pydantic Result Schemas
# ---------------------------------------------------------------------------


class GuardrailResult(BaseModel):
    """Evaluation result for research query safety inspection."""

    is_valid: bool = Field(..., description="True if query passed all security and hygiene checks.")
    sanitized_query: str = Field(..., description="Cleaned, normalized query string.")
    violation_type: Optional[str] = Field(
        default=None,
        description="Type of violation detected: length_too_short, length_too_long, prompt_injection, or malformed.",
    )
    reason: Optional[str] = Field(
        default=None, description="Human-readable explanation of why the query failed guardrails."
    )


class UrlValidationResult(BaseModel):
    """Evaluation result for PDF URL SSRF security inspection."""

    is_safe: bool = Field(..., description="True if URL is safe to fetch without SSRF risk.")
    url: str = Field(..., description="Validated URL string.")
    domain: Optional[str] = Field(default=None, description="Extracted domain hostname.")
    reason: Optional[str] = Field(
        default=None, description="Reason why the URL is deemed unsafe or rejected."
    )


# ---------------------------------------------------------------------------
# Query Guardrail Implementation
# ---------------------------------------------------------------------------


def sanitize_input_text(text: str) -> str:
    """Strip dangerous control characters, normalize whitespace, and trim input."""
    if not text:
        return ""
    # Strip null bytes and control characters except standard tabs and newlines
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
    # Collapse multiple whitespaces/tabs into single space
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def validate_research_query(query: str) -> GuardrailResult:
    """Validate a user research query against adversarial prompt injection and bounds.

    Args:
        query: Raw search query input from the user.

    Returns:
        GuardrailResult with validation decision, sanitized query, and rationale.
    """
    sanitized = sanitize_input_text(query)

    if not sanitized or len(sanitized) < MIN_QUERY_LENGTH:
        return GuardrailResult(
            is_valid=False,
            sanitized_query=sanitized,
            violation_type="length_too_short",
            reason=f"Search query is too short. Minimum required length is {MIN_QUERY_LENGTH} characters.",
        )

    if len(sanitized) > MAX_QUERY_LENGTH:
        return GuardrailResult(
            is_valid=False,
            sanitized_query=sanitized[:MAX_QUERY_LENGTH],
            violation_type="length_too_long",
            reason=f"Search query exceeds maximum limit of {MAX_QUERY_LENGTH} characters.",
        )

    # Check for adversarial prompt injection patterns
    for pattern in PROMPT_INJECTION_PATTERNS:
        match = pattern.search(sanitized)
        if match:
            return GuardrailResult(
                is_valid=False,
                sanitized_query=sanitized,
                violation_type="prompt_injection",
                reason=(
                    "Query contains disallowed prompt manipulation or jailbreak instructions: "
                    f"'{match.group(0)}'."
                ),
            )

    return GuardrailResult(
        is_valid=True,
        sanitized_query=sanitized,
        violation_type=None,
        reason=None,
    )


def enforce_query_guardrail(query: str) -> str:
    """Enforce query guardrails, raising a FastAPI HTTPException 400 on violations.

    Args:
        query: Raw search query input.

    Returns:
        Cleaned, sanitized query string if valid.

    Raises:
        HTTPException: HTTP 400 Bad Request if guardrail validation fails.
    """
    result = validate_research_query(query)
    if not result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "GuardrailValidationError",
                "violation_type": result.violation_type,
                "message": result.reason,
            },
        )
    return result.sanitized_query


# ---------------------------------------------------------------------------
# SSRF & URL Safety Guardrail Implementation
# ---------------------------------------------------------------------------


def is_ip_address(host: str) -> bool:
    """Determine whether a hostname string is a raw IP address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def is_private_or_restricted_ip(host: str) -> bool:
    """Check if an IP address belongs to private, loopback, or cloud metadata subnets."""
    try:
        ip = ipaddress.ip_address(host)
        for network in BLOCKED_IP_NETWORKS:
            if ip in network:
                return True
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def validate_pdf_url(
    url: str,
    strict_academic_whitelist: bool = False,
    additional_allowed_domains: Optional[set[str]] = None,
) -> UrlValidationResult:
    """Inspect and sanitize candidate paper PDF URLs against SSRF and non-HTTPS endpoints.

    Args:
        url: The candidate URL to validate.
        strict_academic_whitelist: If True, only allow pre-approved academic domains.
        additional_allowed_domains: Optional set of extra domains to whitelist.

    Returns:
        UrlValidationResult specifying whether the URL is safe to download.
    """
    if not url or not isinstance(url, str):
        return UrlValidationResult(
            is_safe=False,
            url=str(url),
            reason="URL must be a non-empty string.",
        )

    parsed = urlparse(url.strip())

    # 1. Enforce HTTPS protocol only
    if parsed.scheme.lower() != "https":
        return UrlValidationResult(
            is_safe=False,
            url=url,
            reason=f"Insecure protocol '{parsed.scheme}'. Only HTTPS URLs are permitted for PDF fetching.",
        )

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        return UrlValidationResult(
            is_safe=False,
            url=url,
            reason="Invalid URL: host or domain name could not be parsed.",
        )

    # 2. Block localhost, cloud metadata, and internal hostnames
    if (
        hostname in BLOCKED_HOSTNAMES
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
    ):
        return UrlValidationResult(
            is_safe=False,
            url=url,
            domain=hostname,
            reason=f"Access to internal, loopback, or metadata host '{hostname}' is strictly forbidden (SSRF protection).",
        )

    # 3. Block raw IP addresses targeting internal subnets or cloud metadata
    if is_ip_address(hostname):
        if is_private_or_restricted_ip(hostname):
            return UrlValidationResult(
                is_safe=False,
                url=url,
                domain=hostname,
                reason=f"Direct access to private or metadata IP '{hostname}' is forbidden (SSRF protection).",
            )

    # 4. Academic domain whitelist validation (if strict mode enabled)
    allowed = TRUSTED_ACADEMIC_DOMAINS.copy()
    if additional_allowed_domains:
        allowed.update(d.lower() for d in additional_allowed_domains)

    if strict_academic_whitelist:
        # Match domain or any subdomain (e.g., pdfs.semanticscholar.org matches semanticscholar.org)
        domain_matches = any(hostname == d or hostname.endswith(f".{d}") for d in allowed)
        if not domain_matches:
            return UrlValidationResult(
                is_safe=False,
                url=url,
                domain=hostname,
                reason=(
                    f"Domain '{hostname}' is not in the approved academic repository whitelist."
                ),
            )

    return UrlValidationResult(
        is_safe=True,
        url=url,
        domain=hostname,
        reason=None,
    )


def enforce_pdf_url_safety(url: str, strict_academic_whitelist: bool = False) -> str:
    """Enforce PDF URL safety, raising a ValueError on unsafe or malicious targets.

    Args:
        url: URL string to inspect.
        strict_academic_whitelist: Whether to enforce trusted academic domains only.

    Returns:
        The safe URL string.

    Raises:
        ValueError: If URL fails SSRF safety checks.
    """
    res = validate_pdf_url(url, strict_academic_whitelist=strict_academic_whitelist)
    if not res.is_safe:
        raise ValueError(f"SSRF Protection Error: {res.reason}")
    return res.url
