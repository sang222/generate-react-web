from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

WORKFLOW_SKILL_ROOT = Path(__file__).resolve().parent.parent / "skills" / "dev-team-workflow"
RESOURCE_ROOT = WORKFLOW_SKILL_ROOT / "resources"
HELPER_ROOT = RESOURCE_ROOT / "helpers"


def safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"


def compact_history(history: List[Dict[str, Any]], limit: int = 6) -> str:
    if not history:
        return "[]"
    sliced = history[-limit:]
    simplified = []
    for item in sliced:
        simplified.append(
            {
                "loop": item.get("loop", 0),
                "release_status": item.get("release_status", ""),
                "severity": item.get("severity", ""),
                "execution_error": item.get("execution_error", ""),
                "qa_detail": item.get("qa_detail", {}),
                "fix_suggestion": item.get("fix_suggestion", ""),
            }
        )
    return safe_json(simplified)


def load_skill_resource(name: str) -> str:
    path = RESOURCE_ROOT / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_helper_resource(name: str) -> str:
    path = HELPER_ROOT / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def render_agent_context(agent_context: Dict[str, Any], max_memories: int = 5) -> str:
    if not isinstance(agent_context, dict):
        return "No agent context."
    profile = agent_context.get("profile", {}) or {}
    sanctum = agent_context.get("sanctum", {}) or {}
    shared = agent_context.get("shared_memory", {}) or {}
    memories = (agent_context.get("memories", []) or [])[:max_memories]
    lines = [
        f"Project mode: {agent_context.get('project_mode', 'new_project')}",
        f"Agent type: {agent_context.get('agent_type', 'memory')}",
        f"Persona: {profile.get('persona', '').strip()}",
        f"Creed: {profile.get('creed', '').strip()}",
    ]
    bond = profile.get("bond", {}) or {}
    owner_prefs = bond.get("owner_preferences", []) if isinstance(bond, dict) else []
    if owner_prefs:
        lines.append("Owner preferences:")
        lines.extend([f"- {item}" for item in owner_prefs[:5]])
    caps = profile.get("capabilities", []) or []
    if caps:
        lines.append("Capabilities: " + ", ".join(caps[:8]))
    shared_docs = shared.get("documents", {}) if isinstance(shared, dict) else {}
    shared_memory = str(shared_docs.get("MEMORY.md", "")).strip()
    if shared_memory:
        lines.append("Shared memory excerpt:")
        lines.append(shared_memory[:700])
    curated = sanctum.get("memory_markdown", "").strip()
    if curated:
        lines.append("Curated memory excerpt:")
        lines.append(curated[:800])
    if memories:
        lines.append("Relevant memories:")
        for item in memories:
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            score = item.get("score", "")
            if title or content:
                lines.append(f"- [{score}] {title}: {content[:220]}")
    return "\n".join(lines).strip()


def render_system_target_helper(story_packet: dict | None) -> str:
    target = (story_packet or {}).get("system_target", {})
    level = (story_packet or {}).get("project_level", "")
    profile = (story_packet or {}).get("delivery_profile", "")
    reasons = (story_packet or {}).get("level_reasoning", []) or []
    lines = [
        "Configured system target:",
        f"- System type: {target.get('system_type', 'web_app')}",
        f"- Frontend: {target.get('frontend_stack', 'react-vite')}",
        f"- Backend: {target.get('backend_language', 'none')} + {target.get('backend_framework', 'none')} ({target.get('backend_build_tool', 'n/a')})",
        f"- Database: {target.get('database_engine', 'none')} + {target.get('database_orm', 'none')}",
        f"- Project level: {level} ({profile})",
    ]
    if reasons:
        lines.append("- Sizing reasons: " + ", ".join(reasons))
    return "\n".join(lines)


def render_right_sizing_helper(story_packet: dict | None) -> str:
    level = int((story_packet or {}).get("project_level", 2) or 2)
    profile = (story_packet or {}).get("delivery_profile", "standard")
    base = load_helper_resource("project_levels.md")
    lines = [base, "", f"Current delivery profile: level {level} ({profile})"]
    if level <= 1:
        lines.append("Right-sizing rule: keep the solution very small, prefer fewer files, and avoid unnecessary FE/BE separation work.")
    elif level == 2:
        lines.append("Right-sizing rule: standard story delivery. Keep architecture practical and bounded to the story.")
    else:
        lines.append("Right-sizing rule: preserve story gating, baseline safety, and stronger architecture discipline.")
    return "\n".join([item for item in lines if item]).strip()


def common_workflow_helpers(story_packet: dict | None) -> str:
    parts = [
        load_helper_resource("global_delivery_rules.md"),
        render_system_target_helper(story_packet),
        render_right_sizing_helper(story_packet),
    ]
    return "\n\n".join([item for item in parts if item]).strip()


def developer_resources(project_mode: str, execution_error: str, story_packet: dict | None = None) -> str:
    resources = [
        load_skill_resource("skill_overview.md"),
        common_workflow_helpers(story_packet),
        load_helper_resource("dependency_policy.md"),
        load_skill_resource("developer_output_contract.md"),
        load_skill_resource("react_dependency_policy.md"),
        load_skill_resource("new_project_rules.md" if project_mode == "new_project" else "existing_project_rules.md"),
    ]
    if execution_error:
        resources.append(load_skill_resource("build_repair_rules.md"))
    return "\n\n".join([item for item in resources if item]).strip()


def qa_resources(story_packet: dict | None = None) -> str:
    return "\n\n".join(
        [
            load_skill_resource("skill_overview.md"),
            common_workflow_helpers(story_packet),
            load_skill_resource("qa_review_lenses.md"),
        ]
    ).strip()


def lead_resources(story_packet: dict | None = None) -> str:
    return "\n\n".join(
        [
            load_skill_resource("skill_overview.md"),
            common_workflow_helpers(story_packet),
            load_skill_resource("lead_gate_rules.md"),
        ]
    ).strip()
