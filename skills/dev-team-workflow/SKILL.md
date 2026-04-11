---
name: dev-team-workflow
description: Complex workflow that turns a product task into a validated local artifact. Use for structured delivery with PM -> Architect -> Developer -> QA -> Lead.
---

# Dev Team Workflow

## Identity
This is a **complex workflow skill**, not a long-lived conversational partner. Optimize for reaching an outcome: a planned, generated, validated software artifact.

## Goal
Guide a user or orchestrator through a structured process to produce a specific output:
- PRD / feature brief
- implementation plan
- generated or updated code
- build + QA evidence
- deterministic release result

## Progressive disclosure
- Read `./resources/workflow_overview.md` first.
- Route internally by `project_mode`, `retry_reason`, and execution context.
- Load only the branch resources required for the current path.
- Use scripts for deterministic validation.
- Keep `state/run_state.json` as the current workflow cache for long retries.

## Routing
- `project_mode=new_project` -> load `./resources/new_project_rules.md`
- `project_mode=existing_project` -> load `./resources/existing_project_rules.md`
- `retry_reason=build_failure` -> load `./resources/build_repair_rules.md`
- `operation=generate` -> load `./resources/developer_output_contract.md`
- `operation=qa` -> load `./resources/qa_review_lenses.md`
- `operation=release` -> load `./resources/lead_gate_rules.md`

## Verifiable intermediate outputs
1. Analyze task and current workflow state.
2. Produce `changes.json` plan.
3. Validate plan with `./scripts/validate_changes.py`.
4. Generate files.
5. Run deterministic build validation.
6. Run QA and Lead review.
7. Persist state to `state/run_state.json` for the next retry.

## Headless mode
This workflow supports headless invocation by an orchestrator. When run headless, do not stop for conversational prompts; complete the full process and emit structured artifacts.

## References
- `./resources/workflow_overview.md`
- `./resources/new_project_rules.md`
- `./resources/existing_project_rules.md`
- `./resources/build_repair_rules.md`
- `./resources/developer_output_contract.md`
- `./resources/qa_review_lenses.md`
- `./resources/lead_gate_rules.md`
