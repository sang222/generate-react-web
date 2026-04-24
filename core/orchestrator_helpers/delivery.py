from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.file_manager import copy_tree, summarize_project_tree_for, OUTPUT_DIR
from core.story_state import lock_artifacts, update_delivery_index


def _normalize_required_path(path: str) -> str:
    return str(path).replace("\\", "/").lstrip("./")


def required_files_for_target(system_target: Dict[str, Any]) -> List[str]:
    effective_mode = system_target.get("effective_mode")
    frontend_root = _normalize_required_path(system_target.get("frontend_root", "frontend"))

    def fe(path: str) -> str:
        if frontend_root in {"", "."}:
            return path
        return f"{frontend_root}/{path}"

    if effective_mode == "frontend_only":
        return [
            fe("package.json"),
            fe("index.html"),
            fe("src/main.jsx"),
            fe("src/App.jsx"),
            fe("src/index.css"),
        ]

    if effective_mode == "backend_only":
        return [
            "backend/build.gradle",
            "backend/src/main/resources/application.properties",
        ]

    if system_target.get("system_type") == "fullstack_website":
        return [
            "frontend/package.json",
            "frontend/index.html",
            "frontend/src/main.jsx",
            "frontend/src/App.jsx",
            "frontend/src/index.css",
            "backend/build.gradle",
            "backend/src/main/resources/application.properties",
        ]

    return [
        "package.json",
        "index.html",
        "src/main.jsx",
        "src/App.jsx",
        "src/index.css",
    ]


def find_missing_required_files_in_files(
    files: List[Dict[str, Any]],
    system_target: Dict[str, Any],
) -> List[str]:
    generated_paths = {
        _normalize_required_path(item.get("path", ""))
        for item in files
        if item.get("path")
    }

    return sorted(
        path
        for path in required_files_for_target(system_target)
        if path not in generated_paths
    )


def find_missing_required_files_in_output(system_target: Dict[str, Any]) -> List[str]:
    return sorted(
        path
        for path in required_files_for_target(system_target)
        if not (OUTPUT_DIR / path).exists()
    )


def normalize_files_for_target(
    files: List[Dict[str, Any]],
    system_target: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Normalize generated file paths to the active runtime file contract.

    For frontend_only new projects, the accepted Vite app root is output_project/.
    Some FE skill examples still show frontend/... paths, and models may also wrap
    the app in a single top-level folder. Strip exactly one common wrapper prefix
    only when that prefix contains the full required root Vite set.
    """
    effective_mode = system_target.get("effective_mode")
    frontend_root = _normalize_required_path(system_target.get("frontend_root", "frontend"))

    if effective_mode != "frontend_only" or frontend_root not in {"", "."}:
        return files

    required_suffixes = [
        "package.json",
        "index.html",
        "src/main.jsx",
        "src/App.jsx",
        "src/index.css",
    ]

    normalized_items: List[Dict[str, Any]] = []
    path_to_item: Dict[str, Dict[str, Any]] = {}

    for item in files or []:
        if not isinstance(item, dict):
            continue
        path = _normalize_required_path(item.get("path", ""))
        content = item.get("content")
        if not path or not isinstance(content, str):
            continue
        cloned = dict(item)
        cloned["path"] = path
        normalized_items.append(cloned)
        path_to_item[path] = cloned

    if all(suffix in path_to_item for suffix in required_suffixes):
        return normalized_items

    prefixes: set[str] = set()
    for path in path_to_item:
        parts = path.split("/")
        if len(parts) > 1:
            prefixes.add(parts[0])

    candidate_prefix = None
    for prefix in sorted(prefixes):
        if all(f"{prefix}/{suffix}" in path_to_item for suffix in required_suffixes):
            candidate_prefix = prefix
            break

    if not candidate_prefix:
        return normalized_items

    rewritten: List[Dict[str, Any]] = []
    marker = candidate_prefix + "/"

    for item in normalized_items:
        cloned = dict(item)
        path = _normalize_required_path(cloned.get("path", ""))
        if path.startswith(marker):
            cloned["path"] = path[len(marker):]
        else:
            cloned["path"] = path
        rewritten.append(cloned)

    return rewritten


def create_story_delivery(context: Dict[str, Any], deliveries_dir: Path) -> Dict[str, Any]:
    project_id = context.get("project_id", "")
    epic_id = context.get("epic_id", "")
    story_id = context.get("story_id", "story_1")
    story_name = context.get("story_name", story_id)
    delivery_root = deliveries_dir / project_id / story_id
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
        "existing_system_summary_path": context.get("existing_system_summary_path", ""),
        "change_impact_report_path": context.get("change_impact_report_path", ""),
        "integration_strategy_path": context.get("integration_strategy_path", ""),
        "readiness_report_path": context.get("readiness_report_path", ""),
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
