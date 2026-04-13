# Developer Sizing Guidance
- Level 0-1: keep changes very small, prefer one lane if possible, and avoid introducing new dependencies.
- Level 2: implement the full story scope, but keep the file set bounded and verifiable.
- Level 3-4: respect lane boundaries, preserve baseline contracts, and prefer additive changes over rewrites.
- For existing_project stories, treat allowed_change_scope as the main working area and forbidden_change_scope as read-only unless a change request exists.
