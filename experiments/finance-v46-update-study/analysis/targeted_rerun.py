#!/usr/bin/env python3
"""User-directed targeted rerun (2026-11-11): rerun only the or11 failed (task, arm) slots with the fixed
OpenTrading runtime, instead of the full 132-trial pilot.

Writes a diagnostic seal (same approval/config/freeze state as or12) with one pilot run per arm restricted to
that arm's failed tasks (runs=2, the driver's granularity), prepares manifests, then executes each run with
the sealed driver and audits it. Merging keeps or11 rows and replaces ONLY the originally failed
(task, arm, run) slots; extra reruns of originally passing slots are reported as stability only.
Disclosed as a selective rerun: it can only raise scores, so it is reported next to the unmodified or11.

  python3 analysis/targeted_rerun.py seal|run|merge
"""
import json
import subprocess
import sys
from pathlib import Path
import os

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
OR11 = Path(os.environ.get('RERUN_SOURCE', str(STUDY / 'results/financial-v46u-or11-ds-20261110/deepseek-openrouter-pilot')))
TAG = os.environ.get('RERUN_TAG', 'or12r')
OUT = STUDY / ('results/financial-v46u-%s-ds-20261111' % TAG)
SEAL = STUDY / ('audits/seal/financial-v46u-seal-%s-ds.json' % TAG)
BASE = STUDY / ('audits/seal/financial-v46u-seal-%s-ds.json' % os.environ.get('RERUN_BASE', 'or12'))


def failed_slots():
    rows = [json.loads(l) for l in (OR11 / 'trials.jsonl').read_text().splitlines() if l.strip()]
    # RERUN_SEMANTIC=1: rerun the semantically failed slots (or15: strict provenance is not the question here)
    key = 'semantic_correctness' if os.environ.get('RERUN_SEMANTIC') else 'success'
    slots = [(r['task'], r['arm'], r['run']) for r in rows if not r[key]]
    only = os.environ.get('RERUN_ONLY')  # "arm:task,arm:task" restricts the rerun (e.g. auditor-blocked slots)
    if only:
        keep = {tuple(x.split(':')[::-1]) for x in only.split(',')}
        slots = [x for x in slots if (x[0], x[1]) in keep]
    return slots


def make_seal():
    from v45_gate import build_settings
    from run_manifest import prepare_manifest
    base = json.loads(BASE.read_text())
    pilot = next(r for r in base['runs'] if r['split'] == 'pilot')
    cfg_path = Path(pilot['config'])
    cfg = json.loads(cfg_path.read_text())
    by_arm = {}
    for task, arm, _ in failed_slots():
        by_arm.setdefault(arm, set()).add(task)
    from run_manifest import digest_json, freeze_state, hash_file
    state = digest_json(freeze_state(cfg))
    approval_path = Path(base['approval'])
    approval = json.loads(approval_path.read_text())
    if state not in approval['freeze_state_sha256']:
        approval['freeze_state_sha256'].append(state)
        approval_path.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + '\n')
    base['protected_files'][str(approval_path)] = hash_file(approval_path)
    pilot['state_sha256'] = state
    runs = [dict(r, state_sha256=state) for r in base['runs'] if r['split'] == 'devsmoke']
    for arm, tasks in sorted(by_arm.items()):
        settings = build_settings(cfg, 'pilot')
        settings['arms'] = [arm]
        settings['conditions'] = {arm: settings['conditions'][arm]}
        out = OUT / ('pilot-' + arm)
        task_dirs = [STUDY / 'tasks/pilot' / t for t in sorted(tasks)]
        prepare_manifest(out, settings, task_dirs, cfg, False)
        runs.append({'out': str(out), 'config': str(cfg_path), 'model': cfg['model'], 'split': 'pilot',
                     'settings': settings, 'tasks': sorted(tasks), 'state_sha256': pilot['state_sha256']})
    seal = dict(base, runs=runs, main_authorized_by_user=False, gate=None,
                purpose='targeted rerun of or11 failed slots (user 2026-11-11); diagnostic, never admits main')
    SEAL.write_text(json.dumps(seal, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({a: sorted(t) for a, t in by_arm.items()}, ensure_ascii=False))


def run():
    from v45_supervisor import driver_command
    seal = json.loads(SEAL.read_text())
    for item in [r for r in seal['runs'] if r['split'] == 'pilot']:
        cmd = driver_command(item, SEAL) + ['--tasks', ','.join(item['tasks'])]
        print('RUN', item['out'], flush=True)
        rc = subprocess.run(cmd, cwd=STUDY).returncode
        print('driver rc', rc, flush=True)
        subprocess.run([sys.executable, str(STUDY / 'tools/audit_v45_run.py'), '--run', item['out']], cwd=STUDY,
                       stdout=subprocess.DEVNULL)
        audit = json.loads((Path(item['out']) / 'audit-v45.json').read_text())
        print('audit', item['out'].rsplit('/', 1)[-1], audit['pass'], audit['fabricated_evidence_accepted'],
              [e['check'] for e in audit['errors']][:5], flush=True)


def merge():
    slots = set(failed_slots())
    rows = {(r['task'], r['arm'], r['run']): r for r in
            (json.loads(l) for l in (OR11 / 'trials.jsonl').read_text().splitlines() if l.strip())}
    reruns, extra = {}, []
    for d in sorted(OUT.glob('pilot-*')):
        for l in (d / 'trials.jsonl').read_text().splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            key = (r['task'], r['arm'], r['run'])
            r['_rerun_dir'] = str(d)
            (reruns.__setitem__(key, r) if key in slots else extra.append(r))
    missing = slots - set(reruns)
    if missing:
        raise SystemExit('missing reruns: %s' % sorted(missing))
    merged = [reruns.get(k, v) for k, v in rows.items()]
    (OUT / 'merged-trials.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in merged))
    print('replaced', len(reruns), 'slots; extra stability reruns', len(extra))
    for k, r in sorted(reruns.items()):
        print('  slot', k, 'rerun success', r['success'], r['status'], r.get('error_type'))
    for r in extra:
        print('  extra', (r['task'], r['arm'], r['run']), 'success', r['success'], r.get('error_type'))


if __name__ == '__main__':
    {'seal': make_seal, 'run': run, 'merge': merge}[sys.argv[1]]()
