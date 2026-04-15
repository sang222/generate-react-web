# Bad Case: Safe Implementation Lane

## Weak output
- rewrites the shared layout for a local story
- regenerates frontend or backend root structure
- touches protected auth package without CR

## Why this is bad
- violates safe patching rules
- breaks baseline preservation
- should block or escalate instead of continuing
