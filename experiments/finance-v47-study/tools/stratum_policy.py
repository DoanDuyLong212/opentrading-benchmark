"""Stratum and runs policy for v4.7 benchmark."""
import tomllib
from pathlib import Path

DEFAULT_RUNS_BY_STRATUM = {
    'lookup': 1,
    'compute': 2,
    'memory': 2,
    'safety': 2,
    'investor': 2,
}

def task_stratum(task_dir):
    """Classify task into canonical stratum: lookup (L), compute (C), memory (M), safety (S)."""
    p = Path(task_dir)
    toml_path = p / 'task.toml' if p.is_dir() else p
    if not toml_path.exists():
        name = p.name
        if name.startswith('fin-l') or name.startswith('dev-fin-l') or name.startswith('v45-dev-01') or name.startswith('v45-dev-09'):
            return 'lookup'
        if name.startswith('fin-c') or name.startswith('dev-fin-c'):
            return 'compute'
        if name.startswith('fin-m') or name.startswith('dev-fin-m'):
            return 'memory'
        if name.startswith('fin-s') or name.startswith('dev-fin-s'):
            return 'safety'
        return 'lookup'
    with open(toml_path, 'rb') as f:
        meta = tomllib.load(f)
    s = meta.get('stratum')
    if s:
        s = s.lower().strip()
        if s in ('compute', 'memory', 'safety', 'lookup', 'investor'):
            return s
        if s == 'core':
            return 'lookup'
    lvl = str(meta.get('level', '')).upper()
    if lvl.startswith('L'):
        return 'lookup'
    if lvl.startswith('C'):
        return 'compute'
    if lvl.startswith('M'):
        return 'memory'
    if lvl.startswith('S'):
        return 'safety'
    tid = meta.get('id', p.name)
    if tid.startswith('fin-l'): return 'lookup'
    if tid.startswith('fin-c'): return 'compute'
    if tid.startswith('fin-m'): return 'memory'
    if tid.startswith('fin-s'): return 'safety'
    if tid.startswith('fin-i'): return 'investor'
    return 'lookup'


def runs_for_task(task_dir, policy=None, default_runs=1):
    """Return scheduled replication count for this task under stratum policy."""
    if not policy:
        return default_runs
    s = task_stratum(task_dir)
    return policy.get(s, default_runs)
