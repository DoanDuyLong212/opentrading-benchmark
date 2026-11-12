#!/usr/bin/env python3
"""User-approved (2026-11-11, A1): delete Bun/Node runtime temp libraries (runner/home/tmp/.bun-*.so,
node-addon-native-custom-loader-*) of FINISHED trials of a running cohort. Never touches the active trial, never
evidence (ledgers, captures, results). Stops once the schedule is complete so the supervisor's completed-resume proof
snapshots a stable tree.  python3 analysis/clean_runtime_tmp.py RUN_DIR [RUN_DIR ...]
"""
import json, sys, time
from pathlib import Path


def pass_once(run):
    trials = run / 'trials.jsonl'
    if not trials.is_file():
        return 0, 0, None
    done = {json.loads(l)['trial_id'] for l in trials.read_text().splitlines() if l.strip()}
    total = len(json.loads((run / 'manifest.json').read_text())['plan']['schedule'])
    freed = 0
    for tid in done:
        for tmp in (run / 'trials' / tid).glob('attempts/*/runner/home/tmp'):
            for f in list(tmp.glob('.bun-*.so')) + list(tmp.glob('node-addon-native-custom-loader-*')):
                if f.is_file() and not f.is_symlink():
                    freed += f.stat().st_size; f.unlink()
                elif f.is_dir():
                    for g in f.rglob('*'):
                        if g.is_file():
                            freed += g.stat().st_size; g.unlink()
    return freed, len(done), total


runs = [Path(p).resolve() for p in sys.argv[1:]]
finished = set()
while len(finished) < len(runs):
    for run in runs:
        if run in finished:
            continue
        freed, done, total = pass_once(run)
        if freed:
            print('%s freed %.1f MB (%d/%s trials)' % (run.name, freed / 1e6, done, total), flush=True)
        if total is not None and done >= total:
            finished.add(run)
            print('%s schedule complete: cleaner stops' % run.name, flush=True)
    time.sleep(120)
