from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.file_manager import copy_tree, summarize_project_tree_for, OUTPUT_DIR
from core.story_state import lock_artifacts, update_delivery_index


def find_missing_required_files_in_output(system_target: Dict[str, Any]) -> List[str]:
    required: List[str] = []
    effective_mode = system_target.get("effective_mode")
    if effective_mode == "frontend_only":
        required.extend([
            "frontend/package.json",
            "frontend/index.html",
            "frontend/src/main.jsx",
            "frontend/src/App.jsx",
        ])
    elif effective_mode == "backend_only":
        required.extend([
            "backend/build.gradle",
            "backend/src/main/resources/application.properties",
        ])
    elif system_target.get("system_type") == "fullstack_website":
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
