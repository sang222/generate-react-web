from __future__ import annotations

import json
from pathlib import Path

REQUIRED = ["schema_version", "decision", "score", "issues", "anti_slop_flags", "retry_prompt"]
VALID = {"PASS", "RETRY", "BLOCKED"}

def validate(path: str) -> list[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = [f"Missing field: {key}" for key in REQUIRED if key not in data]
    if data.get("decision") not in VALID:
        errors.append("decision must be PASS, RETRY, or BLOCKED")
    return errors
