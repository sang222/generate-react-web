from __future__ import annotations
import json
from typing import Any, Dict
def _truncate(text: str, max_chars: int) -> str:
    value = (text or '').strip()
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + '\n...[truncated for compact context]'
def is_lightweight_frontend_story(context: Dict[str, Any]) -> bool:
    packet = context.get('story_packet', {}) or {}
    mode = str(packet.get('execution_mode', context.get('execution_mode', 'auto')) or 'auto').lower()
    level = int(packet.get('project_level', 2) or 2)
    active = set(context.get('active_lanes', packet.get('active_lanes', [])) or [])
    return context.get('project_mode', packet.get('project_mode', 'new_project')) == 'new_project' and level <= 2 and (mode == 'frontend_only' or active == {'frontend'})
def compact_story_packet_for_lane(story_packet: Dict[str, Any], lane: str) -> Dict[str, Any]:
    keys = ['project_id','epic_id','story_id','story_name','project_mode','execution_mode','project_level','delivery_profile','acceptance_criteria','in_scope','out_of_scope','allowed_change_scope','forbidden_change_scope','regression_requirements','required_files','loop_count']
    return {key: story_packet.get(key) for key in keys if key in story_packet}
def compact_effective_target_for_lane(system_target: Dict[str, Any], lane: str) -> Dict[str, Any]:
    if lane == 'frontend':
        return {'system_type': system_target.get('system_type', 'web_app'), 'effective_mode': system_target.get('effective_mode', 'frontend_only'), 'frontend_stack': system_target.get('frontend_stack', 'react-vite'), 'frontend_root': system_target.get('frontend_root', '.'), 'required_files': system_target.get('required_files', [])}
    if lane == 'backend':
        return {'system_type': system_target.get('system_type', 'api'), 'effective_mode': system_target.get('effective_mode', 'backend_only'), 'backend_language': system_target.get('backend_language', 'java'), 'backend_framework': system_target.get('backend_framework', 'spring_boot'), 'backend_build_tool': system_target.get('backend_build_tool', 'gradle'), 'database_engine': system_target.get('database_engine', 'postgres'), 'database_orm': system_target.get('database_orm', 'jpa')}
    return dict(system_target or {})
def build_developer_context_view(context: Dict[str, Any], lane: str) -> Dict[str, Any]:
    packet = compact_story_packet_for_lane(context.get('story_packet', {}) or {}, lane)
    target = compact_effective_target_for_lane(context.get('effective_target') or context.get('system_target', {}), lane)
    return {'goal': context.get('story_goal') or context.get('task', ''), 'task': context.get('task', ''), 'story_packet': packet, 'target': target, 'prd': _truncate(context.get('prd', ''), 2500), 'design': _truncate(context.get('design', ''), 2500), 'acceptance_criteria': packet.get('acceptance_criteria', []), 'constraints': {'allowed_change_scope': packet.get('allowed_change_scope', []), 'forbidden_change_scope': packet.get('forbidden_change_scope', []), 'no_fake_api': True}, 'latest_error': _truncate(context.get('execution_error', ''), 1200), 'fix_suggestion': _truncate(context.get('fix_suggestion', ''), 1200)}
def render_context_view(view: Dict[str, Any]) -> str:
    return json.dumps(view, ensure_ascii=False, indent=2)
