import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import judge_primary as jp  # noqa: E402

GROWTH = jp.task_gold('fin-l2-growth-01')    # value -2.03 abs 0.1
TRAP = jp.task_gold('fin-l4-nonexist-01')    # refusal


def row(task, **kw):
    base = {'trial_id': task + '__a__r1', 'arm': 'a', 'task': task, 'run': 1, 'status': 'ok',
            'success': False, 'public_contract_valid': False, 'fp': 0}
    base.update(kw)
    return base


def score(r, verdict, text, gold, review=None):
    return jp.score_trial(r, {'verdict': verdict, '_answer_text': text}, gold, review, Path('/nonexistent'))


def test_numeric_gate_vetoes_judge_correct():
    out = score(row('fin-l2-growth-01'), 'correct', '{"value": -2.5, "unit": "%"}', GROWTH)
    assert out['numeric_gate'] is False and out['primary'] is False


def test_format_agnostic_prose_answer_passes_with_gate():
    out = score(row('fin-l2-growth-01'), 'correct', 'Doanh thu giảm -2.0276% (Q3/2026 so với Q2/2026).', GROWTH)
    assert out['numeric_gate'] is True and out['primary'] is True


def test_trap_numeric_value_is_fp_even_if_judge_correct():
    out = score(row('fin-l4-nonexist-01'), 'correct', '{"value": 12000, "reason": "x"}', TRAP)
    assert out['fp'] is True and out['primary'] is False
    ok = score(row('fin-l4-nonexist-01'), 'correct', '{"value": null, "reason": "không tồn tại"}', TRAP)
    assert ok['primary'] is True and ok['fp'] is False


def test_false_refusal_and_dnf_stay_in_denominator():
    fr = score(row('fin-l2-growth-01'), 'incorrect', '{"value": null, "reason": "chưa có"}', GROWTH)
    assert fr['false_refusal'] is True and fr['primary'] is False
    dnf = score(row('fin-l2-growth-01', status='error'), 'no_answer', '', GROWTH)
    assert dnf['dnf'] is True and dnf['primary'] is False
    s = jp.summarize([fr, dnf], 'a', 10)
    assert s['a']['scheduled'] == 2 and s['a']['dnf'] == 1


def test_manual_review_only_removes():
    r = row('fin-l2-growth-01')
    rej = score(r, 'correct', '{"value": -2.03}', GROWTH, {r['trial_id']: {'pass': False}})
    assert rej['primary'] is False and rej['manual_rejected'] is True
    keep = score(r, 'incorrect', '{"value": -2.03}', GROWTH, {r['trial_id']: {'pass': True}})
    assert keep['primary'] is False
