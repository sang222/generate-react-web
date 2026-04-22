from __future__ import annotations
import json, os, time
from pathlib import Path
from typing import Any
PROGRESS_LOGS = os.getenv('PROGRESS_LOGS', '1') != '0'
def log_event(kind: str, name: str, status: str, message: str = '', **data: Any) -> None:
    if not PROGRESS_LOGS:
        return
    parts: list[str] = []
    if message:
        parts.append(message)
    for key, value in data.items():
        if value is None or value == '':
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        parts.append(f'{key}={value}')
    print(f'[{kind}:{status}] {name}' + ((' ' + ' '.join(parts)) if parts else ''), flush=True)
def append_jsonl(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'timestamp_ms': int(time.time() * 1000), **payload}, ensure_ascii=False) + '\n')
