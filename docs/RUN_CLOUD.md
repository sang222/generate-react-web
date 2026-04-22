# Run with Ollama Cloud

Use Python 3.12. Python 3.14 can fail when creating a venv because of `ensurepip`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python3.12 scripts/check_env.py
python3.12 scripts/check_models.py
```

The repo is Ollama Cloud only. Local Ollama is disabled.

Run:

```bash
python3.12 main.py "Build a clean landing page" --project-mode new_project --project-id demo_cloud --epic-id demo_epic --story-id landing_1 --execution-mode frontend_only
```

Troubleshooting:
- `OLLAMA_API_KEY is required`: run `scripts/check_env.py` and check `.env`.
- model 404: run `scripts/check_models.py` and update model names.
- no output project: inspect `state/run_state.json`, story run state, and `state/llm_errors.jsonl`.
