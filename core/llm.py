from __future__ import annotations

import os
import time
from typing import Any

from ollama import Client
from ollama import ChatResponse
from core.config import get_model_for_role
from core.token_budget import check_budget_before_call, estimate_tokens, record_llm_usage

OLLAMA_CLOUD_HOST = "https://ollama.com"


def get_ollama_cloud_client() -> Client:
    """Return an Ollama Cloud client.

    This repo intentionally uses Ollama Cloud only. Local Ollama fallback was removed
    so production cost control can be centralized through token telemetry/budgets.
    """
    api_key = os.getenv("OLLAMA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OLLAMA_API_KEY is required for Ollama Cloud")
    return Client(
        host=OLLAMA_CLOUD_HOST,
        headers={"Authorization": f"Bearer {api_key}"},
    )


def _extract_ollama_content(response: object) -> str:
    if isinstance(response, dict):
        return ((response.get("message", {}) or {}).get("content", "") or "").strip()
    message = getattr(response, "message", None)
    content = getattr(message, "content", "") if message else ""
    return (content or "").strip()


def call_role_llm(role: str, prompt: str, temperature: float = 0.2, host: str | None = None) -> str:
    if host:
        raise RuntimeError("Local/custom Ollama host is disabled. Use Ollama Cloud only.")
    model = get_model_for_role(role)
    check_budget_before_call(role, estimate_tokens(prompt))
    client = get_ollama_cloud_client()
    started = time.time()
    response: ChatResponse = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
        stream=False,
    )
    content = _extract_ollama_content(response)
    record_llm_usage(
        role=role,
        model=model,
        prompt=prompt,
        completion=content,
        duration_ms=int((time.time() - started) * 1000),
        provider="ollama_cloud",
    )
    return content
