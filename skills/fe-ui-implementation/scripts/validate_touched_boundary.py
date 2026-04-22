from __future__ import annotations

import json
from pathlib import Path

REQUIRED = ["touched_paths", "allowed_scope_matches", "forbidden_scope_hits", "locked_artifact_hits", "change_request_required", "style_strategy", "blocked_reason"]

def validate(path: str) -> list[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    boundary = data.get("touched_boundary", data)
    errors = [f"Missing touched_boundary field: {key}" for key in REQUIRED if key not in boundary]
    file_paths = [item.get("path") for item in data.get("files", []) if isinstance(item, dict)]
    touched = set(boundary.get("touched_paths", []))
    for file_path in file_paths:
        if file_path and file_path not in touched:
            errors.append(f"File not listed in touched_paths: {file_path}")
    return errors
