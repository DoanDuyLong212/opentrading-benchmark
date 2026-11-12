#!/usr/bin/env python3
"""Seal or16r3 (user 2026-11-12 "2 backfill đi"): infra replacement of
fin-m3-update-520 OpenCode r2, which failed during the 14:38 UTC network outage (provider_transport_failure x3 then
local_token_budget_exhausted from conservative reservations). Same code/config/freeze state as or16. The driver runs
both repeats (runs=2, its granularity); the merge replaces ONLY the r2 slot, r1 is reported as stability only.
Writes once.
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
SEAL = STUDY / 'audits/seal/financial-v46u-seal-or16r3-ds.json'
MAIN = STUDY / 'results/financial-v46u-or16-ds-20261111/deepseek-openrouter-main'
OUT = STUDY / 'results/financial-v46u-or16r3-ds-20261111/main-opencode'
ARM = 'opencode'


SLOT = 'fin-m3-update-520__opencode__r2'


def broken_slots():
    rows = {json.loads(l)['trial_id']: json.loads(l) for l in (MAIN / 'trials.jsonl').read_text().splitlines() if l.strip()}
    r = rows[SLOT]
    if r['status'] == 'ok':
        raise SystemExit('slot is not failed: %s' % r['status'])
    return [r['task']]


def main():
    if SEAL.exists():
        raise SystemExit('seal exists')
    cfg = json.loads(CFG.read_text())
    state = digest_json(freeze_state(cfg))
    base = json.loads(BASE.read_text())
    if state != next(r for r in base['runs'] if r['split'] == 'main')['state_sha256']:
        raise SystemExit('freeze state differs from or16')
    names = broken_slots()
    settings = dict(build_settings(cfg, 'main'), arms=[ARM], runs=2, conditions={ARM: CONDITIONS[ARM]})
    tasks = [STUDY / 'tasks/main' / n for n in names]
    prepare_manifest(OUT, settings, tasks, cfg, False)
    runs = [r for r in base['runs'] if r['split'] in ('devsmoke', 'pilot')]
    runs.append({'out': str(OUT), 'config': str(CFG), 'model': cfg['model'], 'split': 'main', 'settings': settings,
                 'tasks': names, 'state_sha256': state})
    seal = dict(base, runs=runs, holdout_authorized_by_user=False,
                purpose='infra replacement of %s (network outage 2026-11-11 14:38 UTC); runs=2 is driver '
                        'granularity, only the r2 slot replaces in the merged main view' % SLOT)
    SEAL.write_text(json.dumps(seal, ensure_ascii=False, indent=2) + '\n')
    validate_seal(SEAL)
    print(json.dumps({'seal': str(SEAL), 'state': state, 'slots': len(names), 'out': str(OUT)}, indent=1))


if __name__ == '__main__':
    main()
