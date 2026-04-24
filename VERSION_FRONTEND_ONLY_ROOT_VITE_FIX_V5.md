# frontend-only-root-vite-runtime-fix-v5

Base: v4 full source package.

## Added in v5

### 1. Fix new_project ownership gate blocker

For `--project-mode new_project`, integration no longer blocks generated files under shared paths such as:

- `docs/design/design_direction.md`
- `docs/design/design_tokens.json`
- `docs/design/component_plan.md`

`shared_path_override` and `locked_artifact_change` gates are now enforced only for `existing_project` / brownfield flows.

Reason: new projects are allowed to create design docs and app files freely; requiring change requests here caused deterministic retry loops.

### 2. LLM runtime telemetry

`core/llm.py` now logs:

- prompt chars
- prompt hash
- request options
- `num_predict`
- Ollama metadata when available
- slow-call events

### 3. Benchmark script

Added:

```bash
python3.12 scripts/benchmark_models.py --model qwen3.5:cloud --runs 5
python3.12 scripts/benchmark_models.py --model glm-5.1:cloud --runs 5
python3.12 scripts/benchmark_models.py --model qwen3-coder-next:cloud --runs 5
```

## Main issue fixed

Previous blocker:

```txt
[shared path override]
docs/design/design_direction.md
docs/design/design_tokens.json
docs/design/component_plan.md
```

This should not block `new_project` runs.
