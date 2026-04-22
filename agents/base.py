from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

WORKFLOW_SKILL_ROOT = Path(__file__).resolve().parent.parent / "skills" / "dev-team-workflow"
RESOURCE_ROOT = WORKFLOW_SKILL_ROOT / "resources"
HELPER_ROOT = RESOURCE_ROOT / "helpers"
CONTRACT_ROOT = RESOURCE_ROOT / "contracts"
CHECKLIST_ROOT = RESOURCE_ROOT / "checklists"
EXAMPLE_ROOT = RESOURCE_ROOT / "examples"
RULE_ROOT = RESOURCE_ROOT / "rules"
SKILL_ROOT = Path(__file__).resolve().parent.parent / "skills"


def safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"


def compact_history(history: List[Dict[str, Any]], limit: int = 4) -> str:
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


def _load_from(root: Path, name: str) -> str:
    path = root / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_skill_resource(name: str) -> str:
    return _load_from(RESOURCE_ROOT, name)


def load_helper_resource(name: str) -> str:
    return _load_from(HELPER_ROOT, name)


def load_contract(name: str) -> str:
    return _load_from(CONTRACT_ROOT, name)


def load_checklist(name: str) -> str:
    return _load_from(CHECKLIST_ROOT, name)


def load_example(name: str) -> str:
    return _load_from(EXAMPLE_ROOT, name)


def load_rule(name: str) -> str:
    return _load_from(RULE_ROOT, name)


def load_skill_pack_doc(skill_name: str, filename: str) -> str:
    return _load_from(SKILL_ROOT / skill_name, filename)


def load_skill_pack_bundle(skill_name: str, include_cases: bool = False) -> str:
    parts = [
        load_skill_pack_doc(skill_name, "SKILL.md"),
        load_skill_pack_doc(skill_name, "contracts.md"),
        load_skill_pack_doc(skill_name, "output_artifact.md"),
        load_skill_pack_doc(skill_name, "when_to_use.md"),
        load_skill_pack_doc(skill_name, "checklist.md"),
        load_skill_pack_doc(skill_name, "escalation_rules.md"),
    ]
    if include_cases:
        parts.append(load_skill_pack_doc(skill_name, "examples_good_bad.md"))
    return "\n\n".join(part for part in parts if part).strip()


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
        lines.append(shared_memory[:500])
    curated = sanctum.get("memory_markdown", "").strip()
    if curated:
        lines.append("Curated memory excerpt:")
        lines.append(curated[:500])
    if memories:
        lines.append("Relevant memories:")
        for item in memories:
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()
            score = item.get("score", "")
            if title or content:
                lines.append(f"- [{score}] {title}: {content[:160]}")
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


def _story_complexity(story_packet: dict | None) -> int:
    try:
        return int((story_packet or {}).get("complexity", (story_packet or {}).get("project_level", 2)) or 2)
    except Exception:
        return 2


def _loop_count(story_packet: dict | None) -> int:
    try:
        return int((story_packet or {}).get("loop_count", 1) or 1)
    except Exception:
        return 1


def _should_include_examples(story_packet: dict | None) -> bool:
    return _loop_count(story_packet) >= 2 or _story_complexity(story_packet) > 2


def _brownfield_corpus(project_mode: str, role: str, story_packet: dict | None = None) -> list[str]:
    if project_mode != "existing_project":
        return []
    pack_map = {
        "pm": ["brownfield-analyst"],
        "architect": ["integration-architect", "change-impact-reviewer"],
        "developer": ["safe-implementation-lane"],
        "fe_developer": ["safe-implementation-lane"],
        "be_developer": ["safe-implementation-lane"],
        "qa": ["change-impact-reviewer"],
        "fe_reviewer": ["change-impact-reviewer"],
        "be_reviewer": ["change-impact-reviewer"],
        "integration_qa": ["integration-architect", "change-impact-reviewer"],
        "lead": ["change-impact-reviewer"],
    }
    parts = [load_skill_resource("existing_project_rules.md")]
    if role in {"pm", "architect"}:
        parts.append(load_checklist("brownfield_readiness_checklist.md"))
    if role in {"qa", "fe_reviewer", "be_reviewer", "integration_qa"}:
        parts.append(load_checklist("qa_regression_checklist.md"))
    if role in {"developer", "fe_developer", "be_developer", "qa", "fe_reviewer", "be_reviewer", "integration_qa", "lead"}:
        parts.append(load_rule("change_request_rules.md"))
    include_cases = _should_include_examples(story_packet)
    for skill_name in pack_map.get(role, []):
        parts.append(load_skill_pack_bundle(skill_name, include_cases=include_cases))
    return [part for part in parts if part]



