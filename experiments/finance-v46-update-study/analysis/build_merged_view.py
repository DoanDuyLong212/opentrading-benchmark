#!/usr/bin/env python3
"""Merged pilot view = or11 rows with ONLY the originally failed slots replaced by the targeted rerun.

Creates results/financial-v46u-or12r-ds-20261111/merged/ with trials.jsonl, per-trial symlinks to the
source artifacts, the matching llm-graded.jsonl rows, and financial-review.json decisions (or11 decisions
for unchanged slots + the rerun review decisions for replaced slots). Sealed sources are not modified.
"""
import json
import os
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
OR11 = STUDY / 'results/financial-v46u-or11-ds-20261110/deepseek-openrouter-pilot'
RR = STUDY / 'results/financial-v46u-or12r-ds-20261111'
OUT = RR / 'merged'


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def main():
    merged = jl(RR / 'merged-trials.jsonl')
    OUT.mkdir(exist_ok=True)
    (OUT / 'trials').mkdir(exist_ok=True)
    graded = {r['trial_id']: r for r in jl(OR11 / 'llm-graded.jsonl')}
    review = json.loads((OR11 / 'financial-review.json').read_text())['decisions']
    rr_graded, rr_review = {}, {}
    for d in RR.glob('pilot-*'):
        rr_graded.update({r['trial_id']: r for r in jl(d / 'llm-graded.jsonl')})
        if (d / 'rerun-review.json').is_file():
            rr_review.update(json.loads((d / 'rerun-review.json').read_text()))
    rows, g_rows, decisions = [], [], {}
    for r in merged:
        tid = r['trial_id']
        src = Path(r.pop('_rerun_dir')) if '_rerun_dir' in r else OR11
        link = OUT / 'trials' / tid
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(src / 'trials' / tid, link)
        rows.append(r)
        if src == OR11:
            g_rows.append(graded[tid])
            if tid in review:
                decisions[tid] = review[tid]
        else:
            g_rows.append(rr_graded[tid])
            if tid in rr_review:
                decisions[tid] = rr_review[tid]
    (OUT / 'trials.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    (OUT / 'llm-graded.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in g_rows))
    (OUT / 'financial-review.json').write_text(json.dumps({'schema': 'merged-view-review', 'decisions': decisions},
                                                          ensure_ascii=False, indent=1))
    print('merged rows', len(rows), 'graded', len(g_rows), 'review decisions', len(decisions))


if __name__ == '__main__':
    main()
