# AI Dev Team Regen v7

This project is a local-first Python delivery system organized in a BMad-style structure.

## What changed in v7
- Removed `gemma3` from the default role mapping
- Switched to env-driven role -> model selection via `.env`
- Added real `.env` loading with `python-dotenv`
- Set `qwen3-coder` as the default Developer model
- Kept `glm4` in the default mapping for PM

## Default model mapping
Configured in `.env`:
- `PM_MODEL=glm4`
- `ARCHITECT_MODEL=qwen2.5:3b`
- `DEVELOPER_MODEL=qwen3-coder:30b`
- `QA_MODEL=qwen3:8b`
- `LEAD_MODEL=llama3.2:3b`

## Runtime architecture
- `main.py` is the CLI entrypoint
- `core/orchestrator.py` runs the PM -> Architect -> Developer -> QA -> Lead workflow
- `core/config.py` loads `_bmad/config.yaml` and role-model mapping from `.env`
- `core/llm.py` resolves the model by role at runtime
- `memory/manager.py` hydrates personal and shared memory

## Useful commands
```bash
cp .env.example .env
python main.py "Build a simple React todo app with add, delete, and filter"
python scripts/inspect_agent_sanctum.py developer
python scripts/inspect_shared_memory.py
```
