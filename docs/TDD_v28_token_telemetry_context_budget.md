# TDD v28 - Token Telemetry and Context Budget

## Goal
Make token/cost behavior measurable and add optional budget guardrails without changing the delivery workflow.

## Additions

### Token telemetry
Every `call_role_llm(...)` estimates prompt/completion tokens and appends a JSONL record under:

```text
project_state/<project_id>/stories/<story_id>/token_usage.jsonl
```

The record includes role, model, provider, run id, story id, estimated prompt tokens, estimated completion tokens, total tokens, and duration.

### Budget guardrail
Optional env vars:

```text
STORY_TOKEN_BUDGET=0
ROLE_TOKEN_BUDGET_DEVELOPER=0
ROLE_TOKEN_BUDGET_QA=0
```

`0` disables hard blocking. If enabled, the next LLM call is rejected before execution when the prompt would exceed budget. The run is marked with:

```text
BLOCKED_TOKEN_BUDGET_EXCEEDED
```

### Context budget
`agents/base.py` now reduces brownfield over-injection:

- PM/Architect receive readiness context.
- QA/reviewer roles receive regression review context.
- Developer roles receive safe implementation/change-request context.
- Examples/cases are loaded only for retry loops or higher-complexity stories.

### Lane detection
Lane detection now prefers:

1. explicit `execution_mode`
2. in-scope/allowed path hints
3. keyword fallback

## Non-goals

- This version does not implement exact tokenizer-based usage for every provider.
- This version does not add adaptive model downgrade on retry.
- This version does not provide a UI dashboard for token usage.
