# TDD v24.1 - Recovery Hardening

## Goals
- Make adaptive recovery safer and more auditable.
- Keep cross review independent from the recovery proposer.
- Restrict auto-apply to narrow runtime overrides only.
- Prevent orchestrator from re-growing into a god loop.
- Make BLOCKED outcomes explainable through explicit reason codes.

## Changes

### 1. Independent reviewer rubric
Added:
- `skills/skill-reviewer/rubric.md`

The reviewer now evaluates candidates using independent criteria:
- scope safety
- contract safety
- brownfield boundary safety
- regression likelihood
- patch target correctness

### 2. Deterministic risk classifier
Added:
- `core/risk_classifier.py`

The classifier decides the maximum auto-apply scope before the reviewer verdict is considered.
This prevents soft review language from bypassing hard safety constraints.

### 3. Recovery engine separation
Added:
- `core/recovery_engine.py`
- `core/cross_reviewer.py`
- `core/runtime_override_manager.py`
- `core/recovery_history.py`

`core/adaptive_recovery.py` now acts as a thin wrapper over the recovery engine.
This keeps `core/orchestrator.py` smaller and reduces recovery-specific domain logic inside the core loop.

### 4. Explicit blocked reason codes
Added blocked reason support for recovery outcomes such as:
- `BLOCKED_REVIEWER_REJECTED`
- `BLOCKED_RISK_TOO_HIGH`
- `BLOCKED_OVERRIDE_APPLY_FAILED`
- `BLOCKED_RECOVERY_RERUN_FAILED`
- `BLOCKED_NO_SAFE_CANDIDATE`

These reason codes are written into:
- workflow status
- run state
- adaptive recovery context
- recovery history

## Auto-apply policy
Only narrow runtime overrides are auto-applied:
- `fix_suggestion_append`
- `implementation_constraints_append`
- `regression_requirements_append`
- `forbidden_change_scope_append`

Core files and semantics are not auto-mutated in autonomous mode.
