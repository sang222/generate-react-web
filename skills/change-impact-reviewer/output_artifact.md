# Output Artifact: `change_impact_report.json`

Required keys:
- `affected_modules`
- `protected_modules`
- `regression_risk`
- `breaking_risks`
- `safe_change_strategy`

The output must be:
- specific to the current baseline
- explicit about direct and indirect impact
- actionable for architect and implementation lanes

Failure conditions:
- empty or vague affected scope
- unjustified regression risk
- safe change strategy is generic or missing
