# When to Use Roles and Gates

## Roles
- PM / BA: clarify scope, PRD, and story boundaries
- Architect: design current story and integration plan
- Brownfield Analyst: summarize existing system before patching
- Change Impact Reviewer: identify affected/protected scope
- Integration Architect: choose safe integration strategy
- Safe Implementation Lane: patch only inside approved scope
- QA / Reviewers: review correctness and regression safety
- Lead: decide DELIVER_STORY / RETRY / BLOCKED

## Gates
- `GATE_1_RESEARCH`: brief/research captured
- `GATE_2_SPECIFICATION`: PRD/story definition ready
- `GATE_3_DESIGN`: design and ownership ready
- `BROWNFIELD_READINESS_GATE`: existing project safe to patch
- `GATE_4_IMPLEMENTATION`: implementation/review/integration passed
- `RELEASE_GATE`: delivery approved
