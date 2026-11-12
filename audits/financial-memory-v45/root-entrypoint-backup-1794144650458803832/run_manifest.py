"""Immutable v2 run plans, content fingerprints and the once-only holdout gate."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import tomllib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 3


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest_json(value):
    return digest_bytes(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode())


def hash_file(path):
    return digest_bytes(Path(path).read_bytes())


def code_fingerprint():
    return {str(p.relative_to(ROOT)): hash_file(p) for p in sorted((ROOT / 'tools').rglob('*'))
            if p.is_file() and p.suffix in ('.py', '.ts', '.json', '.md') and '__pycache__' not in p.parts
            and 'tests' not in p.parts}


def task_fingerprint(task):
    task = Path(task)
    return {str(p.relative_to(task)): hash_file(p) for p in sorted(task.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.json', '.py', '.md', '.toml')}


def protocol_fingerprint(config):
    reference = config.get('experiment_protocol')
    if not reference:
        return None
    path = (ROOT/reference).resolve()
    if not path.is_relative_to(ROOT/'plans') or not path.is_file():
        raise ValueError('Experiment protocol must be an existing workspace plan')
    return {'path': str(path.relative_to(ROOT)), 'sha256': hash_file(path)}


def installed_package_fingerprint(package):
    """Pin shipped runtime/config files without recursively hashing node_modules."""
    package = Path(package)
    files = {}
    for directory, names, filenames in os.walk(package):
        names[:] = sorted(n for n in names if n not in ('node_modules', '.git', 'types'))
        for name in sorted(filenames):
            path = Path(directory)/name
            if path.suffix in ('.js', '.mjs', '.cjs', '.json', '.yml', '.yaml'):
                files[str(path.relative_to(package))] = hash_file(path)
    manifest = package/'package.json'
    metadata = json.loads(manifest.read_text()) if manifest.exists() else {}
    return {'version': metadata.get('version'), 'files_sha256': digest_json(files), 'n_files': len(files)}


def harness_inventory(config=None):
    if config is None:
        config = json.loads((ROOT/'tools/bench_config.json').read_text())
    from experiment_conditions import RUNTIME_ROOT
    locator = config.get('opentrading_runtime_root')
    if not locator or Path(locator).resolve() != RUNTIME_ROOT.resolve() or not RUNTIME_ROOT.is_dir():
        raise ValueError('Explicit trusted OpenTrading experiment runtime root required')
    commands = {'opencode': ['opencode', '--version'], 'dsh': [str(Path.home()/'.local/bin/dsh'), '--version'],
                'bun': [str(Path.home()/'.bun/bin/bun'), '--version']}
    found = {}
    for name, command in commands.items():
        binary = shutil.which(command[0])
        item = {'binary': binary, 'sha256': None, 'version': None}
        if binary:
            item['sha256'] = hash_file(Path(binary).resolve())
            try:
                with tempfile.TemporaryDirectory(prefix='bench-version-') as temp:
                    env = dict(os.environ, HOME=temp, XDG_CONFIG_HOME=temp+'/config',
                               XDG_DATA_HOME=temp+'/data', XDG_CACHE_HOME=temp+'/cache', XDG_STATE_HOME=temp+'/state')
                    result = subprocess.run(command, capture_output=True, text=True, timeout=10, env=env)
                item['version'] = result.stdout.strip() if result.returncode == 0 else None
            except (OSError, subprocess.TimeoutExpired):
                pass
        found[name] = item
        if name == 'dsh' and binary:
            package = Path(binary).resolve().parent.parent
            modules = package/'node_modules'
            selected = [package]
            for scope in ('@deepseek-ai', '@earendil-works', '@modelcontextprotocol'):
                selected.extend(p for p in (modules/scope).glob('*') if (p/'package.json').exists())
            selected.extend(modules/name for name in ('openai',) if (modules/name/'package.json').exists())
            item['runtime_packages'] = {str(p.relative_to(package)) if p != package else '.':
                                        installed_package_fingerprint(p) for p in sorted(selected)}
    repo = RUNTIME_ROOT
    source = {str(p.relative_to(repo)): hash_file(p) for p in sorted((repo/'src').rglob('*'))
              if p.is_file() and p.suffix in ('.ts', '.json')}
    found['opentrading'] = {'source_sha256': digest_json(source), 'runtime_root': str(repo.resolve()),
                           'prompt_files': {str(p.relative_to(repo)): hash_file(p) for p in sorted((repo/'prompts').glob('*.md'))},
                           'calendar_sha256': hash_file(repo/'market/calendar.json'),
                           'dependency_files': {name: hash_file(repo/name) for name in
                               ('package.json', 'bun.lock', 'bun.lockb') if (repo/name).exists()}}
    modules = repo/'node_modules'
    selected = []
    for scope in ('@ai-sdk', '@modelcontextprotocol'):
        selected.extend(p for p in (modules/scope).glob('*') if (p/'package.json').exists())
    selected.extend(modules/name for name in ('ai', 'zod') if (modules/name/'package.json').exists())
    found['opentrading']['runtime_packages'] = {str(p.relative_to(modules)): installed_package_fingerprint(p) for p in sorted(selected)}
    return found


def task_contract(task):
    task = Path(task)
    gold_path, payload_path = task/'solution'/'gold.json', task/'environment'/'payloads.json'
    gold = json.loads(gold_path.read_text()) if gold_path.exists() else {}
    payload = json.loads(payload_path.read_text()) if payload_path.exists() else {}
    fields = [c['path'] for c in gold.get('expects', [])
              if c.get('type') in ('value', 'set', 'list_order', 'verdict')
              and c.get('gold', c.get('accept')) not in (None, [])]
    partial = any((v.get('envelope') or v).get('availability') not in (None, 'available')
                  for v in payload.get('tools', {}).values())
    return dict(task_eligibility(task), **{'scoring': gold.get('scoring'), 'answerable_fields': fields, 'partial': partial,
            'payload_family_sha256': hash_file(payload_path) if payload_path.exists() else None})


def task_eligibility(task):
    metadata = tomllib.loads((Path(task)/'task.toml').read_text())
    eligible = metadata.get('confirmatory_eligible', True)
    reason = metadata.get('exclusion_reason')
    if not isinstance(eligible, bool) or (not eligible and (not isinstance(reason, str) or not reason.strip())):
        raise ValueError('Task eligibility requires a boolean and a nonempty exclusion reason: '+str(task))
    return {'confirmatory_eligible': eligible, 'exclusion_reason': reason if not eligible else None}


def build_schedule(tasks, arms, runs, seed):
    """Seeded task order and equally cycled permutations of arm execution order."""
    rng = random.Random(seed)
    task_ids = sorted(Path(t).name for t in tasks)
    rng.shuffle(task_ids)
    # Cyclic Latin blocks guarantee equal position counts whenever task/run
    # blocks are divisible by arm count (44 blocks / 4 pilot conditions).
    permutations = []
    needed = len(task_ids) * runs
    while len(permutations) < needed:
        base = list(arms)
        rng.shuffle(base)
        shifts = list(range(len(base)))
        rng.shuffle(shifts)
        permutations.extend(tuple(base[s:]+base[:s]) for s in shifts)
    schedule = []
    block = 0
    for run in range(1, runs + 1):
        ids = task_ids[run-1:] + task_ids[:run-1]
        for tid in ids:
            for arm in permutations[block]:
                schedule.append({'trial_id': f'{tid}__{arm}__r{run}', 'task': tid, 'arm': arm, 'run': run})
            block += 1
    return schedule


def write_exclusive(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())


def freeze_state(config):
    return {'schema_version': SCHEMA_VERSION, 'config': config, 'code': code_fingerprint(), 'protocol': protocol_fingerprint(config),
            'tasks': {str(p.relative_to(ROOT)): task_fingerprint(p)
                      for p in sorted((ROOT/'tasks').glob('*/*')) if p.is_dir()},
            'harnesses': harness_inventory(config),
            'quarantined_tasks': {str(p.relative_to(ROOT)): task_eligibility(p)['exclusion_reason']
                                  for p in sorted((ROOT/'tasks').glob('*/*')) if p.is_dir()
                                  and not task_eligibility(p)['confirmatory_eligible']},
            'test_code': {str(p.relative_to(ROOT)): hash_file(p) for p in sorted((ROOT/'tools'/'tests').glob('*.py'))}}


def validate_certificate(certificate, config, state):
    if (certificate.get('state_sha256') != digest_json(state) or not certificate.get('offline_passed')
            or not certificate.get('live_parity_passed') or certificate.get('model') != config.get('model')
            or certificate.get('schema_version') != SCHEMA_VERSION):
        raise ValueError('Freeze needs a current offline+three-arm live parity certificate for this exact model/config')
    live = certificate.get('live_run')
    if not isinstance(live, dict) or not live.get('out_dir'):
        raise ValueError('Freeze certificate needs the actual completed live-run artifacts')
    from ready_check import validate_live_run
    if validate_live_run(live['out_dir'], config, config['model']) != live:
        raise ValueError('Freeze certificate live-run artifacts changed')


def create_freeze(path, config, certificate_path):
    state = freeze_state(config)
    certificate = json.loads(Path(certificate_path).read_text())
    validate_certificate(certificate, config, state)
    scope = config.get('evaluation_scope', 'snapshot_grounded_financial_qa')
    if scope != 'snapshot_grounded_financial_qa':
        raise ValueError('Only snapshot-grounded scope is certified; real-world filings accuracy needs a separate source audit')
    receipt = {'created_at': datetime.now(timezone.utc).isoformat(), 'state': state,
               'certificate': certificate, 'freeze_sha256': digest_json(state)}
    write_exclusive(path, receipt)
    return receipt


def validate_freeze(path, config):
    receipt = json.loads(Path(path).read_text())
    state = freeze_state(config)
    certificate = receipt.get('certificate') or {}
    if digest_json(state) != receipt.get('freeze_sha256') or receipt.get('state') != state:
        raise ValueError('Freeze receipt does not match current configuration, tasks, code or harnesses')
    validate_certificate(certificate, config, state)
    return receipt['freeze_sha256']


def open_holdout(out_dir, freeze_sha256, resume=False):
    receipt_path = ROOT/'results'/'holdout-open-v2.json'
    value = {'schema_version': 2, 'out_dir': str(Path(out_dir).resolve()), 'freeze_sha256': freeze_sha256}
    if receipt_path.exists():
        old = json.loads(receipt_path.read_text())
        if not resume or old != value:
            raise ValueError('Holdout was already opened; only exact --resume of its frozen run is allowed')
    else:
        if resume:
            raise ValueError('Cannot resume holdout without original opening receipt')
        write_exclusive(receipt_path, value)


def prepare_manifest(out_dir, settings, tasks, config, resume=False):
    path = Path(out_dir)/'manifest.json'
    comparable = {'schema_version': SCHEMA_VERSION, 'settings': settings, 'config': config, 'protocol': protocol_fingerprint(config),
                  'code': code_fingerprint(), 'harnesses': harness_inventory(config),
                  'tasks': {Path(t).name: task_fingerprint(t) for t in tasks},
                  'task_contracts': {Path(t).name: task_contract(t) for t in tasks},
                  'schedule': build_schedule(tasks, settings['arms'], settings['runs'], settings['seed'])}
    if resume:
        if not path.exists():
            raise ValueError('--resume requires manifest.json')
        manifest = json.loads(path.read_text())
        if manifest.get('fingerprint') != digest_json(comparable) or manifest.get('plan') != comparable:
            raise ValueError('Resume rejected: model, code, tasks, harnesses, schedule or settings changed')
        return manifest
    if path.exists() or (Path(out_dir)/'trials.jsonl').exists():
        raise ValueError('Output already contains a run; use --resume for the exact frozen configuration')
    manifest = {'created_at': datetime.now(timezone.utc).isoformat(), 'plan': comparable,
                'fingerprint': digest_json(comparable)}
    write_exclusive(path, manifest)
    return manifest


def validate_trial_rows(rows, manifest):
    """Bind persisted results to the frozen schedule, including partial runs."""
    plan = manifest['plan']
    if manifest.get('fingerprint') != digest_json(plan):
        raise ValueError('Manifest fingerprint is invalid')
    schedule = plan['schedule']
    expected = {item['trial_id']: item for item in schedule}
    if len(expected) != len(schedule):
        raise ValueError('Frozen schedule has duplicate trial IDs')
    seen = set()
    for row in rows:
        identity = row.get('trial_id')
        if identity in seen or identity not in expected:
            raise ValueError('Duplicate or unscheduled trial ID: '+str(identity))
        seen.add(identity)
        item = expected[identity]
        if (any(row.get(k) != item[k] for k in ('task', 'arm', 'run'))
                or row.get('model') != plan['settings']['model']
                or row.get('manifest_sha256') != manifest['fingerprint']):
            raise ValueError('Trial identity or manifest disagrees with frozen schedule: '+identity)
    return seen == set(expected)


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Freeze all splits/config/code/harness versions before main/holdout')
    ap.add_argument('--output', required=True)
    ap.add_argument('--config', default=str(ROOT/'tools'/'bench_config.json'))
    ap.add_argument('--certificate', required=True, help='ready_check --certificate with passing offline tests and three-arm live parity')
    args = ap.parse_args()
    receipt = create_freeze(args.output, json.loads(Path(args.config).read_text()), args.certificate)
    print('Frozen:', receipt['freeze_sha256'], str(Path(args.output).resolve()))


if __name__ == '__main__':
    main()
