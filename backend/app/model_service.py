import json
import os
import re
import time

from .config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    INPUT_PRICE_PER_1M,
    OUTPUT_PRICE_PER_1M,
)


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ModelUnavailable(RuntimeError):
    def __init__(self, message, *, attempts=0, retry_wait_ms=0, retryable=False):
        super().__init__(message)
        self.attempts = attempts
        self.retries = max(0, attempts - 1)
        self.retry_wait_ms = retry_wait_ms
        self.retryable = retryable


def is_retryable_gemini_error(exc):
    """Return True only for transient Gemini/API availability errors."""
    for attr in ("code", "status_code", "http_status"):
        value = getattr(exc, attr, None)
        try:
            if int(value) in RETRYABLE_STATUS_CODES:
                return True
        except (TypeError, ValueError):
            pass
    message = str(exc).lower()
    return any(token in message for token in (
        "429", "500", "502", "503", "504", "resource_exhausted",
        "service_unavailable", "temporarily unavailable", "high demand",
        "deadline_exceeded", "internal server error",
    ))


class GeminiService:
    def __init__(self):
        self.client = None
        self.model = GEMINI_MODEL
        if GEMINI_API_KEY:
            try:
                from google import genai
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as exc:
                raise ModelUnavailable(
                    "Gemini client initialization failed. Check the API key and SDK configuration."
                ) from exc

    def generate(self, prompt, json_mode=False):
        if not self.client:
            raise ModelUnavailable(
                "Gemini API key is not configured. Add GEMINI_API_KEY to the service environment."
            )

        config = {"temperature": 0.1}
        if json_mode:
            config["response_mime_type"] = "application/json"

        max_attempts = max(1, min(int(os.getenv("GEMINI_MAX_ATTEMPTS", "4")), 6))
        base_delay = max(0.25, min(float(os.getenv("GEMINI_RETRY_BASE_SECONDS", "1.5")), 10))
        max_delay = max(base_delay, min(float(os.getenv("GEMINI_RETRY_MAX_SECONDS", "12")), 30))
        retry_wait_ms = 0
        last_error = None
        response = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                break
            except Exception as exc:
                last_error = exc
                if not is_retryable_gemini_error(exc):
                    raise
                if attempt >= max_attempts:
                    break
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                time.sleep(delay)
                retry_wait_ms += round(delay * 1000)

        if response is None:
            raise ModelUnavailable(
                "Gemini is temporarily unavailable or under heavy load. "
                f"The request was attempted {max_attempts} times with automatic backoff. "
                "Please retry this research question shortly.",
                attempts=max_attempts,
                retry_wait_ms=retry_wait_ms,
                retryable=True,
            ) from last_error

        text = getattr(response, "text", None) or ""
        usage = getattr(response, "usage_metadata", None)
        input_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        output_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        cost = None
        if INPUT_PRICE_PER_1M is not None and OUTPUT_PRICE_PER_1M is not None:
            cost = (
                input_tokens / 1_000_000 * INPUT_PRICE_PER_1M
                + output_tokens / 1_000_000 * OUTPUT_PRICE_PER_1M
            )

        data = None
        if json_mode:
            try:
                data = json.loads(text)
            except (TypeError, json.JSONDecodeError):
                match = re.search(r"\{.*\}", text, re.S)
                if match:
                    try:
                        data = json.loads(match.group(0))
                    except json.JSONDecodeError:
                        pass

        return {
            "text": text,
            "json": data,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
            "model_attempts": attempt,
            "model_retries": attempt - 1,
            "retry_wait_ms": retry_wait_ms,
        }
