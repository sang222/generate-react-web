from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


def now_ms() -> int:
    return int(time.time() * 1000)


def sha_text(text: str, length: int = 10) -> str:
    raw = (text or '').encode('utf-8', errors='ignore')
    return hashlib.sha256(raw).hexdigest()[:length]


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not str(value).strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def compact_error(exc: BaseException) -> str:
    msg = str(exc) or exc.__class__.__name__
    return msg.replace('\n', ' ')[:1000]


@dataclass
class LLMTrace:
    role: str
    model: str
    prompt: str
    host: str
    stream: bool = False
    num_predict: Optional[int] = None
    temperature: float = 0.2
    prompt_tokens: int = 0
    started_at_ms: int = field(default_factory=now_ms)
    prompt_chars: int = 0
    prompt_sha: str = ''

    def __post_init__(self) -> None:
        self.prompt_chars = len(self.prompt or '')
        self.prompt_sha = sha_text(self.prompt or '')

    def elapsed_ms(self) -> int:
        return max(0, now_ms() - self.started_at_ms)


def safe_response_field(response: Any, field: str) -> Any:
    if response is None:
        return None
    if isinstance(response, dict):
        return response.get(field)
    return getattr(response, field, None)


def extract_response_metadata(response: Any) -> Dict[str, Any]:
    fields = [
        'total_duration',
        'load_duration',
        'prompt_eval_count',
        'prompt_eval_duration',
        'eval_count',
        'eval_duration',
        'done_reason',
    ]
    data: Dict[str, Any] = {}
    for field_name in fields:
        value = safe_response_field(response, field_name)
        if value is not None:
            data[field_name] = value
    return data


def extract_message_content(response: Any) -> str:
    if response is None:
        return ''

    if isinstance(response, dict):
        message = response.get('message') or {}
        if isinstance(message, dict):
            return str(message.get('content') or '').strip()
        return ''

    message = getattr(response, 'message', None)
    if isinstance(message, dict):
        return str(message.get('content') or '').strip()
    if message is not None:
        return str(getattr(message, 'content', '') or '').strip()
    return ''


def metadata_to_log_value(metadata: Dict[str, Any]) -> str:
    if not metadata:
        return ''
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True)
