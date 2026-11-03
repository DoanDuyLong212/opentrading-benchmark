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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPLITS = ("pilot", "smoke", "main", "holdout")
ANSWER_KEYS = ("value", "values", "verdict", "ranking", "reason")


# ------------------------------------------------------------------ utils
def percentile(sorted_vals, p):
    """Nearest-rank percentile trên list ĐÃ SORT; rỗng → None."""
    if not sorted_vals:
        return None
    idx = max(0, min(len(sorted_vals) - 1, -(-p * len(sorted_vals) // 100) - 1))
    return sorted_vals[idx]


def load_trials(out_dir):
    path = os.path.join(out_dir, "trials.jsonl")
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def trial_dir(trial):
    """Thư mục trial (đ chứa grade.json/ws). Ưu tiên ws path tuyệt đối."""
    ws = trial.get("workspace") or ""
    cand = os.path.abspath(os.path.join(ROOT, ws))
    return os.path.dirname(cand)


def grade_path(trial):
    return os.path.join(trial_dir(trial), "grade.json")


def load_grade(trial):
    p = grade_path(trial)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_answer(trial):
    p = os.path.join(trial_dir(trial), "ws", "answer.json")
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
def dnf_rate(trials):
    """DNF = timeout | error | runner_error (không trả lời được trong ngân sách)."""
    n = len(trials)
    dnf = sum(1 for t in trials if t.get("status") in ("timeout", "error", "runner_error"))
    ok = sum(1 for t in trials if t.get("success"))
    answered = n - dnf
    return {"n": n, "dnf": dnf, "dnf_rate": round(dnf / n, 4) if n else None,
            "success_all": round(ok / n, 4) if n else None,
            "success_answered": round(ok / answered, 4) if answered else None,
            "n_answered": answered}


# ------------------------------------------------------------------ A1
def error_taxonomy(trials):
    fails = [t for t in trials if not t.get("success")]
    counts = {}
    for t in fails:
        et = t.get("error_type") or ("timeout" if t.get("status") == "timeout"
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
def is_false_refusal(trial, scoring=None, partial=False):
    """Value task (có dữ liệu): agent trả value=null/từ chối → từ chối oan.
    Loại: trap refusal-scoring, DNF (không có answer), task dữ liệu một phần."""
    if scoring is None:
        scoring = trial.get("_scoring")
    if scoring != "value" or partial:
        return False
    if trial.get("status") not in ("ok",) or trial.get("answer_source") in (None, "missing"):
        return False
    ans = trial.get("_answer")
    if not isinstance(ans, dict):
        return False
    if "value" in ans and ans["value"] is None:
        return True
    text = " ".join(str(ans.get(k) or "") for k in ("reason", "note")).lower()
    return bool(ans.get("value") is None and text) or (
        "value" not in ans and bool(text) and answer_value(ans) is None)


def false_refusal_rate(trials, partial_tasks=frozenset(), task_scoring=None):
    """task_scoring: map task_id → scoring (nếu không có sẽ resolve từ tasks/)."""
    def scoring_of(t):
        if task_scoring and t["task"] in task_scoring:
            return task_scoring[t["task"]]
        d = resolve_task_dir(t["task"])
        return gold_scoring(d) if d else None

    denom = refusals = 0
    for t in trials:
        sc = t.get("_scoring") or scoring_of(t)
        partial = t["task"] in partial_tasks
        answered = t.get("status") == "ok" and t.get("answer_source") not in (None, "missing")
        if sc != "value" or partial or not answered:
            continue
        denom += 1
        ans = t.get("_answer")
        if isinstance(ans, dict) and answer_value(ans) is None:
            refusals += 1
    return {"denominator": denom, "false_refusals": refusals,
            "rate": round(refusals / denom, 4) if denom else None}


# ------------------------------------------------------------------ B2/B3
def norm_tokens(tokens):
    """Chuẩn hoá 2 shape telemetry (opencode / opentrading) → dict thống nhất."""
    if not isinstance(tokens, dict):
        return None
    total = tokens.get("total") or {}
    cache = tokens.get("cache") or {}
    return {"input": tokens.get("input", total.get("input")),
            "output": tokens.get("output", total.get("output")),
            "reasoning": tokens.get("reasoning"),
            "cache_read": cache.get("read") if isinstance(cache, dict) else None}


def token_profile(trials):
    by_in, by_out, n_with = [], [], 0
    for t in trials:
        nt = norm_tokens(t.get("tokens"))
        if nt and isinstance(nt["input"], (int, float)):
            n_with += 1
            by_in.append(nt["input"])
            by_out.append(nt["output"] or 0)
    s_in, s_out = sorted(by_in), sorted(by_out)
    return {"coverage": round(n_with / len(trials), 4) if trials else None,
            "p50_input": percentile(s_in, 50), "p50_output": percentile(s_out, 50),
            "p90_input": percentile(s_in, 90)}


def cost_of_trial(tokens, price):
    nt = norm_tokens(tokens)
    if not nt or not isinstance(nt["input"], (int, float)):
        return None
    cost = (nt["input"] / 1e6) * price.get("input", 0)
    cost += ((nt["output"] or 0) / 1e6) * price.get("output", 0)
    cost += ((nt["cache_read"] or 0) / 1e6) * price.get("cached", 0)
    return cost


def cost_metrics(trials, price):
    costs = [c for c in (cost_of_trial(t.get("tokens"), price) for t in trials) if c is not None]
    n_ok = sum(1 for t in trials if t.get("success"))
    total = sum(costs)
    out = {"coverage": round(len(costs) / len(trials), 4) if trials else None,
           "cost_per_trial": round(total / len(costs), 6) if costs else None,
           "cost_total": round(total, 6) if costs else None,
           "cost_per_success": round(total / n_ok, 6) if costs and n_ok else None}
    return out


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
    return (round(mad / med * 100, 3) if med else None), len(vals)


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
        g = load_grade(t)
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
def per_arm(trials, partial_tasks=frozenset(), task_scoring=None, price=None):
    arms = {}
    for arm in sorted({t.get("arm", "?") for t in trials}):
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


def build_summary(out_dir, price=None):
    """Tổng hợp 1 results dir → dict summary (ghi summary.json + in dashboard)."""
    trials = load_trials(out_dir)
    partial = set()
    task_scoring = {}
    for tid in {t["task"] for t in trials}:
        d = resolve_task_dir(tid)
        if d:
            if task_is_partial(d):
                partial.add(tid)
            task_scoring[tid] = gold_scoring(d)
    # gắn scoring/answer vào trial cho A2 (thuần hoá dữ liệu 1 lần)
    for t in trials:
        t.setdefault("_scoring", task_scoring.get(t["task"]))
        t.setdefault("_answer", load_answer(t))
    cfg_path = os.path.join(HERE, "bench_config.json")
    price = price or {}
    if not price and os.path.exists(cfg_path):
        try:
            price = json.load(open(cfg_path, encoding="utf-8")).get("price_per_1m") or {}
        except json.JSONDecodeError:
            price = {}
    return {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "out_dir": os.path.abspath(out_dir),
        "model": (json.load(open(cfg_path, encoding="utf-8")).get("model")
                  if os.path.exists(cfg_path) else None),
        "n_trials": len(trials),
        "partial_tasks": sorted(partial),
        "arms": per_arm(trials, partial, task_scoring, price),
    }


def print_summary(summary):
    print("=" * 78)
    print("METRICS PHỤ (A1–A4 dashboard · B1–B6 chi tiết trong summary.json)")
    for arm, m in sorted(summary["arms"].items()):
        dnf, te, fr = m["dnf"], m["tool_economy"], m["false_refusal"]
        tax = m["error_taxonomy"]
        top_err = ", ".join("%s %.0f%%" % (k, v * 100)
                            for k, v in list(tax["share"].items())[:3]) or "-"
        tp = m["token_profile"]
        print("-" * 78)
        print("%-11s n=%d | success: all=%.0f%% answered=%.0f%% | DNF=%.0f%%" % (
            arm, m["n"], (dnf["success_all"] or 0) * 100,
            (dnf["success_answered"] or 0) * 100, (dnf["dnf_rate"] or 0) * 100))
        print("  A1 lỗi (trên %d fail): %s" % (tax["n_fail"], top_err))
        print("  A2 từ chối oan: %s/%s (value-task có dữ liệu)" % (
            fr["false_refusals"], fr["denominator"]))
        print("  A4 mcp_calls p50=%s p90=%s (đúng=%s/sai=%s) | retry=%.0f%% | mcp=0: %d" % (
            te["p50"], te["p90"], te["p50_success"], te["p50_fail"],
            (te["retry_rate"] or 0) * 100, te["zero_mcp_answered"]))
        cov = tp["coverage"]
        print("  B2 tokens p50 in/out: %s/%s (coverage %.0f%%)" % (
            tp["p50_input"], tp["p50_output"], (cov or 0) * 100))
        if m["cost"] and m["cost"]["cost_per_trial"] is not None:
            print("  B3 cost/trial=$%.4f · cost/success=$%.4f (coverage %.0f%%)" % (
                m["cost"]["cost_per_trial"], m["cost"]["cost_per_success"] or 0,
                (m["cost"]["coverage"] or 0) * 100))
        else:
            print("  B3 cost: N/A (thiếu usage)")
        d4 = m["dispersion"]
        print("  B4 phân tán đáp án (pass-only, per-task median): %s (task có spread: %s)" % (
            ("MAD %.3f%%" % d4["mad_pct"]) if d4["mad_pct"] is not None else "N/A",
            d4.get("n_tasks_with_spread", 0)))
        b5 = m["bonus"]
        if b5["n_refused_ok"]:
            print("  B5 bonus kỳ thay thế: %d/%d (%.0f%%)" % (
                b5["hit"], b5["n_refused_ok"], (b5["rate"] or 0) * 100))
        pc = m["per_check"]
        if pc:
            line = " · ".join("%s %.0f%%" % (k, v["pass_rate"] * 100) for k, v in pc.items())
            print("  B1 checks: %s" % line)
    print("=" * 78)


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
