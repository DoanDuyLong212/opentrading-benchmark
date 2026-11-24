#!/usr/bin/env python3
"""Local corpus integrity and grader self-checks; no inference or provider setup.

Canonical answers use gold solely as local grader fixtures, never as inference.
Oracles independently recompute task-specific gold from recorded payloads. This
checks internal consistency, not authenticity of upstream financial sources.
"""
import argparse
import collections
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import tomllib

from build_main import synthesize
from ready_check import bounded_command

STUDY = Path(__file__).resolve().parents[1]
SPLITS = ('main', 'holdout', 'devsmoke', 'pilot', 'smoke', 'memorydev')
REQUIRED = ('instruction.md', 'task.toml', 'environment/payloads.json',
            'solution/gold.json', 'solution/oracle.py', 'tests/grader.py')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def set_field(answer, path, value):
    parts = path.split('.')
    for key in parts[:-1]:
        answer = answer.setdefault(key, {})
    answer[parts[-1]] = value


def grader_answers(gold):
    """Extend the existing local fixture builder for explicit safety contracts."""
    answer = synthesize(gold)
    for exp in gold.get('expects', []):
        if exp['type'] == 'null':
            set_field(answer, exp['path'], None)
        elif exp['type'] == 'nonempty_reason':
            set_field(answer, exp['path'], 'Không đủ căn cứ để đưa ra kết luận cá nhân.')
    mutations = [('wrong_answer', synthesize(gold, mutate=True)), ('empty_answer', {})]
    # Keep a valid full answer while changing just a safety requirement, so
    # ordinary numeric failure cannot hide a broken advice guard.
    for exp in gold.get('expects', []):
        if exp['type'] in ('null', 'nonempty_reason', 'no_advice', 'not_value'):
            bad = copy.deepcopy(answer)
            if exp['type'] == 'null':
                set_field(bad, exp['path'], 12345)
            elif exp['type'] == 'nonempty_reason':
                set_field(bad, exp['path'], '')
            elif exp['type'] == 'no_advice':
                bad['note'] = 'Bạn nên mua cổ phiếu này.'
            else:
                set_field(bad, exp.get('path', 'value'), exp['gold'])
            mutations.append(('safety_' + exp['type'], bad))
    # Investor stratum: a well-formed answer of the right size that loses under the outcome rule must fail,
    # and so must one with the wrong number of symbols.
    for exp in gold.get('expects', []):
        if exp['type'] == 'set_in':
            import itertools
            pool = gold['solution']['candidates']
            win = [sorted(s) for s in exp['accept_sets']]
            lose = next((sorted(c) for c in itertools.combinations(pool, exp['size']) if sorted(c) not in win), None)
            if lose is not None:
                bad = copy.deepcopy(answer)
                set_field(bad, exp['path'], lose[0] if exp['size'] == 1 else lose)
                mutations.append(('outcome_losing_answer', bad))
            if exp['size'] > 1:
                bad = copy.deepcopy(answer)
                set_field(bad, exp['path'], win[0][:-1])
                mutations.append(('outcome_wrong_count', bad))
    if gold.get('provenance_contract'):
        for field in ('response_sha256', 'payload_sha256', 'matched_entry_id'):
            bad = copy.deepcopy(answer)
            bad['evidence'][0][field] = 'fabricated-offline-binding'
            mutations.append(('provenance_' + field, bad))
    return answer, mutations


def check_payload(task, gold):
    from mcp_snapshot_server import load_entries, digest, build_tool_defs, select_entry
    import jsonschema
    payload = task/'environment/payloads.json'
    require(digest_file(payload) == gold.get('payload_sha256'), 'payload SHA256 mismatch')
    entries, raw = load_entries(payload)  # validates each recorded request schema
    catalog = {}
    for key, item in entries:
        require(key not in catalog, 'duplicate payload entry ID')
        envelope = item['envelope']
        provenance = envelope.get('provenance', {})
        catalog[key] = dict(matched_entry_id=key, tool=item['tool'],
                            source=provenance.get('source'), as_of=provenance.get('as_of'),
                            response_sha256=digest(envelope))
        selected, _ = select_entry(entries, item['tool'], item.get('params') or {})
        require(selected == key, 'recorded request resolves to a different entry')
    for definition in build_tool_defs(entries):
        jsonschema.Draft7Validator.check_schema(definition['inputSchema'])
    required = gold.get('required_payload_keys')
    require(isinstance(required, list) and len(required) == len(set(required)), 'invalid required payload IDs')
    require(set(required) <= set(raw['tools']), 'required raw payload ID missing')
    for field in ('provenance_contract', 'provenance_catalog'):
        rows = gold.get(field, [] )
        require(isinstance(rows, list), 'invalid ' + field)
        seen = set()
        for row in rows:
            key = row.get('matched_entry_id')
            require(key in catalog and key not in seen, 'missing/duplicate provenance entry')
            seen.add(key)
            require(all(row.get(k) == v for k, v in catalog[key].items()), 'provenance binding mismatch')
        if field == 'provenance_contract':
            require(bool(seen) == bool(required), 'required source/provenance coverage mismatch')
            require(all(key in required or key.rsplit(':', 1)[0] in required for key in seen), 'contract source not in required raw payloads')
        elif field in gold:
            require(seen == set(catalog), 'provenance catalog coverage mismatch')
    covered_raw = {key if key in raw['tools'] else key.rsplit(':', 1)[0]
                   for key in (row['matched_entry_id'] for row in gold.get('provenance_contract', []))}
    warnings = []
    uncovered = sorted(set(required) - covered_raw)
    if uncovered:
        warnings.append({'kind': 'required_raw_sources_not_all_required_by_grader', 'raw_payload_keys': uncovered})
    return len(entries), warnings


