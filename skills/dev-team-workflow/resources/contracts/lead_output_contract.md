# Lead Output Contract

Return ONLY valid JSON.

Required schema:
{
  "reason": "...",
  "improvement": "...",
  "ship_recommendation": "..."
}

Fail conditions:
- overrides rule-based decision
- invents new release criteria
- returns prose outside JSON
