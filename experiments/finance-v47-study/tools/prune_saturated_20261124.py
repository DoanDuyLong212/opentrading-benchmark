#!/usr/bin/env python3
"""Second prune, owner decision 2026-11-24 (#13: "Xoá đi vì vô dụng, chỉ cần các câu có tính phân hoá và khó").

Rule (fixed before any v4.7 inference on main): a main task is retired when every arm scored primary-correct in both
or16 runs (v4.6u main, DeepSeek v4.1 flash 1017, judge_primary.jsonl). Retired tasks move to tasks-retired/main (kept,
never deleted); the receipt lists every retired task with its per-arm or16 evidence.

Limitations (disclosed in the amendment): the rule is post-hoc (written after or16), and or16 ran older runtimes
(OT v4.6u runtime with a native calculator, OpenCode 2.1, DSH 0.2.1). Retiring the 8 saturated refusal traps removes
the main-split fabrication (FP) check; it remains in holdout and pilot.

    python3 tools/prune_saturated_20261124.py --apply     # select, write receipt, git mv
    python3 tools/prune_saturated_20261124.py             # validate only
"""
import argparse, collections, hashlib, json, subprocess, tomllib
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
OR16 = STUDY.parent / 'finance-v46-update-study/results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main/judge-primary.jsonl'
OUT = STUDY / 'audits/taskset-revision-2026-11-24'
RECEIPT = OUT / 'PRUNE2.json'
RETIRED = STUDY / 'tasks-retired/main'


def or16_scores():
    sc = collections.defaultdict(lambda: collections.defaultdict(list))
    for line in OR16.read_text().splitlines():
        row = json.loads(line)
        sc[row['task']][row['arm']].append(bool(row['primary']))
    return sc


def select(sc, main):
    return sorted(t for t in main if t in sc and len(sc[t]) == 3
                  and all(len(v) == 2 and all(v) for v in sc[t].values()))


def composition(split_dir):
    counts = collections.Counter()
    for task in sorted(Path(split_dir).iterdir()):
        if task.is_dir():
            meta = tomllib.loads((task / 'task.toml').read_text(encoding='utf-8'))
            counts[meta.get('stratum', 'lookup')] += 1
    return dict(sorted(counts.items()))


def apply():
    sc = or16_scores()
    main = sorted(p.name for p in (STUDY / 'tasks/main').iterdir() if p.is_dir())
    retired = select(sc, main)
    RETIRED.mkdir(parents=True, exist_ok=True)
    for tid in retired:
        subprocess.run(['git', 'mv', str(STUDY / 'tasks/main' / tid), str(RETIRED / tid)], check=True, cwd=STUDY)
    receipt = {'schema': 'v47-prune2-20261124', 'rule': 'every arm primary-correct in both or16 runs',
               'decision': 'owner 2026-11-24, issue #13 comment https://github.com/DoanDuyLong212/opentrading-benchmark/issues/13#issuecomment-7125742490',
               'or16_judge_primary_sha256': hashlib.sha256(OR16.read_bytes()).hexdigest(),
               'retired': retired,
               'evidence': {t: {arm: v for arm, v in sorted(sc[t].items())} for t in retired},
               'retired_refusal_traps': sorted(t for t in retired if json.loads(
                   (RETIRED / t / 'solution/gold.json').read_text()).get('scoring') == 'refusal'),
               'main_composition_after': composition(STUDY / 'tasks/main')}
    OUT.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    return receipt


def validate():
    receipt = json.loads(RECEIPT.read_text())
    main = {p.name for p in (STUDY / 'tasks/main').iterdir() if p.is_dir()}
    back = sorted(set(receipt['retired']) & main)
    if back:
        raise ValueError('Retired task returned to main: ' + ', '.join(back))
    missing = [t for t in receipt['retired'] if not (RETIRED / t / 'task.toml').is_file()]
    if missing:
        raise ValueError('Retired task not archived: ' + ', '.join(missing))
    return {'valid': True, 'retired': len(receipt['retired']), 'main': len(main), 'composition': composition(STUDY / 'tasks/main')}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    print(json.dumps(apply() if a.apply else validate(), ensure_ascii=False, indent=1)[:2000])
