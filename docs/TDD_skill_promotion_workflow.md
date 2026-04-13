# Technical Design Document: Skill Candidate Store and CLI Review Flow

## Purpose

Add a separate **Skill Promotion Workflow** beside the existing story delivery workflow.

This workflow is used to:
- record AI-proposed skill updates as reviewable candidates
- inspect candidate changes from the CLI
- let a human approve, reject, or request revision
- optionally promote approved candidates into the core skill layer

This design keeps **delivery workflow** and **skill evolution workflow** separate.

---

## Core Principles

- **Story delivery must not pause only because a skill improvement candidate exists.**
- **Skill changes must not auto-apply to the live core skill without review.**
- **Human review happens on CLI using summaries and diffs.**
- **Approved updates are versioned and logged.**

---

## Separation of Flows

### Delivery Workflow
Responsible for:
- epic/story execution
- gates
- QA
- build validation
- story delivery

### Skill Promotion Workflow
Responsible for:
- candidate generation
- candidate inspection
- candidate review
- promotion or rejection

The two workflows are related, but should run independently.

---

## Candidate Storage

Skill candidates are stored under:

```text
skill_candidates/
  <candidate_id>/
    metadata.json
    summary.md
    patch.diff
    structured_patch.json   # optional
    evaluation.json
    review_decision.json    # written after review
```

### metadata.json
Contains:
- candidate id
- target skill
- change type
- summary
- reason
- affected files
- source runs
- status

### summary.md
Human-readable explanation of:
- what problem was detected
- what the candidate changes
- what result is expected

### patch.diff
Unified diff for human review.

### structured_patch.json
Optional machine-apply patch format for safe deterministic replacements.

### evaluation.json
Optional metrics:
- retry rate before/after
- delivery rate impact
- regression count

### review_decision.json
Written after human review.

---

## Registry

Promotion history is stored in:

```text
skill_registry/
  promotion_log.json
```

This file records:
- candidate id
- review decision
- reviewer
- reviewed time
- whether a patch was applied
- target skill
- summary

---

## Review Decisions

Supported review outcomes:
- `reject`
- `revise`
- `approve_for_project_only`
- `promote_to_core`

### Meaning

#### reject
Candidate is not accepted.

#### revise
Candidate has the right idea but needs another iteration.

#### approve_for_project_only
Candidate is valid only for the current project or narrow context.

#### promote_to_core
Candidate is approved as a reusable skill improvement and may be merged into the stable skill layer.

---

## CLI Commands

### List candidates
```bash
python main.py --list-skill-candidates
```

### Show one candidate
```bash
python main.py --show-skill-candidate cand_001
```

### Review one candidate
```bash
python main.py \
  --review-skill-candidate cand_001 \
  --skill-candidate-decision promote_to_core \
  --skill-candidate-note "Recurring brownfield issue; approved for core helper"
```

Equivalent script entrypoint:
```bash
python scripts/skill_candidates.py --list
python scripts/skill_candidates.py --show cand_001
python scripts/skill_candidates.py --review cand_001 --decision promote_to_core
```

---

## Apply Rules

By default, candidate review should be treated as a governance action, not an automatic live rewrite.

This version supports an optional deterministic apply path:
- if `structured_patch.json` exists
- and the review decision is `approve_for_project_only` or `promote_to_core`
- the system may apply allowed `replace` patches

If no structured patch exists:
- the candidate is still reviewed and logged
- but no automatic file mutation occurs

---

## Structured Patch Format

Example:

```json
{
  "patches": [
    {
      "file": "agents/developer.py",
      "changes": [
        {
          "type": "replace",
          "find": "Do not regenerate the project from scratch.",
          "replace": "For existing_project mode, always patch the current baseline in place.\nDo not regenerate the project from scratch."
        }
      ]
    }
  ]
}
```

Current safe behavior:
- only `replace` changes are supported
- files must already exist
- a patch is recorded as applied only if the file content actually changes

---

## Status Model

Candidate metadata status may move through:
- `proposed`
- `revision_requested`
- `rejected`
- `approved_for_project_only`
- `promoted_to_core`

These states are tracked inside `metadata.json` and `review_decision.json`.

---

## Relationship to Delivery Workflow

When a story run detects a recurring issue, the delivery workflow may:
- create a candidate
- reference candidate ids in run output
- mark `human_review_required = true`

But the story run should still:
- deliver
- retry
- or block

according to the current delivery rules.

Skill review does **not** block delivery by default.

Only **story safety approvals** such as locked artifact or protected module changes should block the active story.

---

## Future Extensions

Later versions may add:
- replay evaluation over historical runs
- score-based promotion thresholds
- project-only candidate overlays
- richer patch types
- interactive diff paging in CLI
- tighter integration with workflow status

---

## Summary

This design introduces a separate, human-governed skill evolution path.

It allows the system to:
- learn from recurring failures
- propose skill updates quickly
- keep the live core skill stable
- apply reviewed improvements through a controlled promotion process
