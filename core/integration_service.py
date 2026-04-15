from __future__ import annotations

from typing import Any, Dict

from core.change_request import create_change_request
from core.file_manager import write_project
from core.orchestrator_helpers.delivery import find_missing_required_files_in_output
from core.utils.json_utils import dedupe_files


def integrate_and_validate_outputs(
    *,
    context: Dict[str, Any],
    ownership_map: Dict[str, Any],
    detect_cross_lane_conflicts,
    system_target: Dict[str, Any],
) -> Dict[str, Any]:
    active = set(context.get("active_lanes", []))
    conflicts = (
        detect_cross_lane_conflicts(context["fe_files"], context["be_files"], ownership_map)
        if active == {"frontend", "backend"}
        else []
    )

    change_requests: list[str] = []
    execution_error = ""
    retry_reason = ""
    qa_detail = None
    fix_suggestion = ""
    bugs: list[str] = []

    if conflicts:
        execution_error = "[integration conflict]\n" + "\n".join(conflicts)
        retry_reason = "ownership_conflict"
        cr_path = create_change_request(
            context['project_id'],
            context['story_id'],
            context['ownership_map_path'],
            'Cross-lane ownership conflict detected during integration.',
            conflicts,
        )
        change_requests.append(cr_path)

    merged_files = dedupe_files(context["be_files"] + context["fe_files"])
    write_project(merged_files)

    missing_required_files = find_missing_required_files_in_output(system_target)
    if missing_required_files:
        execution_error = "Missing required files after applying this story: " + ", ".join(missing_required_files)
        retry_reason = "missing_required_files"
        qa_detail = {
            "structural_bugs": [f"Missing required file: {path}" for path in missing_required_files],
            "functional_bugs": [],
            "prd_gaps": [],
            "ui_gaps": [],
            "regression_bugs": [],
        }
        fix_suggestion = "Generate or preserve the minimum required file set before adding extra features."
        bugs = list(qa_detail["structural_bugs"])

    return {
        "merged_files": merged_files,
        "integration_conflicts": conflicts,
        "change_requests": change_requests,
        "execution_error": execution_error,
        "retry_reason": retry_reason,
        "qa_detail": qa_detail,
        "fix_suggestion": fix_suggestion,
        "bugs": bugs,
        "has_blocking_issue": bool(conflicts or missing_required_files),
    }
