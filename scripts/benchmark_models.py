#!/usr/bin/env python3
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path
from typing import List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.config import load_env
from core.llm import call_role_llm
from core.llm_telemetry import sha_text
from core.token_budget import estimate_tokens

DEFAULT_PROMPT = """
You are a concise software planning assistant.

Analyze this task and reply with a short JSON object:
{
  "summary": "...",
  "risks": ["..."],
  "next_steps": ["..."]
}

Task:
Build a clean landing page for a coffee shop.
""".strip()


def percentile(values: List[int], p: float) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * p))
    return sorted_values[index]


def run_one(*, model: str, role: str, prompt: str, num_predict: int, temperature: float, run_index: int) -> int:
    started = time.perf_counter()
    try:
        # Use benchmark role but force model through env-compatible temporary role call.
        # call_role_llm resolves role models, so benchmark uses DEFAULT_MODEL override by setting model in direct helper below.
        from core.llm import get_ollama_cloud_client, OLLAMA_CLOUD_HOST
        from core.llm_telemetry import LLMTrace, extract_message_content, extract_response_metadata, metadata_to_log_value
        from core.runtime_log import log_event

        prompt_tokens = estimate_tokens(prompt)
        trace = LLMTrace(
            role=role,
            model=model,
            prompt=prompt,
            host=OLLAMA_CLOUD_HOST,
            stream=False,
            temperature=temperature,
            num_predict=num_predict,
            prompt_tokens=prompt_tokens,
        )
        client = get_ollama_cloud_client()
        log_event('LLM', role, 'START', model=model, prompt_tokens=prompt_tokens, prompt_chars=trace.prompt_chars, prompt_sha=trace.prompt_sha)
        log_event('LLM', role, 'REQUEST', model=model, host=OLLAMA_CLOUD_HOST, stream=False, temperature=temperature, num_predict=num_predict)
        response = client.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            stream=False,
            options={'temperature': temperature, 'num_predict': num_predict},
        )
        output = extract_message_content(response)
        metadata = extract_response_metadata(response)
        duration_ms = int((time.perf_counter() - started) * 1000)
        log_event(
            'LLM',
            role,
            'DONE',
            model=model,
            duration_ms=duration_ms,
            output_chars=len(output or ''),
            output_tokens_est=estimate_tokens(output or ''),
            metadata=metadata_to_log_value(metadata),
        )
        print(
            f"[BENCH:PASS] model={model} role={role} run={run_index} duration_ms={duration_ms} output_chars={len(output or '')}",
            flush=True,
        )
        return duration_ms
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started) * 1000)
        print(
            f"[BENCH:FAIL] model={model} role={role} run={run_index} duration_ms={duration_ms} error={str(exc).replace(chr(10), ' ')[:1000]}",
            flush=True,
        )
        return duration_ms


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(description='Benchmark Ollama Cloud model latency outside the full workflow.')
    parser.add_argument('--model', required=True, help='Model name, e.g. glm-5.1:cloud or qwen3.5:cloud')
    parser.add_argument('--role', default='benchmark', help='Role label for telemetry logs.')
    parser.add_argument('--runs', type=int, default=5, help='Number of benchmark runs.')
    parser.add_argument('--num-predict', type=int, default=512, help='num_predict cap for each benchmark call.')
    parser.add_argument('--temperature', type=float, default=0.2, help='Sampling temperature.')
    parser.add_argument('--prompt-file', default='', help='Optional prompt file path.')
    parser.add_argument('--prompt', default='', help='Inline prompt override.')
    args = parser.parse_args()

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding='utf-8')
    elif args.prompt:
        prompt = args.prompt
    else:
        prompt = DEFAULT_PROMPT

    print(
        f"[BENCH:START] model={args.model} role={args.role} runs={args.runs} num_predict={args.num_predict} "
        f"temperature={args.temperature} prompt_tokens_est={estimate_tokens(prompt)} prompt_chars={len(prompt)} prompt_sha={sha_text(prompt)}",
        flush=True,
    )

    durations: List[int] = []
    for index in range(1, args.runs + 1):
        durations.append(
            run_one(
                model=args.model,
                role=args.role,
                prompt=prompt,
                num_predict=args.num_predict,
                temperature=args.temperature,
                run_index=index,
            )
        )

    if durations:
        print(
            f"[BENCH:SUMMARY] model={args.model} runs={len(durations)} min_ms={min(durations)} "
            f"avg_ms={int(statistics.mean(durations))} median_ms={int(statistics.median(durations))} "
            f"p90_ms={percentile(durations, 0.90)} max_ms={max(durations)}",
            flush=True,
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
