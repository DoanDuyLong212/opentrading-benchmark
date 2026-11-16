#!/usr/bin/env python3
"""v4.7 main rebalance (plan 2026-11-16, OpenTrading#309 D2): drop 40 saturated lookup tasks, keep main at 200.

Saturated = every one of the 6 or16 trials (3 arms x 2 runs, v4.6u main final, the same task files) was correct.
Such a task tells nothing about which harness is better: removing it lowers every arm by the same amount. Selection
uses only that all-arms-correct fact, never which arm won anything. Fixed rule, decided before looking at results
by arm: only core lookup tasks (L1-L5); a task a tool or a test names by id stays (fixtures, the memory-stratum
builder's sources, gold audits); every family keeps at least 2 tasks; take one task at a time from the family
with the most tasks left, ties by family name, and within a family the highest task id first (the most recently
added task goes first: older ids carry the earliest, most-reviewed gold). The holdout is never touched.

Writes audits/taskset-revision-2026-11-16/PRUNE.json, then removes the task directories (dry run with --dry-run).
"""
import argparse, collections, json, shutil, tomllib
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
OR16 = STUDY.parents[1] / 'experiments/finance-v46-update-study/results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main/trials.jsonl'
DROP = 40
KEEP_PER_FAMILY = 2


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--dry-run', action='store_true'); a = ap.parse_args()
    rows = [json.loads(l) for l in OR16.read_text().splitlines() if l.strip()]
    by = collections.defaultdict(list)
    for r in rows:
        by[r['task']].append(bool(r.get('grounded_financial_correctness', r.get('success'))))
    main_dir = STUDY / 'tasks/main'
    meta = {d.name: tomllib.loads((d / 'task.toml').read_text(encoding='utf-8')) for d in main_dir.iterdir() if (d / 'task.toml').is_file()}
    family = {t: m.get('family', '?') for t, m in meta.items()}
    left = collections.Counter(family.values())
    code = '\n'.join(p.read_text(encoding='utf-8') for p in [*(STUDY / 'tools').glob('*.py'), *(STUDY / 'tools/tests').glob('*.py')])
    named = {t for t in meta if t in code}
    saturated = sorted((t for t, m in meta.items()
                        if str(m.get('level', '')).startswith('L') and len(by.get(t, [])) == 6 and all(by[t]) and t not in named), reverse=True)
    pool = collections.defaultdict(list)
    for t in saturated:
        pool[family[t]].append(t)
    chosen = []
    while len(chosen) < DROP:
        options = [f for f in pool if pool[f] and left[f] > KEEP_PER_FAMILY]
        if not options:
            raise SystemExit('rule cannot reach %d (got %d)' % (DROP, len(chosen)))
        f = max(options, key=lambda f: (left[f], [-ord(c) for c in f]))
        chosen.append(pool[f].pop(0)); left[f] -= 1
    receipt = {'rule': __doc__.strip(), 'source': str(OR16.relative_to(STUDY.parents[1])), 'saturated_lookup_tasks': len(saturated),
               'kept_named_by_tools_or_tests': sorted(named),
               'dropped': sorted(chosen), 'families_after': dict(sorted(left.items())),
               'main_after': len(meta) - DROP}
    out = STUDY / 'audits/taskset-revision-2026-11-16'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'PRUNE.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'rule'}, ensure_ascii=False, indent=1))
    if not a.dry_run:
        for t in chosen:
            shutil.rmtree(main_dir / t)


if __name__ == '__main__':
    main()
