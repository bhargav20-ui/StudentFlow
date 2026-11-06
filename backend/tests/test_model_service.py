import pytest

import app.model_service as service


class ApiError(Exception):
    code = 503


class FakeResponse:
    text = "model response"
    usage_metadata = type(
        "Usage",
        (),
        {"prompt_token_count": 12, "candidates_token_count": 7},
    )()


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


def test_gemini_retries_transient_503_then_succeeds(monkeypatch):
    monkeypatch.setattr(service, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(service, "GEMINI_MAX_ATTEMPTS", 4, raising=False)
    monkeypatch.setattr(service.time, "sleep", lambda delay: None)
    model = service.GeminiService()
    model.client = FakeClient([ApiError("high demand"), FakeResponse()])

    result = model.generate("test prompt")

    assert result["text"] == "model response"
    assert result["model_attempts"] == 2
    assert result["model_retries"] == 1
    assert result["input_tokens"] == 12


def test_gemini_exhausted_transient_retries_raise_diagnostic(monkeypatch):
    monkeypatch.setattr(service, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(service.os, "getenv", lambda key, default=None: {
        "GEMINI_MAX_ATTEMPTS": "2",
        "GEMINI_RETRY_BASE_SECONDS": "0.25",
        "GEMINI_RETRY_MAX_SECONDS": "1",
    }.get(key, default))
    monkeypatch.setattr(service.time, "sleep", lambda delay: None)
    model = service.GeminiService()
    model.client = FakeClient([ApiError("busy"), ApiError("busy")])

    with pytest.raises(service.ModelUnavailable) as caught:
        model.generate("test prompt")

    assert caught.value.retryable is True
    assert caught.value.attempts == 2
    assert caught.value.retries == 1


def test_gemini_does_not_retry_authentication_errors(monkeypatch):
    monkeypatch.setattr(service, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(service.time, "sleep", lambda delay: pytest.fail("unexpected retry"))
    model = service.GeminiService()
    model.client = FakeClient([Exception("401 invalid API key")])

    with pytest.raises(Exception, match="401"):
        model.generate("test prompt")
