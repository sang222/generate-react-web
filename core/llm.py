from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional

from ollama import Client

from core.config import get_model_for_role, load_env
from core.llm_telemetry import (
    LLMTrace,
    compact_error,
    extract_message_content,
    extract_response_metadata,
    get_env_int,
    metadata_to_log_value,
)
from core.runtime_log import append_jsonl, log_event
from core.token_budget import check_budget_before_call, estimate_tokens, record_llm_usage

OLLAMA_CLOUD_HOST = 'https://ollama.com'

ROLE_NUM_PREDICT_DEFAULTS: Dict[str, int] = {
    'pm': 1600,
    'architect': 2200,
    'developer': 8000,
    'fe_developer': 8000,
    'be_developer': 8000,
    'qa': 1800,
    'fe_reviewer': 1800,
    'be_reviewer': 1800,
    'integration_qa': 1800,
    'lead': 1400,
    'recovery_meta': 1600,
    'skill_reviewer': 1400,
    'benchmark': 512,
    'default': 2048,
}

ROLE_SLOW_MS_DEFAULTS: Dict[str, int] = {
    'pm': 60_000,
    'architect': 60_000,
    'developer': 120_000,
    'fe_developer': 120_000,
    'be_developer': 120_000,
    'qa': 60_000,
    'fe_reviewer': 60_000,
    'be_reviewer': 60_000,
    'integration_qa': 60_000,
    'lead': 60_000,
    'recovery_meta': 60_000,
    'skill_reviewer': 60_000,
    'benchmark': 60_000,
    'default': 60_000,
}


def _env_role_key(role: str, suffix: str) -> str:
    return f"LLM_{suffix}_{str(role or 'default').upper().replace('-', '_')}"


def get_role_num_predict(role: str, override: Optional[int] = None) -> int:
    if override is not None:
        return int(override)
    default = ROLE_NUM_PREDICT_DEFAULTS.get(role, ROLE_NUM_PREDICT_DEFAULTS['default'])
    return get_env_int(_env_role_key(role, 'NUM_PREDICT'), default)


def get_role_slow_threshold_ms(role: str) -> int:
    default = ROLE_SLOW_MS_DEFAULTS.get(role, ROLE_SLOW_MS_DEFAULTS['default'])
    return get_env_int(_env_role_key(role, 'SLOW_MS'), default)


def get_ollama_cloud_client() -> Client:
    import os

    load_env()
    api_key = os.getenv('OLLAMA_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('OLLAMA_API_KEY is required for Ollama Cloud. Check .env or run scripts/check_env.py')
    return Client(host=OLLAMA_CLOUD_HOST, headers={'Authorization': f'Bearer {api_key}'})


def _log_slow_if_needed(trace: LLMTrace, threshold_ms: int) -> None:
    duration_ms = trace.elapsed_ms()
    if duration_ms <= threshold_ms:
        return
    log_event(
        'LLM',
        trace.role,
        'SLOW',
        model=trace.model,
        duration_ms=duration_ms,
        threshold_ms=threshold_ms,
        prompt_tokens=trace.prompt_tokens,
        prompt_sha=trace.prompt_sha,
    )


def call_role_llm(
    role: str,
    prompt: str,
    temperature: float = 0.2,
    host: str | None = None,
    num_predict: int | None = None,
    extra_options: Dict[str, Any] | None = None,
) -> str:
    if host:
        raise RuntimeError('Local/custom Ollama host is disabled. Use Ollama Cloud only.')

    load_env()
    model = get_model_for_role(role)
    prompt_tokens = estimate_tokens(prompt)
    check_budget_before_call(role, prompt_tokens)

    resolved_num_predict = get_role_num_predict(role, num_predict)
    options: Dict[str, Any] = {
        'temperature': temperature,
        'num_predict': resolved_num_predict,
    }
    if extra_options:
        options.update(extra_options)

    trace = LLMTrace(
        role=role,
        model=model,
        prompt=prompt,
        host=OLLAMA_CLOUD_HOST,
        stream=False,
        temperature=temperature,
        num_predict=resolved_num_predict,
        prompt_tokens=prompt_tokens,
    )

    client = get_ollama_cloud_client()

    log_event(
        'LLM',
        role,
        'START',
        model=model,
        prompt_tokens=prompt_tokens,
        prompt_chars=trace.prompt_chars,
        prompt_sha=trace.prompt_sha,
    )
    log_event(
        'LLM',
        role,
        'REQUEST',
        model=model,
        host=OLLAMA_CLOUD_HOST,
        stream=False,
        temperature=temperature,
        num_predict=resolved_num_predict,
    )

    try:
        response: dict[str, Any] = client.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            options=options,
            stream=False,
        )
        content = extract_message_content(response)
        metadata = extract_response_metadata(response)
        duration_ms = int((time.time() - (trace.started_at_ms / 1000)) * 1000)

        record_llm_usage(
            role=role,
            model=model,
            prompt=prompt,
            completion=content,
            duration_ms=duration_ms,
            provider='ollama_cloud',
        )

        log_event(
            'LLM',
            role,
            'DONE',
            model=model,
            duration_ms=duration_ms,
            output_chars=len(content),
            output_tokens_est=estimate_tokens(content),
            metadata=metadata_to_log_value(metadata),
        )
        _log_slow_if_needed(trace, get_role_slow_threshold_ms(role))
        return content

    except Exception as exc:
        duration_ms = int((time.time() - (trace.started_at_ms / 1000)) * 1000)
        log_event(
            'LLM',
            role,
            'ERROR',
            model=model,
            duration_ms=duration_ms,
            error=compact_error(exc),
        )
        _log_slow_if_needed(trace, get_role_slow_threshold_ms(role))
        append_jsonl(
            Path('state') / 'llm_errors.jsonl',
            {
                'role': role,
                'model': model,
                'prompt_tokens_estimate': prompt_tokens,
                'prompt_sha': trace.prompt_sha,
                'duration_ms': duration_ms,
                'error': str(exc),
            },
        )
        raise
