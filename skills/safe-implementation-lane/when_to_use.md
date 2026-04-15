# When to Use: Safe Implementation Lane

Use this skill when:
- current story implementation must patch an existing baseline inside allowed scope
- the lane already has change impact and integration strategy artifacts
- touched boundary summary is needed for review and regression QA

Do not use this skill when:
- brownfield readiness has not passed
- allowed/forbidden scope is missing
- the task still requires architecture or impact analysis instead of implementation

Retry when:
- build or review fails but the change still stays inside allowed scope

Block when:
- implementation requires protected scope or locked artifact changes without an approved change request
