# TDD v24 - Adaptive Recovery Mode

## Goal
Add an autonomous recovery flow after 2 failed attempts.

## Flow
- fail twice
- recovery meta-agent proposes a candidate patch / runtime override
- skill reviewer cross-reviews the candidate
- policy applies low/medium-risk changes automatically
- story reruns once with the override
- all events are logged to history for later audit

## Non-goals
- no human approval during runtime
- no automatic mutation of core gate/release/state semantics

## Artifacts
- `skill_candidates/<candidate_id>/metadata.json`
- `skill_candidates/<candidate_id>/summary.md`
- `skill_candidates/<candidate_id>/patch.diff`
- `skill_candidates/<candidate_id>/evaluation.json`
- `skill_candidates/<candidate_id>/cross_review.json`
- `skill_history/candidate_runs.jsonl`
- `skill_history/candidate_reviews.jsonl`
- `skill_history/auto_applied.jsonl`

## Risk policy
- `runtime_override`: safe temporary change for the current rerun
- `project_only`: safe localized rule/update for this project context
- `core_candidate_only`: log only, no auto-apply
- `reject`: ignore the candidate
