import pytest

from app.agents import (
    EvaluatorAgent,
    PlannerAgent,
    ResearcherAgent,
    VerifierAgent,
    WriterAgent,
)


class FakeModel:
    def __init__(self, result=None, text=""):
        self.result = result or {}
        self.text = text
        self.prompts = []

    def generate(self, prompt, json_mode=False):
        self.prompts.append(prompt)
        return {
            "json": self.result if json_mode else None,
            "text": self.text,
            "input_tokens": 10,
            "output_tokens": 5,
            "cost_usd": None,
        }


def test_planner_returns_distinct_bounded_subtasks():
    model = FakeModel({"subtasks": [" Find causes ", "find causes", "Compare evidence"]})
    tasks, _ = PlannerAgent().run("Research the topic", model)
    assert tasks == ["Find causes", "Compare evidence"]


def test_planner_falls_back_when_model_returns_invalid_structure():
    model = FakeModel({"subtasks": "not-a-list"})
    tasks, _ = PlannerAgent().run("Research the topic", model)
    assert tasks == ["Research the topic"]


class FakeMCP:
    async def list_tools(self):
        return [{
            "name": "search_sources_tool",
            "description": "Search source documents",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["query"],
            },
        }]

    async def call_many(self, tool_name, argument_sets):
        assert tool_name == "search_sources_tool"
        return [{"items": [{
            "document_id": "DOC1",
            "title": "Source",
            "source": "test://source",
            "text": "Evidence text",
            "relevance": 1.0,
        }]} for _ in argument_sets]


def test_researcher_discovers_search_tool_and_deduplicates_evidence():
    evidence, log = ResearcherAgent().run(["topic", "topic"], FakeMCP())
    assert len(evidence) == 1
    assert evidence[0]["evidence_id"] == "E001"
    assert len(log) == 2
    assert all(item["success"] for item in log)


def test_researcher_reports_mcp_discovery_failure():
    class BrokenMCP:
        async def list_tools(self):
            raise RuntimeError("MCP offline")

    evidence, log = ResearcherAgent().run(["topic"], BrokenMCP())
    assert evidence == []
    assert log and log[0]["success"] is False


def test_verifier_discards_unknown_evidence_ids_and_downgrades_claim():
    model = FakeModel({
        "claims": [{
            "claim_id": "C1",
            "statement": "A factual claim",
            "evidence_ids": ["E999"],
            "status": "SUPPORTED",
            "confidence": 0.9,
        }]
    })
    evidence = [{"evidence_id": "E001", "title": "Source", "text": "Text"}]
    claims, _ = VerifierAgent().run("Question", evidence, model)
    assert len(claims) == 1
    assert claims[0]["evidence_ids"] == []
    assert claims[0]["status"] == "UNSUPPORTED"


def test_writer_falls_back_to_verified_claims_when_citations_are_invalid():
    model = FakeModel(text="This answer has no usable citation.")
    claims = [{
        "claim_id": "C1",
        "statement": "Verified statement",
        "evidence_ids": ["E001"],
        "status": "SUPPORTED",
        "confidence": 1.0,
        "reason": "",
    }]
    evidence = [{"evidence_id": "E001", "title": "Source", "text": "Evidence"}]
    answer, _ = WriterAgent().run("Question", claims, evidence, model)
    assert answer == "- Verified statement [E001]"


def test_writer_rejects_unknown_citation_ids():
    model = FakeModel(text="Claim [E999]")
    claims = [{
        "claim_id": "C1",
        "statement": "Verified statement",
        "evidence_ids": ["E001"],
        "status": "SUPPORTED",
        "confidence": 1.0,
        "reason": "",
    }]
    evidence = [{"evidence_id": "E001", "title": "Source", "text": "Evidence"}]
    answer, _ = WriterAgent().run("Question", claims, evidence, model)
    assert answer == "- Verified statement [E001]"


def test_evaluator_handles_supported_and_unsupported_claims():
    claims = [
        {"status": "SUPPORTED", "evidence_ids": ["E001"]},
        {"status": "UNSUPPORTED", "evidence_ids": []},
    ]
    result = EvaluatorAgent().run("Answer", claims, [])
    assert result["groundedness"] == 0.5
    assert result["evidence_coverage"] == 0.5
    assert result["hallucination_rate"] == 0.5
    assert result["task_success"] is True


def test_evaluator_marks_empty_claim_metrics_not_applicable():
    result = EvaluatorAgent().run("Insufficient evidence.", [], [])
    assert result["groundedness"] is None
    assert result["evidence_coverage"] is None
    assert result["hallucination_rate"] is None
    assert result["task_success"] is True
