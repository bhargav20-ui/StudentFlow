import os
import re

import httpx

from .storage import load_documents

EUROPE_PMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _local_search(query, limit):
    terms = {word.lower() for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9-]+", query) if len(word) > 2}
    if not terms:
        return []
    found = []
    for document in load_documents():
        text = (str(document.get("title", "")) + " " + str(document.get("text", ""))).lower()
        overlap = sum(term in text for term in terms)
        if overlap:
            found.append({
                **document,
                "relevance": round(overlap / len(terms), 3),
            })
    return sorted(found, key=lambda item: item["relevance"], reverse=True)[:limit]


def _europe_pmc_search(query, limit):
    """Retrieve real biomedical literature abstracts from the public Europe PMC API."""
    timeout = max(2.0, min(float(os.getenv("STUDENTFLOW_SOURCE_TIMEOUT_SECONDS", "7")), 12.0))
    response = httpx.get(
        EUROPE_PMC_URL,
        params={
            "query": query,
            "format": "json",
            "pageSize": limit,
            "resultType": "core",
            "sort": "RELEVANCE",
        },
        timeout=timeout,
        headers={"User-Agent": "StudentFlow/1.0 (evidence-first research assistant)"},
    )
    response.raise_for_status()
    payload = response.json()
    records = payload.get("resultList", {}).get("result", [])
    documents = []
    for record in records:
        title = str(record.get("title") or "").strip()
        abstract = str(record.get("abstractText") or "").strip()
        source_id = str(record.get("id") or "").strip()
        source_name = str(record.get("source") or "MED")
        if not title or not abstract or not source_id:
            continue
        if source_name == "MED":
            url = f"https://europepmc.org/article/MED/{source_id}"
        else:
            url = f"https://europepmc.org/article/{source_name}/{source_id}"
        metadata = " | ".join(
            value for value in (
                str(record.get("authorString") or "").strip(),
                str(record.get("journalTitle") or "").strip(),
                str(record.get("pubYear") or "").strip(),
                str(record.get("doi") or "").strip(),
            ) if value
        )
        documents.append({
            "document_id": f"EPMC:{source_name}:{source_id}",
            "title": title,
            "source": url,
            "text": (f"Publication metadata: {metadata}\nAbstract: {abstract}" if metadata else abstract),
            "relevance": 1.0,
        })
    return documents


def search_sources(query, limit=5):
    """Search local notes and biomedical literature; remote failures never fabricate results."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query must be non-empty")
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError) as exc:
        raise ValueError("Limit must be an integer") from exc

    local = _local_search(query, limit)
    try:
        remote = _europe_pmc_search(query.strip(), limit)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        remote = []

    combined = []
    seen = set()
    for document in remote + local:
        document_id = str(document.get("document_id") or "")
        if document_id and document_id not in seen:
            combined.append(document)
            seen.add(document_id)
    return combined[:limit]


def get_document(document_id):
    """Retrieve a full source document by its stable ID."""
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("Document ID must be non-empty")
    return next(
        (doc for doc in load_documents() if doc.get("document_id") == document_id),
        {"error": "document_not_found"},
    )
