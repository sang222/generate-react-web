# Brownfield Analyst Skill

## Purpose
Analyze an existing project before implementation starts.

## Inputs
- Existing project source or delivered baseline
- Current story packet
- Shared project memory

## Outputs
- `existing_system_summary.md`
- initial brownfield risks
- protected/fragile areas for downstream roles

## Checklist
- Identify current stack and build tools
- Map main folders, routes, services, and shared modules
- Highlight protected or regression-sensitive areas
- Summarize what must remain stable for the current story

## Escalation
Block implementation when the current system cannot be summarized with enough confidence.
