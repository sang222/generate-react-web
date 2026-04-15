# TDD: v21 Skill-Centric Brownfield Improvements

## Goal
Shift the repo further from workflow-centric brownfield handling toward skill-centric, data-backed, output-specific operation.

## Scope
This version focuses on four brownfield skill packs:
- `brownfield-analyst`
- `change-impact-reviewer`
- `integration-architect`
- `safe-implementation-lane`

## Design Principles
1. Skills should be narrow but deep.
2. Knowledge should live in corpus/examples/cases, not only prompt text.
3. Each skill should have a concrete output artifact.
4. Operators should be able to inspect what a skill does from CLI.

## Changes
- Added `when_to_use.md` to each brownfield skill.
- Added `output_artifact.md` to each brownfield skill.
- Added `known_failures.json` to each brownfield skill.
- Added `cases/` with starter good/bad cases to each brownfield skill.
- Updated `agents/base.py` so existing-project prompt resources pull in role-relevant brownfield skill packs.
- Added `scripts/show_skill.py` and `main.py --show-skill <name>`.
- Expanded `evals/brownfield/cases/` with more artifact-focused cases.

## Expected Outcomes
- Narrower brownfield reasoning per role.
- Better operator visibility into skill purpose, output, and use conditions.
- Stronger basis for future evals and candidate skill promotion.
