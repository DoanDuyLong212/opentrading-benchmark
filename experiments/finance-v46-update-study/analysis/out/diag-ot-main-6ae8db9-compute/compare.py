#!/usr/bin/env python3
"""Diagnostic: OT compute stratum, or16 sealed (38f8adb runtime, calculate/compute) vs OT main 6ae8db9 (shell).
Paired by task (2 runs each). Reads judge-primary.jsonl of both runs + run logs of the new run."""
import collections, glob, json, random, re, statistics as st, sys
from pathlib import Path

OLD = Path('/home/doanlong/extra/benchmark/experiments/finance-v46-update-study/results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main')
NEW = Path(sys.argv[1])
sys.path.insert(0, str(NEW.parent / 'study/tools'))


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


old = {r['trial_id']: r for r in jl(OLD / 'judge-primary.jsonl') if r['arm'] == 'opentrading_baseline' and r['stratum'] == 'compute'}
new = {r['trial_id']: r for r in jl(NEW / 'judge-primary.jsonl')}
oldrows = {r['trial_id']: r for r in jl(OLD / 'trials.jsonl')}
newrows = {r['trial_id']: r for r in jl(NEW / 'trials.jsonl')}
tasks = sorted({r['task'] for r in old.values()})


def per_task(d):
    c = collections.Counter()
    for r in d.values():
        c[r['task']] += bool(r['primary'])
    return c


po, pn = per_task(old), per_task(new)
diffs = [pn[t] - po[t] for t in tasks]
rng = random.Random(20261114)
boot = sorted(sum(rng.choice(diffs) for _ in tasks) / (2 * len(tasks)) for _ in range(5000))
out = {'old_primary': sum(po.values()), 'new_primary': sum(pn.values()), 'n': 2 * len(tasks),
       'delta_pp': 100 * sum(diffs) / (2 * len(tasks)), 'ci95_pp': [100 * boot[124], 100 * boot[4874]],
       'tasks_better': [t for t in tasks if pn[t] > po[t]], 'tasks_worse': [t for t in tasks if pn[t] < po[t]]}


def stats(rows, ids):
    req = [rows[i].get('requests') or 0 for i in ids]
    tok = [(rows[i].get('tokens') or {}).get('input') or 0 for i in ids]
    def tcost(i):
        base = Path(rows[i]['workspace']).parent
        s = 0.0
        for f in glob.glob(str(base.parent / '*/provider.jsonl')):
            for l in open(f):
                try:
                    s += float(((json.loads(l).get('usage') or {}).get('cost')) or 0)
                except ValueError:
                    pass
        return s
    cost = [tcost(i) for i in ids]
    wall = [(rows[i].get('wall_ms') or rows[i].get('elapsed_ms') or 0) / 1000 for i in ids]
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
    return {'requests_mean': round(st.mean(req), 2), 'requests_max': max(req), 'input_tok_mean': round(st.mean(tok)),
            'cost_usd': round(sum(cost), 4), 'wall_p50_s': round(q(wall, .5), 1), 'wall_p90_s': round(q(wall, .9), 1)}


out['old_stats'] = stats(oldrows, list(old))
out['new_stats'] = stats(newrows, list(new))
out['old_dnf'] = sum(bool(r.get('dnf')) for r in old.values())
out['new_dnf'] = sum(bool(r.get('dnf')) for r in new.values())

# Shell behaviour on the new run (the six numbers #263 made its merge gate + extra forms).
from math import isfinite  # noqa
sys.path.insert(0, str(NEW.parent / 'study/experiments/opentrading-runtime'))
calls = []; guard = 0; tuthinh = 0; dsml = 0
for tid in new:
    for log in glob.glob(str(NEW / 'trials' / tid / 'attempts/*/run.log')):
        starts = {}
        for line in open(log, errors='replace'):
            try:
                j = json.loads(line)
            except ValueError:
                continue
            if not isinstance(j, dict):
                continue
            if j.get('type') == 'tool-start' and j.get('name') == 'shell':
                inp = j.get('input'); starts[j['callId']] = inp.get('command', '') if isinstance(inp, dict) else 'RAW:' + str(inp)
            if j.get('type') == 'tool-end' and j.get('callId') in starts:
                calls.append({'trial': tid, 'cmd': starts[j['callId']], 'ok': j.get('ok'), 'out': str(j.get('output'))[:300]})
        text = open(log, errors='replace').read()
        guard += text.count('lặp: bạn đã gọi')
    final = newrows[tid].get('final_text') or ''
    res = glob.glob(str(NEW / 'trials' / tid / 'attempts/*/result.json'))
    ft = ''.join(json.load(open(f)).get('final_text') or '' for f in res)
    tuthinh += 'tự tính' in ft.lower()
    dsml += 'DSML' in ft


def kind(c):
    s = c['cmd'].strip()
    if s.startswith('awk') and 'printf' in s: return 'awk_printf'
    if s.startswith('awk'): return 'awk_other'
    if re.match(r'python3?\s+-c', s): return 'python_-c'
    if 'python' in s or 'cat >' in s or '<<' in s: return 'script/heredoc'
    if 'bc' in s or 'echo' in s or 'expr' in s: return 'echo/bc/expr'
    return 'other'


ok = [c for c in calls if c['ok']]
denied = [c for c in calls if not c['ok'] and 'cần người dùng xác nhận' in c['out']]
nearmiss = [c for c in calls if not c['ok'] and 'chưa đúng dạng chỉ-toán' in c['out']]
out['shell'] = {'calls': len(calls), 'ok': len(ok), 'denied_by_gate': len(denied), 'near_miss_hint': len(nearmiss),
                'other_error': len(calls) - len(ok) - len(denied) - len(nearmiss),
                'trials_using_shell': len({c['trial'] for c in calls}), 'trials_with_ok_shell': len({c['trial'] for c in ok}),
                'forms': dict(collections.Counter(kind(c) for c in calls)),
                'forms_ok': dict(collections.Counter(kind(c) for c in ok)),
                'loop_guard_hits': guard, 'answers_tu_tinh': tuthinh, 'answers_dsml_text': dsml}
out['examples_denied'] = [c['cmd'][:160] for c in denied[:4]]
out['examples_nearmiss'] = [c['cmd'][:160] for c in nearmiss[:4]]
json.dump(out, open(NEW / 'diag-compare.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
