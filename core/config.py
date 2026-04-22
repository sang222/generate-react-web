from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / '_bmad' / 'config.yaml'
DEFAULT_ENV_PATH = PROJECT_ROOT / '.env'

def load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(DEFAULT_ENV_PATH, override=False)

load_env()


def get_role_model_map() -> Dict[str, str]:
    load_env()
    default_model = os.getenv('DEFAULT_MODEL', 'qwen3.5:cloud')
    return {
        'pm': os.getenv('PM_MODEL', os.getenv('GLM4_MODEL', default_model)),
        'architect': os.getenv('ARCHITECT_MODEL', default_model),
        'developer': os.getenv('DEVELOPER_MODEL', 'qwen3-coder:480b-cloud'),
        'fe_developer': os.getenv('FE_DEVELOPER_MODEL', os.getenv('DEVELOPER_MODEL', 'qwen3-coder:480b-cloud')),
        'be_developer': os.getenv('BE_DEVELOPER_MODEL', os.getenv('DEVELOPER_MODEL', 'qwen3-coder:480b-cloud')),
        'qa': os.getenv('QA_MODEL', 'qwen3.5:cloud'),
        'fe_reviewer': os.getenv('FE_REVIEWER_MODEL', os.getenv('QA_MODEL', 'qwen3.5:cloud')),
        'be_reviewer': os.getenv('BE_REVIEWER_MODEL', os.getenv('QA_MODEL', 'qwen3.5:cloud')),
        'integration_qa': os.getenv('INTEGRATION_QA_MODEL', os.getenv('QA_MODEL', 'qwen3.5:cloud')),
        'lead': os.getenv('LEAD_MODEL', 'qwen3.5:cloud'),
        'recovery_meta': os.getenv('RECOVERY_META_MODEL', os.getenv('QA_MODEL', 'qwen3.5:cloud')),
        'skill_reviewer': os.getenv('SKILL_REVIEWER_MODEL', os.getenv('QA_MODEL', 'qwen3.5:cloud')),
    }


ROLE_MODEL_MAP = get_role_model_map()


def get_model_for_role(role: str) -> str:
    return get_role_model_map().get(role, os.getenv('DEFAULT_MODEL', 'qwen3.5:cloud'))


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_module_config() -> Dict[str, Any]:
    config: Dict[str, Any] = {
        'module': {'name': 'ai-dev-team', 'code': 'dt', 'default_mode': 'guided'},
        'devteam': {
            'project_mode': 'new_project',
            'output_project_dir': 'output_project',
            'state_dir': 'state',
            'deliveries_dir': 'deliveries',
            'max_retry_loops': 3,
            'install_command': 'npm install',
            'build_command': 'npm run build',
            'qa_enabled': True,
            'build_validation_enabled': True,
            'generate_distillate': True,
        },
        'system': {
            'system_type': 'fullstack_website',
            'frontend': {
                'stack': 'react-vite',
            },
            'backend': {
                'language': 'java',
                'framework': 'spring_boot',
                'build_tool': 'gradle',
            },
            'database': {
                'engine': 'postgres',
                'orm': 'jpa',
            },
        },
        'memory': {
            'sanctum_root': '_bmad/memory',
            'session_logs_enabled': True,
            'curated_memory_enabled': True,
            'shared_memory_enabled': True,
        },
        'models': ROLE_MODEL_MAP,
    }
    if DEFAULT_CONFIG_PATH.exists() and yaml is not None:
        loaded = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding='utf-8')) or {}
        if isinstance(loaded, dict):
            _deep_merge(config, loaded)

    max_loop_env = os.getenv('MAX_RETRY_LOOPS')
    if max_loop_env and max_loop_env.isdigit():
        config.setdefault('devteam', {})['max_retry_loops'] = int(max_loop_env)

    system = config.setdefault('system', {})
    frontend = system.setdefault('frontend', {})
    backend = system.setdefault('backend', {})
    database = system.setdefault('database', {})

    system['system_type'] = os.getenv('SYSTEM_TYPE', system.get('system_type', 'fullstack_website'))
    frontend['stack'] = os.getenv('FRONTEND_STACK', frontend.get('stack', 'react-vite'))
    backend['language'] = os.getenv('BACKEND_LANGUAGE', backend.get('language', 'java'))
    backend['framework'] = os.getenv('BACKEND_FRAMEWORK', backend.get('framework', 'spring_boot'))
    backend['build_tool'] = os.getenv('BACKEND_BUILD_TOOL', backend.get('build_tool', 'gradle'))
    database['engine'] = os.getenv('DATABASE_ENGINE', database.get('engine', 'postgres'))
    database['orm'] = os.getenv('DATABASE_ORM', database.get('orm', 'jpa'))

    # Backward-compatible flat aliases used by some older code/resources.
    config.setdefault('devteam', {})['frontend_stack'] = frontend['stack']
    config['models'] = get_role_model_map()
    return config


def get_system_target(config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    data = config or load_module_config()
    system = data.get('system', {})
    frontend = system.get('frontend', {})
    backend = system.get('backend', {})
    database = system.get('database', {})
    return {
        'system_type': system.get('system_type', 'fullstack_website'),
        'frontend_stack': frontend.get('stack', 'react-vite'),
        'backend_language': backend.get('language', 'java'),
        'backend_framework': backend.get('framework', 'spring_boot'),
        'backend_build_tool': backend.get('build_tool', 'gradle'),
        'database_engine': database.get('engine', 'postgres'),
        'database_orm': database.get('orm', 'jpa'),
    }
