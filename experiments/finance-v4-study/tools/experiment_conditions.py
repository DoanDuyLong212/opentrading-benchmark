"""Explicit experiment identities. Aliases select prompts, never another agent loop."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDITIONS = {
    'opencode': {'native_arm': 'opencode', 'prompt_variant': None, 'finance_policy': False},
    'dsh': {'native_arm': 'dsh', 'prompt_variant': None, 'finance_policy': False},
    'opentrading': {'native_arm': 'opentrading', 'prompt_variant': 'finance', 'finance_policy': True},
    'opentrading_baseline': {'native_arm': 'opentrading', 'prompt_variant': 'baseline', 'finance_policy': False},
    'opentrading_finance': {'native_arm': 'opentrading', 'prompt_variant': 'finance', 'finance_policy': True},
}
RUNTIME_ROOT = ROOT / 'experiments' / 'opentrading-runtime'


def condition(name):
    if name not in CONDITIONS:
        raise ValueError('Unregistered experiment condition: '+str(name))
    return dict(CONDITIONS[name])


def prompt_directory(variant):
    if variant not in ('baseline', 'finance'):
        raise ValueError('Unregistered prompt variant')
    path = (ROOT/'tools'/'prompt_variants'/variant).resolve()
    for name in ('identity.md', 'tools.md', 'citations.md', 'style.md'):
        if not (path/name).is_file():
            raise ValueError('Incomplete trusted prompt directory: '+str(path))
    return path
