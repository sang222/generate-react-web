# TDD v23 - Gate Question Sets

## Purpose

Introduce human-readable gate question sets for all major gates so that the workflow becomes more operator-visible and artifact-quality-driven.

## Goals

- make each gate explainable
- turn gate pass/fail into a quality decision rather than a simple phase transition
- improve operator review and human approval at research, specification, design, implementation, and release boundaries
- reinforce brownfield safety in existing_project mode

## Scope

This version adds gate question resources only. It does not yet wire a full interactive gate questionnaire into the runtime.

Added resources:
- `skills/dev-team-workflow/resources/gates/gate_1_research_questions.md`
- `skills/dev-team-workflow/resources/gates/gate_2_specification_questions.md`
- `skills/dev-team-workflow/resources/gates/gate_3_design_questions.md`
- `skills/dev-team-workflow/resources/gates/brownfield_readiness_gate_questions.md`
- `skills/dev-team-workflow/resources/gates/gate_4_implementation_questions.md`
- `skills/dev-team-workflow/resources/gates/release_gate_questions.md`

## Design principles

1. Each gate must answer:
   - what artifacts are required
   - what quality questions must be asked
   - what pass means
   - what fail means

2. Design gate must explicitly include:
   - ownership readiness
   - decision rationale
   - over-engineering check

3. Brownfield readiness must be treated as a first-class quality gate.

## Expected next step

A later version may wire these gate question sets into:
- operator CLI review
- workflow status surface
- gate scoring or checklist execution
