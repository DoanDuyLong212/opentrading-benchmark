"""Assemble the final 300-task x 3-arm x 1-run table (900 trials) per DEEPINFRA-COMPLETION-20261125.md and report
deterministic strict success by block / stratum / arm. Writes FINAL-300-trials.jsonl and FINAL-300-report.json.
"""
import json
import re
import collections
import subprocess
from pathlib import Path

R = Path('/home/doanlong/extra/bench-v47-pin/runs')
AMD = R / 'main-20261124/amendments'
DI = R / 'deepinfra-20261125'
ARMS = ['opentrading_machine', 'opencode', 'dsh']
fam = lambda t: re.match(r'fin-([a-z0-9]+)-', t).group(1)
STRAT = {'c': 'compute', 'm': 'memory', 'l': 'lookup', 'i': 'investor', 'r': 'investor', 's': 'robustness'}
strat = lambda t: STRAT[fam(t)[0]]


def rows(p):
    p = Path(p)
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


old_raw = subprocess.run(['git', '-C', '/home/doanlong/extra/benchmark', 'show',
                          'origin/fix/v47-dev-gate:experiments/finance-v46-update-study/results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main/trials.jsonl'],
                         capture_output=True, text=True, check=True).stdout
OLD = {(r['task'], r['arm'], r['run']): r for r in map(json.loads, filter(None, old_raw.splitlines()))}
comp = json.loads((AMD / 'FINAL-COMPOSITION-20261125.json').read_text())['tasks']
blockB = json.loads((AMD / 'BLOCK-B-300-20261125.json').read_text())['block_b']
main = {r['trial_id']: r for r in rows(R / 'main-20261124/run/trials.jsonl')}
shard = {r['trial_id']: r for r in rows(R / 'main-20261124-shard2/run/trials.jsonl')}
di = {}
for name in ('a-ot', 'a-dsh', 'a-oc', 'a-dsh2', 'a-all', 'b-ot', 'b2-ot'):
    for r in rows(DI / name / 'run/trials.jsonl'):
        di[(name, r['task'], r['arm'])] = r

VOIDED = {('fin-m6-conv-621','dsh'),('fin-m3-update-536','dsh'),('fin-i2-maxgain-711','dsh'),('fin-i1-pick-705','dsh'),('fin-m6-conv-624','dsh'),
          ('fin-m6-rev-665','opencode'),('fin-m6-conv-621','opencode'),('fin-m3-split-532','opencode'),('fin-m3-update-536','opencode'),('fin-i3-risk-724','opencode'),('fin-m4-port-526','opencode'),
          ('fin-s3-asof-485','opentrading_machine'),('fin-c3-geo-451','opentrading_machine'),('fin-m4-rule-523','opentrading_machine')}
table, missing = [], []


def add(block, task, arm, row, source):
    if row is None:
        missing.append((block, task, arm, source))
        return
    table.append({'block': block, 'task': task, 'arm': arm, 'stratum': strat(task), 'source': source,
                  'status': row.get('status'), 'success': bool(row.get('success')), 'trial_id': row.get('trial_id')})


for t, src in comp.items():
    for a in ARMS:
        if src.startswith('v4.7 r1'):
            tid = f'{t}__{a}__r1'
            rerun = next((di[k] for k in ((n, t, a) for n in ('a-dsh2', 'a-ot', 'a-dsh', 'a-oc')) if k in di), None)
            if rerun is not None:
                add('A', t, a, rerun, 'deepinfra rerun (infra void)')
            elif (t, a) in VOIDED:
                add('A', t, a, None, 'deepinfra rerun pending')
            else:
                add('A', t, a, main.get(tid), 'v4.7 r1 Pearl')
        elif src.startswith('v4.7 shard'):
            add('A', t, a, shard.get(f'{t}__{a}__r1'), 'v4.7 shard r2 Pearl')
        elif src.startswith('v4.7, 3 arms on DeepInfra'):
            add('A', t, a, di.get(('a-all', t, a)), 'v4.7 DeepInfra')
        else:  # v4.6u task in block A
            if a == 'opentrading_machine':
                add('A', t, a, di.get(('b-ot', t, a)), 'OT DeepInfra on v4.6u task')
            else:
                add('A', t, a, OLD.get((t, a, 1)), 'v4.6u run 1')
for t in blockB:
    for a in ARMS:
        if a == 'opentrading_machine':
            add('B', t, a, di.get(('b2-ot', t, a)), 'OT DeepInfra on v4.6u task')
        else:
            add('B', t, a, OLD.get((t, a, 1)), 'v4.6u run 1')


def rate(sel):
    n = len(sel)
    return {'n': n, 'success': sum(x['success'] for x in sel), 'rate': round(sum(x['success'] for x in sel) / n, 3) if n else None,
            'non_ok': sum(x['status'] != 'ok' for x in sel)}


rep = {'trials': len(table), 'missing': len(missing), 'missing_examples': missing[:10]}
for scope, sel in (('ALL', table), ('A', [x for x in table if x['block'] == 'A']), ('B', [x for x in table if x['block'] == 'B'])):
    rep[scope] = {a: rate([x for x in sel if x['arm'] == a]) for a in ARMS}
    rep[scope + '_by_stratum'] = {s: {a: rate([x for x in sel if x['arm'] == a and x['stratum'] == s]) for a in ARMS}
                                  for s in sorted({x['stratum'] for x in sel})}
pair = collections.defaultdict(dict)
for x in table:
    pair[(x['block'], x['task'])][x['arm']] = x['success']
for other in ('opencode', 'dsh'):
    w = sum(1 for v in pair.values() if len(v) == 3 and v['opentrading_machine'] and not v[other])
    l = sum(1 for v in pair.values() if len(v) == 3 and v[other] and not v['opentrading_machine'])
    rep[f'OT_vs_{other}_wins_losses'] = [w, l]
(DI / 'FINAL-300-trials.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in table))
(DI / 'FINAL-300-report.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False))
print(json.dumps({k: rep[k] for k in ('trials', 'missing', 'ALL', 'A', 'B', 'OT_vs_opencode_wins_losses', 'OT_vs_dsh_wins_losses')}, indent=1))
