# Gate 2 - Specification Questions

Purpose:
Ensure the PRD and story definition are specific enough to move into design.

Required artifacts:
- prd.md
- epic_context.json
- story_map.json
- acceptance_criteria.json

Questions:
- Is the scope of the current story clear?
- Are in-scope and out-of-scope boundaries explicit?
- Are acceptance criteria testable?
- Is the business value of the story explicit?
- Are dependencies on other stories or systems clearly defined?
- Are there any blocking TBD items remaining?
- Is the story too large or mixing too many domains?
- For fullstack work, are FE and BE responsibilities clear enough?
- In existing_project mode, are sensitive baseline areas and regression-sensitive zones identified?
- Are major risks or compatibility concerns called out?

Pass when:
- the story is specific enough to design
- acceptance criteria are testable
- boundaries are usable
- dependencies are clear
- no blocking TBD remains

Fail when:
- scope is vague
- acceptance criteria are not testable
- dependencies are unclear
- out-of-scope boundaries are missing
- brownfield risk is ignored

If pass:
- lock prd.md
- lock epic_context.json
- lock story_map.json

If fail:
- return to PM/BA refinement before design
