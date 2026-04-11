from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def safe_json_loads(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    direct = safe_json_loads(text)
    if direct:
        return direct
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    return safe_json_loads(match.group(0))


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
