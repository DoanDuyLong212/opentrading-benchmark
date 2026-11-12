# -*- coding: utf-8 -*-
"""Test tools/metrics.py — các hàm tính metric A1–A4 + B1–B6 (thuần, fixture tổng hợp).

Chạy: python3 -m pytest tools/tests/test_metrics.py -q
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import metrics as M  # noqa: E402


# ---------------------------------------------------------------- helpers
def trial(task="fin-t", arm="opencode", status="ok", success=True, fp=0, error_type=None,
          mcp=2, attempt=1, wall=100_000, tokens=None, answer=None, scoring="value",
          ws="results/x/trials/fin-t__a__r1/ws", src="file"):
    return {"task": task, "arm": arm, "run": 1, "status": status, "success": success,
            "fp": fp, "error_type": error_type, "wall_ms": wall, "mcp_calls": mcp,
            "attempt": attempt, "tokens": tokens, "answer_source": src,
            "workspace": ws, "_answer": answer, "_scoring": scoring}


def pct(values, p):
    return M.percentile(sorted(values), p)


# ---------------------------------------------------------------- percentile
def test_percentile_basic():
    assert pct([1, 2, 3, 4, 5], 50) == 3
    assert pct([1, 2, 3, 4, 5], 90) == 5
    assert pct([10, 20], 50) == 10  # làm tròn xuống — nearest-rank
    assert M.percentile([], 50) is None


# ---------------------------------------------------------------- A3 DNF + 2 mẫu số
def test_dnf_and_two_denominators():
    trials = [trial(status="ok", success=True), trial(status="ok", success=False),
              trial(status="timeout", success=False, error_type=None),
              trial(status="error", success=False, error_type="grader_error")]
    a3 = M.dnf_rate(trials)
    assert a3["n"] == 4
    assert a3["dnf"] == 2 and a3["dnf_rate"] == 0.5
    assert a3["success_all"] == 0.25          # 1/4
    assert a3["success_answered"] == 0.5      # 1/2 (loại DNF)


# ---------------------------------------------------------------- A1 error taxonomy
def test_error_taxonomy():
    trials = [trial(status="ok", success=False, error_type="sai_don_vi"),
              trial(status="ok", success=False, error_type="sai_don_vi"),
              trial(status="ok", success=False, error_type="sai_ky"),
              trial(status="timeout", success=False, error_type=None),
              trial(status="ok", success=True)]
    tax = M.error_taxonomy(trials)
    assert tax["n_fail"] == 4
    assert tax["counts"] == {"sai_don_vi": 2, "sai_ky": 1, "timeout": 1}
    assert tax["share"]["sai_don_vi"] == 0.5


# ---------------------------------------------------------------- A4 tool economy
def test_tool_economy_and_retry():
    trials = [trial(mcp=1, success=True), trial(mcp=3, success=True), trial(mcp=9, success=False),
              trial(mcp=0, status="timeout", success=False), trial(mcp=2, attempt=3, success=True)]
    te = M.tool_economy(trials)
    assert te["p50"] == 2 and te["p90"] == 9
    assert te["p50_success"] == 2      # 1,3,2 → sorted [1,2,3] p50=2
    assert te["retry_rate"] == 0.2     # 1/5 attempt>1
    assert te["zero_mcp_answered"] == 0  # trial mcp=0 là DNF (timeout), không phải answered


# ---------------------------------------------------------------- A2 false refusal
def test_false_refusal_classification():
    # value task, agent trả value=null → từ chối oan
    t_refuse = trial(answer={"value": None, "reason": "chưa có"}, status="ok", success=False,
                     error_type="khong_tra_loi")
    assert M.is_false_refusal(t_refuse) is True
    # value task, trả số sai → KHÔNG phải từ chối
    t_wrong = trial(answer={"value": 4.0}, status="ok", success=False, error_type="sai_so")
    assert M.is_false_refusal(t_wrong) is False
    # refusal task (trap) → loại khỏi mẫu
    t_trap = trial(answer={"value": None, "reason": "chưa công bố"}, scoring="refusal",
                   status="ok", success=True)
    assert M.is_false_refusal(t_trap) is False
    # DNF → không phải từ chối
    t_dnf = trial(answer=None, status="timeout", success=False)
    assert M.is_false_refusal(t_dnf) is False


def test_false_refusal_rate_excludes_partial_tasks(tmp_path):
    # task POM-like: payload availability partial → loại khỏi mẫu số
    trials = [trial(task="fin-partial", answer={"value": None, "reason": "x"}, status="ok"),
              trial(task="fin-normal", answer={"value": None, "reason": "x"}, status="ok"),
              trial(task="fin-normal", answer={"value": 5.0}, status="ok", success=True)]
    partial = {"fin-partial"}
    rate = M.false_refusal_rate(trials, partial_tasks=partial)
    assert rate["denominator"] == 2          # fin-normal answered ×2 (1 từ chối + 1 đúng)
    assert rate["false_refusals"] == 1       # fin-partial bị loại khỏi mẫu
    assert rate["rate"] == 0.5


# ---------------------------------------------------------------- B5 bonus rate
def test_bonus_rate(tmp_path):
    d = tmp_path / "t1"; d.mkdir()
    (d / "grade.json").write_text(json.dumps(
        {"success": True, "fp": 0, "bonus": {"hit": True, "strings": ["Q3/2026"]}}), encoding="utf-8")
    trials = [trial(scoring="refusal", success=True, ws=str(d) + "/ws")]
    br = M.bonus_replacement_rate(trials, grade_path=lambda t: str(d / "grade.json"))
    assert br["hit"] == 1 and br["rate"] == 1.0


# ---------------------------------------------------------------- B2/B3 tokens + cost
def test_token_normalize_shapes():
    oc = M.norm_tokens({"input": 100, "output": 50, "reasoning": 10, "cache": {"read": 7}})
    assert oc == {"input": 100, "output": 50, "reasoning": 10, "cache_read": 7}
    ot = M.norm_tokens({"contextTokens": 900, "total": {"input": 200, "output": 60}})
    assert ot == {"input": 200, "output": 60, "reasoning": None, "cache_read": None}
    assert M.norm_tokens(None) is None


def test_cost_per_success():
    trials = [trial(tokens={"input": 1_000_000, "output": 1_000_000, "cache_read": 0}, success=True),
              trial(tokens={"input": 1_000_000, "output": 1_000_000, "cache_read": 0}, success=False)]
    price = {"input": 0.15, "output": 0.60, "cached": 0.003}  # USD / 1M
    c = M.cost_metrics(trials, price)
    # mỗi trial: 1M*0.15 + 1M*0.60 = 0.75 USD → tổng 1.5
    assert c["coverage"] == 1.0
    assert c["cost_per_trial"] == pytest.approx(0.75)
    assert c["cost_per_success"] == pytest.approx(1.5)  # 1.5 tổng / 1 success


# ---------------------------------------------------------------- B4 dispersion
def test_dispersion_passed_only():
    trials = [trial(answer={"value": 5.08}, success=True),
              trial(answer={"value": 5.09}, success=True),
              trial(answer={"value": 5.10}, success=True),
              trial(answer={"value": 99.0}, success=False)]  # fail loại khỏi mẫu
    d = M.answer_dispersion(trials)
    assert d["n_tasks_with_spread"] == 1
    assert d["mad_pct"] == pytest.approx(0.196, abs=0.01)  # MAD(0.01)/median(5.09)*100


def test_dispersion_per_task_khong_tron_dai_luong():
    """2 task có đại lượng KHÁC NHAU (CPI 5% vs giá 16000) — MAD phải tính per task
    rồi lấy median, không được trộn (trộn sẽ ra MAD vô nghĩa hàng trăm %)."""
    trials = [trial(task="cpi", answer={"value": 5.08}, success=True),
              trial(task="cpi", answer={"value": 5.12}, success=True),
              trial(task="gia", answer={"value": 16000}, success=True),
              trial(task="gia", answer={"value": 16050}, success=True)]
    d = M.answer_dispersion(trials)
    # cpi: MAD 0.02/5.10 = 0.392% ; gia: MAD 25/16025 = 0.156% → median 0.274%
    assert d["n_tasks_with_spread"] == 2
    assert d["mad_pct"] == pytest.approx(0.274, abs=0.01)


# ---------------------------------------------------------------- task resolution
def test_resolve_task_dir():
    d = M.resolve_task_dir("fin-l1-macro-01")
    assert d is not None and os.path.isdir(d)
    assert M.resolve_task_dir("fin-khong-ton-tai-999") is None


def test_gold_scoring_and_partial():
    d = M.resolve_task_dir("fin-l1-macro-01")
    assert M.gold_scoring(d) == "value"
    d2 = M.resolve_task_dir("fin-l5-valuation-300")
    assert M.gold_scoring(d2) == "value"
    # POM: payloads có availability partial → partial-task
    assert M.task_is_partial(d2) is True
    assert M.task_is_partial(d) is False


@pytest.mark.parametrize('field', ['values.VCB', 'ranking', 'items'])
def test_uniform_public_refusal_branch_counts_on_aggregate_answerable_tasks(field):
    row=trial(scoring='values',answer={'value':None,'reason':'No supported data retrieved','evidence':[]})
    row['_answerable_fields']=[field]
    assert M.is_false_refusal(row)
    row['_answer']={'evidence':[]}
    assert not M.is_false_refusal(row)
    row['_answer']={'value':'null','reason':'Malformed string null'}
    assert not M.is_false_refusal(row)

