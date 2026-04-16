# TDD v25 - Cost Down and Preflight Hardening

## Goals
- Reduce unnecessary backend lane activation for small frontend-only stories.
- Run FE/BE lanes in parallel instead of sequentially.
- Add deterministic preflight checks before reviewer and lead LLM calls.
- Avoid repeated `npm install` work when frontend manifests have not changed.

## Main changes
- Add `execution_mode` to story packet and CLI.
- Narrow `detect_needed_lanes()` so fullstack target does not imply backend work by default.
- Use thread pools for developer lanes and reviewer lanes.
- Add `run_preflight_checks()` for files, package policy, and local import checks.
- Cache `node_modules` by manifest hash under `.build_cache/npm/`.