def _fe_corpus(role: str, story_packet: dict | None = None) -> list[str]:
    lanes = set((story_packet or {}).get("active_lanes", []) or [])
    execution_mode = str((story_packet or {}).get("execution_mode", "auto") or "auto").lower()
    is_frontend = "frontend" in lanes or execution_mode in {"frontend_only", "fullstack", "auto"}
    if not is_frontend and role not in {"fe_developer", "fe_reviewer"}:
        return []

    include_cases = _should_include_examples(story_packet)
    parts: list[str] = []

    if role in {"pm", "architect"}:
        parts.append(load_skill_pack_bundle("fe-design-direction", include_cases=include_cases))

    if role in {"developer", "fe_developer"}:
        parts.append(load_skill_pack_bundle("fe-ui-implementation", include_cases=include_cases))
        parts.append(load_skill_pack_doc("fe-ui-implementation", "anti_slop_rules.md"))
        parts.append(load_skill_pack_doc("fe-ui-implementation", "references/css_framework_policy.md"))
        parts.append(load_skill_pack_doc("fe-ui-implementation", "references/animation_policy.md"))
        parts.append(load_skill_pack_doc("fe-ui-implementation", "references/component_library_policy.md"))
        parts.append(load_skill_pack_doc("fe-ui-implementation", "references/no_fake_api_protocol.md"))

    if role in {"qa", "fe_reviewer", "integration_qa"}:
        parts.append(load_skill_pack_bundle("fe-visual-review", include_cases=include_cases))
        parts.append(load_skill_pack_doc("fe-visual-review", "anti_slop_rules.md"))
        parts.append(load_skill_pack_doc("fe-visual-review", "references/visual_review_rubric.md"))

    return [part for part in parts if part]

def _role_sizing_resource(role: str) -> str:
    mapping = {
        "pm": "role_sizing_pm.md",
        "architect": "role_sizing_architect.md",
        "developer": "role_sizing_developer.md",
        "fe_developer": "role_sizing_developer.md",
        "be_developer": "role_sizing_developer.md",
        "qa": "role_sizing_qa.md",
        "fe_reviewer": "role_sizing_qa.md",
        "be_reviewer": "role_sizing_qa.md",
        "integration_qa": "role_sizing_qa.md",
        "lead": "role_sizing_lead.md",
    }
    return load_skill_resource(mapping.get(role, "")) if mapping.get(role) else ""


def build_prompt_resources(
    *,
    role: str,
    story_packet: dict | None,
    project_mode: str,
    extra_rules: list[str] | None = None,
    contract: str = "",
    checklist: str = "",
    examples: str = "",
) -> str:
    parts = [
        common_workflow_helpers(story_packet),
        _role_sizing_resource(role),
        load_rule("gate_rules.md"),
        *(extra_rules or []),
        contract,
        checklist,
        (examples if _should_include_examples(story_packet) else ""),
        *_fe_corpus(role, story_packet),
        *_brownfield_corpus(project_mode, role, story_packet),
    ]
    return "\n\n".join(part for part in parts if part).strip()


def pm_resources(story_packet: dict | None = None, project_mode: str = "new_project") -> str:
    return build_prompt_resources(
        role="pm",
        story_packet=story_packet,
        project_mode=project_mode,
        contract=load_contract("pm_output_contract.md"),
        checklist=load_checklist("pm_checklist.md"),
        examples=load_example("pm_good_bad.md"),
    )


def architect_resources(story_packet: dict | None = None, project_mode: str = "new_project") -> str:
    return build_prompt_resources(
        role="architect",
        story_packet=story_packet,
        project_mode=project_mode,
        extra_rules=[load_skill_resource("new_project_rules.md" if project_mode == "new_project" else "existing_project_rules.md")],
        contract=load_contract("architect_output_contract.md"),
        checklist=load_checklist("architect_checklist.md"),
        examples=load_example("architect_good_bad.md"),
    )


def developer_resources(project_mode: str, execution_error: str, story_packet: dict | None = None, role: str = "developer") -> str:
    extra_rules = [
        load_helper_resource("dependency_policy.md"),
        load_skill_resource("react_dependency_policy.md"),
        load_skill_resource("new_project_rules.md" if project_mode == "new_project" else "existing_project_rules.md"),
        load_rule("change_request_rules.md"),
    ]
    if execution_error:
        extra_rules.append(load_skill_resource("build_repair_rules.md"))
    return build_prompt_resources(
        role=role,
        story_packet=story_packet,
        project_mode=project_mode,
        extra_rules=extra_rules,
        contract=load_contract("developer_output_contract.md"),
        checklist=load_checklist("developer_implementation_checklist.md"),
        examples=load_example("developer_good_bad.md"),
    )


def qa_resources(story_packet: dict | None = None, project_mode: str = "new_project", role: str = "qa") -> str:
    return build_prompt_resources(
        role=role,
        story_packet=story_packet,
        project_mode=project_mode,
        extra_rules=[load_skill_resource("qa_review_lenses.md")],
        contract=load_contract("qa_output_contract.md"),
        checklist=load_checklist("reviewer_checklist.md"),
        examples=load_example("qa_good_bad.md"),
    )


def lead_resources(story_packet: dict | None = None, project_mode: str = "new_project") -> str:
    return build_prompt_resources(
        role="lead",
        story_packet=story_packet,
        project_mode=project_mode,
        extra_rules=[load_skill_resource("lead_gate_rules.md")],
        contract=load_contract("lead_output_contract.md"),
        checklist=load_checklist("lead_decision_checklist.md"),
        examples=load_example("lead_good_bad.md"),
    )
