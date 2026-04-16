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
python3 main.py --project-id shop_web --epic-id SHOP-EPIC-1 --story-id SHOP-101 --story-name "App shell and routing foundation" "Build the first story for an ordering website"
python3 main.py --project-id shop_web --epic-id SHOP-EPIC-1 --story-id SHOP-102 --story-name "Catalog and product detail" "Build the next story on top of the delivered baseline"
python3 main.py --project-id shop_web --epic-id SHOP-EPIC-1 --story-id SHOP-102 --resume-from deliveries/shop_web/SHOP-101/source "Continue from story SHOP-101 and add catalog pages"
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
- Helper pattern under `skills/dev-team-workflow/resources/helpers/` to reduce repeated prompt policy text
- `workflow_status.yaml` per project for quick operator-readable status
- `scripts/workflow_status.py` and `python3 main.py --workflow-status --project-id ...`
- Right-sizing via project levels (`project_level` and `delivery_profile`) injected into each story packet
- Lane activation now respects story size and backend need instead of always forcing FE/BE together


## v16 existing_project mode
- Added brownfield-specific artifacts under `project_state/<project_id>/`:
  - `existing_system_summary.md`
  - `change_impact_report.json`
  - `integration_strategy.md`
  - `brownfield_readiness_report.json`
- Added `BROWNFIELD_READINESS_GATE` before implementation for `existing_project` stories
- Existing-project story packets now include allowed / forbidden change scope and readiness artifact paths
- Workflow status now surfaces brownfield readiness and affected-module counts


## Skill Candidate Store and CLI Review Flow

This project now includes a separate skill-promotion path beside story delivery.

Main locations:
- `skill_candidates/<candidate_id>/`
- `skill_registry/promotion_log.json`
- `docs/TDD_skill_promotion_workflow.md`

CLI:
```bash
python3 main.py --list-skill-candidates
python3 main.py --show-skill-candidate cand_001
python3 main.py --review-skill-candidate cand_001 --skill-candidate-decision promote_to_core
```

Purpose:
- inspect AI-proposed skill changes
- review diffs on CLI
- approve, reject, or request revision
- keep delivery workflow separate from skill evolution

## v19 improvements

### 1. Skill packs are first-class citizens
Added dedicated brownfield skill packs:
- `skills/brownfield-analyst/`
- `skills/change-impact-reviewer/`
- `skills/integration-architect/`
- `skills/safe-implementation-lane/`

Each pack includes:
- `SKILL.md`
- `contracts.md`
- `checklist.md`
- `examples_good_bad.md`
- `escalation_rules.md`

### 2. Operator surface / command aliases
Added operator-facing scripts:
- `scripts/create_prd.py`
- `scripts/design_story.py`
- `scripts/run_story.py`
- `scripts/resume_story.py`
- `scripts/list_agents.py`
- `scripts/list_skills.py`
- `scripts/run_skill_eval.py`

Also added docs:
- `docs/operator_surface.md`
- `docs/when_to_use_roles_and_gates.md`

Main CLI now supports:
- `--list-agents`
- `--list-skills`
- `--run-skill-evals`
- `--show-skill-eval-case <case_id>`

### 3. Brownfield skill eval corpus
Added a starter eval corpus under:
- `evals/brownfield/`

Includes:
- artifact-focused cases
- role scorecards
- bad markers for brownfield reasoning quality


## v20 Prompt Architecture Refactor

- Slimmed role prompts so each agent prompt now focuses on role identity, current task, and priority order.
- Moved output contracts into `skills/dev-team-workflow/resources/contracts/`.
- Moved role checklists into `skills/dev-team-workflow/resources/checklists/`.
- Moved good/bad examples into `skills/dev-team-workflow/resources/examples/`.
- Added shared rules under `skills/dev-team-workflow/resources/rules/` for gate and change-request behavior.

## v21 Skill-Centric Brownfield Improvements

- Made brownfield skill packs narrower and more data-backed.
- Added per-skill docs for:
  - `when_to_use.md`
  - `output_artifact.md`
  - `known_failures.json`
  - `cases/good_case_01.md`
  - `cases/bad_case_01.md`
- Brownfield prompt resources now load role-relevant skill packs instead of relying only on generic brownfield rules.
- Added `python3 main.py --show-skill <skill_name>` for operator-friendly skill inspection.
- Expanded the brownfield eval corpus with additional artifact and implementation cases.


## v22 changes

- MongoDB removed. Run history and agent memory now use local file-based storage.
- CLI logging slimmed to question/answer style for interactive use.
- Technical trace output is suppressed by default; set `TRACE_AGENTS=1` and `QA_ONLY_CLI=0` to re-enable verbose traces.

## v23 additions
- Added human-readable Gate Question Sets under `skills/dev-team-workflow/resources/gates/`
- Added TDD for gate questions at `docs/TDD_v23_gate_question_sets.md`
- Gate resources now cover Research, Specification, Design, Brownfield Readiness, Implementation, and Release


## v24 additions

- Added **Adaptive Recovery Mode** after 2 failed attempts
- Added **Recovery Meta-Agent** and **Skill Reviewer** routing
- Added autonomous **cross review + auto-apply policy** for low/medium-risk runtime overrides
- Added audit/history files under `skill_history/`
- Added `python3 main.py --show-recovery-history`

## v24.1 additions
- hardened adaptive recovery with an independent skill reviewer rubric
- deterministic risk classifier for recovery candidates
- recovery engine split out from the orchestrator loop
- explicit blocked reason codes for recovery outcomes


## v24.2 hardening

- reviewer fallback is now conservative: invalid reviewer output results in `reject` and no auto-apply
- `python3 main.py --show-recovery-history` is wired end-to-end
- recovery history records reviewer fallback reason codes for audit


## v25 additions

- Smarter lane detection with `--execution-mode` (`auto`, `frontend_only`, `backend_only`, `fullstack`) so small UI stories do not automatically activate backend work.
- Real parallel FE/BE developer and reviewer execution using thread pools.
- Deterministic preflight runs before reviewer/lead LLM calls to avoid wasting expensive calls on obvious file/import/package errors.
- Frontend dependency installs use manifest-hash caching and prefer `npm ci` when a lockfile exists, reducing repeated install cost across retries.
- JSON extraction is more robust than the old greedy-regex approach.
