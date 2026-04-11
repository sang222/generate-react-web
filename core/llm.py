from __future__ import annotations

import os
from typing import Optional

import ollama

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


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
    message = response.get("message", {})
    return str(message.get("content", "")).strip()


def call_gemma(prompt: str, model: str = "gemma3:4b") -> str:
    return call_local_llm(prompt=prompt, model=model, temperature=0.2)


def call_qwen(prompt: str, model: str = "qwen3:8b") -> str:
    return call_local_llm(prompt=prompt, model=model, temperature=0.2)
