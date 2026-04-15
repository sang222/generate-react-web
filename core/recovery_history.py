from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def history_root(root: str | Path = ".") -> Path:
    return Path(root) / "skill_history"


def candidate_history_path(root: str | Path = ".") -> Path:
    return history_root(root) / "candidate_runs.jsonl"


def review_history_path(root: str | Path = ".") -> Path:
    return history_root(root) / "candidate_reviews.jsonl"


def auto_apply_history_path(root: str | Path = ".") -> Path:
    return history_root(root) / "auto_applied.jsonl"


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_candidate_run(payload: Dict[str, Any], root: str | Path = ".") -> None:
    enriched = {"timestamp": _now_iso(), **payload}
    append_jsonl(candidate_history_path(root), enriched)


def log_candidate_review(payload: Dict[str, Any], root: str | Path = ".") -> None:
    enriched = {"timestamp": _now_iso(), **payload}
    append_jsonl(review_history_path(root), enriched)


def log_auto_applied(payload: Dict[str, Any], root: str | Path = ".") -> None:
    enriched = {"timestamp": _now_iso(), **payload}
    append_jsonl(auto_apply_history_path(root), enriched)
