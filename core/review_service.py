from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, TypedDict, cast

from memory.manager import AgentMemoryManager

from core.orchestrator_helpers.context import merge_qa_details
from core.orchestrator_helpers.lanes import build_lane_code, run_lane_review


class ReviewResult(TypedDict, total=False):
    structural_bugs: List[str]
    functional_bugs: List[str]
    prd_gaps: List[str]
    ui_gaps: List[str]
    regression_bugs: List[str]
    integration_issues: List[str]
    fix_suggestion: str


def _as_review_result(value: Any) -> ReviewResult:
    if isinstance(value, dict):
        return cast(ReviewResult, value)
    return ReviewResult()


def _get_fix_suggestion(review: ReviewResult) -> str:
    value = review.get('fix_suggestion', '')
    return value if isinstance(value, str) else ''


def _join_fix_suggestions(*reviews: ReviewResult) -> str:
    parts: list[str] = []
    for review in reviews:
        text = _get_fix_suggestion(review).strip()
        if text:
            parts.append(text)
    return ' '.join(parts).strip()


def review_merged_output(
    *,
    context: Dict[str, Any],
    memory_manager: AgentMemoryManager,
    ownership_map: Dict[str, Any],
    active_lanes: List[str],
    merged_files: List[Dict[str, str]],
    system_target: Dict[str, Any],
) -> Dict[str, Any]:
    empty_review: ReviewResult = {
        'structural_bugs': [],
        'functional_bugs': [],
        'prd_gaps': [],
        'ui_gaps': [],
        'regression_bugs': [],
        'fix_suggestion': '',
    }

    jobs = []
    if 'frontend' in active_lanes:
        jobs.append(('frontend', 'fe_reviewer', build_lane_code(merged_files, 'frontend', ownership_map)))
    if 'backend' in active_lanes:
        jobs.append(('backend', 'be_reviewer', build_lane_code(merged_files, 'backend', ownership_map)))
    if len(active_lanes) > 1:
        jobs.append(('integration', 'integration_qa', {'files': merged_files}))

    results: Dict[str, ReviewResult] = {'frontend': empty_review, 'backend': empty_review, 'integration': empty_review}
    if jobs:
        with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            future_map = {
                executor.submit(run_lane_review, context, memory_manager, lane, role, code, system_target): lane
                for lane, role, code in jobs
            }
            for future in as_completed(future_map):
                lane = future_map[future]
                results[lane] = _as_review_result(future.result())

    fe_review = results['frontend']
    be_review = results['backend']
    integration_review = results['integration']

    qa_detail = merge_qa_details(fe_review, be_review, integration_review)
    for conflict in context.get('integration_conflicts', []):
        if conflict not in qa_detail['structural_bugs']:
            qa_detail['structural_bugs'].append(conflict)

    bugs = [
        *qa_detail['structural_bugs'],
        *qa_detail['functional_bugs'],
        *qa_detail['prd_gaps'],
        *qa_detail['regression_bugs'],
    ]

    return {
        'fe_review': dict(fe_review),
        'be_review': dict(be_review),
        'integration_review': dict(integration_review),
        'qa_detail': qa_detail,
        'fix_suggestion': _join_fix_suggestions(fe_review, be_review, integration_review),
        'bugs': bugs,
    }
