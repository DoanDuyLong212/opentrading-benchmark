#!/usr/bin/env python3
"""Install receipt-pinned Linux development tools; never contacts a model provider.

Network setup is explicit. --offline uses only a previously populated cache.
The tracked manifest, not the mutable installation receipt, anchors trust.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
DATA = HERE / 'bootstrap'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tree_digest(root):
    """Hash every file and link, relative to root; directory mtimes are irrelevant."""
    root = Path(root)
    entries = []
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('toolchain symlink escapes tree: ' + name)
            entries.append({'path': name, 'symlink': os.readlink(path)})
        elif path.is_file():
            entries.append({'path': name, 'sha256': sha256(path)})
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def specification():
    return json.loads((DATA / 'toolchain-receipts.json').read_text())


def verify_installation(prefix):
    """Validate installed bytes against tracked anchors, ignoring receipt assertions."""
    prefix = Path(prefix).resolve()
    spec = specification()
    tools = {}
    for name in ('bun', 'opencode', 'node'):
        root = prefix / name
        path = root / 'bin' / name
        expected = spec['artifacts'][name]
        if sha256(path) != expected['binary_sha256']:
            raise ValueError(name + ' binary differs from trusted distribution')
        if expected.get('tree_sha256') and tree_digest(root) != expected['tree_sha256']:
            raise ValueError(name + ' tree differs from trusted distribution')
        tools[name] = {'path': str(path), 'root': str(root), 'sha256': expected['binary_sha256']}
        if expected.get('tree_sha256'):
            tools[name]['tree_sha256'] = expected['tree_sha256']
    dsh_root = prefix / 'dsh'
    if sha256(dsh_root / 'package-lock.json') != spec['dsh']['lock_sha256']:
        raise ValueError('DSH lock differs from tracked dependency closure')
    if tree_digest(dsh_root / 'node_modules') != spec['dsh']['tree_sha256']:
        raise ValueError('DSH installed dependency tree differs from trusted closure')
    if sha256(dsh_root / 'node_modules/@deepseek-ai/dsh/lib/bin.js') != spec['dsh']['binary_sha256']:
        raise ValueError('DSH launcher differs from trusted distribution')
    tools['dsh'] = {'path': str(dsh_root / 'node_modules/.bin/dsh'),
                    'module_root': str(dsh_root / 'node_modules'), 'root': str(dsh_root),
                    'tree_sha256': spec['dsh']['tree_sha256'],
                    'sha256': spec['dsh']['binary_sha256'],
                    'lock_sha256': spec['dsh']['lock_sha256']}
    return tools


def obtain(cache, name, url, expected, offline):
    path = cache / name
    if not path.exists():
        if offline:
            raise ValueError('offline cache missing: ' + name)
        temporary = path.with_suffix(path.suffix + '.partial')
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as stream:
            shutil.copyfileobj(response, stream)
        if sha256(temporary) != expected:
            temporary.unlink()
            raise ValueError('download checksum mismatch: ' + name)
        temporary.replace(path)
    if sha256(path) != expected:
        raise ValueError('cache checksum mismatch: ' + name)
    return path


def install_native(prefix, cache, offline):
    for name, artifact in specification()['artifacts'].items():
        archive = obtain(cache, artifact['archive'], artifact['url'], artifact['archive_sha256'], offline)
        root = prefix / name
        if root.exists():
            raise ValueError('refusing existing tool directory: ' + str(root))
        if name == 'node':
            staging = prefix / '.node-extract'
            staging.mkdir()
            with tarfile.open(archive) as bundle:
                bundle.extractall(staging, filter='data')
            (staging / artifact['member']).rename(root)
            staging.rmdir()
        else:
            if name == 'bun':
                with zipfile.ZipFile(archive) as bundle:
                    binary = bundle.read(artifact['member'])
            else:
                with tarfile.open(archive) as bundle:
                    binary = bundle.extractfile(artifact['member']).read()
            path = root / 'bin' / name
            path.parent.mkdir(parents=True)
            path.write_bytes(binary)
            path.chmod(0o755)
        if sha256(root / 'bin' / name) != artifact['binary_sha256']:
            raise ValueError('extracted binary checksum mismatch: ' + name)
        if artifact.get('tree_sha256') and tree_digest(root) != artifact['tree_sha256']:
            raise ValueError('extracted tree checksum mismatch: ' + name)


def clean_environment(prefix):
    home = prefix / '.home'
    home.mkdir(exist_ok=True)
    for name in ('npm-user.conf', 'npm-global.conf'):
        (home / name).touch()
    return {'HOME': str(home), 'XDG_CONFIG_HOME': str(home / 'config'),
            'XDG_CACHE_HOME': str(home / 'cache'), 'LANG': 'C.UTF-8',
            'PATH': str(prefix / 'node/bin') + ':' + str(prefix / 'bun/bin') + ':/usr/bin:/bin',
            'PYTHONNOUSERSITE': '1', 'PIP_CONFIG_FILE': os.devnull,
            'NPM_CONFIG_USERCONFIG': str(home / 'npm-user.conf'),
            'NPM_CONFIG_GLOBALCONFIG': str(home / 'npm-global.conf')}


def run(command, *, env, cwd=None):
    subprocess.run([str(x) for x in command], env=env, cwd=cwd, check=True)


def install_python(prefix, cache, python, offline, env):
    version = subprocess.check_output([python, '-I', '-c', 'import sys;print("%d.%d.%d"%sys.version_info[:3])'], env=env, text=True).strip()
    if version != specification()['python']:
        raise ValueError('bootstrap requires supplied CPython ' + specification()['python'])
    wheels = cache / 'wheels'
    wheels.mkdir(exist_ok=True)
    artifacts = json.loads((DATA / 'python-artifacts.json').read_text())['artifacts']
    for artifact in artifacts:
        obtain(wheels, artifact['filename'], artifact['url'], artifact['sha256'], offline)
    venv = prefix / 'venv'
    run([python, '-I', '-m', 'venv', '--without-pip', venv], env=env)
    executable = venv / 'bin/python'
    pip_wheel = next(wheels.glob('pip-26.3-*.whl'))
    # The verified pip wheel bootstraps a venv even on hosts without ensurepip.
    bootstrap = 'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_module("pip",run_name="__main__")'
    run([executable, '-I', '-c', bootstrap, pip_wheel, 'install', '--no-index', '--find-links', wheels,
         '--require-hashes', '-r', DATA / 'requirements-bootstrap.lock'], env=env)
    run([executable, '-I', '-m', 'pip', 'install', '--no-index', '--find-links', wheels,
         '--require-hashes', '-r', DATA / 'requirements-offline.lock'], env=env)
    run([executable, '-I', '-m', 'pip', 'check'], env=env)
    return {'path': str(executable), 'host_interpreter': str(Path(python).resolve()),
            'version': subprocess.check_output([executable, '-I', '--version'], env=env, text=True).strip(),
            'requirements_sha256': sha256(DATA / 'requirements-offline.lock')}


def install_dsh(prefix, cache, offline, env):
    if sha256(DATA / 'dsh/package-lock.json') != specification()['dsh']['lock_sha256']:
        raise ValueError('tracked DSH lock differs from approved manifest')
    root = prefix / 'dsh'
    root.mkdir()
    for name in ('package.json', 'package-lock.json'):
        shutil.copyfile(DATA / 'dsh' / name, root / name)
    command = [prefix / 'node/bin/node', prefix / 'node/lib/node_modules/npm/bin/npm-cli.js',
               'ci', '--ignore-scripts', '--no-audit', '--no-fund', '--cache', cache / 'npm']
    if offline:
        command.append('--offline')
    run(command, env=env, cwd=root)


def install_runtime_dependencies(prefix, cache, env, offline):
    study = HERE.parent
    roots = [study / 'experiments/opentrading-runtime',
             study.parent / 'finance-v46-update-study/experiments/opentrading-runtime']
    receipts = []
    for root in roots:
        if not root.is_dir():
            raise ValueError('runtime root missing: ' + str(root))
        tracked = [root / 'package.json', root / 'bun.lock'] + sorted((root / 'patches').glob('*'))
        before = {str(p.relative_to(root)): sha256(p) for p in tracked if p.is_file()}
        command = [prefix / 'bun/bin/bun', 'install', '--frozen-lockfile', '--cache-dir', cache / 'bun']
        if offline:
            command.append('--offline')
        run(command, env=env, cwd=root)
        if any(sha256(root / p) != digest for p, digest in before.items()):
            raise ValueError('runtime install changed frozen inputs: ' + str(root))
        receipts.append({'root': str(root), 'frozen_inputs': before})
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--skip-python', action='store_true')
    parser.add_argument('--skip-runtime-deps', action='store_true')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    prefix, cache = args.prefix.resolve(), args.cache.resolve()
    if platform.system() != 'Linux' or platform.machine() != 'x86_64' or platform.libc_ver()[0] != 'glibc':
        parser.error('only Linux x86_64 glibc platform receipts are available')
    if args.verify_only:
        print(json.dumps(verify_installation(prefix), indent=2))
        return
    if prefix.exists() and any(prefix.iterdir()):
        parser.error('prefix must be empty; verify existing installs with --verify-only')
    prefix.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    env = clean_environment(prefix)
    install_native(prefix, cache, args.offline)
    python = None if args.skip_python else install_python(prefix, cache, args.python, args.offline, env)
    install_dsh(prefix, cache, args.offline, env)
    tools = verify_installation(prefix)
    runtime = [] if args.skip_runtime_deps else install_runtime_dependencies(prefix, cache, env, args.offline)
    receipt = {'schema': 1, 'platform': specification()['platform'], 'tools': tools,
               'python': python, 'runtime_dependencies': runtime,
               'trusted_manifest_sha256': sha256(DATA / 'toolchain-receipts.json')}
    receipt_path = prefix / 'toolchain-receipt.json'
    receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')
    exports = {'BENCH_BUN_BIN': tools['bun']['path'], 'BENCH_OPENCODE_BIN': tools['opencode']['path'],
               'BENCH_NODE_BIN': tools['node']['path'], 'BENCH_DSH_BIN': tools['dsh']['path'],
               'BENCH_DSH_MODULE_ROOT': tools['dsh']['module_root'], 'BENCH_TOOLCHAIN_RECEIPT': str(receipt_path)}
    if python:
        exports['BENCH_PYTHON_BIN'] = python['path']
    (prefix / 'env.sh').write_text(''.join('export ' + key + '=' + shlex.quote(value) + '\n' for key, value in exports.items()))
    print('Verified toolchain installed: ' + str(receipt_path))


if __name__ == '__main__':
    main()
