# TDD v31 - DeepAgents-Inspired Runtime Refactor

## Goal
Keep BMAD delivery semantics while moving execution toward a graph/node runtime with checkpoints, subagent primitives, and tool boundaries.

This branch is not a LangGraph migration and does not replace the existing orchestrator. It adds the first migration slice:

- runtime state models
- node/result contracts
- graph runner
- checkpoint persistence
- legacy orchestrator node wrapper
- subagent runner primitive
- tool boundary primitives
- Ollama Cloud only runtime

## Principles

1. No big-bang refactor.
2. GraphRunner applies state updates; nodes return `NodeResult`.
3. Tool boundary must become enforceable, not just decorative.
4. Candidate learning remains a recovery branch, not a default phase.
5. Existing BMAD files remain compatible: `run_state.json`, `workflow_status.yaml`, gate state, delivery index, artifact locks.

## Current Runtime Shape

```text
CLI
-> RuntimeGraph
   -> LegacyOrchestratorNode
      -> existing run_orchestrator
-> Checkpointer before/after/final
```

This proves graph/checkpoint semantics first. Phase nodes will be extracted later.

## New modules

```text
core/runtime/
  state.py
  node_result.py
  graph.py
  checkpoints.py
  transitions.py
  context_policy.py
  factory.py
  nodes/base.py
  nodes/legacy_orchestrator_node.py

core/agents/
  role_registry.py
  subagent_runner.py
  agent_runtime.py

core/tools/
  tool_boundary.py
  filesystem_tool.py
  shell_tool.py
  artifact_writer.py
  project_scan_tool.py

core/services/
  gate_service.py
  story_service.py
  delivery_service.py
  checkpoint_service.py
```

## Migration order

1. Runtime primitives and graph wrapper.
2. Low-risk services.
3. ToolBoundary early.
4. Review node.
5. Implementation node.
6. CandidateLearningNode.
7. Bootstrap/Brownfield nodes.
8. Planning/Design nodes.
9. CLI subcommands.
10. Tests/evals.

## Ollama Cloud only

Local Ollama fallback is removed. Use:

```env
OLLAMA_API_KEY=...
DEFAULT_MODEL=qwen3.5:cloud
FE_DEVELOPER_MODEL=qwen3-coder:480b-cloud
```

## Test commands

```bash
python3 -m compileall -q core agents scripts main.py tests
python3 -m unittest discover -s tests
python3 main.py --help
python3 scripts/test_ollama_cloud_connection.py --model qwen3.5:cloud
```
