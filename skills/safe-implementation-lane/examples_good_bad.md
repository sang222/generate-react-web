# Safe Implementation Good / Bad Examples

## Good
- Adds new module beside stable shell
- Extends route tree without rewriting layout
- Adds backend package under approved domain boundary

## Bad
- Rewrites shared layout for a local story need
- Regenerates the entire frontend or backend
- Touches protected auth or order modules without CR
