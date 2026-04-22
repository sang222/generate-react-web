# FE Visual Review Contract

Return ONLY JSON:

```json
{
  "schema_version": "1.0",
  "decision": "PASS | RETRY | BLOCKED",
  "score": {
    "visual_hierarchy": 0,
    "layout_composition": 0,
    "brand_consistency": 0,
    "interaction_quality": 0,
    "implementation_fit": 0
  },
  "issues": [
    {
      "severity": "blocker | major | minor",
      "category": "hierarchy | spacing | color | typography | motion | accessibility | scope | framework_misuse | anti_slop",
      "file_path": "",
      "description": "",
      "fix_suggestion": ""
    }
  ],
  "anti_slop_flags": [],
  "retry_prompt": ""
}
```

Decision rules:
- PASS: score >= 36 and no blocker.
- RETRY: fixable visual/implementation issues.
- BLOCKED: scope/API/protected-path issue or UI ignores direction.
