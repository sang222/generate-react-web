from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _root(project_id: str) -> Path:
    return Path("project_state") / project_id


def story_artifact_root(project_id: str, story_id: str) -> Path:
    return _root(project_id) / "stories" / story_id


def existing_system_summary_path(project_id: str, story_id: str) -> Path:
    return story_artifact_root(project_id, story_id) / "existing_system_summary.md"


def change_impact_report_path(project_id: str, story_id: str) -> Path:
    return story_artifact_root(project_id, story_id) / "change_impact_report.json"


def integration_strategy_path(project_id: str, story_id: str) -> Path:
    return story_artifact_root(project_id, story_id) / "integration_strategy.md"


def readiness_report_path(project_id: str, story_id: str) -> Path:
    return story_artifact_root(project_id, story_id) / "brownfield_readiness_report.json"


def _write_text(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return str(path)


def _write_json(path: Path, payload: Dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def generate_existing_system_summary(
    project_id: str,
    story_id: str,
    baseline_path: str,
    baseline_tree: str,
    system_target: Dict[str, Any],
    ownership_map: Dict[str, Any],
) -> str:
    shared_paths = ", ".join(ownership_map.get("shared_paths", []) or []) or "none"
    content = f"""
# Existing System Summary

## Baseline source
- Path: {baseline_path or 'unknown'}

## Current stack
- Frontend: {system_target.get('frontend_stack', '')}
- Backend: {system_target.get('backend_language', '')} + {system_target.get('backend_framework', '')}
- Backend build tool: {system_target.get('backend_build_tool', '')}
- Database: {system_target.get('database_engine', '')}
- ORM: {system_target.get('database_orm', '')}

## Ownership summary
- Shared paths: {shared_paths}

## Baseline tree
{baseline_tree or 'No baseline tree available.'}

## Brownfield guidance
- Reuse the baseline project instead of regenerating it from scratch.
- Preserve shared modules and existing contracts unless explicitly approved.
"""
    return _write_text(existing_system_summary_path(project_id, story_id), content)


def generate_change_impact_report(project_id: str, story_id: str, story_packet: Dict[str, Any], ownership_map: Dict[str, Any]) -> str:
    frontend_paths = ownership_map.get("teams", {}).get("frontend", {}).get("owned_paths", []) or []
    backend_paths = ownership_map.get("teams", {}).get("backend", {}).get("owned_paths", []) or []
    in_scope = story_packet.get("in_scope", []) or []
    affected_modules: List[str] = []
    if frontend_paths:
        affected_modules.extend(frontend_paths[:2])
    if backend_paths and story_packet.get("system_target", {}).get("system_type") == "fullstack_website":
        affected_modules.extend(backend_paths[:2])
    protected = ownership_map.get("shared_paths", []) or []
    report = {
        "project_id": project_id,
        "story_id": story_packet.get("story_id", ""),
        "affected_modules": affected_modules,
        "protected_modules": protected,
        "regression_risk": "high" if protected else "medium",
        "breaking_risks": [
            "baseline route or integration regression",
            "shared module side effects",
        ],
        "safe_change_strategy": [
            "Prefer additive changes on top of the existing baseline.",
            "Avoid rewriting protected/shared modules.",
            "Respect ownership map and locked artifacts.",
        ],
        "in_scope": in_scope,
        "out_of_scope": story_packet.get("out_of_scope", []) or [],
    }
    return _write_json(change_impact_report_path(project_id, story_id), report)


def generate_integration_strategy(project_id: str, story_id: str, story_packet: Dict[str, Any], design: str, impact_report: Dict[str, Any]) -> str:
    affected = impact_report.get("affected_modules", []) or []
    protected = impact_report.get("protected_modules", []) or []
    content = f"""
# Integration Strategy

## Strategy
Incremental extension

## Current story
- Story ID: {story_packet.get('story_id', '')}
- Story name: {story_packet.get('story_name', '')}

## Safe change zones
{chr(10).join(f'- {m}' for m in affected) if affected else '- None identified'}

## Protected modules
{chr(10).join(f'- {m}' for m in protected) if protected else '- None identified'}

## Implementation rules
- Extend the baseline instead of replacing it.
- Keep changes scoped to affected modules.
- Avoid touching protected modules without a change request.
- Preserve existing behavior unless this story explicitly changes it.

## Architect guidance
{design[:3000] if design else 'No architect guidance provided.'}
"""
    return _write_text(integration_strategy_path(project_id, story_id), content)


def generate_readiness_report(
    project_id: str,
    story_id: str,
    story_packet: Dict[str, Any],
    baseline_path: str,
    impact_report: Dict[str, Any],
    integration_strategy_text: str,
) -> str:
    missing = []
    protected_missing = []
    baseline_root = Path(baseline_path) if baseline_path else None
    if not baseline_path:
        missing.append("missing baseline path")
    elif not baseline_root.exists():
        missing.append("baseline path does not exist")
    elif not baseline_root.is_dir():
        missing.append("baseline path is not a directory")
    else:
        has_any_file = any(p.is_file() for p in baseline_root.rglob("*"))
        if not has_any_file:
            missing.append("baseline tree is empty")
    if not impact_report.get("affected_modules"):
        missing.append("missing affected modules")
    if not integration_strategy_text.strip():
        missing.append("missing integration strategy")
    if baseline_root and baseline_root.exists() and baseline_root.is_dir():
        for protected in impact_report.get("protected_modules", []) or []:
            protected_path = baseline_root / protected
            if not protected_path.exists():
                protected_missing.append(protected)
        if protected_missing:
            missing.append("protected modules missing from baseline")
    ready = len(missing) == 0
    payload = {
        "project_id": project_id,
        "story_id": story_packet.get("story_id", ""),
        "ready": ready,
        "missing_information": missing,
        "known_risks": impact_report.get("breaking_risks", []),
        "protected_modules_checked": impact_report.get("protected_modules", []),
        "missing_protected_modules": protected_missing,
        "approved_strategy": "incremental extension" if ready else "",
        "can_start_implementation": ready,
    }
    return _write_json(readiness_report_path(project_id, story_id), payload)


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
