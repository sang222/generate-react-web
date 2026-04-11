# AI Dev Team Regen v10

This project is a local-first Python delivery system organized in a BMad-style structure with epic / story / run delivery semantics.

## What changed in v10
- Added epic / story / run semantics
- Added delivered story artifacts under `deliveries/<project_id>/<story_id>/`
- Added resume support via `--project-id`, `--epic-id`, `--story-id`, and `--resume-from`
- Successful story runs now end with `DELIVER_STORY` and emit a `story_manifest.json`
- Story 2+ can continue from the previously delivered baseline story

## Default model mapping
Configured in `.env`:
- `PM_MODEL=glm4`
- `ARCHITECT_MODEL=qwen2.5:3b`
- `DEVELOPER_MODEL=qwen3-coder:30b`
- `QA_MODEL=qwen3:8b`
- `LEAD_MODEL=llama3.2:3b`

## Runtime architecture
- `main.py` is the CLI entrypoint
- `core/orchestrator.py` runs epic / story delivery through PM -> Architect -> Developer -> QA -> Lead
- `core/config.py` loads `_bmad/config.yaml` and role-model mapping from `.env`
- `core/file_manager.py` supports baseline loading and story delivery copying
- `memory/manager.py` hydrates personal and shared memory

## Useful commands
```bash
cp .env.example .env
python main.py --project-id shop_web --epic-id SHOP-EPIC-1 --story-id SHOP-101 --story-name "App shell and routing foundation" "Build the first story for an ordering website"
python main.py --project-id shop_web --epic-id SHOP-EPIC-1 --story-id SHOP-102 --story-name "Catalog and product detail" "Build the next story on top of the delivered baseline"
python main.py --project-id shop_web --epic-id SHOP-EPIC-1 --story-id SHOP-102 --resume-from deliveries/shop_web/SHOP-101/source "Continue from story SHOP-101 and add catalog pages"
```


## v12 additions
- Gate state machine for Research -> Specification -> Design -> Implementation -> Release
- Artifact lock registry at `project_state/<project_id>/artifact_locks.json`
- Change request groundwork at `project_state/<project_id>/change_requests/`
- Richer story packet and story manifest with scope, business goal, acceptance criteria, and gate state
