from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List

from ollama import Client

from core.config import get_role_model_map, load_env

OLLAMA_CLOUD_HOST = "https://ollama.com"


@dataclass
class ModelCheckResult:
    role: str
    model: str
    ok: bool
    error: str = ""
    duration_ms: int = 0


@dataclass
class UniqueModelCheckResult:
    model: str
    ok: bool
    error: str = ""
    duration_ms: int = 0


def get_cloud_client() -> Client:
    load_env()
    api_key = os.getenv("OLLAMA_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("OLLAMA_API_KEY is required for Ollama Cloud")

    return Client(
        host=OLLAMA_CLOUD_HOST,
        headers={"Authorization": f"Bearer {api_key}"},
    )


def collect_role_models() -> Dict[str, str]:
    load_env()
    return get_role_model_map()


def check_one_unique_model(
    client: Client,
    model: str,
    prompt: str = "Reply exactly: OK",
) -> UniqueModelCheckResult:
    started = time.time()

    try:
        client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            options={
                "temperature": 0,
                "num_predict": 3,
            },
        )

        return UniqueModelCheckResult(
            model=model,
            ok=True,
            duration_ms=int((time.time() - started) * 1000),
        )

    except Exception as exc:
        return UniqueModelCheckResult(
            model=model,
            ok=False,
            error=str(exc),
            duration_ms=int((time.time() - started) * 1000),
        )


def run_model_preflight(roles: Iterable[str] | None = None) -> List[ModelCheckResult]:
    models = collect_role_models()
    selected = set(roles or models.keys())

    model_to_roles: Dict[str, List[str]] = {}

    for role, model in models.items():
        if role not in selected:
            continue
        model_to_roles.setdefault(model, []).append(role)

    client = get_cloud_client()
    results: list[ModelCheckResult] = []

    for model, mapped_roles in model_to_roles.items():
        print(
            f"[MODEL:START] model={model} roles={','.join(mapped_roles)}",
            flush=True,
        )

        raw = check_one_unique_model(client, model)

        print(
            f"[MODEL:{'PASS' if raw.ok else 'FAIL'}] "
            f"model={model} duration_ms={raw.duration_ms}"
            + (f" error={raw.error}" if raw.error else ""),
            flush=True,
        )

        for role in mapped_roles:
            results.append(
                ModelCheckResult(
                    role=role,
                    model=model,
                    ok=raw.ok,
                    error=raw.error,
                    duration_ms=raw.duration_ms,
                )
            )

    return results