# Existing Project Rules

Use when the workflow is changing an existing project.

Core brownfield rules:
- Preserve current conventions and stable baseline contracts.
- Prefer targeted additive changes over broad rewrites.
- Never regenerate the entire project in existing_project mode.
- Read allowed_change_scope and forbidden_change_scope from the story packet.
- Treat protected modules as read-only unless a change request is approved.
- Use brownfield readiness artifacts before implementation:
  - existing_system_summary.md
  - change_impact_report.json
  - integration_strategy.md
  - brownfield_readiness_report.json

Brownfield expectations:
- Respect shared layout, routing, and protected module boundaries.
- Patch in place when possible.
- Preserve previously delivered stories unless the current story explicitly changes them.
- When in doubt, choose the smaller and safer patch.
