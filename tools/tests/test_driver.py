# -*- coding: utf-8 -*-
"""Test cho tools/run_benchmark.py — driver benchmark.

Chạy: python3 -m pytest tools/tests/test_driver.py -q
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import run_benchmark as rb  # noqa: E402

PILOT = os.path.join(ROOT, "tasks", "pilot")


# ---------------------------------------------------------------- select_tasks
def test_select_all_pilot_sorted():
    tasks = rb.select_tasks("pilot", sample=None, seed=None, tasks_filter=None)
    ids = [os.path.basename(t) for t in tasks]
    assert len(ids) == 22 and ids == sorted(ids)
    assert 'fin-l1-macro-01' not in ids  # ambiguous CPI series is quarantined
    assert 'fin-l4-narrative-01' not in ids  # incomplete narrative evidence rubric


def test_select_sample_deterministic():
    a = rb.select_tasks("pilot", sample=5, seed=20261102, tasks_filter=None)
    b = rb.select_tasks("pilot", sample=5, seed=20261102, tasks_filter=None)
    assert [os.path.basename(x) for x in a] == [os.path.basename(x) for x in b]
    assert len(a) == 5


def test_select_tasks_filter_unknown_raises():
    with pytest.raises(ValueError):
        rb.select_tasks("pilot", sample=None, seed=None, tasks_filter=["fin-l9-khong-tontai"])


def test_select_holdout_requires_confirm():
    with pytest.raises(SystemExit):
        rb.select_tasks("holdout", sample=None, seed=None, tasks_filter=None, confirm_holdout=False)
    tasks = rb.select_tasks("holdout", sample=None, seed=None, tasks_filter=None, confirm_holdout=True)
    assert len(tasks) == 43


# ---------------------------------------------------------------- workspace
def test_make_workspace_only_instruction(tmp_path):
    task_dir = os.path.join(PILOT, "fin-l1-macro-01")
    ws = rb.make_workspace(tmp_path, task_dir)
    entries = sorted(os.listdir(ws))
    assert entries == ["instruction.md"], "workspace chỉ được chứa instruction.md"
    instr = open(os.path.join(ws, "instruction.md"), encoding="utf-8").read()
    assert "Ràng buộc chung" in instr


# ---------------------------------------------------------------- extract answer (opentrading arm)
def test_extract_fenced_json():
    text = '```json\n{"value": 5.08, "unit": "%", "period": "tháng 9/2026"}\n```'
    ans = rb.extract_answer_json(text)
    assert ans == {"value": 5.08, "unit": "%", "period": "tháng 9/2026"}


def test_extract_inline_object():
    text = '{"value": 2015.37, "unit": "triệu đồng"}'
    ans = rb.extract_answer_json(text)
    assert ans["value"] == 2015.37


def test_extract_prefers_object_with_answer_keys():
    text = '{"a": 1} rồi {"value": 3}'
    ans = rb.extract_answer_json(text)
    assert ans is None


def test_extract_refusal_style():
    text = '{"value": null, "reason": "Q4/2026 chưa được công bố"}'
    ans = rb.extract_answer_json(text)
    assert ans["value"] is None and "chưa" in ans["reason"]


def test_extract_none_when_no_json():
    assert rb.extract_answer_json("Tôi không trả lời được.") is None


# ---------------------------------------------------------------- grading wiring
def test_grade_trial_with_real_grader(tmp_path):
    """Đi qua grader THẬT của 1 task pilot với answer tổng hợp đúng → success=True."""
    from build_main import synthesize

    task_dir = os.path.join(ROOT, "tasks", "pilot", "fin-l1-quote-01")
    gold = json.load(open(os.path.join(task_dir, "solution", "gold.json")))
    ans = synthesize(gold)
    ans['evidence'] = [dict(row, call_id='offline-fixture', payload_sha256=gold['payload_sha256'])
                       for row in gold['provenance_contract']]
    ap = tmp_path / "answer.json"
    ap.write_text(json.dumps(ans, ensure_ascii=False), encoding="utf-8")
    res = rb.grade_answer(str(ap), task_dir, out_dir=str(tmp_path))
    assert res["success"] is True
    assert os.path.exists(res["grade_path"])


def test_grade_trial_missing_answer(tmp_path):
    res = rb.grade_answer(str(tmp_path / "khong-ton-tai.json"),
                          os.path.join(ROOT, "tasks", "pilot", "fin-l1-quote-01"),
                          out_dir=str(tmp_path))
    assert res["success"] is False


# ---------------------------------------------------------------- path invariants
def test_retry_only_identifiable_transient_errors():
    assert rb.transient_failure({'status':'error'}, 'HTTP 429 too many requests')
    assert rb.transient_failure({'status':'error'}, 'HTTP 503 service unavailable')
    assert not rb.transient_failure({'status':'runner_error'}, 'TypeError unexpected argument')
    assert not rb.transient_failure({'status':'error'}, 'HTTP 401 invalid api key')
    assert not rb.transient_failure({'status':'error'}, 'HTTP 400 unsupported effort; prior 429')
    assert not rb.transient_failure({'status':'error', 'final_text':'{"value":2}'}, '429')


def test_workspace_reuse_rejected(tmp_path):
    rb.make_workspace(tmp_path, os.path.join(PILOT, 'fin-l1-macro-01'))
    (tmp_path/'answer.json').write_text('{"value": 12}')
    with pytest.raises(ValueError, match='empty'):
        rb.make_workspace(tmp_path, os.path.join(PILOT, 'fin-l1-macro-01'))


def test_multiple_answer_objects_are_invalid():
    assert rb.extract_answer_json('{"value": 1} {"value": 2}') is None
