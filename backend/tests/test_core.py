from app.agents import EvaluatorAgent
from app.mcp_tools import get_document, search_sources
from app.model_service import is_retryable_gemini_error


def test_corpus_search_returns_relevant_documents():
    results = search_sources("orchestrator agents MCP", 5)
    assert results
    assert all("document_id" in item for item in results)
    assert all("text" in item for item in results)


def test_document_lookup_returns_full_document():
    results = search_sources("orchestrator agents MCP", 1)
    document = get_document(results[0]["document_id"])
    assert document["document_id"] == results[0]["document_id"]
    assert document["text"]


def test_search_rejects_empty_query():
    import pytest

    with pytest.raises(ValueError):
        search_sources("   ")


def test_cost_formula_example():
    input_tokens, output_tokens = 4000, 1000
    input_price, output_price = 1.0, 5.0
    cost = (
        input_tokens / 1_000_000 * input_price
        + output_tokens / 1_000_000 * output_price
    )
    assert abs(cost - 0.009) < 1e-9


def test_retryable_gemini_errors():
    class ApiError(Exception):
        code = 503

    assert is_retryable_gemini_error(ApiError("busy"))
    assert is_retryable_gemini_error(Exception("429 RESOURCE_EXHAUSTED"))
    assert not is_retryable_gemini_error(Exception("401 invalid API key"))


def test_no_claims_metrics_are_not_applicable():
    result = EvaluatorAgent().run(
        "No verified answer.", [], [{"evidence_id": "E1"}]
    )
    assert result["groundedness"] is None
    assert result["evidence_coverage"] is None
    assert result["hallucination_rate"] is None
    assert result["task_success"] is False
