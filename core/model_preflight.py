from __future__ import annotations
import os, time
from dataclasses import dataclass
from typing import Dict, Iterable, List
from ollama import Client
from core.config import get_role_model_map, load_env
OLLAMA_CLOUD_HOST = 'https://ollama.com'
@dataclass
class ModelCheckResult:
    role: str
    model: str
    ok: bool
    error: str = ''
    duration_ms: int = 0
def get_cloud_client() -> Client:
    load_env(); api_key = os.getenv('OLLAMA_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('OLLAMA_API_KEY is required for Ollama Cloud')
    return Client(host=OLLAMA_CLOUD_HOST, headers={'Authorization': f'Bearer {api_key}'})
def collect_role_models() -> Dict[str, str]:
    load_env(); return get_role_model_map()
def check_one_model(client: Client, role: str, model: str, prompt: str = 'Reply with OK.') -> ModelCheckResult:
    started = time.time()
    try:
        client.chat(model=model, messages=[{'role': 'user', 'content': prompt}], stream=False, options={'temperature': 0})
        return ModelCheckResult(role=role, model=model, ok=True, duration_ms=int((time.time() - started) * 1000))
    except Exception as exc:
        return ModelCheckResult(role=role, model=model, ok=False, error=str(exc), duration_ms=int((time.time() - started) * 1000))
def run_model_preflight(roles: Iterable[str] | None = None) -> List[ModelCheckResult]:
    models = collect_role_models(); selected = set(roles or models.keys()); client = get_cloud_client(); results: list[ModelCheckResult] = []
    for role, model in models.items():
        if role in selected:
            results.append(check_one_model(client, role, model))
    return results
