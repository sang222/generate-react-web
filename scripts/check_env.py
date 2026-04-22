from __future__ import annotations
import importlib.util, os, sys
from pathlib import Path
def show(ok: bool, label: str, detail: str = '') -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {label}{': ' + detail if detail else ''}"); return ok
def main() -> int:
    ok = True
    ok &= show(sys.version_info[:2] == (3, 12), 'Python version', f'found {sys.version.split()[0]}, expected 3.12.x')
    ok &= show(sys.prefix != getattr(sys, 'base_prefix', sys.prefix), 'Virtualenv active', sys.prefix)
    ok &= show(importlib.util.find_spec('ollama') is not None, 'ollama package installed', 'use python -m pip install -r requirements.txt')
    ok &= show(importlib.util.find_spec('dotenv') is not None, 'python-dotenv installed', 'use python -m pip install python-dotenv')
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(Path.cwd() / '.env', override=False)
    except Exception:
        pass
    ok &= show(bool(os.getenv('OLLAMA_API_KEY', '').strip()), 'OLLAMA_API_KEY loaded', 'set it in .env or shell')
    ok &= show(not os.getenv('OLLAMA_HOST', '').startswith('http://localhost'), 'Ollama Cloud only', 'remove local OLLAMA_HOST')
    return 0 if ok else 2
if __name__ == '__main__':
    raise SystemExit(main())
