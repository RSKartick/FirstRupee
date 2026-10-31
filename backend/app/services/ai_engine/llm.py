"""Provider-independent LLM client (OpenAI-compatible chat completions over HTTPX).

Every response is validated against a Pydantic schema. Failures are classified (timeout, rate limit, invalid JSON, empty,
schema mismatch, provider error) and returned as short, sanitised messages. Provider bodies, keys and stack traces are never
returned to the user; details are written to the server log only.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

logger = logging.getLogger("firstrupee.llm")
T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class LLMResult:
    ok: bool
    data: Any = None
    kind: str = ""
    message: str = ""
    provider: str = "none"
    model: str | None = None


def _failure(kind: str, message: str) -> LLMResult:
    return LLMResult(ok=False, kind=kind, message=message)


def extract_json_object(text: str) -> Any:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(text[start : end + 1])


def _call_gemini(settings: Any, api_key: str, system: str, user: str) -> tuple[httpx.Response | None, LLMResult | None, str]:
    raw_model = (settings.llm_model or "gemini-2.5-flash").strip()
    model = raw_model if raw_model.startswith("gemini-") else "gemini-2.5-flash"
    base = settings.llm_base_url.rstrip("/")
    if "openai.com" in base:
        base = "https://generativelanguage.googleapis.com/v1beta"
    if base.endswith("/openai"):
        base = base[: -len("/openai")]

    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    models_to_try = [model]
    if model != "gemini-2.0-flash":
        models_to_try.append("gemini-2.0-flash")

    response: httpx.Response | None = None
    used_model = model
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            for candidate_model in models_to_try:
                used_model = candidate_model
                url = f"{base}/models/{candidate_model}:generateContent"
                response = client.post(url, headers=headers, json=payload)
                if response.status_code != 404:
                    break
    except httpx.TimeoutException:
        logger.warning("Gemini request timed out after %.1fs", settings.llm_timeout_seconds)
        return None, _failure("TIMEOUT", "The model did not answer in time."), used_model
    except httpx.HTTPError as exc:
        logger.error("Gemini transport error: %s", type(exc).__name__)
        return None, _failure("PROVIDER_ERROR", "The model provider could not be reached."), used_model
    return response, None, used_model


def call_json(system: str, user: str, schema: type[T]) -> LLMResult:
    settings = get_settings()
    if not settings.llm_enabled:
        return _failure("NO_PROVIDER", "No language model is configured; the deterministic engine produced this output.")

    provider = getattr(settings, "effective_provider", settings.llm_provider)
    api_key = getattr(settings, "effective_api_key", settings.llm_api_key) or ""

    if provider == "google-gemini":
        response, err, used_model = _call_gemini(settings, api_key, system, user)
        if err is not None or response is None:
            return err or _failure("PROVIDER_ERROR", "The model provider could not be reached.")
        if response.status_code == 429:
            return _failure("RATE_LIMIT", "The model provider is rate-limiting requests. Try again shortly.")
        if response.status_code >= 400:
            logger.error("Gemini provider returned HTTP %s", response.status_code)
            return _failure("PROVIDER_ERROR", f"The model provider returned an error (HTTP {response.status_code}).")
        try:
            body = response.json()
            parts = body["candidates"][0]["content"]["parts"]
            content = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        except (ValueError, KeyError, IndexError, TypeError):
            return _failure("PROVIDER_ERROR", "The model provider returned an unexpected response shape.")
        if not isinstance(content, str) or not content.strip():
            return _failure("EMPTY_RESPONSE", "The model returned an empty response.")
        try:
            parsed = extract_json_object(content)
            if isinstance(parsed, dict) and "answer" not in parsed and schema.__name__ == "AssistantDraft":
                for k in ("response", "message", "text", "reply"):
                    if isinstance(parsed.get(k), str):
                        parsed = {"answer": parsed[k]}
                        break
        except (ValueError, json.JSONDecodeError):
            if schema.__name__ == "AssistantDraft":
                parsed = {"answer": content.strip()}
            else:
                return _failure("INVALID_JSON", "The model response was not valid JSON.")
        try:
            validated = schema.model_validate(parsed)
        except ValidationError:
            return _failure("SCHEMA_INVALID", "The model response did not match the required structure.")
        return LLMResult(ok=True, data=validated, provider="google-gemini", model=used_model)

    payload = {
        "model": settings.llm_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=settings.llm_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException:
        logger.warning("LLM request timed out after %.1fs", settings.llm_timeout_seconds)
        return _failure("TIMEOUT", "The model did not answer in time.")
    except httpx.HTTPError as exc:
        logger.error("LLM transport error: %s", type(exc).__name__)
        return _failure("PROVIDER_ERROR", "The model provider could not be reached.")

    if response.status_code == 429:
        return _failure("RATE_LIMIT", "The model provider is rate-limiting requests. Try again shortly.")
    if response.status_code >= 400:
        logger.error("LLM provider returned HTTP %s", response.status_code)
        return _failure("PROVIDER_ERROR", f"The model provider returned an error (HTTP {response.status_code}).")

    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        return _failure("PROVIDER_ERROR", "The model provider returned an unexpected response shape.")
    if not isinstance(content, str) or not content.strip():
        return _failure("EMPTY_RESPONSE", "The model returned an empty response.")

    try:
        parsed = extract_json_object(content)
    except (ValueError, json.JSONDecodeError):
        return _failure("INVALID_JSON", "The model response was not valid JSON.")
    try:
        validated = schema.model_validate(parsed)
    except ValidationError:
        return _failure("SCHEMA_INVALID", "The model response did not match the required structure.")
    return LLMResult(ok=True, data=validated, provider=provider, model=settings.llm_model)
