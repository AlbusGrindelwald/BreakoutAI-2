from __future__ import annotations

import json
import re
import ssl
from typing import Any

import httpx

from src.models import AgentResponse


class OpenRouterWorkflowError(RuntimeError):
    """Raised when OpenRouter cannot return a usable workflow decision."""


class OpenRouterWorkflowClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_models: list[str] | None = None,
        base_url: str | None = None,
        app_name: str | None = None,
        site_url: str | None = None,
    ) -> None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The OpenAI SDK is not installed. Run 'pip install -r requirements.txt' "
                "or leave OPENROUTER_API_KEY unset to use the local fallback demos."
            ) from exc

        default_headers = {}
        if site_url:
            default_headers["HTTP-Referer"] = site_url
        if app_name:
            default_headers["X-Title"] = app_name

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers or None,
            http_client=build_http_client(),
        )
        self.model = model
        self.fallback_models = fallback_models or []

    def decide(self, system_prompt: str, user_message: str) -> AgentResponse:
        errors: list[str] = []
        for model in [self.model, *self.fallback_models]:
            try:
                return self._decide_with_model(model, system_prompt, user_message)
            except Exception as exc:
                errors.append(f"{model}: {describe_exception(exc)}")

        raise OpenRouterWorkflowError(" | ".join(errors))

    def _decide_with_model(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
    ) -> AgentResponse:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            content = response.choices[0].message.content or "{}"
            return parse_agent_response(json.loads(content))
        except Exception as exc:
            detail = describe_exception(exc)
            raise OpenRouterWorkflowError(detail) from exc


def build_http_client() -> httpx.Client:
    try:
        import truststore
    except ModuleNotFoundError:
        return httpx.Client(timeout=30.0, trust_env=False)

    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(timeout=30.0, trust_env=False, verify=ssl_context)


def describe_exception(exc: Exception) -> str:
    parts = [f"{type(exc).__name__}: {exc}"]
    cause = exc.__cause__
    while cause:
        parts.append(f"caused by {type(cause).__name__}: {cause}")
        cause = cause.__cause__
    return " | ".join(parts)


def parse_agent_response(payload: dict[str, Any]) -> AgentResponse:
    return AgentResponse(
        answer=clean_answer(payload.get("answer", "")),
        confidence=parse_confidence(payload.get("confidence")),
        should_escalate=bool(payload.get("should_escalate", False)),
        escalation_reason=payload.get("escalation_reason"),
        sop_gap=payload.get("sop_gap"),
        next_stage=payload.get("next_stage", "faq_answering"),
    )


def parse_confidence(value: Any) -> float:
    if isinstance(value, int | float):
        confidence = float(value)
    elif isinstance(value, str):
        normalized = value.replace(",", ".")
        match = re.search(r"\d+(?:\.\d+)?", normalized)
        confidence = float(match.group(0)) if match else 0.5
    else:
        confidence = 0.5

    return max(0.0, min(confidence, 1.0))


def clean_answer(value: Any) -> str:
    return str(value).strip().lstrip(": ").strip()
