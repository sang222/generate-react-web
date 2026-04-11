from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from memory.schemas import AGENT_IDS, MEMORY_AGENT_IDS, SHARED_MEMORY_DEFAULTS, get_default_agent_profile

BMAD_DIRNAME = "_bmad"
MEMORY_DIRNAME = "memory"
SHARED_DIRNAME = "_shared"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_project_root(start: str | Path | None = None) -> Path:
    if start is None:
        return Path(__file__).resolve().parent.parent
    return Path(start).resolve()


def get_bmad_root(project_root: str | Path | None = None) -> Path:
    return get_project_root(project_root) / BMAD_DIRNAME


def get_memory_root(project_root: str | Path | None = None) -> Path:
    return get_bmad_root(project_root) / MEMORY_DIRNAME


def get_agent_sanctum_dir(agent_id: str, project_root: str | Path | None = None) -> Path:
    return get_memory_root(project_root) / agent_id


def get_agent_sessions_dir(agent_id: str, project_root: str | Path | None = None) -> Path:
    return get_agent_sanctum_dir(agent_id, project_root) / "sessions"


def get_shared_memory_dir(project_root: str | Path | None = None) -> Path:
    return get_memory_root(project_root) / SHARED_DIRNAME


def ensure_sanctum(project_root: str | Path | None = None) -> None:
    ensure_shared_memory(project_root)
    for agent_id in AGENT_IDS:
        ensure_agent_sanctum(agent_id, project_root)


def ensure_shared_memory(project_root: str | Path | None = None) -> Path:
    shared_dir = get_shared_memory_dir(project_root)
    shared_dir.mkdir(parents=True, exist_ok=True)
    index_path = shared_dir / "INDEX.md"
    if not index_path.exists():
        index_path.write_text(build_shared_index_md(), encoding="utf-8")
    for filename, content in SHARED_MEMORY_DEFAULTS.items():
        path = shared_dir / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")
    return shared_dir


def ensure_agent_sanctum(agent_id: str, project_root: str | Path | None = None) -> Path:
    sanctum_dir = get_agent_sanctum_dir(agent_id, project_root)
    sessions_dir = get_agent_sessions_dir(agent_id, project_root)
    sanctum_dir.mkdir(parents=True, exist_ok=True)
    if agent_id in MEMORY_AGENT_IDS:
        sessions_dir.mkdir(parents=True, exist_ok=True)

    profile = get_default_agent_profile(agent_id) or {}
    files = {
        "INDEX.md": build_index_md(agent_id),
        "PERSONA.md": build_persona_md(agent_id, str(profile.get("persona", ""))),
        "CREED.md": build_creed_md(agent_id, str(profile.get("creed", ""))),
        "BOND.md": build_bond_md(agent_id, profile.get("bond", {})),
        "MEMORY.md": build_memory_md(agent_id),
        "CAPABILITIES.md": build_capabilities_md(agent_id, profile.get("capabilities", [])),
    }
    for filename, content in files.items():
        path = sanctum_dir / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")
    pulse = sanctum_dir / "PULSE.md"
    if not pulse.exists():
        pulse.write_text(build_pulse_md(agent_id), encoding="utf-8")
    first_breath = sanctum_dir / "FIRST_BREATH.md"
    if not first_breath.exists():
        first_breath.write_text(build_first_breath_md(agent_id), encoding="utf-8")
    return sanctum_dir


def build_shared_index_md() -> str:
    return (
        "# Shared Module Memory\n\n"
        "Load these files as shared project context when relevant:\n"
        "- PROJECT.md\n- CONVENTIONS.md\n- RELEASE_PHILOSOPHY.md\n- STACK.md\n- MEMORY.md\n"
    )


def build_index_md(agent_id: str) -> str:
    return (
        f"# {agent_id} sanctum\n\n"
        "Load these files on each rebirth/session start:\n"
        "- PERSONA.md\n- CREED.md\n- BOND.md\n- MEMORY.md\n- CAPABILITIES.md\n\n"
        "Reference FIRST_BREATH.md to check whether onboarding and owner bonding already happened.\n"
        "Session logs live in `sessions/YYYY-MM-DD.md` for memory agents only.\n"
        "Curated durable lessons belong in `MEMORY.md`.\n"
    )


def build_persona_md(agent_id: str, persona: str) -> str:
    return f"# Persona\n\nAgent: {agent_id}\n\n{persona}\n"


def build_creed_md(agent_id: str, creed: str) -> str:
    return f"# Creed\n\nAgent: {agent_id}\n\n{creed}\n"


def build_bond_md(agent_id: str, bond: object) -> str:
    prefs = bond.get("owner_preferences", []) if isinstance(bond, dict) else []
    lines = ["# Bond", "", f"Agent: {agent_id}", "", "## Owner preferences"]
    if prefs:
        lines.extend([f"- {item}" for item in prefs])
    else:
        lines.append("- None recorded yet.")
    return "\n".join(lines) + "\n"


def build_memory_md(agent_id: str) -> str:
    return (
        "# Curated Memory\n\n"
        f"Agent: {agent_id}\n\n"
        "Keep this file concise. Durable lessons only. Prefer under 200 lines.\n\n"
        "## Lessons\n- None recorded yet.\n"
    )


