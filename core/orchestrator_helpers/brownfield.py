from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from core.existing_project import (
    generate_change_impact_report,
    generate_existing_system_summary,
    generate_integration_strategy,
    generate_readiness_report,
    load_json as load_existing_json,
)


def prepare_existing_project_artifacts(context: Dict[str, Any], ownership_map: Dict[str, Any], system_target: Dict[str, Any]) -> Dict[str, Any]:
    project_id = context["project_id"]
    summary_path = generate_existing_system_summary(
        project_id=project_id,
        baseline_path=context.get("baseline_path", ""),
        baseline_tree=context.get("baseline_tree", ""),
        system_target=context.get("system_target", system_target),
        ownership_map=ownership_map,
    )
    impact_path = generate_change_impact_report(project_id, context.get("story_packet", {}), ownership_map)
    impact_report = load_existing_json(impact_path)
    strategy_path = generate_integration_strategy(project_id, context.get("story_packet", {}), context.get("design", ""), impact_report)
    readiness_path = generate_readiness_report(
        project_id,
        context.get("story_packet", {}),
        context.get("baseline_path", ""),
        impact_report,
        Path(strategy_path).read_text(encoding="utf-8"),
    )
    readiness = load_existing_json(readiness_path)
    return {
        "existing_system_summary_path": summary_path,
        "change_impact_report_path": impact_path,
        "integration_strategy_path": strategy_path,
        "readiness_report_path": readiness_path,
        "impact_report": impact_report,
        "readiness_report": readiness,
    }