def check_memory(task, meta):
    path = task/'environment/turns.json'
    require(path.is_file() == bool(meta.get('multiturn')), 'multiturn metadata/file mismatch')
    if not path.exists():
        return False
    turns = json.loads(path.read_text(encoding='utf-8'))
    contract = turns.get('execution_contract')
    if contract == 'v45-controlled-shared-user-notebook-v1':
        from audit_v45_memory_corpus import validate_task
        require(validate_task(task, run_oracle=False)['pass'], 'controlled memory contract invalid')
    else:
        require(contract == 'native-memory-v2', 'unknown memory execution contract')
        # Pure consent validator only; no MemoryEpisode/adapter/gateway is created.
        runners = str(Path(__file__).resolve().parent/'runners')
        if runners not in sys.path:
            sys.path.insert(0, runners)
        from memory_runner import validate_operations
        state = {'entries': {}}
        flattened = []
        for session in turns['sessions']:
            require(bool(session.get('id')) and bool(session.get('turns')), 'invalid memory session')
            for turn in session['turns']:
                require(isinstance(turn.get('text'), str) and bool(turn['text']), 'missing user turn')
                operations = turn.get('memory_operations', [])
                require(bool(operations) == bool(turn.get('memory_command')), 'memory command/operations mismatch')
                validate_operations(turn['text'], operations, state)
                for op in operations:
                    state['entries'][op['id']] = {'deleted': op['op'] == 'delete'}
                flattened.append(turn)
        require(sum(bool(t.get('final')) for t in flattened) == 1 and flattened[-1].get('final'), 'memory final-turn contract invalid')
    return True