def build_capabilities_md(agent_id: str, capabilities: object) -> str:
    caps = capabilities if isinstance(capabilities, list) else []
    lines = ["# Capabilities", "", f"Agent: {agent_id}", "", "## Built-in"]
    lines.extend([f"- {item}" for item in caps] if caps else ["- None recorded yet."])
    lines.extend(["", "## Learned", "- None recorded yet."])
    return "\n".join(lines) + "\n"


def build_pulse_md(agent_id: str) -> str:
    return f"# Pulse\n\nAgent: {agent_id}\n\nUse this file only if autonomous wake or heartbeat behavior is later enabled.\n"


def build_first_breath_md(agent_id: str) -> str:
    return (
        f"# First Breath\n\nAgent: {agent_id}\n\n"
        "status: pending\n\n"
        "This file records the first bonding and territory-discovery pass with the owner.\n"
    )


def read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


def parse_bullets(markdown: str) -> List[str]:
    items: List[str] = []
    for line in markdown.splitlines():
        match = re.match(r"^\s*[-*]\s+(.*)\s*$", line)
        if match:
            value = match.group(1).strip()
            if value and value.lower() != "none recorded yet.":
                items.append(value)
    return items


def load_agent_sanctum(agent_id: str, project_root: str | Path | None = None) -> Dict[str, object]:
    ensure_agent_sanctum(agent_id, project_root)
    sanctum_dir = get_agent_sanctum_dir(agent_id, project_root)
    first_breath = read_markdown(sanctum_dir / "FIRST_BREATH.md")
    return {
        "agent_id": agent_id,
        "persona_markdown": read_markdown(sanctum_dir / "PERSONA.md"),
        "creed_markdown": read_markdown(sanctum_dir / "CREED.md"),
        "bond_markdown": read_markdown(sanctum_dir / "BOND.md"),
        "memory_markdown": read_markdown(sanctum_dir / "MEMORY.md"),
        "capabilities_markdown": read_markdown(sanctum_dir / "CAPABILITIES.md"),
        "first_breath_markdown": first_breath,
        "first_breath_complete": "status: complete" in first_breath.lower(),
        "bond_items": parse_bullets(read_markdown(sanctum_dir / "BOND.md")),
        "memory_items": parse_bullets(read_markdown(sanctum_dir / "MEMORY.md")),
        "capability_items": parse_bullets(read_markdown(sanctum_dir / "CAPABILITIES.md")),
        "sanctum_dir": str(sanctum_dir),
    }


def load_shared_memory(project_root: str | Path | None = None) -> Dict[str, object]:
    ensure_shared_memory(project_root)
    shared_dir = get_shared_memory_dir(project_root)
    docs = {name: read_markdown(shared_dir / name) for name in ["PROJECT.md", "CONVENTIONS.md", "RELEASE_PHILOSOPHY.md", "STACK.md", "MEMORY.md"]}
    return {"dir": str(shared_dir), "documents": docs, "memory_items": parse_bullets(docs.get("MEMORY.md", ""))}


def append_session_log(agent_id: str, summary: str, project_root: str | Path | None = None) -> Path:
    ensure_agent_sanctum(agent_id, project_root)
    sessions_dir = get_agent_sessions_dir(agent_id, project_root)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".md"
    path = sessions_dir / filename
    stamp = utc_now_iso()
    block = f"\n## {stamp}\n\n{summary.strip()}\n"
    if path.exists():
        path.write_text(path.read_text(encoding="utf-8") + block, encoding="utf-8")
    else:
        path.write_text(f"# Session Log\n\nAgent: {agent_id}\n" + block, encoding="utf-8")
    return path


def append_curated_memory(agent_id: str, lesson: str, project_root: str | Path | None = None, max_items: int = 24) -> Path:
    ensure_agent_sanctum(agent_id, project_root)
    path = get_agent_sanctum_dir(agent_id, project_root) / "MEMORY.md"
    return _append_memory_line(path, f"Agent: {agent_id}", lesson, max_items)


def append_shared_memory(lesson: str, project_root: str | Path | None = None, max_items: int = 32) -> Path:
    ensure_shared_memory(project_root)
    path = get_shared_memory_dir(project_root) / "MEMORY.md"
    return _append_memory_line(path, "Shared module memory", lesson, max_items, title="# Shared Module Memory")


def _append_memory_line(path: Path, owner_line: str, lesson: str, max_items: int, title: str = "# Curated Memory") -> Path:
    existing = read_markdown(path)
    current_items = parse_bullets(existing)
    lesson = lesson.strip()
    if not lesson:
        return path
    normalized = {item.lower() for item in current_items}
    if lesson.lower() not in normalized:
        current_items.append(lesson)
    trimmed = current_items[-max_items:]
    lines = [title, "", owner_line, "", "Keep this file concise. Durable lessons only.", "", "## Lessons"]
    lines.extend([f"- {item}" for item in trimmed] if trimmed else ["- None recorded yet."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def set_first_breath_complete(agent_id: str, notes: str, project_root: str | Path | None = None) -> Path:
    ensure_agent_sanctum(agent_id, project_root)
    path = get_agent_sanctum_dir(agent_id, project_root) / "FIRST_BREATH.md"
    content = (
        f"# First Breath\n\nAgent: {agent_id}\n\nstatus: complete\n\ncompleted_at: {utc_now_iso()}\n\n{notes.strip()}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path
