from __future__ import annotations

from typing import Any, Dict, Iterable


def derive_effective_target(
    system_target: Dict[str, Any],
    active_lanes: Iterable[str] | None = None,
) -> Dict[str, Any]:
    target = dict(system_target or {})
    lanes = set(active_lanes or [])

    if not lanes:
        return target

    has_frontend = "frontend" in lanes
    has_backend = "backend" in lanes

    if has_frontend and has_backend:
        target["effective_mode"] = "fullstack"
        target.setdefault("frontend_root", "frontend")
        return target

    if has_frontend:
        target["effective_mode"] = "frontend_only"

        # For frontend_only new projects, the runnable Vite app lives at output root.
        # Fullstack still uses frontend/ when both lanes are active.
        target["frontend_root"] = "."

        target["backend_language"] = "none"
        target["backend_framework"] = "none"
        target["backend_build_tool"] = "none"
        target["database_engine"] = "none"
        target["database_orm"] = "none"
        return target

    if has_backend:
        target["effective_mode"] = "backend_only"
        target["frontend_stack"] = "none"
        return target

    return target