# Gate 4 - Implementation Questions

Purpose:
Ensure the implementation is complete enough and safe enough to proceed to release.

Required artifacts:
- source code output
- review_report.json
- integration_report.json
- build outputs

Questions:
- Has the current story been implemented according to acceptance criteria?
- Did implementation stay within allowed change scope?
- Were any protected modules changed without approval?
- Are there FE/BE lane conflicts?
- Do review findings contain blockers?
- Do integration findings contain blockers?
- Did the build pass?
- In existing_project mode, is the baseline still intact?
- Are there regression bugs that block delivery?
- Do changed files match the intended story scope?

Pass when:
- build passes
- review passes
- integration passes
- no blocker remains
- scope boundaries were respected

Fail when:
- build fails
- lane conflicts remain
- structural, functional, or regression blockers remain
- protected modules were changed unsafely
