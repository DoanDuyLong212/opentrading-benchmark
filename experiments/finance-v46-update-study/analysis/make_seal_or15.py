#!/usr/bin/env python3
"""Seal or15 (amendment 2026-11-11 d/e/f, user-approved): fresh sealed pilot (36 tasks: 22 core + 8 compute + 6
native memory) and the main manifest (200 tasks), same shape as the or14 seal (devsmoke = audited or7 cohort).
Main still requires the b0 judge-primary pilot gate and pilot-review-approval.json written after the user approves
the pilot report. Supersedes or14 (never run). Writes once; refuses to overwrite.

  python3 analysis/make_seal_or15.py
"""
import hashlib
import json
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from run_manifest import digest_json, freeze_state, hash_file, prepare_manifest, task_eligibility  # noqa: E402
from v45_gate import build_settings, validate_seal  # noqa: E402

CFG = STUDY / 'tools/bench_config_deepseek_openrouter.json'
APPROVAL = STUDY / 'audits/engineering-approval-v46-update.json'
BASE = STUDY / 'audits/seal/financial-v46u-seal-or14-ds.json'
SEAL = STUDY / 'audits/seal/financial-v46u-seal-or15-ds.json'
OUT = STUDY / 'results/financial-v46u-or15-ds-20261111'
AMEND = STUDY / 'plans/2026-11-11-v46u-taskset-revision-amendment.md'


def main():
    if SEAL.exists():
        raise SystemExit('seal exists: ' + str(SEAL))
    cfg = json.loads(CFG.read_text())
    state = digest_json(freeze_state(cfg))
    approval = json.loads(APPROVAL.read_text())
    approval['amendments']['2026-11-11-taskset-revision'] = {
        'document': str(AMEND), 'sha256': hashlib.sha256(AMEND.read_bytes()).hexdigest(),
        'approved_by_user': '2026-11-11 (plan: "2 ok … 3 chung, 4 ok, 5 ok"; D1 "Giữ tắt … session-query … đồng ý"; '
                            'addendum e "2 duyệt"; addendum f "1-b")'}
    if state not in approval['freeze_state_sha256']:
        approval['freeze_state_sha256'].append(state)
    APPROVAL.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + '\n')
    base = json.loads(BASE.read_text())
    runs = [dict(r, state_sha256=state) for r in base['runs'] if r['split'] == 'devsmoke']
    for split in ('pilot', 'main'):
        settings = build_settings(cfg, split)
        tasks = [p for p in sorted((STUDY / 'tasks' / split).iterdir()) if p.is_dir() and task_eligibility(p)['confirmatory_eligible']]
        out = OUT / (cfg['model_stratum'] + '-' + split)
        prepare_manifest(out, settings, tasks, cfg, False)
        runs.append({'out': str(out), 'config': str(CFG), 'model': cfg['model'], 'split': split, 'settings': settings,
                     'tasks': [p.name for p in tasks], 'state_sha256': state})
    protected = dict(base['protected_files'])
    protected[str(APPROVAL)] = hash_file(APPROVAL)
    seal = dict(base, runs=runs, protected_files=protected,
                purpose='amendment 2026-11-11 (d/e/f): fresh sealed pilot 36 tasks (core/compute/native memory) -> b0 gate -> main 200')
    SEAL.write_text(json.dumps(seal, ensure_ascii=False, indent=2) + '\n')
    validate_seal(SEAL)
    print(json.dumps({'seal': str(SEAL), 'state': state, 'runs': [(r['split'], len(r['tasks']), r['out']) for r in runs]}, indent=1))


if __name__ == '__main__':
    main()
