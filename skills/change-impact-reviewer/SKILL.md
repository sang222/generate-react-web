# Change Impact Reviewer Skill

## Purpose
Review and score the likely impact radius of a story on an existing project.

## Inputs
- `existing_system_summary.md`
- current story packet
- baseline source tree

## Outputs
- `change_impact_report.json`
- affected modules
- protected modules
- regression risk level
- safe change strategy hints

## When to block
Block when affected or protected scope cannot be identified confidently.
