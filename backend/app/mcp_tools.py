from .storage import load_documents


def search_sources(query, limit=5):
    """Search the curated StudentFlow corpus and return matching evidence records."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query must be non-empty")
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError) as exc:
        raise ValueError("Limit must be an integer") from exc

    terms = {word.lower() for word in query.split() if len(word) > 2}
    if not terms:
        return []

    found = []
    for document in load_documents():
        text = (
            str(document.get("title", "")) + " " +
            str(document.get("text", ""))
        ).lower()
        overlap = sum(term in text for term in terms)
        if overlap:
            found.append({
                **document,
                "relevance": round(overlap / len(terms), 3),
            })

    return sorted(found, key=lambda item: item["relevance"], reverse=True)[:limit]


def get_document(document_id):
    """Retrieve a full source document by its stable ID."""
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("Document ID must be non-empty")
    return next(
        (doc for doc in load_documents() if doc.get("document_id") == document_id),
        {"error": "document_not_found"},
    )
