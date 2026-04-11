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


## System target config

The workflow now reads stack choices from `_bmad/config.yaml` and `.env`.

Default target:
- Frontend: React + Vite
- Backend: Java + Spring Boot
- Build tool: Gradle
- Database: PostgreSQL
- ORM: JPA

Override with environment variables such as `FRONTEND_STACK`, `BACKEND_LANGUAGE`, `BACKEND_FRAMEWORK`, `BACKEND_BUILD_TOOL`, `DATABASE_ENGINE`, and `DATABASE_ORM`.


## Fullstack default target

This version validates a fullstack target by default:
- frontend: React + Vite under `frontend/`
- backend: Java + Spring Boot under `backend/`
- build tool: Gradle
- database: PostgreSQL + JPA

Frontend validation runs `npm install` and `npm run build` inside `frontend/`. Backend validation runs `./gradlew build -x test` when a wrapper exists, otherwise `gradle build -x test`.


## v15 additions

### 1. Helper pattern
Shared helper resources now live under:
- `skills/dev-team-workflow/resources/helpers/`

Purpose:
- reduce repeated prompt policy text
- keep common workflow rules in one place
- make prompts smaller and easier to maintain

Typical helper content includes:
- delivery rules
- dependency rules
- system target rules
- lane execution constraints

### 2. Workflow status
Each project now has a lightweight operator-readable workflow status view.

Main status files:
- `project_state/<project_id>/workflow_status.yaml`
- `project_state/<project_id>/delivery_index.json`
- `project_state/<project_id>/gate_state.json`

Purpose:
- show the current delivered story
- show the last successful gate
- show the current workflow state
- suggest the next step for the operator

Commands:
```bash
python main.py --workflow-status --project-id <project_id>
python scripts/workflow_status.py --project-id <project_id>
```

### 3. Project sizing / right-sizing
Each story packet now includes:
- `project_level`
- `delivery_profile`
- `level_reasoning`

Purpose:
- avoid using the same heavy workflow for every request
- scale workflow depth based on story size and complexity
- decide when FE/BE lanes should be activated

Typical meaning:
- lower level = lighter workflow
- higher level = stricter workflow, more review, more coordination

Runtime effect:
- small stories can stay lighter and narrower
- larger stories can activate stronger review, richer manifests, and FE/BE lane coordination
