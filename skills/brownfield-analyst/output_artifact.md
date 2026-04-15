# Output Artifact: `existing_system_summary.md`

Required sections:
- Current stack
- Frontend structure
- Backend structure
- Shared/protected modules
- Fragile or regression-sensitive areas
- Constraints relevant to the current story

The output must be:
- concrete, not generic
- tied to actual folders/modules/packages
- useful for change impact review

Failure conditions:
- only mentions high-level stack without boundaries
- omits protected/shared areas
- gives no fragile or regression-sensitive areas
