from __future__ import annotations

from typing import Any, Dict, List, Tuple


def clean_path(path: str) -> str:
    return str(path or "").replace("\\", "/").lstrip("./")


def is_under_root(path: str, root: str) -> bool:
    clean = clean_path(path)
    root_clean = clean_path(root).rstrip("/")
    if root_clean in {"", "."}:
        return True
    return clean == root_clean or clean.startswith(root_clean + "/")


def allowed_roots_for_lane(lane: str, effective_target: Dict[str, Any]) -> List[str]:
    mode = effective_target.get("effective_mode")
    layout = effective_target.get("layout") or effective_target.get("app_topology")
    if mode == "fullstack" and layout == "monorepo":
        if lane == "frontend":
            return [str(root) for root in (effective_target.get("frontend_roots") or [])]
        if lane == "backend":
            return [str(effective_target.get("backend_root") or "api")]
    if lane == "frontend":
        root = str(effective_target.get("frontend_root", "frontend") or "")
        return ["."] if root in {"", "."} else [root]
    if lane == "backend":
        return [str(effective_target.get("backend_root") or "backend")]
    return ["."]


def filter_files_for_lane(files: List[Dict[str, Any]], lane: str, effective_target: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    roots = allowed_roots_for_lane(lane, effective_target)
    if not roots:
        return files, []
    kept: List[Dict[str, Any]] = []
    dropped: List[str] = []
    for item in files or []:
        path = clean_path(item.get("path", ""))
        if any(is_under_root(path, root) for root in roots):
            cloned = dict(item)
            cloned["path"] = path
            kept.append(cloned)
        else:
            dropped.append(path)
    return kept, dropped


def format_allowed_roots(lane: str, effective_target: Dict[str, Any]) -> str:
    roots = allowed_roots_for_lane(lane, effective_target)
    if not roots:
        return "no writable roots"
    return ", ".join(f"{root}/**" if root not in {"", "."} else "root app files" for root in roots)
