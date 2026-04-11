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
from core.config import load_module_config
from core.executor import run_react_check
from core.file_manager import reset_output_dir, summarize_project_tree, write_project
from core.memory import save_run
from memory.manager import AgentMemoryManager

MODULE_CONFIG = load_module_config()
MAX_LOOP = int(MODULE_CONFIG.get("devteam", {}).get("max_retry_loops", 3))
OUTPUT_PROJECT_DIR = MODULE_CONFIG.get("devteam", {}).get("output_project_dir", "output_project")
STATE_DIR = Path(MODULE_CONFIG.get("devteam", {}).get("state_dir", "state"))
RUN_STATE_PATH = STATE_DIR / "run_state.json"
REQUIRED_FILES = {"package.json", "index.html", "src/main.jsx", "src/App.jsx", "src/index.css"}


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
    seen_paths = set()
    for item in raw_files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not path.strip():
            continue
        if not isinstance(content, str):
            continue
        clean_path = path.strip().replace("\\", "/")
        if clean_path in seen_paths:
            continue
        seen_paths.add(clean_path)
        normalized.append({"path": clean_path, "content": content})
    return normalized


def _find_missing_required_files(files: List[Dict[str, str]]) -> List[str]:
    existing_paths = {file["path"] for file in files}
    return sorted(REQUIRED_FILES - existing_paths)


def _make_empty_qa_detail() -> Dict[str, List[str]]:
    return {"structural_bugs": [], "functional_bugs": [], "prd_gaps": [], "ui_gaps": []}


def classify_release_status(context: Dict[str, Any]) -> Tuple[str, str, str]:
    execution_error = (context.get("execution_error") or "").strip()
    qa_detail = context.get("qa_detail") or {}
    structural_bugs = qa_detail.get("structural_bugs") or []
    functional_bugs = qa_detail.get("functional_bugs") or []
    prd_gaps = qa_detail.get("prd_gaps") or []
    ui_gaps = qa_detail.get("ui_gaps") or []

    if execution_error or structural_bugs or functional_bugs or prd_gaps:
        return ("RETRY", "BLOCKER", "Build failed, core logic is broken, or PRD coverage is incomplete.")
    if ui_gaps:
        return ("DONE", "MINOR", "Build and core requirements passed, with only minor UI gaps remaining.")
    return ("DONE", "NONE", "Build passed and no important QA gaps remain.")


def _append_history(context: Dict[str, Any]) -> None:
    context["history"].append(
        {
            "loop": context.get("loop_count", 0),
            "release_status": context.get("release_status", ""),
            "severity": context.get("severity", ""),
            "execution_error": context.get("execution_error", ""),
            "qa_detail": context.get("qa_detail", _make_empty_qa_detail()),
            "fix_suggestion": context.get("fix_suggestion", ""),
        }
    )


def _build_planned_changes(context: Dict[str, Any]) -> Dict[str, Any]:
    planned_updates = []
    if context.get("prd"):
        planned_updates.append({"kind": "requirements", "summary": "Implement PRD scope safely."})
    if context.get("design"):
        planned_updates.append({"kind": "architecture", "summary": "Follow the concrete file tree and component plan."})
    if context.get("execution_error"):
        planned_updates.append({"kind": "repair", "summary": f"Fix execution error: {context.get('execution_error', '')[:240]}"})
    for bug in (context.get("bugs") or [])[:5]:
        planned_updates.append({"kind": "bug_fix", "summary": str(bug)[:240]})
    return {"project_mode": context.get("project_mode", "new_project"), "goal": context.get("task", ""), "planned_updates": planned_updates}


def _build_workflow_context(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task": context.get("task", ""),
        "project_mode": context.get("project_mode", "new_project"),
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
        "task": context.get("task", ""),
        "project_mode": context.get("project_mode", "new_project"),
        "loop_count": context.get("loop_count", 0),
        "operation": context.get("operation", "generate"),
        "retry_reason": context.get("retry_reason", ""),
        "release_status": context.get("release_status", ""),
        "severity": context.get("severity", ""),
        "execution_error": context.get("execution_error", ""),
        "qa_detail": context.get("qa_detail", {}),
        "planned_changes": context.get("planned_changes", {}),
        "history_tail": context.get("history", [])[-3:],
        "output_project_dir": OUTPUT_PROJECT_DIR,
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
    )
    context["lead_summary"] = _extract_json_object(lead_raw)


