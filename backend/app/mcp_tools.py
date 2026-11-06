import os
import re

import httpx

from .storage import load_documents

EUROPE_PMC_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _local_search(query, limit):
    stop = {
        "about", "after", "against", "among", "also", "and", "approach",
        "approaches", "are", "based", "between", "both", "can", "compare",
        "comparison", "could", "does", "from", "have", "how", "into", "its",
        "major", "method", "methods", "their", "them", "these", "those",
        "through", "using", "what", "when", "where", "which", "while", "with",
        "within", "would", "evaluate", "evaluation", "role", "benefits",
        "limitations", "challenges", "support", "supported",
    }
    terms = {
        word.casefold()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", query)
        if word.casefold() not in stop
    }
    if not terms:
        return []
    found = []
    for document in load_documents():
        text = (
            str(document.get("title", "")) + " " +
            str(document.get("text", ""))
        ).casefold()
        overlap = sum(bool(re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text)) for term in terms)
        # Avoid treating generic word overlap as meaningful source retrieval.
        if overlap >= 2:
            found.append({
                **document,
                "relevance": round(overlap / len(terms), 3),
            })
    return sorted(found, key=lambda item: item["relevance"], reverse=True)[:limit]


def _literature_query(query):
    """Turn natural-language research tasks into compact Europe PMC queries."""
    text = re.sub(r"\s+", " ", query.casefold()).strip()
    groups = []

    concepts = [
        (("drug-drug interaction", "drug drug interaction", "drug interaction", "ddi"),
         '"drug-drug interaction" OR "drug interaction" OR DDI'),
        (("knowledge graph", "knowledge graphs", "biomedical graph"),
         '"knowledge graph" OR "knowledge graphs" OR "biomedical knowledge graph"'),
        (("machine learning", "deep learning"),
         '"machine learning" OR "deep learning"'),
        (("ontology", "ontologies"),
         'ontology OR ontologies'),
        (("drug discovery",), '"drug discovery"'),
        (("clinical decision support",), '"clinical decision support"'),
        (("heterogeneous data", "data integration"),
         '"data integration" OR "heterogeneous data"'),
        (("prediction", "predictive"), 'prediction OR predictive'),
    ]
    for needles, expression in concepts:
        if any(needle in text for needle in needles):
            groups.append(f"({expression})")

    if not groups:
        stop = {
            "about", "after", "also", "among", "approach", "approaches",
            "based", "between", "both", "can", "compare", "comparison",
            "does", "from", "have", "into", "its", "major", "methods",
            "their", "these", "those", "using", "what", "which", "with",
            "would", "evaluate", "evaluation", "benefits", "limitations",
            "challenges", "support", "research", "literature",
        }
        words = []
        for word in re.findall(r"[a-z][a-z0-9-]{2,}", text):
            if word not in stop and word not in words:
                words.append(word)
            if len(words) == 8:
                break
        groups = [f'"{word}"' for word in words]

    # Anchor method searches to the requested biomedical task. OR is used
    # among synonymous approaches, while AND connects the task to its method.
    domain_groups = [
        group for group in groups
        if '"drug-drug interaction"' in group
        or '"drug discovery"' in group
        or '"clinical decision support"' in group
    ]
    method_groups = [
        group for group in groups
        if '"knowledge graph"' in group
        or '"machine learning"' in group
        or "ontology OR ontologies" in group
        or '"data integration"' in group
    ]
    if domain_groups and method_groups:
        return f"{domain_groups[0]} AND ({' OR '.join(method_groups)})"
    if domain_groups:
        return domain_groups[0]
    # A topic-only query can broaden recall safely across synonymous concepts.
    return " OR ".join((method_groups or groups)[:4]) or query


def _europe_pmc_search(query, limit):
    """Retrieve biomedical literature abstracts from the public Europe PMC API."""
    timeout = max(
        2.0,
        min(float(os.getenv("STUDENTFLOW_SOURCE_TIMEOUT_SECONDS", "6")), 10.0),
    )
    search_query = _literature_query(query)
    response = httpx.get(
        EUROPE_PMC_URL,
        params={
            "query": search_query,
            "format": "json",
            "pageSize": limit,
            "resultType": "core",
            "synonym": "true",
            # Omit sort: Europe PMC defaults to relevance order.
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
        url = f"https://europepmc.org/article/{source_name}/{source_id}"
        journal = record.get("journalTitle")
        if not journal:
            journal_info = record.get("journalInfo") or {}
            journal = (journal_info.get("journal") or {}).get("title", "")
        metadata = " | ".join(
            value for value in (
                str(record.get("authorString") or "").strip(),
                str(journal or "").strip(),
                str(record.get("pubYear") or "").strip(),
                str(record.get("doi") or "").strip(),
            ) if value
        )
        documents.append({
            "document_id": f"EPMC:{source_name}:{source_id}",
            "title": title,
            "source": url,
            "text": f"Publication metadata: {metadata}\nAbstract: {abstract}",
            "relevance": 1.0,
        })
    return documents, int(payload.get("hitCount") or 0), search_query


def search_sources(query, limit=5):
    """Search local notes and external literature; report external failures explicitly."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query must be non-empty")
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError) as exc:
        raise ValueError("Limit must be an integer") from exc

    local = _local_search(query, limit)
    remote = []
    source_status = {
        "local": {"ok": True, "returned": len(local)},
        "europe_pmc": {"ok": False, "returned": 0, "hit_count": 0},
    }
    try:
        remote, hit_count, used_query = _europe_pmc_search(query.strip(), limit)
        source_status["europe_pmc"] = {
            "ok": True,
            "returned": len(remote),
            "hit_count": hit_count,
            "query": used_query,
        }
    except Exception as exc:
        source_status["europe_pmc"]["error"] = (
            f"{type(exc).__name__}: {str(exc)[:300]}"
        )

    combined = []
    seen = set()
    for document in remote + local:
        document_id = str(document.get("document_id") or "")
        if document_id and document_id not in seen:
            combined.append(document)
            seen.add(document_id)
    return {
        "items": combined[:limit],
        "source_status": source_status,
    }


def get_document(document_id):
    """Retrieve a full local source document by its stable ID."""
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("Document ID must be non-empty")
    return next(
        (doc for doc in load_documents() if doc.get("document_id") == document_id),
        {"error": "document_not_found"},
    )
