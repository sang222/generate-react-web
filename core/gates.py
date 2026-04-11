from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PHASE_ORDER = [
    'GATE_1_RESEARCH',
    'GATE_2_SPECIFICATION',
    'GATE_3_DESIGN',
    'GATE_4_IMPLEMENTATION',
    'RELEASE_GATE',
]


def gate_state_path(project_id: str) -> Path:
    return Path('project_state') / project_id / 'gate_state.json'


def default_gate_state(project_id: str, epic_id: str, story_id: str) -> Dict[str, Any]:
    return {
        'project_id': project_id,
        'epic_id': epic_id,
        'story_id': story_id,
        'current_gate': PHASE_ORDER[0],
        'passed_gates': [],
        'history': [],
    }


def load_gate_state(project_id: str, epic_id: str, story_id: str) -> Dict[str, Any]:
    path = gate_state_path(project_id)
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('story_id') == story_id:
            return data
    return default_gate_state(project_id, epic_id, story_id)


def save_gate_state(state: Dict[str, Any]) -> str:
    path = gate_state_path(state['project_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(path)


def pass_gate(state: Dict[str, Any], gate_name: str, summary: str, artifacts: List[str] | None = None) -> Dict[str, Any]:
    if gate_name not in PHASE_ORDER:
        return state
    if gate_name not in state['passed_gates']:
        state['passed_gates'].append(gate_name)
    idx = PHASE_ORDER.index(gate_name)
    next_gate = PHASE_ORDER[min(idx + 1, len(PHASE_ORDER) - 1)]
    state['current_gate'] = next_gate if gate_name != 'RELEASE_GATE' else 'RELEASE_APPROVED'
    state['history'].append({
        'gate': gate_name,
        'status': 'passed',
        'summary': summary,
        'artifacts': artifacts or [],
        'timestamp': datetime.now().isoformat(timespec='seconds'),
    })
    return state


def fail_gate(state: Dict[str, Any], gate_name: str, summary: str) -> Dict[str, Any]:
    state['current_gate'] = gate_name
    state['history'].append({
        'gate': gate_name,
        'status': 'failed',
        'summary': summary,
        'timestamp': datetime.now().isoformat(timespec='seconds'),
    })
    return state
