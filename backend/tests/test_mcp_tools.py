from app import mcp_tools


def test_literature_query_anchors_method_to_drug_interactions():
    query = mcp_tools._literature_query(
        "Machine learning methods for drug-drug interaction prediction"
    )
    assert '"drug-drug interaction"' in query
    assert " AND " in query
    assert '"machine learning"' in query


def test_search_sources_returns_flat_evidence_payload(monkeypatch):
    monkeypatch.setattr(mcp_tools, "load_documents", lambda: [])
    document = {
        "document_id": "EPMC:MED:123",
        "title": "A biomedical study",
        "source": "https://europepmc.org/article/MED/123",
        "text": "Abstract text",
        "relevance": 1.0,
    }
    monkeypatch.setattr(
        mcp_tools,
        "_europe_pmc_search",
        lambda query, limit: ([document], 1, "test query"),
    )

    result = mcp_tools.search_sources("drug interaction", 3)

    assert result["items"] == [document]
    assert result["source_status"]["europe_pmc"]["ok"] is True


def test_search_sources_exposes_external_source_failures(monkeypatch):
    monkeypatch.setattr(mcp_tools, "load_documents", lambda: [])

    def fail_search(query, limit):
        raise RuntimeError("Europe PMC unavailable")

    monkeypatch.setattr(mcp_tools, "_europe_pmc_search", fail_search)
    result = mcp_tools.search_sources("drug interaction", 3)

    assert result["items"] == []
    assert result["source_status"]["europe_pmc"]["ok"] is False
    assert "Europe PMC unavailable" in result["source_status"]["europe_pmc"]["error"]
