from __future__ import annotations

import os
from typing import Optional

import ollama
from openai import OpenAI

from core.config import get_model_for_role


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
QWEN_CLOUD_MODEL = os.getenv("QWEN_CLOUD_MODEL", "qwen-plus")


def _extract_ollama_content(response: object) -> str:
    if isinstance(response, dict):
        return ((response.get("message", {}) or {}).get("content", "") or "").strip()
    message = getattr(response, "message", None)
    content = getattr(message, "content", "") if message else ""
    return (content or "").strip()


def call_local_llm(
    prompt: str,
    model: str,
    host: Optional[str] = None,
    temperature: float = 0.2,
) -> str:
    client = ollama.Client(host=host or OLLAMA_HOST)
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature},
    )
    return _extract_ollama_content(response)


def call_role_llm(
    role: str,
    prompt: str,
    temperature: float = 0.2,
    host: Optional[str] = None,
) -> str:
    model = get_model_for_role(role)
    return call_local_llm(prompt=prompt, model=model, host=host, temperature=temperature)


def call_qwen_cloud(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.2,
    system_prompt: str | None = None,
) -> str:
    if not DASHSCOPE_API_KEY:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is missing. Please export your Qwen cloud API key first."
        )

    client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=DASHSCOPE_BASE_URL)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model=model or QWEN_CLOUD_MODEL,
        messages=messages,
        temperature=temperature,
    )
    content = resp.choices[0].message.content
    return (content or "").strip()
