"""Receipt-backed locators shared by execution and manifest inventory.

Environment variables select locations, never trusted hashes. Installation
receipts supply paths only; immutable hashes come from the tracked bootstrap spec.
"""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'tools/bootstrap'
PREFIX = ROOT.parents[1] / '.toolchains'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def spec():
    return json.loads((BOOTSTRAP/'toolchain-receipts.json').read_text(encoding='utf-8'))


def installation():
    path = Path(os.environ.get('BENCH_TOOLCHAIN_RECEIPT', PREFIX/'toolchain-receipt.json'))
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ValueError('Pinned toolchain missing; run tools/bootstrap_offline.py and source its env.sh') from exc


def trusted_tool(name):
    if name not in ('bun', 'opencode', 'node', 'dsh'):
        raise ValueError('Unknown trusted tool: '+str(name))
    anchor = spec()
    env = 'BENCH_'+name.upper()+'_BIN'
    installed = None
    candidate = os.environ.get(env)
    if not candidate:
        installed = installation()
        candidate = installed['tools'][name]['path']
    path = Path(candidate).expanduser().resolve()
    expected = (anchor['dsh']['binary_sha256'] if name == 'dsh' else anchor['artifacts'][name]['binary_sha256'])
    if not path.is_file() or sha256(path) != expected:
        raise ValueError('Pinned '+name+' binary SHA256 mismatch or missing; rerun verified bootstrap')
    if name in ('node', 'dsh'):
        from bootstrap_offline import tree_digest
        if name == 'node':
            root = path.parent.parent
            expected_tree = anchor['artifacts']['node']['tree_sha256']
        else:
            if installed is None:
                installed = installation()
            modules = Path(os.environ.get('BENCH_DSH_MODULE_ROOT', installed['tools']['dsh']['module_root'])).resolve()
            root = modules
            expected_tree = anchor['dsh']['tree_sha256']
            launcher = modules/'@deepseek-ai/dsh/lib/bin.js'
            if path != launcher.resolve() or sha256(modules.parent/'package-lock.json') != anchor['dsh']['lock_sha256']:
                raise ValueError('Pinned DSH launcher/module root or lock mismatch')
        # 2026-11-24: hashing the whole DSH tree costs ~25 s and ran on every call (2x per DSH turn),
        # inflating DSH wall time. Verify the full digest once per process; afterwards re-verify cheaply that
        # no file in the tree changed (path, size, mtime_ns) since that verified digest.
        stamp = _tree_stamp(root)
        if _VERIFIED_TREES.get((str(root), expected_tree)) != stamp:
            if tree_digest(root) != expected_tree:
                raise ValueError('Pinned '+name+' installed package tree SHA256 mismatch')
            _VERIFIED_TREES[(str(root), expected_tree)] = stamp
    return path


_VERIFIED_TREES = {}


def _tree_stamp(root):
    """Cheap change detector for a tree whose full SHA256 digest was already verified in this process."""
    entries = []
    for current, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            item = os.path.join(current, name)
            st = os.lstat(item)
            entries.append((item, st.st_size, st.st_mtime_ns, st.st_mode))
    return hashlib.sha256(repr(entries).encode()).hexdigest()


def trusted_dsh_modules():
    launcher = trusted_tool('dsh')
    return launcher.parents[3]


def resolve_runtime(config):
    """Resolve explicit local vendored runtime without rewriting historical config."""
    value = config.get('opentrading_runtime_root')
    if not value:
        raise ValueError('Explicit trusted OpenTrading experiment runtime root required')
    path = Path(value)
    path = (ROOT/path).resolve() if not path.is_absolute() else path.resolve()
    expected_path = (ROOT/'experiments/opentrading-runtime').resolve()
    if path != expected_path or not path.is_dir():
        raise ValueError('OpenTrading runtime must be this study vendored runtime; use the portable v4.7 config')
    return path


def trusted_runtime(config):
    root = resolve_runtime(config)
    receipt = json.loads((BOOTSTRAP/'runtime-source.json').read_text(encoding='utf-8'))
    commit = (ROOT/'experiments/opentrading-runtime.SHA').read_text(encoding='utf-8').strip()
    if commit != receipt['commit'] or config.get('opentrading_runtime_commit', commit) != commit:
        raise ValueError('Pinned OpenTrading commit receipt mismatch')
    paths = set()
    for directory in ('src', 'prompts', 'market', 'patches'):
        paths.update(p for p in (root/directory).rglob('*') if p.is_file())
    for name in ('package.json', 'bun.lock', 'bunfig.toml', 'tsconfig.json'):
        if (root/name).is_file(): paths.add(root/name)
    actual = {str(p.relative_to(root)):sha256(p) for p in sorted(paths)}
    if actual != receipt['files']:
        raise ValueError('Pinned OpenTrading source/dependency receipt mismatch')
    return root
