import json
import logging
import os
import re
import time

from .config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    INPUT_PRICE_PER_1M,
    OUTPUT_PRICE_PER_1M,
)


logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ModelUnavailable(RuntimeError):
    def __init__(
        self, message, *, attempts=0, retry_wait_ms=0, retryable=False, status_code=None
    ):
        super().__init__(message)
        self.attempts = attempts
        self.retries = max(0, attempts - 1)
        self.retry_wait_ms = retry_wait_ms
        self.retryable = retryable
        self.status_code = status_code


def is_daily_quota_error(exc):
    """Detect exhausted daily quotas that cannot recover through short retries."""
    message = str(exc).lower()
    return any(token in message for token in (
        "per day limit exceeded",
        "daily limit exceeded",
        "generate_content_free_tier_requests",
        "free tier requests, limit",
    ))


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
                logger.exception("Gemini client initialization failed")
                raise ModelUnavailable(
                    "Gemini client initialization failed. Check the API key and SDK configuration."
                ) from exc

    def generate(self, prompt, json_mode=False):
        if not self.client:
            raise ModelUnavailable(
                "Gemini API key is not configured. Add GEMINI_API_KEY to the service environment."
            )

        # Gemini 3 models use the default sampling configuration; avoid
        # sending legacy temperature/top_p/top_k settings.
        config = {}
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
                logger.info(
                    "Calling Gemini | model=%s | attempt=%s/%s | json_mode=%s",
                    self.model,
                    attempt,
                    max_attempts,
                    json_mode,
                )
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
                logger.info("Gemini call succeeded | model=%s | attempt=%s", self.model, attempt)
                break
            except Exception as exc:
                last_error = exc
                status = (
                    getattr(exc, "code", None)
                    or getattr(exc, "status_code", None)
                    or getattr(exc, "http_status", None)
                )
                # Never write the configured API key to application logs.
                error_message = str(exc)
                if GEMINI_API_KEY:
                    error_message = error_message.replace(GEMINI_API_KEY, "[REDACTED]")

                # A daily quota cannot recover after a few seconds. Stop immediately
                # instead of burning retries and return an actionable message.
                if is_daily_quota_error(exc):
                    logger.error(
                        "Gemini daily quota exhausted | model=%s | status=%s | error=%s",
                        self.model,
                        status,
                        error_message[:1000],
                    )
                    raise ModelUnavailable(
                        "Gemini's daily free-tier request quota has been exhausted. "
                        "Changing the API key to one from a project with available quota, "
                        "enabling billing, or waiting for the quota reset is required. "
                        "Check https://ai.dev/rate-limit for the reset and usage details.",
                        attempts=attempt,
                        retry_wait_ms=retry_wait_ms,
                        retryable=False,
                        status_code=429,
                    ) from exc

                if not is_retryable_gemini_error(exc):
                    logger.exception(
                        "Non-retryable Gemini failure | model=%s | attempt=%s/%s | "
                        "type=%s | status=%s | error=%s",
                        self.model,
                        attempt,
                        max_attempts,
                        type(exc).__name__,
                        status,
                        error_message[:1000],
                    )
                    raise

                logger.warning(
                    "Retryable Gemini failure | model=%s | attempt=%s/%s | "
                    "type=%s | status=%s | error=%s",
                    self.model,
                    attempt,
                    max_attempts,
                    type(exc).__name__,
                    status,
                    error_message[:1000],
                )

                if attempt >= max_attempts:
                    break

                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                logger.info("Waiting %.2f seconds before Gemini retry", delay)
                time.sleep(delay)
                retry_wait_ms += round(delay * 1000)

        if response is None:
            logger.error(
                "Gemini retries exhausted | model=%s | attempts=%s | retry_wait_ms=%s | "
                "last_error_type=%s | last_error=%s",
                self.model,
                max_attempts,
                retry_wait_ms,
                type(last_error).__name__ if last_error else "Unknown",
                (
                    str(last_error).replace(GEMINI_API_KEY, "[REDACTED]")
                    if last_error and GEMINI_API_KEY
                    else str(last_error)
                )[:1000] if last_error else "No response and no exception captured",
            )
            raise ModelUnavailable(
                "Gemini request failed after "
                f"{max_attempts} attempts. Check Render application logs for the original "
                "Gemini API status and error details.",
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
