from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from memory.sanctum import get_agent_sessions_dir, parse_bullets, read_markdown
from memory.schemas import MEMORY_AGENT_IDS


def curate_and_prune_sessions(project_root: str | Path | None = None, keep_days: int = 30) -> List[str]:
    pruned: List[str] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    for agent_id in MEMORY_AGENT_IDS:
        sessions_dir = get_agent_sessions_dir(agent_id, project_root)
        if not sessions_dir.exists():
            continue
        for path in sessions_dir.glob('*.md'):
            try:
                file_date = datetime.strptime(path.stem, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except Exception:
                continue
            if file_date >= cutoff:
                continue
            text = read_markdown(path)
            bullets = parse_bullets(text)
            if bullets:
                path.write_text('# Session Log\n\nArchived and pruned after curation.\n', encoding='utf-8')
            else:
                path.unlink(missing_ok=True)
            pruned.append(str(path))
    return pruned
