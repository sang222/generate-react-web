# Operator Surface

## Common commands

- `python scripts/create_prd.py "<task>"`
- `python scripts/design_story.py "<task>" --prd "<prd text>"`
- `python scripts/run_story.py "<task>" --project-id ... --epic-id ... --story-id ... --story-name ...`
- `python scripts/resume_story.py "<task>" --project-id ... --epic-id ... --story-id ... --story-name ... --resume-from ...`
- `python scripts/show_story_status.py --project-id <project_id>`
- `python scripts/workflow_status.py --project-id <project_id>`
- `python scripts/list_agents.py`
- `python scripts/list_skills.py`

## When to use which gate
- Research/spec/design gates for drafting and readiness
- Brownfield readiness gate for existing_project before implementation
- Implementation/release gates for deliverable safety

## Skill inspection

```bash
python main.py --list-skills
python main.py --show-skill brownfield-analyst
```

Use this to inspect a skill pack before running or reviewing a brownfield story.
