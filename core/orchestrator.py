from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Tuple

from agents.architect import run_architect
from agents.developer import run_developer
from agents.lead import run_lead
from agents.pm import run_pm
from agents.qa import run_qa
from core.executor import run_react_check
from core.file_manager import reset_output_dir, summarize_project_tree, write_project
from core.memory import save_run, summarize_similar_runs

MAX_LOOP = 3

REQUIRED_FILES = {
    "package.json",
    "index.html",
    "src/main.jsx",
    "src/App.jsx",
}


def _safe_json_loads(text: str) -> Dict[str, Any]:
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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

        if not isinstance(path, str) or not path.strip():
            continue
        if not isinstance(content, str):
            continue

        normalized.append({"path": path.strip(), "content": content})

    return normalized


def _find_missing_required_files(files: List[Dict[str, str]]) -> List[str]:
    existing_paths = {file["path"] for file in files}
    return sorted(REQUIRED_FILES - existing_paths)


def _make_empty_qa_detail() -> Dict[str, List[str]]:
    return {
        "structural_bugs": [],
        "functional_bugs": [],
        "prd_gaps": [],
        "ui_gaps": [],
    }


def classify_release_status(context: Dict[str, Any]) -> Tuple[str, str, str]:
    execution_error = (context.get("execution_error") or "").strip()
    qa_detail = context.get("qa_detail") or {}

    structural_bugs = qa_detail.get("structural_bugs") or []
    functional_bugs = qa_detail.get("functional_bugs") or []
    prd_gaps = qa_detail.get("prd_gaps") or []
    ui_gaps = qa_detail.get("ui_gaps") or []

    if execution_error or structural_bugs or functional_bugs or prd_gaps:
        return (
            "RETRY",
            "BLOCKER",
            "Build failed, core logic is broken, or PRD coverage is incomplete.",
        )

    if ui_gaps:
        return (
            "DONE",
            "MINOR",
            "Build and core requirements passed, with only minor UI gaps remaining.",
        )

    return (
        "DONE",
        "NONE",
        "Build passed and no important QA gaps remain.",
    )


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


def _run_lead_and_store_summary(context: Dict[str, Any], rule_reason: str) -> None:
    lead_raw = run_lead(
        task=context["task"],
        prd=context["prd"],
        design=context["design"],
        code=context["code"],
        qa_detail=context["qa_detail"],
        execution_error=context["execution_error"],
        loop_count=context["loop_count"],
        max_loop=MAX_LOOP,
        rule_result={
            "release_status": context["release_status"],
            "severity": context["severity"],
            "reason": rule_reason,
        },
        history=context["history"],
        memory_context=context["memory_context"],
    )
    context["lead_summary"] = _safe_json_loads(lead_raw)


def run_orchestrator(task: str) -> Dict[str, Any]:
    context: Dict[str, Any] = {
        "run_id": str(uuid.uuid4()),
        "task": task,
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
        "memory_context": "[]",
        "project_tree": "",
    }

    context["memory_context"] = summarize_similar_runs(task, limit=5)

    context["prd"] = run_pm(task=context["task"], memory_context=context["memory_context"])
    context["design"] = run_architect(
        task=context["task"],
        prd=context["prd"],
        memory_context=context["memory_context"],
    )

    for loop in range(1, MAX_LOOP + 1):
        context["loop_count"] = loop
        context["execution_error"] = ""
        context["qa_detail"] = _make_empty_qa_detail()

        dev_raw = run_developer(
            task=context["task"],
            prd=context["prd"],
            design=context["design"],
            bugs=context["bugs"],
            fix_suggestion=context["fix_suggestion"],
            execution_error=context["execution_error"],
            history=context["history"],
            memory_context=context["memory_context"],
        )
        context["raw_code"] = dev_raw

        dev_result = _safe_json_loads(dev_raw)
        files = _normalize_files(dev_result)

        if not files:
            context["execution_error"] = "Developer returned empty or invalid project JSON"
            context["qa_detail"] = {
                "structural_bugs": ["Developer returned empty or invalid project JSON"],
                "functional_bugs": [],
                "prd_gaps": [],
                "ui_gaps": [],
            }
            context["fix_suggestion"] = "Return valid JSON with a non-empty files array."
            context["bugs"] = list(context["qa_detail"]["structural_bugs"])
            context["code"] = {}

            (
                context["release_status"],
                context["severity"],
                rule_reason,
            ) = classify_release_status(context)
            _run_lead_and_store_summary(context, rule_reason)
            _append_history(context)
            continue

        missing_required_files = _find_missing_required_files(files)
        if missing_required_files:
            context["execution_error"] = (
                "Missing required files: " + ", ".join(missing_required_files)
            )
            context["qa_detail"] = {
                "structural_bugs": [
                    f"Missing required file: {path}" for path in missing_required_files
                ],
                "functional_bugs": [],
                "prd_gaps": [],
                "ui_gaps": [],
            }
            context["fix_suggestion"] = "Generate the minimum required React + Vite file set."
            context["bugs"] = list(context["qa_detail"]["structural_bugs"])
            context["code"] = {"files": files}

            (
                context["release_status"],
                context["severity"],
                rule_reason,
            ) = classify_release_status(context)
            _run_lead_and_store_summary(context, rule_reason)
            _append_history(context)
            continue

        context["code"] = {"files": files}

        reset_output_dir()
        write_project(files)

        qa_raw = run_qa(
            task=context["task"],
            prd=context["prd"],
            design=context["design"],
            code=context["code"],
            extra_bugs=[],
            memory_context=context["memory_context"],
        )
        qa_result = _safe_json_loads(qa_raw)

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

        success, error_message = run_react_check()
        context["execution_error"] = "" if success else (error_message or "")

        (
            context["release_status"],
            context["severity"],
            rule_reason,
        ) = classify_release_status(context)
        _run_lead_and_store_summary(context, rule_reason)
        _append_history(context)

        if context["release_status"] == "DONE":
            break

    context["final_decision"] = context["release_status"]
    context["project_tree"] = summarize_project_tree()
    save_run(context)

    return context
