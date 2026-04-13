# Safe Implementation Lane Skill

## Purpose
Patch an existing project within approved change scope and integration strategy.

## Inputs
- current story packet
- `change_impact_report.json`
- `integration_strategy.md`
- baseline source

## Outputs
- code changes limited to allowed scope
- notes for review and regression QA

## When to retry
Retry when build or review fails within allowed scope.

## When to block
Block when implementation requires protected scope or locked artifact changes without CR approval.