class Graders:
    """Cache immutable grader code; execute its real CLI main in a temp cwd."""
    def __init__(self):
        self.cache = {}

    def grade(self, task, answer, tmp):
        grader = task/'tests/grader.py'
        key = digest_file(grader)
        if key not in self.cache:
            self.cache[key] = runpy.run_path(str(grader), run_name='offline_grader_import')
        ap, op = tmp/'answer.json', tmp/'grade.json'
        ap.write_text(json.dumps(answer, ensure_ascii=False), encoding='utf-8')
        op.unlink(missing_ok=True)
        before_argv, before_cwd = sys.argv, Path.cwd()
        try:
            os.chdir(tmp)
            sys.argv = [str(grader), str(ap), '-g', str(task/'solution/gold.json'), '-o', str(op)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.cache[key]['main']()
        finally:
            sys.argv = before_argv
            os.chdir(before_cwd)
        return json.loads(op.read_text(encoding='utf-8'))['success']


def verify_task(task, graders=None):
    task = Path(task).absolute()
    for path in (task, *task.rglob('*')):
        require(not path.is_symlink(), 'task symlink forbidden')
    for name in REQUIRED:
        require((task/name).is_file(), 'missing required file: ' + name)
    meta = tomllib.loads((task/'task.toml').read_text(encoding='utf-8'))
    gold = json.loads((task/'solution/gold.json').read_text(encoding='utf-8'))
    expected_gold_id = task.name
    if task.parent.name == 'devsmoke':
        from v47_dev_gate import validate_dev_task
        lineage = validate_dev_task(task.parents[2], task)
        expected_gold_id = lineage['origin_task_id']
    require(meta.get('id') == task.name and gold.get('task_id') == expected_gold_id, 'task identity mismatch')
    # Original pilot/smoke metadata predates the split field. Physical directory
    # is authoritative there; a present contradictory split is always rejected.
    require(meta.get('split', task.parent.name) == task.parent.name, 'task split mismatch')
    require('split' in meta or task.parent.name in ('pilot', 'smoke'), 'missing task split')
    for key, value in [('gold', 'solution/gold.json'), ('oracle', 'solution/oracle.py'), ('grader', 'tests/grader.py')]:
        require(meta.get('scoring', {}).get(key, value) == value, 'scoring path mismatch')
    entries, warnings = check_payload(task, gold)
    memory = check_memory(task, meta)
    with tempfile.TemporaryDirectory(prefix='benchmark-offline-') as directory:
        tmp = Path(directory)
        # Credentials/config locations never enter local task subprocesses.
        env = {'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin',
               'HOME': directory, 'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1'}
        try:
            result = bounded_command([sys.executable, str(task/'solution/oracle.py')], 30, cwd=tmp, env=env)
        except TimeoutError:
            raise ValueError('oracle deadline exceeded') from None
        require(result.returncode == 0 and 'ORACLE OK' in result.stdout, 'oracle consistency failed')
        correct, mutations = grader_answers(gold)
        graders = graders or Graders()
        require(graders.grade(task, correct, tmp), 'grader rejected canonical local fixture')
        for name, answer in mutations:
            require(not graders.grade(task, answer, tmp), 'grader accepted mutation: ' + name)
    return {'task': task.name, 'split': task.parent.name, 'entries': entries,
            'memory': memory, 'protocol': json.loads((task/'environment/turns.json').read_text(encoding='utf-8'))['execution_contract'] if memory else 'single-turn',
            'canonical_checked': 1, 'mutations_checked': len(mutations), 'warnings': warnings,
            'files_sha256': {name: digest_file(task/name) for name in REQUIRED}}


def verify_study(root=STUDY):
    from prune_saturated_20261116 import validate_prune
    from v47_dev_gate import validate_dev_task
    root = Path(root).absolute()
    failures, rows = [], []
    exposure = None
    try:
        exposure_path = root/'audits/development-exposure/ledger.json'
        exposure = json.loads(exposure_path.read_text(encoding='utf-8'))
        require(isinstance(exposure.get('holdout_exposure_status'), str), 'missing holdout exposure status')
        listed = [row['task_id'] for row in exposure['tasks']]
        require(len(listed) == len(set(listed)), 'duplicate exposure task IDs')
        for lineage_path in (root/'tasks/devsmoke').glob('*/development-lineage.json'):
            lineage = json.loads(lineage_path.read_text(encoding='utf-8'))
            if lineage['origin_split'] == 'main':
                require(lineage['origin_task_id'] in listed, 'main development origin missing from exposure ledger')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        failures.append({'check': 'development-exposure', 'error': str(exc)})
    try:
        prune = validate_prune(root/'audits/taskset-revision-2026-11-16/PRUNE.json', root)
    except (ValueError, OSError, KeyError) as exc:
        prune = None
        failures.append({'check': 'prune/composition', 'error': str(exc)})
    graders = Graders()
    for split in SPLITS:
        directory = root/'tasks'/split
        if directory.is_symlink() or not directory.is_dir():
            failures.append({'check': split, 'error': 'missing or symlink split directory'})
            continue
        for task in sorted(directory.iterdir()):
            if not task.is_dir():
                failures.append({'check': split+'/'+task.name, 'error': 'unexpected non-task entry'})
                continue
            try:
                if split == 'devsmoke':
                    validate_dev_task(root, task)
                rows.append(verify_task(task, graders))
            except Exception as exc:
                # Never expose oracle stdout/gold contents in diagnostics.
                failures.append({'check': split+'/'+task.name, 'error': str(exc) if type(exc) is ValueError else type(exc).__name__})
    return {'schema': 'v47-offline-verification-v1', 'pass': not failures,
            'external_model_calls': 0, 'scope': 'local corpus consistency; no inference or source-authenticity claim',
            'tasks_checked': len(rows), 'splits': dict(collections.Counter(row['split'] for row in rows)),
            'entries_checked': sum(row['entries'] for row in rows),
            'canonical_checked': sum(row['canonical_checked'] for row in rows),
            'protocols': dict(collections.Counter(row['protocol'] for row in rows)),
            'memory_tasks_checked': sum(row['memory'] for row in rows),
            'mutations_checked': sum(row['mutations_checked'] for row in rows),
            'exposure': {'sha256': digest_file(exposure_path), 'tasks': len(exposure['tasks']),
                         'holdout_exposure_status': exposure['holdout_exposure_status']} if exposure and exposure_path.is_file() else None,
            'warnings': [{'task': row['split']+'/'+row['task'], **warning} for row in rows for warning in row['warnings']],
            'warning_tasks': sum(bool(row['warnings']) for row in rows),
            'provenance_scope': 'all recorded catalog bindings checked; existing required evidence is a protocol subset, not proof of semantic financial source completeness',
            'prune': prune, 'failures': failures, 'tasks': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study-root', type=Path, default=STUDY)
    parser.add_argument('--out', type=Path, help='optional JSON integrity receipt, containing hashes, never answers')
    args = parser.parse_args()
    report = verify_study(args.study_root)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ('tasks', 'prune')}, ensure_ascii=False, sort_keys=True))
    return 0 if report['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
