"""Recompute every number in Results.md from trials.jsonl + judge.jsonl (this folder). Writes summary.json.
Usage: python3 summarize.py
"""
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ['opentrading_machine', 'opencode', 'dsh']
# Published OpenRouter list price for deepseek/deepseek-v4.1-flash-1017 (USD per 1M tokens), used only when a trial
# has no provider-reported cost.
PRICE = {'prompt': 0.03, 'cache_read': 0.001, 'completion': 0.2}


def rows(name):
    return [json.loads(l) for l in (HERE / name).read_text(encoding='utf-8-sig').splitlines() if l.strip()]


def cost(t):
    measured = [a.get('provider_usage', {}).get('measured_cost_usd') for a in t.get('attempts') or []
                if isinstance(a.get('provider_usage'), dict)]
    if measured and all(m is not None for m in measured):
        return sum(float(m) for m in measured), True
    tk = tok(t)
    cache = tk.get('cache_read') or 0
    return ((tk['input'] - cache) * PRICE['prompt'] + cache * PRICE['cache_read'] + tk['output'] * PRICE['completion']) / 1e6, False


def tok(t):
    """Trial token totals; when the trial-level total is missing (usage incomplete), sum the per-attempt usage."""
    tk = t.get('tokens') or {}
    if tk.get('input') is None:
        us = [a['provider_usage'] for a in t.get('attempts') or [] if isinstance(a.get('provider_usage'), dict)]
        tk = {k: sum(u.get(k) or 0 for u in us) for k in ('input', 'output', 'cache_read')}
    return {k: tk.get(k) or 0 for k in ('input', 'output', 'cache_read')}


def sign_test(w, l):
    n, k = w + l, min(w, l)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def pct(v, q):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, math.ceil(q * len(v)) - 1))]


T = {(t['task'], t['arm']): t for t in rows('trials.jsonl')}
J = {(j['task'], j['arm']): j for j in rows('judge.jsonl')}
assert len(T) == len(J) == 900 and T.keys() == J.keys()
tasks = sorted({k[0] for k in J})
fam = lambda task: re.match(r'fin-([a-z0-9]+)-', task).group(1).upper()
out = {'tasks': len(tasks), 'trials': len(J), 'arms': {}}
for a in ARMS:
    js = [J[(t, a)] for t in tasks]
    ts = [T[(t, a)] for t in tasks]
    costs = [cost(t) for t in ts]
    ok = sum(j['primary'] for j in js)
    wall = [t['wall_ms'] / 1000 for t in ts]
    answerable = [j for j in js if j['scoring'] != 'refusal']
    out['arms'][a] = {
        'primary': ok, 'primary_rate': round(ok / len(js), 4),
        'by_stratum': {s: [sum(j['primary'] for j in js if j['stratum'] == s), sum(j['stratum'] == s for j in js)]
                       for s in sorted({j['stratum'] for j in js})},
        'by_family': {f: [sum(j['primary'] for j in js if fam(j['task']) == f), sum(fam(j['task']) == f for j in js)]
                      for f in sorted({fam(j['task']) for j in js})},
        'verdicts': dict(Counter(j['verdict'] for j in js)),
        'format_valid': sum(bool(j['raw_format_valid']) for j in js),
        'dnf': sum(bool(j['dnf']) for j in js),
        'false_refusal': [sum(bool(j['false_refusal']) for j in answerable), len(answerable)],
        'answer_on_refusal_task': [sum(bool(j['fp']) for j in js if j['scoring'] == 'refusal'),
                                   sum(j['scoring'] == 'refusal' for j in js)],
        'numeric_gate_veto': sum(j['numeric_gate'] is False for j in js),
        'cost_total_usd': round(sum(c for c, _ in costs), 4),
        'cost_measured_trials': sum(m for _, m in costs),
        'cost_per_trial_usd': round(sum(c for c, _ in costs) / len(ts), 5),
        'cost_per_success_usd': round(sum(c for c, _ in costs) / ok, 5),
        'tokens_in_avg': round(statistics.mean(tok(t)['input'] for t in ts)),
        'tokens_out_avg': round(statistics.mean(tok(t)['output'] for t in ts)),
        'requests_avg': round(statistics.mean(t['requests'] or 0 for t in ts), 2),
        'mcp_calls_avg': round(statistics.mean(t.get('mcp_calls') or 0 for t in ts), 2),
        'wall_p50_s': round(statistics.median(wall), 1), 'wall_p90_s': round(pct(wall, 0.9), 1),
        'trials_over_5min': sum(w > 300 for w in wall),
    }
out['paired_vs_opentrading'] = {}
for o in ('opencode', 'dsh'):
    w = sum(J[(t, 'opentrading_machine')]['primary'] and not J[(t, o)]['primary'] for t in tasks)
    l = sum(J[(t, o)]['primary'] and not J[(t, 'opentrading_machine')]['primary'] for t in tasks)
    out['paired_vs_opentrading'][o] = {'ot_wins': w, 'ot_losses': l, 'p_two_sided_sign': sign_test(w, l)}
out['all_fail_tasks'] = [t for t in tasks if not any(J[(t, a)]['primary'] for a in ARMS)]
out['ot_only_fail_tasks'] = [t for t in tasks if not J[(t, 'opentrading_machine')]['primary']
                             and J[(t, 'opencode')]['primary'] and J[(t, 'dsh')]['primary']]
(HERE / 'summary.json').write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
print(json.dumps({a: {k: v for k, v in m.items() if k not in ('by_family',)} for a, m in out['arms'].items()}, indent=1, ensure_ascii=False))
print(json.dumps(out['paired_vs_opentrading']), out['all_fail_tasks'], out['ot_only_fail_tasks'])
