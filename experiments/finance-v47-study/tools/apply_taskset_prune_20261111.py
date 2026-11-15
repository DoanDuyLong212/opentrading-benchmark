"""Amendment 2026-11-11 (d): outcome-blind pruning of main/holdout and retirement of quarantined + old memory tasks.

Rule (fixed before any main data, uses no arm outcome):
  per family quota; keep tasks by round-robin over template signatures (tools_expected + expects paths),
  within a signature prefer an entity not yet kept, then more expects, then smaller id.
Usage: python tools/apply_taskset_prune_20261111.py [--apply]
"""
import argparse, json, shutil, sys, tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from run_manifest import task_eligibility  # noqa: E402

QUOTA = {
    'main': {'fin-l1-bctc': 7, 'fin-l5-profile': 7, 'fin-l4-nonexist': 5, 'fin-l5-valuation': 6, 'fin-l2-growth': 5,
             'fin-l3-screen': 5, 'fin-l4-future': 6, 'fin-l2-margin': 5, 'fin-l1-quote-vn': 5, 'fin-l1-quote-gf': 3,
             'fin-l1-quote-crypto': 3},
    'holdout': {'fin-l1-bctc': 2, 'fin-l5-valuation': 2, 'fin-l4-future': 2, 'fin-l4-nonexist': 1, 'fin-l5-profile': 2,
                'fin-l2-growth': 1, 'fin-l2-margin': 1, 'fin-l2-tech': 1},
}
TARGET_CORE = {'main': 140, 'holdout': 36}


def meta(p):
    m = tomllib.loads((p / 'task.toml').read_text())
    g = json.loads((p / 'solution/gold.json').read_text())
    paths = tuple(sorted(e.get('type', '') + ':' + e.get('path', '') for e in g.get('expects', [])))
    return {'id': p.name, 'family': p.name.rsplit('-', 1)[0], 'entity': str(m.get('entity', '')),
            'sig': (tuple(m.get('tools_expected', [])), paths), 'n_expects': len(paths)}


def select(items, quota):
    by_sig = defaultdict(list)
    for it in items:
        by_sig[it['sig']].append(it)
    for v in by_sig.values():
        v.sort(key=lambda x: (-x['n_expects'], x['id']))
    sigs = sorted(by_sig, key=lambda s: min(x['id'] for x in by_sig[s]))
    kept, entities = [], set()
    while len(kept) < quota and any(by_sig[s] for s in sigs):
        for s in sigs:
            if len(kept) >= quota or not by_sig[s]:
                continue
            pool = by_sig[s]
            pick = next((x for x in pool if x['entity'] not in entities), pool[0])
            pool.remove(pick)
            kept.append(pick)
            entities.add(pick['entity'])
    return kept


def plan(split):
    tasks = [p for p in sorted((ROOT / 'tasks' / split).iterdir()) if p.is_dir()]
    retire, keep = [], []
    fam = defaultdict(list)
    for p in tasks:
        e = task_eligibility(p)
        if not e['confirmatory_eligible']:
            retire.append({'id': p.name, 'reason': 'memory_redesign_native' if e.get('memory_multiturn') else 'quarantined:' + str(e['exclusion_reason'])})
            continue
        fam[p.name.rsplit('-', 1)[0]].append(meta(p))
    for f, items in sorted(fam.items()):
        q = QUOTA[split].get(f)
        if q is None or q >= len(items):
            keep += [x['id'] for x in items]
            continue
        k = select(items, q)
        keep += [x['id'] for x in k]
        kid = {x['id'] for x in k}
        retire += [{'id': x['id'], 'reason': f'prune_template_cap:{f}:{q}'} for x in items if x['id'] not in kid]
    return sorted(keep), retire


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    out = {'amendment': 'plans/2026-11-11-v46u-taskset-revision-amendment.md', 'rule': __doc__.strip(), 'quota': QUOTA, 'splits': {}}
    for split in ('main', 'holdout'):
        keep, retire = plan(split)
        assert len(keep) == TARGET_CORE[split], (split, len(keep))
        out['splits'][split] = {'core_kept': keep, 'retired': retire}
        print(split, 'core kept', len(keep), 'retired', len(retire))
    if a.apply:
        for split, d in out['splits'].items():
            dst = ROOT / 'tasks-retired' / split
            dst.mkdir(parents=True, exist_ok=True)
            for r in d['retired']:
                shutil.move(str(ROOT / 'tasks' / split / r['id']), str(dst / r['id']))
        rec = ROOT / 'audits/taskset-revision-2026-11-11'
        rec.mkdir(parents=True, exist_ok=True)
        (rec / 'PRUNE.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print('applied')
    else:
        print(json.dumps({s: [r for r in d['retired'] if r['reason'].startswith('prune')] for s, d in out['splits'].items()}, ensure_ascii=False)[:3000])


if __name__ == '__main__':
    main()
