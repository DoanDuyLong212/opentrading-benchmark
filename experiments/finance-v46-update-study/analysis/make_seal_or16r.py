#!/usr/bin/env python3
"""Seal or16r (user 2026-11-11 "tạm dừng và bổ sung OT bị hỏng trước rồi chạy tiếp"): infra replacement of the
OpenTrading main slots that crashed before any model request (runner_error, 0 requests) because the disk cleanup moved
the directory its node_modules symlink pointed to. Same code/config/freeze state as or16; only those slots, r1 only.
Runs while the or16 main is paused (sequential, not parallel). Writes once.
"""
import json, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from run_manifest import digest_json, freeze_state, prepare_manifest  # noqa: E402
from v45_gate import build_settings, validate_seal  # noqa: E402
from experiment_conditions import CONDITIONS  # noqa: E402

CFG = STUDY / 'tools/bench_config_deepseek_openrouter.json'
BASE = STUDY / 'audits/seal/financial-v46u-seal-or16-ds.json'
SEAL = STUDY / 'audits/seal/financial-v46u-seal-or16r-ds.json'
MAIN = STUDY / 'results/financial-v46u-or16-ds-20261111/deepseek-openrouter-main'
OUT = STUDY / 'results/financial-v46u-or16r-ds-20261111/main-opentrading_baseline'
ARM = 'opentrading_baseline'


def broken_slots():
    rows = [json.loads(l) for l in (MAIN / 'trials.jsonl').read_text().splitlines() if l.strip()]
    return sorted({r['task'] for r in rows if r['arm'] == ARM and r['status'] == 'runner_error' and not r.get('requests')
                   and r['run'] == 1})


def main():
    if SEAL.exists():
        raise SystemExit('seal exists')
    cfg = json.loads(CFG.read_text())
    state = digest_json(freeze_state(cfg))
    base = json.loads(BASE.read_text())
    if state != next(r for r in base['runs'] if r['split'] == 'main')['state_sha256']:
        raise SystemExit('freeze state differs from or16')
    names = broken_slots()
    settings = dict(build_settings(cfg, 'main'), arms=[ARM], runs=1, conditions={ARM: CONDITIONS[ARM]})
    tasks = [STUDY / 'tasks/main' / n for n in names]
    prepare_manifest(OUT, settings, tasks, cfg, False)
    runs = [r for r in base['runs'] if r['split'] in ('devsmoke', 'pilot')]
    runs.append({'out': str(OUT), 'config': str(CFG), 'model': cfg['model'], 'split': 'main', 'settings': settings,
                 'tasks': names, 'state_sha256': state})
    seal = dict(base, runs=runs, holdout_authorized_by_user=False,
                purpose='infra replacement of %d OpenTrading main r1 slots that crashed before any request '
                        '(node_modules symlink target moved during disk cleanup 2026-11-11 09:17-11:20 UTC); '
                        'replaces only those slots in the merged main view' % len(names))
    SEAL.write_text(json.dumps(seal, ensure_ascii=False, indent=2) + '\n')
    validate_seal(SEAL)
    print(json.dumps({'seal': str(SEAL), 'state': state, 'slots': len(names), 'out': str(OUT)}, indent=1))


if __name__ == '__main__':
    main()
