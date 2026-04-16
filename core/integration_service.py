from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.change_request import create_change_request, find_approved_change_requests
from core.effective_target import derive_effective_target
from core.file_manager import write_project
from core.orchestrator_helpers.delivery import find_missing_required_files_in_output
from core.utils.json_utils import dedupe_files


def _normalize_path(path: str) -> str:
    return path.replace('\\', '/').lstrip('./')


def _matches_prefix(path: str, prefixes: Iterable[str]) -> bool:
    clean = _normalize_path(path)
    for raw in prefixes or []:
        prefix = _normalize_path(str(raw)).rstrip('/')
        if clean == prefix or clean.startswith(prefix + '/'):
            return True
    return False


def _allowed_scope_violation(path: str, allowed_scope: Iterable[str]) -> bool:
    allowed = list(allowed_scope or [])
    if not allowed:
        return False
    return not _matches_prefix(path, allowed)


def _load_locked_artifacts(path: str) -> list[str]:
    target = Path(path)
    if not target.exists():
        return []
    data = json.loads(target.read_text(encoding='utf-8'))
    locks: list[str] = []
    for item in data.get('locked_artifacts', []):
        raw = str(item.get('path', ''))
        if not raw:
            continue
        normalized = _normalize_path(raw)
        source_root = Path(raw)
        if source_root.exists() and source_root.is_dir() and source_root.name == 'source':
            for file in source_root.rglob('*'):
                if file.is_file():
                    locks.append(_normalize_path(str(file.relative_to(source_root))))
            continue
        locks.append(normalized)
    return sorted(set(locks))


def _has_approved_cr(project_id: str, story_id: str, request_type: str, changed_paths: List[str]) -> bool:
    return bool(find_approved_change_requests(project_id, story_id, request_type, changed_paths))


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
            request_type='cross_lane_conflict',
            details={'conflicts': conflicts},
        )
        change_requests.append(cr_path)

    merged_files = dedupe_files(context["be_files"] + context["fe_files"])
    changed_paths = [_normalize_path(item.get('path', '')) for item in merged_files if item.get('path')]

    story_packet = context.get('story_packet', {}) or {}
    allowed_scope = story_packet.get('allowed_change_scope', []) or []
    allowed_hits = [path for path in changed_paths if _allowed_scope_violation(path, allowed_scope)] if context.get('project_mode') == 'existing_project' else []
    if allowed_hits and not _has_approved_cr(context['project_id'], context['story_id'], 'allowed_scope_violation', allowed_hits):
        execution_error += ("\n" if execution_error else "") + "[allowed scope violation]\n" + "\n".join(allowed_hits)
        retry_reason = retry_reason or 'allowed_scope_violation'
        change_requests.append(create_change_request(
            context['project_id'], context['story_id'], 'story_packet.allowed_change_scope',
            'Generated files touched paths outside allowed change scope.', allowed_hits,
            request_type='ownership_override', details={'allowed_hits': allowed_hits}))

    forbidden_scope = story_packet.get('forbidden_change_scope', []) or []
    forbidden_hits = [path for path in changed_paths if _matches_prefix(path, forbidden_scope)]
    if forbidden_hits and not _has_approved_cr(context['project_id'], context['story_id'], 'protected_scope_violation', forbidden_hits):
        execution_error += ("\n" if execution_error else "") + "[protected scope violation]\n" + "\n".join(forbidden_hits)
        retry_reason = retry_reason or 'protected_scope_violation'
        change_requests.append(create_change_request(
            context['project_id'], context['story_id'], 'story_packet.forbidden_change_scope',
            'Generated files touched forbidden/protected scope.', forbidden_hits,
            request_type='protected_scope_violation', details={'forbidden_hits': forbidden_hits}))

    shared_paths = ownership_map.get('shared_paths', []) or []
    shared_hits = [path for path in changed_paths if _matches_prefix(path, shared_paths)]
    if shared_hits and (ownership_map.get('lock_rules', {}) or {}).get('shared_requires_change_request', False) and not _has_approved_cr(context['project_id'], context['story_id'], 'shared_path_override', shared_hits):
        execution_error += ("\n" if execution_error else "") + "[shared path override]\n" + "\n".join(shared_hits)
        retry_reason = retry_reason or 'shared_path_override'
        change_requests.append(create_change_request(
            context['project_id'], context['story_id'], 'ownership_map.shared_paths',
            'Generated files touched shared paths that require change request.', shared_hits,
            request_type='shared_path_override', details={'shared_hits': shared_hits}))

    locked_artifacts = _load_locked_artifacts(context.get('artifact_locks_path', ''))
    locked_hits = [path for path in changed_paths if path in locked_artifacts]
    if locked_hits and not _has_approved_cr(context['project_id'], context['story_id'], 'locked_artifact_change', locked_hits):
        execution_error += ("\n" if execution_error else "") + "[locked artifact change]\n" + "\n".join(locked_hits)
        retry_reason = retry_reason or 'locked_artifact_change'
        change_requests.append(create_change_request(
            context['project_id'], context['story_id'], context.get('artifact_locks_path', ''),
            'Generated files touched locked artifacts.', locked_hits,
            request_type='locked_artifact_change', details={'locked_hits': locked_hits}))

    effective_target = derive_effective_target(system_target, active)
    missing_required_files = find_missing_required_files_in_output(effective_target)
    blocking = bool(conflicts or missing_required_files or allowed_hits or forbidden_hits or shared_hits or locked_hits)

    if missing_required_files:
        execution_error += ("\n" if execution_error else "") + "Missing required files after applying this story: " + ", ".join(missing_required_files)
        retry_reason = retry_reason or 'missing_required_files'
        qa_detail = {
            "structural_bugs": [f"Missing required file: {path}" for path in missing_required_files],
            "functional_bugs": [],
            "prd_gaps": [],
            "ui_gaps": [],
            "regression_bugs": [],
        }
        fix_suggestion = "Generate or preserve the minimum required file set before adding extra features."
        bugs = list(qa_detail["structural_bugs"])

    if not blocking:
        write_project(merged_files)

    return {
        "merged_files": merged_files,
        "integration_conflicts": conflicts,
        "change_requests": change_requests,
        "execution_error": execution_error,
        "retry_reason": retry_reason,
        "qa_detail": qa_detail,
        "fix_suggestion": fix_suggestion,
        "bugs": bugs,
        "has_blocking_issue": blocking,
        "effective_target": effective_target,
    }
