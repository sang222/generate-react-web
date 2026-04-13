# Developer Output Contract

Return ONLY valid JSON.

Required schema:
{
  "files": [
    {"path": "...", "content": "..."}
  ]
}

Requirements:
- only return files needed for the current lane and story
- use double quotes for all keys and string values
- no markdown or prose
- no extra top-level keys

Fail conditions:
- invalid JSON
- files outside allowed scope without integration need
- overwriting unrelated baseline files
