# Brownfield Readiness Gate Questions

Purpose:
Ensure an existing project is understood well enough to begin safe implementation.

Required artifacts:
- existing_system_summary.md
- change_impact_report.json
- integration_strategy.md
- brownfield_readiness_report.json

Questions:
- Does the existing system summary describe the current structure clearly enough?
- Are affected modules identified explicitly?
- Are protected modules identified explicitly?
- Is the regression risk justified and usable?
- Is the integration strategy actionable rather than generic?
- Does the readiness report still contain missing-information blockers?
- Are allowed and forbidden change scopes clear enough for implementation?
- Is there any sign that the plan would regenerate the baseline instead of patching it?
- Are change-request-sensitive areas identified?
- Is the current story genuinely ready for safe implementation?

Pass when:
- all four brownfield artifacts exist
- readiness_report.ready is true
- scope boundaries are clear
- the strategy is actionable
- regression risk is acknowledged

Fail when:
- the summary is too generic
- impact analysis is incomplete
- strategy is vague
- readiness passes too early
- critical information is still missing

If pass:
- lock brownfield artifacts
- allow implementation to proceed

If fail:
- block implementation
- return to brownfield analysis or architecture refinement
