# Output Artifacts

Primary outputs:
- changed files JSON payload
- touched-boundary summary markdown/text

The implementation output must:
- stay inside allowed scope unless CR exists
- preserve baseline instead of regenerating it
- summarize touched FE/BE boundaries for review

Failure conditions:
- regenerates project from scratch
- touches protected modules without approval
- changes exceed allowed scope without escalation