def run_orchestrator(task: str, project_mode: str = "new_project") -> Dict[str, Any]:
    memory_manager = AgentMemoryManager()
    memory_manager.ensure_bootstrap()

    context: Dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "task": task,
        "project_mode": project_mode,
        "prd": "",
        "design": "",
        "code": {},
        "raw_code": "",
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
        "first_breath": {},
    }

    context["first_breath"] = memory_manager.ensure_first_breath(task, _build_workflow_context(context))
    _write_run_state(context)

    log_step("Hydrating PM memory")
    pm_ctx = memory_manager.load_context("pm", task, _build_workflow_context(context))
    log_step("Running PM")
    context["prd"] = run_pm(task=context["task"], agent_context=pm_ctx)

    log_step("Hydrating Architect memory")
    architect_ctx = memory_manager.load_context("architect", task, _build_workflow_context(context))
    log_step("Running Architect")
    context["design"] = run_architect(task=context["task"], prd=context["prd"], agent_context=architect_ctx)

    for loop in range(1, MAX_LOOP + 1):
        context["loop_count"] = loop
        context["execution_error"] = ""
        context["qa_detail"] = _make_empty_qa_detail()
        context["operation"] = "generate"
        context["planned_changes"] = _build_planned_changes(context)
        _write_run_state(context)

        log_step(f"Loop {loop}/{MAX_LOOP} - Hydrating Developer memory")
        developer_ctx = memory_manager.load_context("developer", task, _build_workflow_context(context))
        log_step(f"Loop {loop}/{MAX_LOOP} - Running Developer")
        dev_raw = run_developer(
            task=context["task"],
            prd=context["prd"],
            design=context["design"],
            bugs=context["bugs"],
            fix_suggestion=context["fix_suggestion"],
            execution_error=context["execution_error"],
            history=context["history"],
            planned_changes=context["planned_changes"],
            agent_context=developer_ctx,
            project_mode=context["project_mode"],
        )
        context["raw_code"] = dev_raw

        log_step(f"Loop {loop}/{MAX_LOOP} - Parsing developer output")
        dev_result = _extract_json_object(dev_raw)
        files = _normalize_files(dev_result)

        if not files:
            context["execution_error"] = "Developer returned empty or invalid project JSON"
            context["retry_reason"] = "invalid_json"
            context["qa_detail"] = {
                "structural_bugs": ["Developer returned empty or invalid project JSON"],
                "functional_bugs": [],
                "prd_gaps": [],
                "ui_gaps": [],
            }
            context["fix_suggestion"] = "Return valid JSON with a non-empty files array. Keep the output schema minimal."
            context["code"] = {}
            context["bugs"] = context["qa_detail"]["structural_bugs"]
            context["release_status"], context["severity"], rule_reason = classify_release_status(context)
            _write_run_state(context)
            if dev_raw:
                print("\n[debug] Invalid developer raw output:\n", dev_raw[:4000], flush=True)
            _run_lead_and_store_summary(context, memory_manager, rule_reason)
            _append_history(context)
            continue

        missing_required_files = _find_missing_required_files(files)
        if missing_required_files:
            context["execution_error"] = "Missing required files: " + ", ".join(missing_required_files)
            context["retry_reason"] = "missing_required_files"
            context["qa_detail"] = {
                "structural_bugs": [f"Missing required file: {path}" for path in missing_required_files],
                "functional_bugs": [],
                "prd_gaps": [],
                "ui_gaps": [],
            }
            context["fix_suggestion"] = "Generate the minimum required file set before adding extra features."
            context["code"] = {"files": files}
            context["bugs"] = context["qa_detail"]["structural_bugs"]
            context["release_status"], context["severity"], rule_reason = classify_release_status(context)
            _write_run_state(context)
            _run_lead_and_store_summary(context, memory_manager, rule_reason)
            _append_history(context)
            continue

        context["code"] = {"files": files}

        log_step(f"Loop {loop}/{MAX_LOOP} - Writing project files")
        reset_output_dir()
        write_project(files)

        context["operation"] = "qa"
        _write_run_state(context)
        qa_ctx = memory_manager.load_context("qa", task, _build_workflow_context(context))
        log_step(f"Loop {loop}/{MAX_LOOP} - Running QA")
        qa_raw = run_qa(task=context["task"], prd=context["prd"], design=context["design"], code=context["code"], extra_bugs=[], agent_context=qa_ctx)
        qa_result = _extract_json_object(qa_raw)
        context["qa_detail"] = {
            "structural_bugs": qa_result.get("structural_bugs", []) or [],
            "functional_bugs": qa_result.get("functional_bugs", []) or [],
            "prd_gaps": qa_result.get("prd_gaps", []) or [],
            "ui_gaps": qa_result.get("ui_gaps", []) or [],
        }
        context["fix_suggestion"] = qa_result.get("fix_suggestion", "") or ""
        context["bugs"] = [
            *context["qa_detail"].get("structural_bugs", []),
            *context["qa_detail"].get("functional_bugs", []),
            *context["qa_detail"].get("prd_gaps", []),
        ]

        log_step(f"Loop {loop}/{MAX_LOOP} - Running build validation")
        success, error_message = run_react_check()
        context["execution_error"] = "" if success else (error_message or "")
        context["retry_reason"] = "" if success else "build_failure"
        context["release_status"], context["severity"], rule_reason = classify_release_status(context)
        context["operation"] = "release"
        _write_run_state(context)

        if not success and error_message:
            log_step(f"Loop {loop}/{MAX_LOOP} - Build error:\n{error_message[:2000]}")

        _run_lead_and_store_summary(context, memory_manager, rule_reason)
        _append_history(context)

        if context["release_status"] == "DONE":
            log_step(f"Loop {loop}/{MAX_LOOP} - DONE, stopping retry loop")
            break
        log_step(f"Loop {loop}/{MAX_LOOP} - RETRY, continuing to next loop")

    context["final_decision"] = context["release_status"]
    context["project_tree"] = summarize_project_tree()
    _write_run_state(context)
    save_run(context)
    memory_manager.remember_run(context)
    log_step(f"Finished with final decision: {context['final_decision']}")
    return context
