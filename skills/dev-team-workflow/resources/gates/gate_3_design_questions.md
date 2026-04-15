# Gate 3 - Design Questions

Purpose:
Ensure the design is safe, specific, and implementation-ready.

Required artifacts:
- architecture.md
- work_breakdown.json
- ownership_map.json
- readiness_report.json

Questions:
- Is the proposed architecture appropriate for the current story?
- Is the design over-engineered for the current scope?
- Is the integration strategy clear and actionable?
- Are module boundaries clear?
- Are affected and protected modules clearly identified?
- Is ownership clear enough to activate FE and BE lanes?
- Does the architect provide decision rationale for major choices?
- Are integration points and dependency boundaries explicit?
- In existing_project mode, is the patch strategy safe for the current baseline?
- Can implementation begin without guessing architecture or ownership?

Pass when:
- architecture is actionable
- ownership is clear
- strategy is safe
- the story is implementation-ready

Fail when:
- architecture is vague
- ownership is unclear
- strategy is unsafe
- readiness is incomplete
- decision rationale is missing

If pass:
- lock architecture.md
- lock ownership_map.json
- lock work_breakdown.json
- freeze ownership map before implementation lanes start

If fail:
- return to design refinement before implementation
