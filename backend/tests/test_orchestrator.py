import app.orchestrator as orchestration


class FakeModel:
    model = "test-model"

    def generate(self, *args, **kwargs):
        return {"text": "ok", "json": {}, "input_tokens": 5, "output_tokens": 3, "cost_usd": None}


class FakePlanner:
    def run(self, question, model):
        return ["research " + question], {"input_tokens": 5, "output_tokens": 3}


class FakeResearcher:
    def __init__(self, fail=False):
        self.fail = fail

    def run(self, tasks, mcp):
        if self.fail:
            return [], [{"tool": "search", "success": False, "error": "offline"}]
        return [{
            "evidence_id": "E001",
            "document_id": "DOC1",
            "title": "Source",
            "source": "test://source",
            "text": "Evidence text",
        }], [{"tool": "search", "success": True, "returned": 1}]


class FakeVerifier:
    def run(self, question, evidence, model):
        if not evidence:
            return [], None
        return [{
            "claim_id": "C1",
            "statement": "Evidence-backed statement",
            "evidence_ids": ["E001"],
            "status": "SUPPORTED",
            "confidence": 1.0,
            "reason": "Direct support",
        }], {"input_tokens": 5, "output_tokens": 3}


class FakeWriter:
    def run(self, question, claims, evidence, model):
        if not evidence:
            return "Insufficient evidence: no source documents were retrieved.", None
        return "Evidence-backed statement [E001]", {
            "input_tokens": 5, "output_tokens": 3, "cost_usd": None
        }


def setup_orchestrator(monkeypatch, researcher):
    monkeypatch.setattr(orchestration, "GeminiService", FakeModel)
    monkeypatch.setattr(orchestration, "MCPToolClient", lambda: object())
    monkeypatch.setattr(orchestration, "PlannerAgent", FakePlanner)
    monkeypatch.setattr(orchestration, "ResearcherAgent", lambda: researcher)
    monkeypatch.setattr(orchestration, "VerifierAgent", FakeVerifier)
    monkeypatch.setattr(orchestration, "WriterAgent", FakeWriter)
    monkeypatch.setattr(orchestration, "save_run", lambda result: None)
    return orchestration.Orchestrator()


def test_orchestrator_records_successful_agent_pipeline(monkeypatch):
    system = setup_orchestrator(monkeypatch, FakeResearcher())
    result = system.run("Explain the evidence")

    assert result["metrics"]["pipeline_execution_success"] is True
    assert result["metrics"]["retrieval_success"] is True
    assert result["metrics"]["agent_completion_rate"] == 1.0
    assert result["metrics"]["groundedness"] == 1.0
    assert result["metrics"]["citation_validity"] == 1.0
    assert result["metrics"]["task_success"] is True
    assert [event["agent"] for event in result["events"]] == [
        "planner", "researcher", "verifier", "writer", "evaluator"
    ]


def test_orchestrator_separates_tool_failure_from_safe_abstention(monkeypatch):
    system = setup_orchestrator(monkeypatch, FakeResearcher(fail=True))
    result = system.run("Explain the evidence")

    assert result["metrics"]["pipeline_execution_success"] is False
    assert result["metrics"]["retrieval_success"] is False
    assert result["metrics"]["task_success"] is True
    assert result["metrics"]["groundedness"] is None
    assert result["warnings"]
