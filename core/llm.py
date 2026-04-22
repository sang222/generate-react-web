from __future__ import annotations

import os
import time

from dotenv import load_dotenv
from ollama import ChatResponse, Client

from core.config import get_model_for_role
from core.token_budget import check_budget_before_call, estimate_tokens, record_llm_usage

load_dotenv()

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


def _extract_ollama_content(response: ChatResponse | dict[str, object] | object) -> str:
    """Extract assistant text from Ollama response.

    Supports both the new typed ChatResponse object and older dict-like responses.
    """
    if isinstance(response, dict):
        message = response.get("message", {})
        if isinstance(message, dict):
            return str(message.get("content", "") or "").strip()
        return ""

    message = getattr(response, "message", None)
    if message is None:
        return ""

    content = getattr(message, "content", "") or ""
    return str(content).strip()


def call_role_llm(
    role: str,
    prompt: str,
    temperature: float = 0.2,
    host: str | None = None,
) -> str:
    """Call the configured Ollama Cloud model for a role."""
    if host:
        raise RuntimeError("Local/custom Ollama host is disabled. Use Ollama Cloud only.")

    model = get_model_for_role(role)
    prompt_tokens = estimate_tokens(prompt)

    check_budget_before_call(role, prompt_tokens)

    client = get_ollama_cloud_client()
    started = time.time()

    print(
        f"\n[LLM:START] role={role} model={model} prompt_tokens~={prompt_tokens}",
        flush=True,
    )

    try:
        response: ChatResponse = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature},
            stream=False,
        )

        content = _extract_ollama_content(response)
        duration_ms = int((time.time() - started) * 1000)

        print(
            f"[LLM:DONE] role={role} model={model} "
            f"output_chars={len(content)} duration_ms={duration_ms}",
            flush=True,
        )

        record_llm_usage(
            role=role,
            model=model,
            prompt=prompt,
            completion=content,
            duration_ms=duration_ms,
            provider="ollama_cloud",
        )

        return content

    except Exception as exc:
        duration_ms = int((time.time() - started) * 1000)

        print(
            f"[LLM:ERROR] role={role} model={model} "
            f"duration_ms={duration_ms} error={exc}",
            flush=True,
        )

        raise