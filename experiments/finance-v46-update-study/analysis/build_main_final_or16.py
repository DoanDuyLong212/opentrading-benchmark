#!/usr/bin/env python3
"""Merged main view or16 (user 2026-11-11 "tạm dừng và bổ sung OT bị hỏng trước rồi chạy tiếp"): or16 main rows with
ONLY the OpenTrading r1 slots that crashed before any model request (runner_error, 0 requests; node_modules symlink
target moved during disk cleanup) replaced by the or16r infra replacement (same code/config/freeze state). Every slot
with >=1 request is kept as is. Sources are untouched; per-trial artifacts are symlinked. Re-runnable: judge files are
re-merged on each run (the NIM judge on main may still be finishing).

Judge precedence per trial (later wins): llm-graded-nim.jsonl < llm-graded-nim-confirm.jsonl (amendment i) <
llm-graded-nim-fix.jsonl < analysis/labels/or16-manual-overrides.json (user-confirmed). The original OpenRouter
llm-graded.jsonl is kept untouched in the sources.

  python3 analysis/build_main_final_or16.py
"""
import json, os, shutil, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
BASE = STUDY / 'results/financial-v46u-or16-ds-20261111/deepseek-openrouter-main'
RERUN = STUDY / 'results/financial-v46u-or16r-ds-20261111/main-opentrading_baseline'
# user 2026-11-11 "Có": back-fill of the outage-hit slot (or16r2 runs=2 for driver granularity; only r2 replaces)
RERUN2 = STUDY / 'results/financial-v46u-or16r2-ds-20261111/main-opentrading_baseline'
OUTAGE_SLOTS = {'fin-m3-update-520__opentrading_baseline__r2'}
# user 2026-11-12 "2 backfill đi": same outage (14:38 UTC) hit the OpenCode r2 slot; or16r3 runs=2, only r2 replaces
RERUN3 = STUDY / 'results/financial-v46u-or16r3-ds-20261111/main-opencode'
OUTAGE_SLOTS3 = {'fin-m3-update-520__opencode__r2'}
OUT = STUDY / 'results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main'
OVERRIDES = STUDY / 'analysis/labels/or16-manual-overrides.json'
JUDGE_LAYERS = ['llm-graded-nim.jsonl', 'llm-graded-nim-p0.jsonl', 'llm-graded-nim-p1.jsonl', 'llm-graded-nim-p2.jsonl', 'llm-graded-nim-p3.jsonl', 'llm-graded-nim-p4.jsonl', 'llm-graded-nim-p5.jsonl', 'llm-graded-nim-p6.jsonl', 'llm-graded-or-free-p7.jsonl', 'llm-graded-nim-p8.jsonl', 'llm-graded-nim-retry00.jsonl', 'llm-graded-nim-retry01.jsonl', 'llm-graded-nim-confirm.jsonl', 'llm-graded-nim-fix.jsonl']


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()] if Path(p).is_file() else []


def infra_slots(base):
    return {r['trial_id'] for r in base if r['arm'] == 'opentrading_baseline' and r['status'] == 'runner_error'
            and not r.get('requests') and r['run'] == 1}


def merged_judge(src, tids):
    out = {}
    for name in JUDGE_LAYERS:
        for g in jl(src / name):
            if g['trial_id'] in tids:
                out[g['trial_id']] = dict(g, judge_file=name)
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'trials').mkdir(exist_ok=True)
    shutil.copy(BASE / 'manifest.json', OUT / 'manifest.json')
    base = jl(BASE / 'trials.jsonl')
    broken = infra_slots(base)
    rerun = {r['trial_id']: r for r in jl(RERUN / 'trials.jsonl') if r['trial_id'] in broken}
    rerun2 = {r['trial_id']: r for r in jl(RERUN2 / 'trials.jsonl') if r['trial_id'] in OUTAGE_SLOTS}
    rerun3 = {r['trial_id']: r for r in jl(RERUN3 / 'trials.jsonl') if r['trial_id'] in OUTAGE_SLOTS3}
    missing = (broken - set(rerun)) | (OUTAGE_SLOTS - set(rerun2)) | (OUTAGE_SLOTS3 - set(rerun3))
    if missing:
        raise SystemExit('infra slots without replacement: %s' % sorted(missing))
    src_of = dict({t: RERUN for t in rerun}, **{t: RERUN2 for t in rerun2}, **{t: RERUN3 for t in rerun3})
    rerun = dict(rerun, **rerun2, **rerun3)
    rows = []
    for r in base:
        tid = r['trial_id']
        src = src_of.get(tid, BASE)
        row = dict(rerun.get(tid, r), manifest_sha256=r['manifest_sha256'])
        if tid in rerun:
            row['main_merge_source'] = str(src)
        link = OUT / 'trials' / tid
        if link.is_symlink() or link.exists():
            link.unlink()
        os.symlink(src / 'trials' / tid, link)
        rows.append(row)
    base_ids = {r['trial_id'] for r in base} - set(rerun)
    judge = merged_judge(BASE, base_ids)
    judge.update(merged_judge(RERUN, set(rerun) - set(rerun2) - set(rerun3)))
    judge.update(merged_judge(RERUN3, set(rerun3)))
    judge.update(merged_judge(RERUN2, set(rerun2)))
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.is_file() else {}
    for ov in overrides.get('overrides', []):
        tid = ov['trial_id']
        if tid in judge:
            judge[tid] = dict(judge[tid], verdict=ov['verdict'], judge_file='manual-override',
                              override_reason=ov.get('reason') or ov.get('evidence'), pre_override_verdict=judge[tid].get('verdict'))
    graded = [judge[r['trial_id']] for r in rows if r['trial_id'] in judge]
    (OUT / 'trials.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    (OUT / 'llm-graded.jsonl').write_text(''.join(json.dumps(g, ensure_ascii=False) + '\n' for g in graded))
    (OUT / 'MAIN-MERGE.json').write_text(json.dumps({
        'decision': 'user 2026-11-11 "tạm dừng và bổ sung OT bị hỏng trước rồi thực hiện chạy tiếp": infra replacement '
                    'of OpenTrading r1 slots that never reached the model (runner_error, 0 requests)',
        'base': str(BASE), 'rerun': str(RERUN), 'rerun_outage': str(RERUN2),
        'outage_backfill': 'user 2026-11-11 "Có": %s; user 2026-11-12 "2 backfill đi": %s (network outage 14:38 UTC)' % (sorted(rerun2), sorted(rerun3)),
        'rerun_outage_oc': str(RERUN3),
        'replaced_slots': sorted(rerun),
        'judge_layers': JUDGE_LAYERS + ['manual-override'], 'graded_rows': len(graded), 'rows': len(rows)},
        ensure_ascii=False, indent=1))
    print('rows', len(rows), 'replaced', len(rerun), 'graded', len(graded))


if __name__ == '__main__':
    main()
