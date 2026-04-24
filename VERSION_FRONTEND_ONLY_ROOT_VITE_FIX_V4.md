# frontend-only-root-vite-runtime-fix-v4

Full repo zip based on uploaded base zip, with runtime fixes applied while preserving the original skills directory contents.

Applied source changes:
- core/effective_target.py
- core/orchestrator_helpers/delivery.py
- core/integration_service.py
- core/executor.py
- core/orchestrator_helpers/lanes.py
- core/model_preflight.py
- scripts/check_models.py
- core/context_views.py
- agents/developer.py

Fixes:
- frontend_only new_project uses root Vite contract.
- generated files are normalized/validated before retry.
- deterministic missing_required_files retries skip Lead LLM.
- model preflight dedupes unique cloud models.
- original skills/ content from base zip is preserved.
