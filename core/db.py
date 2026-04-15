from __future__ import annotations

"""Legacy compatibility shim. MongoDB has been removed in v22.
Use file-based stores in core.memory and memory.manager instead.
"""

from pathlib import Path
from typing import Any

STORE_DIR = Path('.memory_store')


def get_mongo_client() -> None:
    return None


def get_database() -> None:
    return None


def get_runs_collection() -> None:
    return None


def get_agent_profiles_collection() -> None:
    return None


def get_agent_memories_collection() -> None:
    return None
