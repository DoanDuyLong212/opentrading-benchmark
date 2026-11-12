#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""metrics.py — metric phụ A1–A4 (dashboard) + B1–B6 (lớp phân tích).

Toàn bộ tính từ telemetry ĐÃ GHI của một results dir (trials.jsonl + grade.json +
answer.json + gold) — không benchmark lại (nguyên tắc 1.0-②). Thiếu số đo → N/A
(không ghi 0 — nguyên tắc 1.0-③).

A1 error_taxonomy      — phân bố loại lỗi trên trial FAIL
A2 false_refusal_rate  — % từ chối oan trên task CÓ dữ liệu (ma trận trung thực với FP)
A3 dnf_rate            — % không hoàn thành + Success hai mẫu số (answered / started)
A4 tool_economy        — mcp_calls p50/p90, tách đúng/sai + retry_rate + zero-mcp
B1 per-check breakdown — % pass từng thành phần Success (value/unit/period/source/…)
B2 token_profile       — input/output/reasoning/cache p50 + coverage (N/A rõ)
B3 cost_metrics        — cost/trial + cost-per-success từ bảng giá freeze
B4 answer_dispersion   — MAD% giá trị trả lời giữa các runs (chỉ trial PASS — unit-safe)
B5 bonus_replacement   — % từ chối đúng CÓ kèm kỳ/số thay thế
B6 (gộp vào B2) coverage
"""
import glob
import json
import os
import re
import statistics
import math
import itertools
import random

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPLITS = ("pilot", "smoke", "main", "holdout")
ANSWER_KEYS = ("value", "values", "verdict", "ranking", "reason")


# ------------------------------------------------------------------ utils
def percentile(sorted_vals, p):
    """Nearest-rank percentile trên list ĐÃ SORT; rỗng → None."""
    if not sorted_vals:
        return None
    idx = max(0, min(len(sorted_vals) - 1, math.ceil(p * len(sorted_vals) / 100) - 1))
    return sorted_vals[idx]


def load_trials(out_dir):
    path = os.path.join(out_dir, "trials.jsonl")
    if not os.path.exists(path):
        return []
    rows = []
    seen = set()
    with open(path, encoding="utf-8") as f:
        for number, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)  # Corrupted or truncated rows must never silently disappear.
            identity = row.get("trial_id") or (row.get("task"), row.get("arm"), row.get("run"))
            if identity in seen:
                raise ValueError("Duplicate trial at line %d: %s" % (number, identity))
            seen.add(identity)
            rows.append(row)
    return rows


def trial_dir(trial):
    """Thư mục trial (đ chứa grade.json/ws). Ưu tiên ws path tuyệt đối."""
    ws = trial.get("workspace") or ""
    cand = os.path.abspath(os.path.join(ROOT, ws))
    return os.path.dirname(cand)


def grade_path(trial):
    return os.path.join(trial_dir(trial), "grade.json")


def load_grade(trial):
    p = trial.get("grade_path") or grade_path(trial)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_answer(trial):
    p = trial.get("answer_path") or os.path.join(trial_dir(trial), "ws", "answer.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def resolve_task_dir(task_id):
    """Task id duy nhất trong tasks/{pilot,smoke,main,holdout} → đường dẫn."""
    for split in SPLITS:
        d = os.path.join(ROOT, "tasks", split, task_id)
        if os.path.isdir(d):
            return d
    return None


def gold_scoring(task_dir):
    try:
        return json.load(open(os.path.join(task_dir, "solution", "gold.json"),
                              encoding="utf-8")).get("scoring", "value")
    except (OSError, json.JSONDecodeError):
        return None


def task_is_partial(task_dir):
    """Task dữ liệu một phần (availability != available) — loại khỏi mẫu false-refusal."""
    try:
        payloads = json.load(open(os.path.join(task_dir, "environment", "payloads.json"),
                                  encoding="utf-8"))
        return any((v.get("envelope") or v).get("availability") not in (None, "available")
                   for v in payloads["tools"].values())
    except (OSError, json.JSONDecodeError, KeyError, AttributeError):
        return False


def answer_value(answer):
    """Trích value chính của answer (dict lồng values.* hoặc value)."""
    if not isinstance(answer, dict):
        return None
    if "value" in answer:
        return answer["value"]
    vals = answer.get("values")
    if isinstance(vals, dict):
        if isinstance(vals.get("value"), (int, float)):
            return vals["value"]
        for k, v in vals.items():
            if isinstance(v, (int, float)):
                return v
    return None


# ------------------------------------------------------------------ A3
def is_answered(trial):
    return (trial.get("status") == "ok" and trial.get("timely", True)
            and trial.get("answer_source") not in (None, "missing"))


def dnf_rate(trials):
    n = len(trials)
    answered_rows = [t for t in trials if is_answered(t)]
    answered = len(answered_rows)
    ok_all = sum(bool(t.get("success")) for t in answered_rows)
    ok_answered = sum(bool(t.get("success")) for t in answered_rows)
    return {"n": n, "dnf": n-answered, "dnf_rate": (n-answered)/n if n else None,
            "success_all": ok_all/n if n else None,
            "success_answered": ok_answered/answered if answered else None, "n_answered": answered}


# ------------------------------------------------------------------ A1
def error_taxonomy(trials):
    fails = [t for t in trials if not t.get("success")]
    counts = {}
    for t in fails:
        et = t.get("execution_error") or t.get("error_type") or ("timeout" if t.get("status") == "timeout"
                                     else t.get("status") or "unknown")
        counts[et] = counts.get(et, 0) + 1
    n = len(fails)
    share = {k: round(v / n, 4) for k, v in counts.items()} if n else {}
    return {"n_fail": n, "counts": dict(sorted(counts.items(), key=lambda x: -x[1])),
            "share": dict(sorted(share.items(), key=lambda x: -x[1]))}


# ------------------------------------------------------------------ A4
def tool_economy(trials):
    calls = [t["mcp_calls"] for t in trials
             if isinstance(t.get("mcp_calls"), int) and t.get("status") == "ok"]
    ok_calls = [t["mcp_calls"] for t in trials
                if isinstance(t.get("mcp_calls"), int) and t.get("status") == "ok" and t.get("success")]
    fail_calls = [t["mcp_calls"] for t in trials
                  if isinstance(t.get("mcp_calls"), int) and t.get("status") == "ok" and not t.get("success")]
    answered = [t for t in trials if t.get("status") == "ok"]
    sc = sorted(calls)
    return {
        "n_answered": len(answered),
        "p50": percentile(sc, 50), "p90": percentile(sc, 90),
        "p50_success": percentile(sorted(ok_calls), 50),
        "p50_fail": percentile(sorted(fail_calls), 50),
        "zero_mcp_answered": sum(1 for c in calls if c == 0),
        "retry_rate": round(sum(1 for t in trials if (t.get("attempt") or 1) > 1) / len(trials), 4)
                      if trials else None,
    }


# ------------------------------------------------------------------ A2
_MISSING = object()


def get_path(obj, path):
    for key in path.split("."):
        if not isinstance(obj, dict) or key not in obj:
            return _MISSING
        obj = obj[key]
    return obj


def answerable_fields(trial):
    if "_answerable_fields" in trial:
        return trial["_answerable_fields"]
    # Legacy synthetic fixtures; live analysis uses gold's requested field contracts.
    return ["value"] if trial.get("_scoring") == "value" else []


def is_false_refusal(trial, scoring=None, partial=False):
    sc = scoring or trial.get("_scoring")
    if sc == "refusal" or not is_answered(trial) or partial:
        return False
    ans = trial.get("_answer")
    if not isinstance(ans, dict):
        return False
    fields = answerable_fields(trial)
    # Missing keys are format failures, not evidence of deliberate refusal.
    # Empty sets/rankings need an explicit refusal statement; valid empty results
    # have no answerable non-empty gold field and never enter this denominator.
    reason = bool(str(ans.get("reason") or ans.get("note") or "").strip())
    return any((get_path(ans, path) is None or
                (get_path(ans, path) == [] and reason)) for path in fields)


def false_refusal_rate(trials, partial_tasks=frozenset(), task_scoring=None):
    eligible = [t for t in trials if (t.get("_scoring") or (task_scoring or {}).get(t["task"])) != "refusal"
                and answerable_fields(t) and not (t["task"] in partial_tasks and "_answerable_fields" not in t)]
    answered = [t for t in eligible if is_answered(t)]
    refusals = sum(is_false_refusal(t) for t in answered)
    return {"denominator": len(answered), "denominator_started": len(eligible),
            "false_refusals": refusals, "rate": refusals/len(answered) if answered else None,
            "rate_started": refusals/len(eligible) if eligible else None}


# ------------------------------------------------------------------ B2/B3
def norm_tokens(tokens):
    if not isinstance(tokens, dict):
        return None
    total = tokens.get("total") or {}
    cache = tokens.get("cache") or {}
    return {"input": tokens.get("input", tokens.get("inputTokens", tokens.get("prompt_tokens", total.get("input")))),
            "output": tokens.get("output", tokens.get("outputTokens", tokens.get("completion_tokens", total.get("output")))),
            "reasoning": tokens.get("reasoning", tokens.get("reasoningTokens")),
            "cache_read": tokens.get("cache_read", tokens.get("cached", tokens.get("cacheReadTokens", cache.get("read") if isinstance(cache, dict) else None)))}


def token_profile(trials):
    norms = [norm_tokens(t.get("tokens")) for t in trials]
    fields = ("input", "output", "reasoning", "cache_read")
    result = {}
    for field in fields:
        values = sorted(n[field] for n in norms if n and isinstance(n.get(field), (int, float)))
        result["p50_"+field] = percentile(values, 50)
        result["p90_"+field] = percentile(values, 90)
        result["coverage_"+field] = len(values)/len(trials) if trials else None
    result['coverage'] = sum(bool(n) and isinstance(n.get('input'), (int, float))
                             and isinstance(n.get('output'), (int, float)) and t.get('tokens', {}).get('complete') is not False
                             for n, t in zip(norms, trials))/len(trials) if trials else None
    return result


def cost_of_trial(tokens, price):
    nt = norm_tokens(tokens)
    if not nt or tokens.get('complete') is False or not all(isinstance(nt.get(k), (int, float)) for k in ('input', 'output')):
        return None
    if not all(isinstance(price.get(k), (int, float)) for k in ('input', 'output')):
        return None
    cached = nt.get('cache_read')
    semantics = price.get('input_cache_semantics')
    if 'cached' in price and not isinstance(cached, (int, float)):
        return None  # A cache-priced table needs measured cache usage, including zero.
    # A plain two-rate table is usable only for no reported cache use. Nonzero
    # cache needs an explicit provider convention (inclusive vs exclusive input).
    if cached and semantics not in ('inclusive', 'exclusive'):
        return None
    if cached and not isinstance(price.get('cached'), (int, float)):
        return None
    uncached_input = nt['input'] - cached if cached and semantics == 'inclusive' else nt['input']
    if uncached_input < 0:
        return None
    return (uncached_input*price['input'] + nt['output']*price['output']
            + (cached or 0)*price.get('cached', 0))/1e6


def cost_metrics(trials, price):
    paired = [(t, cost_of_trial(t.get("tokens"), price)) for t in trials]
    observed = [(t, c) for t, c in paired if c is not None]
    total = sum(c for _, c in observed)
    complete = len(observed) == len(trials) and bool(trials)
    n_ok = sum(bool(t.get('success')) for t in trials)
    return {"basis": price.get('basis', 'estimated_list_price'),
            "coverage": len(observed)/len(trials) if trials else None,
            "cost_per_trial": total/len(observed) if observed else None,
            "cost_total_observed": total if observed else None,
            "cost_total": total if complete else None,
            "cost_per_success": total/n_ok if complete and n_ok else None}


# ------------------------------------------------------------------ B1
def per_check_breakdown(trials):
    """% pass từng loại check trong grade.json (prefix trước ':' — value/unit/…)."""
    agg = {}
    for t in trials:
        g = load_grade(t)
        if not g:
            continue
        for c in g.get("checks", []):
            kind = (c.get("check") or "").split(":")[0]
            a = agg.setdefault(kind, {"n": 0, "pass": 0})
            a["n"] += 1
            a["pass"] += 1 if c.get("pass") else 0
    return {k: {"n": v["n"], "pass_rate": round(v["pass"] / v["n"], 4)}
            for k, v in sorted(agg.items())}


# ------------------------------------------------------------------ B4
def _mad_pct_one_task(trials_one_task):
    vals = []
    for t in trials_one_task:
        if not t.get("success"):
            continue
        ans = t["_answer"] if "_answer" in t else load_answer(t)
        v = answer_value(ans)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    if len(vals) < 2:
        return None, len(vals)
    med = statistics.median(vals)
    mad = statistics.median([abs(v - med) for v in vals])
    return (round(mad / abs(med) * 100, 3) if abs(med) > 1e-12 else None), len(vals)


def answer_dispersion(trials):
    """MAD% giữa các giá trị trả lời — tính PER TASK (tránh trộn đại lượng khác nhau),
    CHỈ trial PASS (value đã khớp gold trong tol nên unit-safe). Báo median MAD%
    trên các task có ≥2 pass."""
    by_task = {}
    for t in trials:
        by_task.setdefault(t.get("task"), []).append(t)
    mads, n_pass = [], 0
    for _tid, ts in sorted(by_task.items()):
        mad, np_ = _mad_pct_one_task(ts)
        n_pass = max(n_pass, np_)
        if mad is not None:
            mads.append(mad)
    if not mads:
        return {"n_tasks_with_spread": 0, "mad_pct": None}
    return {"n_tasks_with_spread": len(mads),
            "mad_pct": round(statistics.median(mads), 3)}


# ------------------------------------------------------------------ B5
def bonus_replacement_rate(trials, grade_path=None):
    """Trên trap refusal: % trial từ chối đúng CÓ bonus (kỳ/số thay thế)."""
    gp = grade_path or (lambda t: os.path.join(trial_dir(t), "grade.json"))
    n_refused = hit = 0
    for t in trials:
        try:
            g = json.load(open(gp(t), encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            g = None
        # CHỈ task trap refusal có trường bonus trong gold — grade của task thường
        # không có "bonus" → không thuộc mẫu số
        if not g or not g.get("success") or "bonus" not in g:
            continue
        n_refused += 1
        b = g.get("bonus") or {}
        hit += 1 if b.get("hit") else 0
    return {"n_refused_ok": n_refused, "hit": hit,
            "rate": round(hit / n_refused, 4) if n_refused else None}


# ------------------------------------------------------------------ tổng hợp
def per_arm(trials, partial_tasks=frozenset(), task_scoring=None, price=None, expected_arms=()):
    arms = {}
    for arm in sorted({t.get("arm", "?") for t in trials} | set(expected_arms)):
        ts = [t for t in trials if t.get("arm") == arm]
        arms[arm] = {
            "n": len(ts),
            "dnf": dnf_rate(ts),                        # A3 (+ 2 mẫu số Success)
            "error_taxonomy": error_taxonomy(ts),       # A1
            "tool_economy": tool_economy(ts),           # A4
            "false_refusal": false_refusal_rate(ts, partial_tasks, task_scoring),  # A2
            "token_profile": token_profile(ts),         # B2/B6
            "cost": cost_metrics(ts, price) if price else None,                    # B3
            "per_check": per_check_breakdown(ts),       # B1
            "dispersion": answer_dispersion(ts),        # B4
            "bonus": bonus_replacement_rate(ts),        # B5
        }
    return arms


def stable_correct(trials, expected_runs=3, expected_tasks=None):
    by_task = {tid: [] for tid in (expected_tasks or [])}
    for t in trials:
        by_task.setdefault(t['task'], []).append(t)
    complete = {tid: ts for tid, ts in by_task.items()
                if len(ts) == expected_runs and {t['run'] for t in ts} == set(range(1, expected_runs+1))}
    stable = sum(all(bool(t.get('success')) for t in ts) for ts in complete.values())
    return {'expected_runs': expected_runs, 'n_tasks': len(by_task), 'n_complete': len(complete),
            'n_incomplete': len(by_task)-len(complete), 'stable_correct': stable,
            'rate_complete': stable/len(complete) if complete else None,
            'rate_all_scheduled': stable/len(by_task) if by_task else None,
            'endpoint': 'all_runs_correct' if expected_runs == 3 else 'all_runs_correct_nonprimary'}


def fp_metrics(trials):
    ts = [t for t in trials if t.get('_scoring') == 'refusal']
    answered = [t for t in ts if is_answered(t)]
    fp = sum(bool(t.get('fp')) for t in ts)
    fp_answered = sum(bool(t.get('fp')) for t in answered)
    return {'n_started': len(ts), 'n_answered': len(answered), 'fp_started': fp,
            'fp_answered': fp_answered, 'rate_started': fp/len(ts) if ts else None,
            'rate_answered': fp_answered/len(answered) if answered else None}


def latency_metrics(trials):
    values = sorted(t['wall_ms'] for t in trials if isinstance(t.get('wall_ms'), (int, float)))
    valid = sorted(t['wall_ms'] for t in trials if t.get('success') and isinstance(t.get('wall_ms'), (int, float)))
    return {'coverage': len(values)/len(trials) if trials else None,
            'p50_ms': percentile(values, 50), 'p90_ms': percentile(values, 90),
            'valid_answer_p50_ms': percentile(valid, 50),
            'timeout_rate': sum(t.get('status') == 'timeout' or t.get('timely') is False for t in trials)/len(trials) if trials else None}


def _bootstrap(deltas_by_cluster, draws=2000, seed=20261104):
    keys = sorted(deltas_by_cluster)
    if not keys:
        return {'estimate': None, 'ci95': None, 'n_clusters': 0}
    rng = random.Random(seed)
    def average(groups):
        values = [d for key in groups for d in deltas_by_cluster[key]]
        return sum(values)/len(values)
    estimates = sorted(average(rng.choices(keys, k=len(keys))) for _ in range(draws))
    return {'estimate': average(keys), 'ci95': [percentile(estimates, 2.5), percentile(estimates, 97.5)],
            'n_clusters': len(keys), 'draws': draws, 'seed': seed}


def paired_statistics(trials, expected_runs=3, clusters=None):
    arms = sorted({t['arm'] for t in trials})
    cells = {}
    for t in trials:
        cells.setdefault((t['arm'], t['task']), []).append(t)
    output = []
    for left, right in itertools.combinations(arms, 2):
        tasks = sorted({t['task'] for t in trials})
        deltas, families, b, c = {}, {}, 0, 0
        for tid in tasks:
            a, z = cells.get((left, tid), []), cells.get((right, tid), [])
            if any(len(ts) != expected_runs or {t['run'] for t in ts} != set(range(1, expected_runs+1)) for ts in (a, z)):
                continue
            delta = sum(bool(t.get('success')) for t in a)/expected_runs - sum(bool(t.get('success')) for t in z)/expected_runs
            deltas[tid] = [delta]
            families.setdefault((clusters or {}).get(tid, tid), []).append(delta)
            sa, sz = all(t.get('success') for t in a), all(t.get('success') for t in z)
            b += int(sa and not sz)
            c += int(sz and not sa)
        n = b+c
        p = min(1., 2*sum(math.comb(n, k) for k in range(min(b,c)+1))/2**n) if n else 1.
        output.append({'left': left, 'right': right, 'paired_tasks': len(deltas),
                       'trial_success_difference': _bootstrap(deltas),
                       'payload_family_sensitivity': _bootstrap(families),
                       'stable_mcnemar': ({'left_only': b, 'right_only': c, 'p_exact': p}
                                           if expected_runs == 3 else {'available': False, 'reason': 'requires exactly 3 scheduled runs'})})
    # Holm step-down over the three registered pairwise stable endpoints.
    running = 0
    for rank, row in enumerate(sorted([r for r in output if 'p_exact' in r['stable_mcnemar']], key=lambda r:r['stable_mcnemar']['p_exact'])):
        running = max(running, min(1., (len(output)-rank)*row['stable_mcnemar']['p_exact']))
        row['stable_mcnemar']['p_holm'] = running
    return output


def build_summary(out_dir, price=None):
    trials = load_trials(out_dir)
    models = sorted({t.get('model') for t in trials}, key=str)
    if len(models) > 1:
        raise ValueError('Mixed-model trials must be analyzed in separate result directories')
    manifest_path = os.path.join(out_dir, 'manifest.json')
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else None
    plan = manifest.get('plan', {}) if manifest else {}
    settings = plan.get('settings', {})
    from run_manifest import validate_trial_rows
    complete = validate_trial_rows(trials, manifest) if manifest else None
    partial, task_scoring, clusters = set(), {}, {}
    from run_manifest import task_contract
    contracts = plan.get('task_contracts', {})
    for tid in {t['task'] for t in trials}:
        contract = contracts.get(tid)
        if contract is None:
            d = resolve_task_dir(tid)
            contract = task_contract(d) if d else {}
        task_scoring[tid] = contract.get('scoring')
        if contract.get('partial'): partial.add(tid)
        clusters[tid] = contract.get('payload_family_sha256') or tid
        for t in trials:
            if t['task'] == tid:
                t['_answerable_fields'] = contract.get('answerable_fields', [])
    for t in trials:
        t.setdefault('_scoring', task_scoring.get(t['task']))
        t.setdefault('_answer', load_answer(t))
    frozen_price = plan.get('config', {}).get('price_per_1m')
    # Historical runs without a manifest remain unpriced; never reprice with live config.
    price = price if price is not None else frozen_price
    result = {'generated_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
              'out_dir': os.path.abspath(out_dir), 'model': models[0] if models else settings.get('model'),
              'n_trials': len(trials),
              'completion': {'observed_trials': len(trials), 'scheduled_trials': len(plan.get('schedule', [])) if manifest else None,
                             'complete': complete},
              'manifest_sha256': manifest.get('fingerprint') if manifest else None,
              'legacy_unfrozen': manifest is None, 'partial_tasks': sorted(partial),
              'task_eligibility': {'quarantined_tasks': settings.get('quarantined_tasks', {}),
                                   'n_quarantined': len(settings.get('quarantined_tasks', {})),
                                   'diagnostic_includes_quarantined': settings.get('include_quarantined', False)},
              'arms': per_arm(trials, partial, task_scoring, price, settings.get('arms', []))}
    expected_runs = settings.get('runs', 3)
    expected_tasks = list(plan.get('tasks', {})) or sorted({t['task'] for t in trials})
    for arm, values in result['arms'].items():
        ts = [t for t in trials if t['arm'] == arm]
        values['stable'] = stable_correct(ts, expected_runs, expected_tasks)
        values['hallucination_on_unanswerable'] = fp_metrics(ts)
        values['latency'] = latency_metrics(ts)
        values['frozen_v3_successes'] = sum(bool(t.get('frozen_v3_success')) for t in ts)
        values['grader_sensitivity_deltas'] = sum(bool(t.get('success')) != bool(t.get('frozen_v3_success')) for t in ts)
        values['semantic_correctness_rate'] = sum(bool(t.get('semantic_correctness')) for t in ts)/len(ts) if ts else None
    result['paired'] = paired_statistics(trials, expected_runs, clusters)
    result['statistics_note'] = 'Task paired bootstrap; payload hash cluster sensitivity; exact McNemar+Holm on complete all-runs-correct tasks. Stable 3/3 is primary only for frozen runs=3.'
    return result


def print_summary(summary):
    def pct(value):
        return 'N/A' if value is None else '%.1f%%' % (value*100)
    print('Model: %s | trials=%d | frozen=%s | complete=%s' %
          (summary.get('model'), summary['n_trials'], not summary.get('legacy_unfrozen'), summary.get('completion', {}).get('complete')))
    for arm, m in sorted(summary['arms'].items()):
        dnf, stable, token, cost = m['dnf'], m.get('stable', {}), m['token_profile'], m['cost']
        print('%s: success/started=%s success/answered=%s DNF=%s' %
              (arm, pct(dnf['success_all']), pct(dnf['success_answered']), pct(dnf['dnf_rate'])))
        print('  stable %s/%s complete tasks, incomplete=%s, scheduled runs=%s' %
              (stable.get('stable_correct'), stable.get('n_complete'), stable.get('n_incomplete'), stable.get('expected_runs')))
        print('  false refusal=%s/%s answered; token coverage=%s; cost/success=%s' %
              (m['false_refusal']['false_refusals'], m['false_refusal']['denominator'], pct(token['coverage']),
               ('N/A' if not cost or cost['cost_per_success'] is None else '$%.6f' % cost['cost_per_success'])))
        print('  latency ms p50=%s p90=%s; ledger calls p50=%s; errors=%s' %
              (m.get('latency', {}).get('p50_ms'), m.get('latency', {}).get('p90_ms'), m['tool_economy']['p50'], m['error_taxonomy']['counts']))
    print('Statistics and coverage: summary.json. Legacy/unfrozen runs are diagnostic only.')


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else None
    if not out or not os.path.isdir(out):
        print("Cách dùng: python3 tools/metrics.py <results-dir>")
        sys.exit(2)
    s = build_summary(out)
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    print_summary(s)
