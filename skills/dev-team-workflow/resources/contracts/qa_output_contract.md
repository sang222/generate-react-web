# QA Output Contract

Return ONLY valid JSON.

Required schema:
{
  "structural_bugs": [],
  "functional_bugs": [],
  "prd_gaps": [],
  "ui_gaps": [],
  "regression_bugs": [],
  "fix_suggestion": ""
}

Fail conditions:
- mixed prose outside JSON
- uncategorized findings
- missing regression concerns in existing_project mode
