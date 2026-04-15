# Gate 1 - Research Questions

Purpose:
Ensure research and brief artifacts are clear enough to move into specification.

Required artifacts:
- brief.md
- market_research.md (optional but recommended)
- domain_research.md (optional but recommended)

Questions:
- Is the core problem statement clear and actionable?
- Is the business goal concrete rather than aspirational?
- Is the target user or segment clearly identified?
- Are the main use cases clear enough to write a PRD?
- Is there enough market or domain insight to support specification?
- Are major assumptions explicitly called out?
- Does the brief avoid vague language such as "better", "optimize", or "improve" without measurable meaning?
- In existing_project mode, is there enough baseline context to place the current story safely?

Pass when:
- the brief is specific
- the target user is clear
- the business goal is usable for specification
- no major ambiguity blocker remains

Fail when:
- the brief is too generic
- the target user is missing
- the business goal is unclear
- brownfield context is insufficient for safe story refinement

If pass:
- lock brief.md

If fail:
- return to PM/BA refinement before specification
