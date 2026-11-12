#!/usr/bin/env python3
"""Seal or16 (user 2026-11-11 "A chọn b"): main 200 under the b0 judge-primary gate, with pilot evidence = the merged
or15 + confirmation-rerun view (results/financial-v46u-pilot-final-or15-20261111). Judge calibration file = batched
judge vs manual labels on or15 (n=211, kappa 1.0). Writes once.
"""
import hashlib, json, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from run_manifest import digest_json, freeze_state, hash_file, prepare_manifest, task_eligibility  # noqa: E402
from v45_gate import build_settings, validate_seal  # noqa: E402

CFG = STUDY / 'tools/bench_config_deepseek_openrouter.json'
APPROVAL = STUDY / 'audits/engineering-approval-v46-update.json'
BASE = STUDY / 'audits/seal/financial-v46u-seal-or15-ds.json'
SEAL = STUDY / 'audits/seal/financial-v46u-seal-or16-ds.json'
PILOT = STUDY / 'results/financial-v46u-pilot-final-or15-20261111/deepseek-openrouter-pilot'
MAIN = STUDY / 'results/financial-v46u-or16-ds-20261111/deepseek-openrouter-main'
HOLDOUT = STUDY / 'results/financial-v46u-or16-ds-20261111/deepseek-openrouter-holdout'
KAPPA = STUDY / 'analysis/labels/or15-batch-kappa.json'
AMEND = STUDY / 'plans/2026-11-11-v46u-taskset-revision-amendment.md'


def main():
    if SEAL.exists():
        raise SystemExit('seal exists')
    cfg = json.loads(CFG.read_text())
    state = digest_json(freeze_state(cfg))
    a = json.loads(APPROVAL.read_text())
    a['amendments']['2026-11-11-taskset-revision'].update(sha256=hashlib.sha256(AMEND.read_bytes()).hexdigest(),
        pilot_evidence_exception='user 2026-11-11 "A chọn b": merged or15 + confirmation reruns accepted as pilot evidence; '
                                 'after main check the key limit and run holdout immediately if sufficient')
    a['judge_kappa_file'] = str(KAPPA)
    a['holdout_authorized_by_user'] = True
    a['holdout_authorization'] = ('user 2026-11-11: "Sau khi chạy xong main thì kiểm tra hạn mức, đủ holdout thì lập tức chạy" '
                                  '- gated by holdout-go.json written after the key-limit check')
    if state not in a['freeze_state_sha256']:
        a['freeze_state_sha256'].append(state)
    APPROVAL.write_text(json.dumps(a, ensure_ascii=False, indent=2) + '\n')
    base = json.loads(BASE.read_text())
    runs = [dict(r, state_sha256=state) for r in base['runs'] if r['split'] == 'devsmoke']
    pilot = next(r for r in base['runs'] if r['split'] == 'pilot')
    runs.append(dict(pilot, out=str(PILOT), state_sha256=state))
    settings = build_settings(cfg, 'main')
    tasks = [p for p in sorted((STUDY / 'tasks/main').iterdir()) if p.is_dir() and task_eligibility(p)['confirmatory_eligible']]
    prepare_manifest(MAIN, settings, tasks, cfg, False)
    runs.append({'out': str(MAIN), 'config': str(CFG), 'model': cfg['model'], 'split': 'main', 'settings': settings,
                 'tasks': [p.name for p in tasks], 'state_sha256': state})
    hsettings = build_settings(cfg, 'holdout')
    htasks = [p for p in sorted((STUDY / 'tasks/holdout').iterdir()) if p.is_dir() and task_eligibility(p)['confirmatory_eligible']]
    prepare_manifest(HOLDOUT, hsettings, htasks, cfg, False)
    runs.append({'out': str(HOLDOUT), 'config': str(CFG), 'model': cfg['model'], 'split': 'holdout', 'settings': hsettings,
                 'tasks': [p.name for p in htasks], 'state_sha256': state})
    protected = dict(base['protected_files'])
    protected[str(APPROVAL)] = hash_file(APPROVAL)
    protected.pop(str(STUDY / 'analysis/labels/or10-kappa-free.json'), None)
    protected[str(KAPPA)] = hash_file(KAPPA)
    seal = dict(base, runs=runs, protected_files=protected, judge_kappa_file=str(KAPPA), holdout_authorized_by_user=True,
                purpose='main 200 (core/compute/native memory) under b0 judge-primary gate; pilot evidence = user exception (B)')
    SEAL.write_text(json.dumps(seal, ensure_ascii=False, indent=2) + '\n')
    validate_seal(SEAL)
    print(json.dumps({'seal': str(SEAL), 'state': state, 'runs': [(r['split'], len(r['tasks']), r['out']) for r in runs]}, indent=1))


if __name__ == '__main__':
    main()
