from __future__ import annotations
import time
from pathlib import Path
from typing import Any
from ollama import Client
from core.config import get_model_for_role, load_env
from core.runtime_log import append_jsonl, log_event
from core.token_budget import check_budget_before_call, estimate_tokens, record_llm_usage
OLLAMA_CLOUD_HOST = 'https://ollama.com'
def get_ollama_cloud_client() -> Client:
    import os
    load_env(); api_key = os.getenv('OLLAMA_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('OLLAMA_API_KEY is required for Ollama Cloud. Check .env or run scripts/check_env.py')
    return Client(host=OLLAMA_CLOUD_HOST, headers={'Authorization': f'Bearer {api_key}'})
def _extract_ollama_content(response: object) -> str:
    if isinstance(response, dict):
        return ((response.get('message', {}) or {}).get('content', '') or '').strip()
    message = getattr(response, 'message', None)
    content = getattr(message, 'content', '') if message else ''
    return (content or '').strip()
def call_role_llm(role: str, prompt: str, temperature: float = 0.2, host: str | None = None) -> str:
    if host:
        raise RuntimeError('Local/custom Ollama host is disabled. Use Ollama Cloud only.')
    load_env(); model = get_model_for_role(role); prompt_tokens = estimate_tokens(prompt)
    check_budget_before_call(role, prompt_tokens)
    client = get_ollama_cloud_client(); started = time.time()
    log_event('LLM', role, 'START', model=model, prompt_tokens=prompt_tokens)
    try:
        response: dict[str, Any] = client.chat(model=model, messages=[{'role': 'user', 'content': prompt}], options={'temperature': temperature}, stream=False)
        content = _extract_ollama_content(response); duration_ms = int((time.time() - started) * 1000)
        record_llm_usage(role=role, model=model, prompt=prompt, completion=content, duration_ms=duration_ms, provider='ollama_cloud')
        log_event('LLM', role, 'DONE', model=model, duration_ms=duration_ms, output_chars=len(content))
        return content
    except Exception as exc:
        duration_ms = int((time.time() - started) * 1000)
        log_event('LLM', role, 'ERROR', model=model, duration_ms=duration_ms, error=str(exc))
        append_jsonl(Path('state') / 'llm_errors.jsonl', {'role': role, 'model': model, 'prompt_tokens_estimate': prompt_tokens, 'duration_ms': duration_ms, 'error': str(exc)})
        raise
