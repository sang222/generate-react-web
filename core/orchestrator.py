from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from agents.architect import run_architect
from agents.developer import run_developer
from agents.lead import run_lead
from agents.pm import run_pm
from agents.qa import run_qa
from core.config import get_system_target, load_module_config
from core.executor import run_system_check
from core.file_manager import (
    OUTPUT_DIR,
    copy_tree,
    load_baseline_project,
    reset_output_dir,
    summarize_project_tree,
    summarize_project_tree_for,
    write_project,
)
from core.memory import save_run
from core.ownership import detect_cross_lane_conflicts, ensure_ownership_map, lane_files, ownership_map_path
from core.story_state import (
    default_story_packet,
    ensure_artifact_locks,
    ensure_delivery_index,
    ensure_epic_context,
    find_baseline_from_dependencies,
    get_story_definition,
    load_epic_context,
    lock_artifacts,
    update_delivery_index,
)
from core.gates import fail_gate, load_gate_state, pass_gate, save_gate_state
from core.change_request import create_change_request
from memory.manager import AgentMemoryManager

MODULE_CONFIG = load_module_config()
SYSTEM_TARGET = get_system_target(MODULE_CONFIG)
MAX_LOOP = int(MODULE_CONFIG.get("devteam", {}).get("max_retry_loops", 3))
OUTPUT_PROJECT_DIR = MODULE_CONFIG.get("devteam", {}).get("output_project_dir", "output_project")
STATE_DIR = Path(MODULE_CONFIG.get("devteam", {}).get("state_dir", "state"))
RUN_STATE_PATH = STATE_DIR / "run_state.json"
DELIVERIES_DIR = Path(MODULE_CONFIG.get("devteam", {}).get("deliveries_dir", "deliveries"))


