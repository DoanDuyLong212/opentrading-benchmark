"""Aggregate the Haiku-primary judge over the final 300-task composition."""
import json, collections
from pathlib import Path

B = Path('/home/doanlong/extra/bench-v47-pin/runs/deepinfra-20261125')
FINAL = B / 'FINAL-300-trials.jsonl'
RUNS = {
    'main': B / '../main-20261124/run',
    'shard2': B / '../main-20261124-shard2/run',
    'a-ot': B / 'a-ot/run',
    'a-dsh': B / 'a-dsh/run',
    'a-oc': B / 'a-oc/run',
    'a-dsh2': B / 'a-dsh2/run',
    'a-all': B / 'a-all/run',
    'b-ot': B / 'b-ot/run',
    'b2-ot': B / 'b2-ot/run',
    'old-v46u': B / 'old-v46u-selected/run',
}
ARMS = ['opentrading_machine', 'opencode', 'dsh']

def rows(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

primary = {}
for name, run in RUNS.items():
    for r in rows(run / 'judge-primary.jsonl'):
        primary[r['trial_id']] = r

final = rows(FINAL)
missing = [r['trial_id'] for r in final if r['trial_id'] not in primary]
table = []
for r in final:
    p = primary.get(r['trial_id'])
    table.append({**r, 'primary': bool(p and p.get('primary')),
                  'judge_verdict': p.get('judge_verdict') if p else None,
                  'dnf': bool(p and p.get('dnf')),
                  'dnf_infra': bool(p and p.get('dnf_infra')),
                  'numeric_gate': p.get('numeric_gate') if p else None,
                  'false_refusal': bool(p and p.get('false_refusal')),
                  'fp': bool(p and p.get('fp')),
                  'manual_rejected': bool(p and p.get('manual_rejected')),
                  'strict_success': bool(r.get('success'))})

def agg(sel):
    n = len(sel)
    return {
        'n': n,
        'primary': sum(x['primary'] for x in sel),
        'primary_rate': round(sum(x['primary'] for x in sel) / n, 4) if n else None,
        'strict_success': sum(x['strict_success'] for x in sel),
        'strict_rate': round(sum(x['strict_success'] for x in sel) / n, 4) if n else None,
        'dnf': sum(x['dnf'] for x in sel),
        'dnf_infra': sum(x['dnf_infra'] for x in sel),
        'false_refusal': sum(x['false_refusal'] for x in sel),
        'fp': sum(x['fp'] for x in sel),
        'manual_rejected': sum(x['manual_rejected'] for x in sel),
        'judge_verdicts': dict(collections.Counter(x['judge_verdict'] for x in sel)),
    }

out = {'trials': len(table), 'missing_primary': len(missing), 'missing_examples': missing[:10]}
for scope, sel in (('ALL', table),
                   ('A', [x for x in table if x['block'] == 'A']),
                   ('B', [x for x in table if x['block'] == 'B'])):
    out[scope] = {a: agg([x for x in sel if x['arm'] == a]) for a in ARMS}
    out[scope + '_by_stratum'] = {
        s: {a: agg([x for x in sel if x['arm'] == a and x['stratum'] == s]) for a in ARMS}
        for s in sorted({x['stratum'] for x in sel})
    }
(B / 'HAIKU-FINAL-300-report.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
print(json.dumps({k: out[k] for k in ('trials', 'missing_primary', 'ALL', 'A', 'B')}, ensure_ascii=False, indent=1))
