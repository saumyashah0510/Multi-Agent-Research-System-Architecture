"""Academic literature search service wrapper (ArXiv, PubMed, Semantic Scholar & Crossref APIs)."""

import asyncio
import logging
from typing import Any, Dict, List

import defusedxml.ElementTree as ET
import httpx

from app.services.redis_service import get_cached_query, set_cached_query

logger = logging.getLogger(__name__)

ARXIV_API_URL = "http://export.arxiv.org/api/query"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_API_URL = "https://api.crossref.org/works"

REQUEST_TIMEOUT = 10.0
CACHE_EXPIRY = 3600

ARXIV_NAMESPACE = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


async def _request_with_retries(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any],
    retries: int = 3,
) -> httpx.Response:
    """Make an HTTP request with retries for rate limits and network errors."""
    for attempt in range(retries):
        try:
            response = await client.get(url, params=params)

            if response.status_code == 429:
                if attempt == retries - 1:
                    response.raise_for_status()

                await asyncio.sleep(2**attempt)
                continue

            response.raise_for_status()
            return response

        except httpx.HTTPError:
            if attempt == retries - 1:
                raise

            await asyncio.sleep(2**attempt)

    raise httpx.HTTPError("Request failed after retries")


async def _search_arxiv(
    client: httpx.AsyncClient,
    query: str,
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search ArXiv and convert the Atom response into paper dictionaries."""
    try:
        response = await _request_with_retries(
            client,
            ARXIV_API_URL,
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
            },
        )

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

    except (httpx.HTTPError, ET.ParseError):
        return []


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

    except (httpx.HTTPError, ET.ParseError):
        return []


async def _search_semantic_scholar(
    client: httpx.AsyncClient,
    query: str,
    max_results: int,
) -> List[Dict[str, Any]]:
    """Search Semantic Scholar API and return structured paper dictionaries."""
    try:
        response = await _request_with_retries(
            client,
            SEMANTIC_SCHOLAR_URL,
            params={
                "query": query,
                "limit": max_results,
                "fields": "title,authors,abstract,year,externalIds,openAccessPdf",
            },
        )
        data = response.json()
        results: List[Dict[str, Any]] = []

        for item in data.get("data", []):
            title = (item.get("title") or "").strip()
            abstract = (item.get("abstract") or "").strip()
            year = item.get("year")
            authors_list = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
            ext_ids = item.get("externalIds") or {}
            arxiv_id = ext_ids.get("ArXiv")
            doi = ext_ids.get("DOI")

            pdf_info = item.get("openAccessPdf") or {}
            pdf_url = pdf_info.get("url")

            results.append(
                {
                    "title": title,
                    "authors": authors_list,
                    "abstract": abstract,
                    "publication_date": str(year) if year else "",
                    "published_year": year,
                    "arxiv_id": arxiv_id,
                    "doi": doi,
                    "pdf_url": pdf_url,
                    "source": "semanticscholar",
                }
            )

        return results
    except Exception as err:
        logger.warning(f"Semantic Scholar API search error: {err}")
        return []


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
        return []


async def search_academic_papers(
    query: str,
    max_results: int = 20,
    sources: list[str] | None = None,
) -> List[Dict[str, Any]]:
    """Search academic repositories for literature matching query."""
    if not query.strip():
        return []

    if sources is None:
        sources = ["arxiv", "pubmed", "semanticscholar", "crossref"]

    sources = [source.lower() for source in sources]

    cache_key = (
        f"academic_search:{query.strip().lower()}:" f"{max_results}:{','.join(sorted(sources))}"
    )

    cached_results = await get_cached_query(cache_key, as_json=True)
    if cached_results is not None:
        return cached_results

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        tasks = []

        if "arxiv" in sources:
            tasks.append(_search_arxiv(client, query, max_results))

        if "pubmed" in sources:
            tasks.append(_search_pubmed(client, query, max_results))

        if "semanticscholar" in sources:
            tasks.append(_search_semantic_scholar(client, query, max_results))

        if "crossref" in sources:
            tasks.append(_search_crossref(client, query, max_results))

        if not tasks:
            return []

        search_results = await asyncio.gather(*tasks, return_exceptions=True)

    papers: List[Dict[str, Any]] = []
    for result in search_results:
        if isinstance(result, list):
            papers.extend(result)

    try:
        await set_cached_query(cache_key, papers, expire_seconds=CACHE_EXPIRY)
    except Exception:
        pass

    return papers
