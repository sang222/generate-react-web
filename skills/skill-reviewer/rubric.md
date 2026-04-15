# Skill Reviewer Rubric

Evaluate recovery candidates independently using these criteria:

1. Scope safety
- Does the patch stay within the current story boundary?
- Does it avoid expanding allowed scope implicitly?

2. Contract safety
- Does it avoid mutating output contracts, gate semantics, or release semantics?
- Does it avoid hidden changes to forbidden scope rules?

3. Brownfield boundary safety
- In existing_project mode, does it respect allowed_change_scope and forbidden_change_scope?
- Does it preserve baseline and protected modules?

4. Regression likelihood
- Could the patch make future retries less safe or hide real regressions?
- Is the patch narrowly targeted?

5. Patch target correctness
- Should this be a runtime override, a project-only rule, or a core candidate only?
- Reject if the patch target is wrong or unjustified.

Decision guidance:
- approved_runtime_override: low-risk, narrow, temporary behavior reinforcement only
- approved_project_only: medium-risk, localized project-specific guidance only
- core_candidate_only: anything touching core semantics or requiring manual audit
- reject: low-quality, irrelevant, unsafe, or over-broad candidate
