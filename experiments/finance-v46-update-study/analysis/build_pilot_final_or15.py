#!/usr/bin/env python3
"""Pilot evidence for main under user exception (B) 2026-11-11 ("A chọn b"): or15 pilot rows with ONLY the
semantically failed slots replaced by the confirmation reruns (or15r: OpenCode/DSH, or15r2: OpenTrading, latest code).
Selective rerun can only raise scores and mixes code versions; disclosed in the pilot report. Sources are untouched;
per-trial artifacts are symlinked.

  python3 analysis/build_pilot_final_or15.py
"""
import json, os, shutil, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
BASE = STUDY / 'results/financial-v46u-or15-ds-20261111/deepseek-openrouter-pilot'
RERUNS = [STUDY / 'results/financial-v46u-or15r-ds-20261111/pilot-opencode',
          STUDY / 'results/financial-v46u-or15r-ds-20261111/pilot-dsh',
          STUDY / 'results/financial-v46u-or15r2-ds-20261111/pilot-opentrading_baseline']
OUT = STUDY / 'results/financial-v46u-pilot-final-or15-20261111/deepseek-openrouter-pilot'


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()] if Path(p).is_file() else []


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'trials').mkdir(exist_ok=True)
    shutil.copy(BASE / 'manifest.json', OUT / 'manifest.json')
    base = jl(BASE / 'trials.jsonl')
    failed = {r['trial_id'] for r in base if not r['semantic_correctness']}
    rerun_rows, rerun_src = {}, {}
    for d in RERUNS:
        for r in jl(d / 'trials.jsonl'):
            if r['trial_id'] in failed:
                rerun_rows[r['trial_id']] = r; rerun_src[r['trial_id']] = d
    missing = failed - set(rerun_rows)
    if missing:
        raise SystemExit('failed slots without rerun: %s' % sorted(missing))
    rows, graded = [], []
    base_graded = {g['trial_id']: g for g in jl(BASE / 'llm-graded-batch.jsonl')}
    rerun_graded = {g['trial_id']: g for d in RERUNS for g in jl(d / 'llm-graded.jsonl')}
    for r in base:
        tid = r['trial_id']
        src = rerun_src.get(tid, BASE)
        row = dict(rerun_rows.get(tid, r), manifest_sha256=r['manifest_sha256'])
        if tid in rerun_rows:
            row['pilot_merge_source'] = str(src)
        link = OUT / 'trials' / tid
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(src / 'trials' / tid, link)
        rows.append(row)
        g = (rerun_graded if tid in rerun_rows else base_graded).get(tid)
        if g:
            graded.append(g)
    (OUT / 'trials.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    (OUT / 'llm-graded.jsonl').write_text(''.join(json.dumps(g, ensure_ascii=False) + '\n' for g in graded))
    (OUT / 'PILOT-MERGE.json').write_text(json.dumps({'decision': 'user 2026-11-11 "A chọn b": accept merged or15 + confirmation reruns as pilot evidence (exception)',
                                                      'base': str(BASE), 'reruns': [str(d) for d in RERUNS],
                                                      'replaced_slots': sorted(rerun_rows), 'graded_rows': len(graded)}, ensure_ascii=False, indent=1))
    print('rows', len(rows), 'replaced', len(rerun_rows), 'graded', len(graded))


if __name__ == '__main__':
    main()
