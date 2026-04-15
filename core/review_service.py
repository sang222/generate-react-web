from __future__ import annotations

from typing import Any, Dict

from core.orchestrator_helpers.context import make_empty_qa_detail, merge_qa_details
from core.orchestrator_helpers.lanes import build_lane_code, run_lane_review


def review_merged_output(
    *,
    context: Dict[str, Any],
    memory_manager,
    ownership_map: Dict[str, Any],
    system_target: Dict[str, Any],
) -> Dict[str, Any]:
    empty_review = make_empty_qa_detail() | {"fix_suggestion": ""}
    merged_files = context["code"]["files"]

    fe_review = (
        run_lane_review(
            context,
            memory_manager,
            "frontend",
            "fe_reviewer",
            build_lane_code(merged_files, 'frontend', ownership_map),
            system_target,
        )
        if "frontend" in context.get("active_lanes", [])
        else empty_review
    )
    be_review = (
        run_lane_review(
            context,
            memory_manager,
            "backend",
            "be_reviewer",
            build_lane_code(merged_files, 'backend', ownership_map),
            system_target,
        )
        if "backend" in context.get("active_lanes", [])
        else empty_review
    )
    integration_review = (
        run_lane_review(
            context,
            memory_manager,
            "integration",
            "integration_qa",
            context["code"],
            system_target,
        )
        if len(context.get("active_lanes", [])) > 1
        else empty_review
    )

    qa_detail = merge_qa_details(fe_review, be_review, integration_review)
    for conflict in context.get("integration_conflicts", []):
        if conflict not in qa_detail["structural_bugs"]:
            qa_detail["structural_bugs"].append(conflict)

    fix_parts = [
        fe_review.get("fix_suggestion", ""),
        be_review.get("fix_suggestion", ""),
        integration_review.get("fix_suggestion", ""),
    ]
    fix_suggestion = " ".join(str(part) for part in fix_parts if isinstance(part, str) and part).strip()
    bugs = [
        *qa_detail["structural_bugs"],
        *qa_detail["functional_bugs"],
        *qa_detail["prd_gaps"],
        *qa_detail["regression_bugs"],
    ]

    return {
        "fe_review": fe_review,
        "be_review": be_review,
        "integration_review": integration_review,
        "qa_detail": qa_detail,
        "fix_suggestion": fix_suggestion,
        "bugs": bugs,
    }
