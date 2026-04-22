# FE UI Implementation Contract

Return ONLY JSON:

```json
{
  "files": [
    {"path": "frontend/src/...", "content": "..."}
  ],
  "touched_boundary": {
    "touched_paths": [],
    "allowed_scope_matches": [],
    "forbidden_scope_hits": [],
    "locked_artifact_hits": [],
    "new_components": [],
    "reused_components": [],
    "change_request_required": false,
    "style_strategy": "existing_convention | css_modules | tailwind | stylesheet_tokens | nativewind_existing",
    "blocked_reason": ""
  }
}
```

Required:
- every file path must appear in `touched_boundary.touched_paths`
- every touched path must match allowed scope or be covered by approved CR
- `forbidden_scope_hits` must be empty to proceed
- no fake API/data contracts
