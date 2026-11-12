"""Academic literature search service wrapper (ArXiv, PubMed & Crossref APIs)."""

import asyncio
import logging
import time
from typing import Any, Dict, List

import defusedxml.ElementTree as ET
import httpx

from app.core.config import Settings
from app.services.redis_service import get_cached_query, set_cached_query

logger = logging.getLogger(__name__)
settings = Settings()

ARXIV_API_URL = "https://export.arxiv.org/api/query"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CROSSREF_API_URL = "https://api.crossref.org/works"

REQUEST_TIMEOUT = 10.0
CACHE_EXPIRY = 3600
ACADEMIC_USER_AGENT = "Scholaris-Academic-Assistant/1.0 (https://github.com/saumyashah0510/Multi-Agent-Research-System-Architecture; mailto:saumyashah0510@gmail.com)"

ARXIV_NAMESPACE = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


_arxiv_lock = asyncio.Lock()
_last_arxiv_time = 0.0


async def _request_with_retries(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    retries: int = 3,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Make an HTTP request with retries for rate limits and network errors."""
    req_kwargs: dict[str, Any] = {"params": params}
    if headers:
        req_kwargs["headers"] = headers

    for attempt in range(retries):
        try:
            response = await client.get(url, **req_kwargs)

            if response.status_code == 429 or "Rate exceeded" in getattr(response, "text", ""):
                if attempt == retries - 1:
                    response.raise_for_status()

                retry_after_hdr = (
                    response.headers.get("Retry-After") if hasattr(response, "headers") else None
                )
                try:
                    retry_after = float(retry_after_hdr) if retry_after_hdr else None
                except (ValueError, TypeError):
                    retry_after = None

                backoff = retry_after if retry_after is not None else max(3.5, 2.0**attempt)
                await asyncio.sleep(backoff)
                continue

            response.raise_for_status()
            return response

        except httpx.HTTPError:
            if attempt == retries - 1:
                raise

            backoff = max(3.5, 2.0**attempt)
            await asyncio.sleep(backoff)

    raise httpx.HTTPError("Request failed after retries")


async def _search_arxiv(
    client: httpx.AsyncClient,
    query: str,
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search ArXiv and convert the Atom response into paper dictionaries."""
    global _last_arxiv_time
    try:
        async with _arxiv_lock:
            now = time.monotonic()
            elapsed = now - _last_arxiv_time
            if elapsed < 3.2:
                await asyncio.sleep(3.2 - elapsed)
            _last_arxiv_time = time.monotonic()

            response = await _request_with_retries(
                client,
                ARXIV_API_URL,
                params={
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": max_results,
                },
                headers={"User-Agent": ACADEMIC_USER_AGENT},
            )

        if "Rate exceeded" in response.text:
            logger.warning("ArXiv rate limit hit ('Rate exceeded.') for query: %s", query)
            return []

        root = ET.fromstring(response.text)
        results: List[Dict[str, Any]] = []

        for entry in root.findall("atom:entry", ARXIV_NAMESPACE):
            title = entry.findtext(
                "atom:title",
                default="",
                namespaces=ARXIV_NAMESPACE,
            ).strip()

            abstract = entry.findtext(
                "atom:summary",
                default="",
                namespaces=ARXIV_NAMESPACE,
            ).strip()

            publication_date = entry.findtext(
                "atom:published",
                default="",
                namespaces=ARXIV_NAMESPACE,
            ).strip()

            paper_id = entry.findtext(
                "atom:id",
                default="",
                namespaces=ARXIV_NAMESPACE,
            ).strip()

            authors = []
            for author in entry.findall("atom:author", ARXIV_NAMESPACE):
                author_name = author.findtext(
                    "atom:name",
                    default="",
                    namespaces=ARXIV_NAMESPACE,
                ).strip()
                if author_name:
                    authors.append(author_name)

            arxiv_id = paper_id.rsplit("/", 1)[-1] if paper_id else None
            pdf_url = None

            for link in entry.findall("atom:link", ARXIV_NAMESPACE):
                if link.attrib.get("title") == "pdf":
                    pdf_url = link.attrib.get("href")
                    break

            doi = entry.findtext(
                "arxiv:doi",
                default="",
                namespaces=ARXIV_NAMESPACE,
            ).strip()

            results.append(
                {
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "publication_date": publication_date,
                    "arxiv_id": arxiv_id,
                    "doi": doi or None,
                    "pdf_url": pdf_url,
                    "source": "arxiv",
                }
            )

        return results

    except (httpx.HTTPError, ET.ParseError) as exc:
        logger.warning("ArXiv search failed for query '%s': %s", query, exc)
        raise


async def _search_pubmed(
    client: httpx.AsyncClient,
    query: str,
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search PubMed and convert XML response into paper dictionaries."""
    try:
        search_response = await _request_with_retries(
            client,
            PUBMED_SEARCH_URL,
            params={
                "db": "pubmed",
                "term": query,
                "retmode": "xml",
                "retmax": max_results,
            },
        )

        search_root = ET.fromstring(search_response.text)
        pmids = [element.text for element in search_root.findall(".//Id") if element.text]

        if not pmids:
            return []

        fetch_response = await _request_with_retries(
            client,
            PUBMED_FETCH_URL,
            params={
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml",
            },
        )

        root = ET.fromstring(fetch_response.text)
        results: List[Dict[str, Any]] = []

        for article in root.findall(".//PubmedArticle"):
            title_element = article.find(".//ArticleTitle")
            title = "".join(title_element.itertext()).strip() if title_element is not None else ""

            abstract_parts = []
            for abstract_text in article.findall(".//Abstract/AbstractText"):
                text = "".join(abstract_text.itertext()).strip()
                if text:
                    label = abstract_text.attrib.get("Label")
                    if label:
                        abstract_parts.append(f"{label}: {text}")
                    else:
                        abstract_parts.append(text)

            abstract = " ".join(abstract_parts)
            authors = []

            for author in article.findall(".//Author"):
                last_name = author.findtext("LastName", default="")
                fore_name = author.findtext("ForeName", default="")
                full_name = " ".join(part for part in [fore_name, last_name] if part).strip()
                if full_name:
                    authors.append(full_name)

            pmid = article.findtext(".//PMID", default="").strip()
            doi = None
            for article_id in article.findall(".//ArticleId"):
                if article_id.attrib.get("IdType") == "doi":
                    doi = article_id.text
                    break

            publication_date = ""
            pub_date = article.find(".//PubDate")
            if pub_date is not None:
                year = pub_date.findtext("Year", default="")
                month = pub_date.findtext("Month", default="")
                day = pub_date.findtext("Day", default="")
                publication_date = "-".join(part for part in [year, month, day] if part)

            results.append(
                {
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "publication_date": publication_date,
                    "arxiv_id": None,
                    "doi": doi,
                    "pdf_url": None,
                    "source": "pubmed",
                    "pubmed_id": pmid,
                }
            )

        return results

    except (httpx.HTTPError, ET.ParseError) as exc:
        logger.warning("PubMed search failed for query '%s': %s", query, exc)
        raise


async def _search_crossref(
    client: httpx.AsyncClient,
    query: str,
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search Crossref API and return structured paper dictionaries."""
    try:
        response = await _request_with_retries(
            client,
            CROSSREF_API_URL,
            params={
                "query": query,
                "rows": max_results,
            },
        )
        data = response.json()
        items = data.get("message", {}).get("items", [])
        results: List[Dict[str, Any]] = []

        for item in items:
            titles = item.get("title") or []
            title = titles[0].strip() if titles else ""

            authors_list = []
            for a in item.get("author", []):
                name_parts = [a.get("given", ""), a.get("family", "")]
                full_name = " ".join(p for p in name_parts if p).strip()
                if full_name:
                    authors_list.append(full_name)

            doi = item.get("DOI")
            published = item.get("published-print") or item.get("published-online") or {}
            date_parts = published.get("date-parts", [[]])[0]
            year = date_parts[0] if date_parts else None

            # Look for open-access PDF link
            pdf_url = None
            for link in item.get("link", []):
                if link.get("content-type") == "application/pdf":
                    pdf_url = link.get("URL")
                    break

            results.append(
                {
                    "title": title,
                    "authors": authors_list,
                    "abstract": (item.get("abstract") or "").strip(),
                    "publication_date": str(year) if year else "",
                    "published_year": year,
                    "arxiv_id": None,
                    "doi": doi,
                    "pdf_url": pdf_url,
                    "source": "crossref",
                }
            )

        return results
    except Exception as err:
        logger.warning(f"Crossref API search error: {err}")
        raise


async def search_academic_papers(
    query: str,
    max_results: int = 20,
    sources: list[str] | None = None,
) -> List[Dict[str, Any]]:
    """Search academic repositories for literature matching query."""
    if not query.strip():
        return []

    if sources is None:
        sources = ["arxiv", "pubmed", "crossref"]

    sources = [source.lower() for source in sources]

    cache_key = (
        f"academic_search:v2:{query.strip().lower()}:{max_results}:{','.join(sorted(sources))}"
    )

    cached_results = await get_cached_query(cache_key, as_json=True)
    if cached_results is not None:
        return cached_results

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        follow_redirects=True,
        max_redirects=5,
        headers={"User-Agent": ACADEMIC_USER_AGENT},
    ) as client:
        source_tasks = {}

        if "arxiv" in sources:
            source_tasks["arxiv"] = _search_arxiv(client, query, max_results)

        if "pubmed" in sources:
            source_tasks["pubmed"] = _search_pubmed(client, query, max_results)

        if "crossref" in sources:
            source_tasks["crossref"] = _search_crossref(client, query, max_results)

        if not source_tasks:
            return []

        search_results = await asyncio.gather(*source_tasks.values(), return_exceptions=True)

    papers: List[Dict[str, Any]] = []
    failed_sources: List[str] = []

    for source, result in zip(source_tasks.keys(), search_results, strict=True):
        if isinstance(result, BaseException):
            failed_sources.append(source)
            logger.error(
                "Academic source '%s' failed for query '%s': %s",
                source,
                query,
                result,
            )
            continue
        if isinstance(result, list):
            logger.info(
                "Academic source '%s' returned %d papers for query '%s'",
                source,
                len(result),
                query,
            )
            papers.extend(result)

    # Only cache complete multi-source results; never cache partial failures
    if not failed_sources and papers:
        try:
            await set_cached_query(cache_key, papers, expire_seconds=CACHE_EXPIRY)
        except Exception:
            pass
    elif failed_sources:
        logger.warning(
            "Skipping Redis search cache for query '%s' due to failed sources: %s",
            query,
            failed_sources,
        )

    return papers
