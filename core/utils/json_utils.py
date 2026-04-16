from __future__ import annotations

import json
from typing import Any, Dict, List


def safe_json_loads(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _json_substrings(text: str) -> List[str]:
    candidates: List[str] = []
    stack = 0
    start = -1
    in_string = False
    escape = False

    for idx, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == '{':
            if stack == 0:
                start = idx
            stack += 1
        elif ch == '}' and stack:
            stack -= 1
            if stack == 0 and start >= 0:
                candidates.append(text[start:idx + 1])
                start = -1

    return candidates


def extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    direct = safe_json_loads(text)
    if direct:
        return direct

    stripped = text.strip()
    if stripped.startswith('```'):
        parts = stripped.split('```')
        for part in parts:
            payload = part.strip()
            if payload.lower().startswith('json'):
                payload = payload[4:].strip()
            candidate = safe_json_loads(payload)
            if candidate:
                return candidate

    for candidate_text in _json_substrings(text):
        candidate = safe_json_loads(candidate_text)
        if candidate:
            return candidate
    return {}


def normalize_files(dev_result: Dict[str, Any]) -> List[Dict[str, str]]:
    raw_files = dev_result.get("files", [])
    if not isinstance(raw_files, list):
        return []
    normalized: List[Dict[str, str]] = []
    for item in raw_files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not path.strip() or not isinstance(content, str):
            continue
        clean_path = path.strip().replace("\\", "/")
        normalized.append({"path": clean_path, "content": content})
    return normalized


def dedupe_files(files: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, str] = {}
    for item in files:
        merged[item["path"]] = item["content"]
    return [{"path": k, "content": v} for k, v in merged.items()]