def log_step(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [orchestrator] {message}", flush=True)


def _safe_json_loads(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    direct = _safe_json_loads(text)
    if direct:
        return direct
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return {}
    return _safe_json_loads(match.group(0))


def _normalize_files(dev_result: Dict[str, Any]) -> List[Dict[str, str]]:
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


def _dedupe_files(files: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, str] = {}
    for item in files:
        merged[item["path"]] = item["content"]
    return [{"path": k, "content": v} for k, v in merged.items()]


def _find_missing_required_files_in_output() -> List[str]:
    required: List[str] = []
    if SYSTEM_TARGET.get("system_type") == "fullstack_website":
        required.extend([
            "frontend/package.json",
            "frontend/index.html",
            "frontend/src/main.jsx",
            "frontend/src/App.jsx",
            "backend/build.gradle",
            "backend/src/main/resources/application.properties",
        ])
    else:
        required.extend([
            "package.json",
            "index.html",
            "src/main.jsx",
            "src/App.jsx",
        ])
    return sorted(path for path in required if not (OUTPUT_DIR / path).exists())


def _detect_needed_lanes(story_packet: Dict[str, Any], task: str) -> List[str]:
    packet_text = (task + "\n" + json.dumps(story_packet, ensure_ascii=False)).lower()
    level = int(story_packet.get("project_level", 2) or 2)
    backend_markers = ["backend", "api", "spring", "controller", "repository", "database", "postgres", "jpa", "auth", "service"]
    needs_backend = any(marker in packet_text for marker in backend_markers)
    if level <= 1 and not needs_backend:
        return ["frontend"]
    if needs_backend or story_packet.get("system_target", {}).get("system_type") == "fullstack_website":
        return ["frontend", "backend"]
    return ["frontend"]


def _workflow_status_path(project_id: str) -> Path:
    return Path("project_state") / project_id / "workflow_status.yaml"


def _write_workflow_status(context: Dict[str, Any], recommendation: str = "") -> None:
    path = _workflow_status_path(context['project_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if isinstance(context.get('delivery_index'), dict):
        current = context.get('delivery_index', {}).get('current_delivered_story', {}) or {}
    gate_state = context.get('gate_state', {}) or {}
    lines = [
        f"project_id: {context.get('project_id','')}",
        f"epic_id: {context.get('epic_id','')}",
        f"story_id: {context.get('story_id','')}",
        f"story_name: {json.dumps(context.get('story_name',''), ensure_ascii=False)}",
        f"project_mode: {context.get('project_mode','')}",
        f"project_level: {context.get('story_packet',{}).get('project_level','')}",
        f"delivery_profile: {context.get('story_packet',{}).get('delivery_profile','')}",
        f"current_gate: {gate_state.get('current_gate','')}",
        f"final_decision: {context.get('final_decision','')}",
        f"release_status: {context.get('release_status','')}",
        f"current_delivered_story_id: {current.get('story_id','')}",
        f"current_delivered_story_name: {json.dumps(current.get('story_name',''), ensure_ascii=False)}",
        f"next_story: {context.get('next_story','')}",
        f"recommendation: {json.dumps(recommendation, ensure_ascii=False)}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding='utf-8')


def _make_empty_qa_detail() -> Dict[str, List[str]]:
    return {
        "structural_bugs": [],
        "functional_bugs": [],
        "prd_gaps": [],
        "ui_gaps": [],
        "regression_bugs": [],
    }


def _merge_qa_details(*details: Dict[str, List[str]]) -> Dict[str, List[str]]:
    result = _make_empty_qa_detail()
    for detail in details:
        for key in result.keys():
            for item in detail.get(key, []) or []:
                if item not in result[key]:
                    result[key].append(item)
    return result


def classify_release_status(context: Dict[str, Any]) -> Tuple[str, str, str]:
    execution_error = (context.get("execution_error") or "").strip()
    qa_detail = context.get("qa_detail") or {}
    structural_bugs = qa_detail.get("structural_bugs") or []
    functional_bugs = qa_detail.get("functional_bugs") or []
    prd_gaps = qa_detail.get("prd_gaps") or []
    regression_bugs = qa_detail.get("regression_bugs") or []
    ui_gaps = qa_detail.get("ui_gaps") or []

    if execution_error or structural_bugs or functional_bugs or prd_gaps or regression_bugs:
        return ("RETRY", "BLOCKER", "Build failed, ownership/integration failed, or story acceptance criteria are incomplete.")
    if ui_gaps:
        return ("DONE", "MINOR", "Build and current story requirements passed, with only minor UI gaps remaining.")
    return ("DONE", "NONE", "Build passed and no important QA gaps remain for the current story.")


def _append_history(context: Dict[str, Any]) -> None:
    context["history"].append(
        {
            "loop": context.get("loop_count", 0),
            "epic_id": context.get("epic_id", ""),
            "story_id": context.get("story_id", "story_1"),
            "story_name": context.get("story_name", context.get("story_id", "story_1")),
            "release_status": context.get("release_status", ""),
            "severity": context.get("severity", ""),
            "execution_error": context.get("execution_error", ""),
            "qa_detail": context.get("qa_detail", _make_empty_qa_detail()),
            "fix_suggestion": context.get("fix_suggestion", ""),
        }
    )


def _build_planned_changes(context: Dict[str, Any], lane: str = "integration") -> Dict[str, Any]:
    return {
        "project_mode": context.get("project_mode", "new_project"),
        "goal": context.get("task", ""),
        "project_id": context.get("project_id", ""),
        "epic_id": context.get("epic_id", ""),
        "story_id": context.get("story_id", "story_1"),
        "story_name": context.get("story_name", context.get("story_id", "story_1")),
        "resume_from": context.get("baseline_path", ""),
        "lane": lane,
        "parallel_mode": True,
        "gate_state": context.get("gate_state", {}),
        "change_requests": context.get("change_requests", []),
    }


def _build_workflow_context(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task": context.get("task", ""),
        "project_mode": context.get("project_mode", "new_project"),
        "project_id": context.get("project_id", ""),
        "epic_id": context.get("epic_id", ""),
        "story_id": context.get("story_id", "story_1"),
        "story_name": context.get("story_name", context.get("story_id", "story_1")),
        "delivery_mode": context.get("delivery_mode", "story_based"),
        "baseline_path": context.get("baseline_path", ""),
        "baseline_tree": context.get("baseline_tree", ""),
        "story_packet": context.get("story_packet", {}),
        "system_target": context.get("system_target", SYSTEM_TARGET),
        "prd": context.get("prd", ""),
        "design": context.get("design", ""),
        "bugs": context.get("bugs", []),
        "fix_suggestion": context.get("fix_suggestion", ""),
        "execution_error": context.get("execution_error", ""),
        "history": context.get("history", []),
        "qa_detail": context.get("qa_detail", {}),
        "release_status": context.get("release_status", ""),
        "severity": context.get("severity", ""),
        "retry_reason": context.get("retry_reason", ""),
        "operation": context.get("operation", "generate"),
    }


def _write_run_state(context: Dict[str, Any]) -> str:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": context.get("run_id", ""),
        "project_id": context.get("project_id", ""),
        "epic_id": context.get("epic_id", ""),
        "story_id": context.get("story_id", "story_1"),
        "story_name": context.get("story_name", context.get("story_id", "story_1")),
        "delivery_mode": context.get("delivery_mode", "story_based"),
        "task": context.get("task", ""),
        "project_mode": context.get("project_mode", "new_project"),
        "baseline_path": context.get("baseline_path", ""),
        "loop_count": context.get("loop_count", 0),
        "operation": context.get("operation", "generate"),
        "retry_reason": context.get("retry_reason", ""),
        "release_status": context.get("release_status", ""),
        "severity": context.get("severity", ""),
        "execution_error": context.get("execution_error", ""),
        "qa_detail": context.get("qa_detail", {}),
        "story_packet": context.get("story_packet", {}),
        "system_target": context.get("system_target", SYSTEM_TARGET),
        "history_tail": context.get("history", [])[-3:],
        "output_project_dir": OUTPUT_PROJECT_DIR,
        "gate_state": context.get("gate_state", {}),
        "artifact_locks_path": context.get("artifact_locks_path", ""),
        "change_requests": context.get("change_requests", []),
    }
    RUN_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(RUN_STATE_PATH)


def _run_lead_and_store_summary(context: Dict[str, Any], memory_manager: AgentMemoryManager, rule_reason: str) -> None:
    log_step(f"Loop {context['loop_count']}/{MAX_LOOP} - Running Lead (status={context['release_status']}, severity={context['severity']})")
    lead_ctx = memory_manager.load_context("lead", task=context["task"], workflow_context=_build_workflow_context(context))
    lead_raw = run_lead(
        task=context["task"],
        prd=context["prd"],
        design=context["design"],
        code=context["code"],
        qa_detail=context["qa_detail"],
        execution_error=context["execution_error"],
        loop_count=context["loop_count"],
        max_loop=MAX_LOOP,
        rule_result={"release_status": context["release_status"], "severity": context["severity"], "reason": rule_reason},
        history=context["history"],
        agent_context=lead_ctx,
        story_packet=context.get("story_packet", {}),
    )
    context["lead_summary"] = _extract_json_object(lead_raw)


def _prepare_baseline(context: Dict[str, Any]) -> None:
    baseline_path = context.get("baseline_path", "")
    if baseline_path:
        log_step(f"Loading baseline from {baseline_path}")
        load_baseline_project(baseline_path)
        context["baseline_tree"] = summarize_project_tree_for(baseline_path)
    else:
        reset_output_dir()
        context["baseline_tree"] = ""


def _create_story_delivery(context: Dict[str, Any]) -> Dict[str, Any]:
    project_id = context.get("project_id", "")
    epic_id = context.get("epic_id", "")
    story_id = context.get("story_id", "story_1")
    story_name = context.get("story_name", story_id)
    delivery_root = DELIVERIES_DIR / project_id / story_id
    source_dir = delivery_root / "source"
    manifest_path = delivery_root / "story_manifest.json"
    review_path = delivery_root / "review_report.json"
    integration_path = delivery_root / "integration_report.json"
    delivery_root.mkdir(parents=True, exist_ok=True)
    copy_tree(OUTPUT_DIR, source_dir)
    manifest = {
        "project_id": project_id,
        "epic_id": epic_id,
        "story_id": story_id,
        "story_name": story_name,
        "status": "delivered",
        "release_decision": "DELIVER_STORY",
        "delivered_at": datetime.now().isoformat(timespec="seconds"),
        "baseline_from_story": (context.get("story_packet", {}).get("baseline_story_id") or ""),
        "depends_on": context.get("depends_on", []),
        "business_goal": context.get("story_packet", {}).get("business_goal", context.get("task", "")),
        "acceptance_criteria": context.get("story_acceptance_criteria", []),
        "acceptance_result": {
            "passed": context.get("story_acceptance_criteria", []),
            "failed": [],
        },
        "in_scope": context.get("story_packet", {}).get("in_scope", []),
        "out_of_scope": context.get("story_packet", {}).get("out_of_scope", []),
        "summary": context.get("lead_summary", {}).get("reason") or context.get("task", ""),
        "source_dir": str(source_dir),
        "project_tree": summarize_project_tree_for(source_dir),
        "ownership_map_path": context.get("ownership_map_path", ""),
        "parallel_mode": True,
        "gate_state": context.get("gate_state", {}),
        "change_requests": context.get("change_requests", []),
        "fe_changed_files": sorted(item["path"] for item in context.get("fe_files", [])),
        "be_changed_files": sorted(item["path"] for item in context.get("be_files", [])),
        "next_story": context.get("next_story", ""),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    review_path.write_text(json.dumps({
        "fe_review": context.get("fe_review", {}),
        "be_review": context.get("be_review", {}),
        "integration_review": context.get("integration_review", {}),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    integration_path.write_text(json.dumps({
        "integration_conflicts": context.get("integration_conflicts", []),
        "integration_notes": context.get("integration_notes", []),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    lock_artifacts(project_id, story_id, 'RELEASE_GATE', [str(manifest_path), str(source_dir), str(review_path), str(integration_path)])
    data = update_delivery_index(project_id, epic_id, story_id, story_name, str(manifest_path))
    return {"delivery_root": str(delivery_root), "delivery_source": str(source_dir), "delivery_manifest": str(manifest_path), "delivery_index": data}


def _run_lane_developer(context: Dict[str, Any], memory_manager: AgentMemoryManager, lane: str, role: str, ownership_map: Dict[str, Any]) -> tuple[list[dict], dict]:
    dev_ctx = memory_manager.load_context(role, context["task"], _build_workflow_context(context))
    log_step(f"Loop {context['loop_count']}/{MAX_LOOP} - Running {role}")
    task = context["task"]
    if context.get("baseline_tree"):
        task += f"\n\nExisting baseline tree:\n{context['baseline_tree']}"
    raw = run_developer(
        task=task,
        prd=context["prd"],
        design=context["design"],
        bugs=context["bugs"],
        fix_suggestion=context["fix_suggestion"],
        execution_error=context["execution_error"],
        history=context["history"],
        planned_changes=_build_planned_changes(context, lane),
        agent_context=dev_ctx,
        project_mode=context["project_mode"],
        role=role,
        lane=lane,
        ownership_map=ownership_map,
        story_packet=context["story_packet"],
    )
    result = _extract_json_object(raw)
    return _normalize_files(result), result


def _run_lane_review(context: Dict[str, Any], memory_manager: AgentMemoryManager, lane: str, role: str, code: dict) -> dict:
    qa_ctx = memory_manager.load_context(role, context["task"], _build_workflow_context(context))
    raw = run_qa(
        task=context["task"],
        prd=context["prd"],
        design=context["design"],
        code=code,
        extra_bugs=[],
        agent_context=qa_ctx,
        role=role,
        lane=lane,
        story_packet=context["story_packet"],
    )
    res = _extract_json_object(raw)
    return {
        "structural_bugs": res.get("structural_bugs", []) or [],
        "functional_bugs": res.get("functional_bugs", []) or [],
        "prd_gaps": res.get("prd_gaps", []) or [],
        "ui_gaps": res.get("ui_gaps", []) or [],
        "regression_bugs": res.get("regression_bugs", []) or [],
        "fix_suggestion": res.get("fix_suggestion", "") or "",
    }


def run_orchestrator(task: str, project_mode: str = "new_project", project_id: str | None = None, epic_id: str | None = None, story_id: str | None = None, story_name: str | None = None, resume_from: str | None = None, depends_on: List[str] | None = None) -> Dict[str, Any]:
    memory_manager = AgentMemoryManager()
    memory_manager.ensure_bootstrap()

    story_id = (story_id or "story_1").strip() or "story_1"
    story_name = (story_name or story_id).strip() or story_id
    project_id = (project_id or f"project_{uuid.uuid4().hex[:8]}").strip()
    epic_id = (epic_id or f"{project_id}-epic").strip()

    epic_context = ensure_epic_context(project_id, epic_id, story_id, story_name, depends_on or [])
    story_def = get_story_definition(project_id, story_id)
    delivery_index = ensure_delivery_index(project_id, epic_id, epic_context)
    artifact_locks = ensure_artifact_locks(project_id)
    ownership_map = ensure_ownership_map(project_id)
    ownership_path = str(ownership_map_path(project_id))
    inferred_baseline = resume_from or find_baseline_from_dependencies(project_id, story_id, DELIVERIES_DIR)
    effective_project_mode = "existing_project" if inferred_baseline else project_mode

    story_packet = default_story_packet(project_id, epic_id, story_id, story_name, inferred_baseline or "", ownership_path, task)
    story_packet["depends_on"] = depends_on or story_packet.get('depends_on', [])
    story_packet['acceptance_criteria'] = story_def.get('acceptance_criteria', story_packet.get('acceptance_criteria', []))
    story_packet['in_scope'] = story_def.get('in_scope', story_packet.get('in_scope', []))
    story_packet['out_of_scope'] = story_def.get('out_of_scope', story_packet.get('out_of_scope', []))
    if story_packet.get('depends_on'):
        story_packet["baseline_story_id"] = story_packet['depends_on'][-1]
    context: Dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "project_id": project_id,
        "epic_id": epic_id,
        "story_id": story_id,
        "story_name": story_name,
        "delivery_mode": "story_based",
        "baseline_path": inferred_baseline or "",
        "baseline_tree": summarize_project_tree_for(inferred_baseline) if inferred_baseline else "",
        "story_goal": f"Deliver story {story_id} as a runnable baseline for project {project_id}.",
        "task": task,
        "project_mode": effective_project_mode,
        "prd": "",
        "design": "",
        "code": {},
        "bugs": [],
        "fix_suggestion": "",
        "execution_error": "",
        "history": [],
        "loop_count": 0,
        "final_decision": "",
        "release_status": "",
        "severity": "",
        "qa_detail": _make_empty_qa_detail(),
        "lead_summary": {},
        "project_tree": "",
        "retry_reason": "initial_generation",
        "operation": "plan",
        "run_state_path": str(RUN_STATE_PATH),
        "delivery_manifest": "",
        "delivery_source": "",
        "delivery_root": "",
        "resume_from": inferred_baseline or "",
        "depends_on": depends_on or [],
        "story_acceptance_criteria": story_packet.get('acceptance_criteria', []),
        "ownership_map_path": ownership_path,
        "artifact_locks_path": str(Path('project_state') / project_id / 'artifact_locks.json'),
        "change_requests": [],
        "story_packet": story_packet,
        "fe_files": [],
        "be_files": [],
        "integration_conflicts": [],
        "integration_notes": [],
        "next_story": "",
        "delivery_index": delivery_index,
    }

    context["first_breath"] = memory_manager.ensure_first_breath(task, _build_workflow_context(context))
    gate_state = load_gate_state(project_id, epic_id, story_id)
    context['gate_state'] = gate_state
    _write_run_state(context)

    pm_ctx = memory_manager.load_context("pm", task, _build_workflow_context(context))
    context["prd"] = run_pm(task=f"{task}\n\nStory packet:\n{json.dumps(story_packet, ensure_ascii=False, indent=2)}", agent_context=pm_ctx)
    context['gate_state'] = pass_gate(context['gate_state'], 'GATE_1_RESEARCH', 'Research/brief context captured.', ['docs/brief.md'])
    context['gate_state'] = pass_gate(context['gate_state'], 'GATE_2_SPECIFICATION', 'Specification captured for current story.', ['docs/prd.md', 'project_state/%s/epic_context.json' % project_id])
    save_gate_state(context['gate_state'])
    _write_workflow_status(context, 'Proceed to architecture for the current story.')

    architect_ctx = memory_manager.load_context("architect", task, _build_workflow_context(context))
    context["design"] = run_architect(
        task=f"{task}\n\nCurrent story packet:\n{json.dumps(story_packet, ensure_ascii=False, indent=2)}\n\nOwnership map:\n{json.dumps(ownership_map, ensure_ascii=False, indent=2)}",
        prd=context["prd"],
        agent_context=architect_ctx,
        story_packet=story_packet,
    )
    if context["baseline_tree"]:
        context["design"] += f"\n\nBaseline project tree:\n{context['baseline_tree']}"
    context['gate_state'] = pass_gate(context['gate_state'], 'GATE_3_DESIGN', 'Architecture and ownership map prepared.', ['docs/architecture.md', context['ownership_map_path']])
    save_gate_state(context['gate_state'])
    _write_workflow_status(context, 'Proceed to implementation for the current story.')

    for loop in range(1, MAX_LOOP + 1):
        context["loop_count"] = loop
        context["execution_error"] = ""
        context["qa_detail"] = _make_empty_qa_detail()
        context["operation"] = "generate"
        _write_run_state(context)
        _prepare_baseline(context)

        active_lanes = _detect_needed_lanes(context["story_packet"], context["task"])
        be_files: List[Dict[str, str]] = []
        fe_files: List[Dict[str, str]] = []
        if "backend" in active_lanes:
            be_files, _ = _run_lane_developer(context, memory_manager, "backend", "be_developer", ownership_map)
        if "frontend" in active_lanes:
            fe_files, _ = _run_lane_developer(context, memory_manager, "frontend", "fe_developer", ownership_map)
        context["active_lanes"] = active_lanes
        context["fe_files"] = fe_files
        context["be_files"] = be_files

        if not fe_files and not be_files:
            context["execution_error"] = "Both FE and BE developers returned empty or invalid JSON"
            context["retry_reason"] = "invalid_json_parallel"
            context["qa_detail"] = {
                "structural_bugs": [context["execution_error"]],
                "functional_bugs": [],
                "prd_gaps": [],
                "ui_gaps": [],
                "regression_bugs": [],
            }
            context["fix_suggestion"] = "At least one implementation lane must return valid JSON with files."
            context["bugs"] = context["qa_detail"]["structural_bugs"]
            context["release_status"], context["severity"], reason = classify_release_status(context)
            _run_lead_and_store_summary(context, memory_manager, reason)
            _append_history(context)
            _write_workflow_status(context, "Retry required for the current story.")
            continue

        conflicts = detect_cross_lane_conflicts(fe_files, be_files, ownership_map) if set(context.get("active_lanes", [])) == {"frontend", "backend"} else []
        context["integration_conflicts"] = conflicts
        if conflicts:
            context["execution_error"] = "[integration conflict]\n" + "\n".join(conflicts)
            context["retry_reason"] = "ownership_conflict"
            cr_path = create_change_request(project_id, story_id, context['ownership_map_path'], 'Cross-lane ownership conflict detected during integration.', conflicts)
            context.setdefault('change_requests', []).append(cr_path)

        merged_files = _dedupe_files(be_files + fe_files)
        context["code"] = {"files": merged_files}
        write_project(merged_files)

        missing_required_files = _find_missing_required_files_in_output()
        if missing_required_files:
            context["execution_error"] = "Missing required files after applying this story: " + ", ".join(missing_required_files)
            context["retry_reason"] = "missing_required_files"
            context["qa_detail"] = {
                "structural_bugs": [f"Missing required file: {path}" for path in missing_required_files],
                "functional_bugs": [],
                "prd_gaps": [],
                "ui_gaps": [],
                "regression_bugs": [],
            }
            context["fix_suggestion"] = "Generate or preserve the minimum required file set before adding extra features."
            context["bugs"] = context["qa_detail"]["structural_bugs"]
            context["release_status"], context["severity"], reason = classify_release_status(context)
            _run_lead_and_store_summary(context, memory_manager, reason)
            _append_history(context)
            _write_workflow_status(context, "Retry required for the current story.")
            continue

        empty_review = _make_empty_qa_detail() | {"fix_suggestion": ""}
        fe_review = _run_lane_review(context, memory_manager, "frontend", "fe_reviewer", {"files": lane_files(merged_files, 'frontend', ownership_map)}) if "frontend" in context.get("active_lanes", []) else empty_review
        be_review = _run_lane_review(context, memory_manager, "backend", "be_reviewer", {"files": lane_files(merged_files, 'backend', ownership_map)}) if "backend" in context.get("active_lanes", []) else empty_review
        integration_review = _run_lane_review(context, memory_manager, "integration", "integration_qa", context["code"]) if len(context.get("active_lanes", [])) > 1 else empty_review
        context["fe_review"] = fe_review
        context["be_review"] = be_review
        context["integration_review"] = integration_review
        context["qa_detail"] = _merge_qa_details(fe_review, be_review, integration_review)
        if conflicts:
            for c in conflicts:
                if c not in context["qa_detail"]["structural_bugs"]:
                    context["qa_detail"]["structural_bugs"].append(c)
        context["fix_suggestion"] = " ".join(filter(None, [fe_review.get("fix_suggestion", ""), be_review.get("fix_suggestion", ""), integration_review.get("fix_suggestion", "")])).strip()
        context["bugs"] = [*context["qa_detail"]["structural_bugs"], *context["qa_detail"]["functional_bugs"], *context["qa_detail"]["prd_gaps"], *context["qa_detail"]["regression_bugs"]]

        success, error_message = run_system_check(system_target=SYSTEM_TARGET)
        if context["execution_error"]:
            success = False
        if not success and not context["execution_error"]:
            context["execution_error"] = error_message or "build failed"
        context["retry_reason"] = "" if success else (context.get("retry_reason") or "build_failure")
        context["release_status"], context["severity"], reason = classify_release_status(context)
        context["operation"] = "release"
        _write_run_state(context)
        _run_lead_and_store_summary(context, memory_manager, reason)
        _append_history(context)
        if context["release_status"] == "DONE":
            context['gate_state'] = pass_gate(context['gate_state'], 'GATE_4_IMPLEMENTATION', 'Implementation, reviews, and integration checks passed.', ['output_project'])
            context['gate_state'] = pass_gate(context['gate_state'], 'RELEASE_GATE', 'Release checklist approved for current story.', ['output_project'])
            save_gate_state(context['gate_state'])
            break
        else:
            context['gate_state'] = fail_gate(context['gate_state'], 'GATE_4_IMPLEMENTATION', context.get('execution_error', '') or 'Implementation gate failed.')
            save_gate_state(context['gate_state'])

    context["project_tree"] = summarize_project_tree()
    if context["release_status"] == "DONE":
        delivery = _create_story_delivery(context)
        context.update(delivery)
        _write_workflow_status(context, "Current story delivered. Move to the next ready story if any.")
        context["next_story"] = context.get("lead_summary", {}).get("improvement", "")
        context["final_decision"] = "DELIVER_STORY"
    else:
        context["final_decision"] = context["release_status"]
    _write_run_state(context)
    save_run(context)
    memory_manager.remember_run(context)
    log_step(f"Finished with final decision: {context['final_decision']}")
    return context
