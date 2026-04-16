from __future__ import annotations

import json
from typing import Any, Dict, List

def _text_has_markers(text: str, markers: List[str]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def detect_needed_lanes(story_packet: Dict[str, Any], task: str) -> List[str]:
    execution_mode = str(story_packet.get("execution_mode", "auto") or "auto").lower()
    if execution_mode == "frontend_only":
        return ["frontend"]
    if execution_mode == "backend_only":
        return ["backend"]
    if execution_mode == "fullstack":
        return ["frontend", "backend"]

    story_text_parts = [task, json.dumps(story_packet, ensure_ascii=False)]
    story_text_parts.extend(story_packet.get("in_scope", []) or [])
    story_text_parts.extend(story_packet.get("allowed_change_scope", []) or [])
    packet_text = "\n".join(str(part) for part in story_text_parts if part)
    level = int(story_packet.get("project_level", 2) or 2)

    backend_markers = [
        "backend",
        "api",
        "spring",
        "controller",
        "repository",
        "database",
        "postgres",
        "jpa",
        "auth",
        "service",
        "backend/",
        "src/main/java",
        "endpoint",
        "schema",
        "migration",
        "gradle",
        "entity",
    ]
    frontend_markers = ["frontend", "ui", "page", "component", "layout", "route", "screen", "banner"]

    needs_backend = _text_has_markers(packet_text, backend_markers)
    needs_frontend = _text_has_markers(packet_text, frontend_markers) or not needs_backend

    if level <= 1 and not needs_backend:
        return ["frontend"]
    if needs_backend and needs_frontend:
        return ["frontend", "backend"]
    if needs_backend:
        return ["backend"]
    return ["frontend"]


