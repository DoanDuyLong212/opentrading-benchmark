"""Offline tests for the secondary LLM judge (no network)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import grade_run_llm  # noqa: E402
import llm_judge  # noqa: E402

PILOT = ROOT / 'tasks' / 'pilot'


def gold(name):
    return json.loads((PILOT / name / 'solution/gold.json').read_text())


def fake_call(log):
    def call(user, model=llm_judge.JUDGE_MODEL):
        log.append(user)
        return {'verdict': 'correct' if '14550.96' in user.split('CÂU TRẢ LỜI CẦN CHẤM:')[1] else 'incorrect',
                'reason': 'x', 'failed_fields': [], 'returned_model': model, 'usage': {}}
    return call


def test_cache_distinguishes_answers_of_same_task():
    calls, cache = [], {}
    g = gold('fin-l1-bctc-01')
    a = llm_judge.judge_answer(PILOT / 'fin-l1-bctc-01', g, '{"value": 14550.96}', cache=cache, call=fake_call(calls))
    b = llm_judge.judge_answer(PILOT / 'fin-l1-bctc-01', g, '{"value": 999}', cache=cache, call=fake_call(calls))
    c = llm_judge.judge_answer(PILOT / 'fin-l1-bctc-01', g, '{"value": 14550.96}', cache=cache, call=fake_call(calls))
    assert (a['verdict'], b['verdict'], c['verdict']) == ('correct', 'incorrect', 'correct')
    assert len(calls) == 2 and c['cached'] and a['cache_key'] != b['cache_key']


def test_prompt_carries_full_question_and_refusal_reference():
    user = llm_judge.build_prompt(llm_judge.public_question(PILOT / 'fin-l4-future-01'), gold('fin-l4-future-01'), 'x')
    assert 'quý 4/2026' in user and '"scoring": "refusal"' in user and 'chưa công bố' in user
    assert '## Ràng buộc chung' not in user
    growth = llm_judge.build_prompt(llm_judge.public_question(PILOT / 'fin-l2-growth-01'), gold('fin-l2-growth-01'), 'x')
    assert 'Nêu rõ hai quý đối chiếu' in growth and '"tol"' in growth and 'financial_statements' not in growth.split('ĐÁP ÁN CHUẨN')[1].split('CÂU TRẢ LỜI')[0].split('"notes"')[0]


def test_numeric_prepass_uses_expect_tolerance():
    g = gold('fin-l2-growth-01')  # gold -2.03 abs 0.1
    assert llm_judge.numeric_prepass('```json\n{"value": -2.0276}\n```', g)['all_ok'] is True
    assert llm_judge.numeric_prepass('Kết quả: {"value": -2.2}', g)['all_ok'] is False
    assert llm_judge.numeric_prepass('không có json', g) == {'parsed': False, 'fields': {}, 'all_ok': False}


@pytest.mark.parametrize('text,expected', [
    ('suy luận {"a": 1} ... {"verdict":"partial","reason":"thiếu kỳ","failed_fields":["period"]}', 'partial'),
    ('{"verdict":"correct","reason":"ok"}\nfinal {"verdict":"incorrect","reason":"sai số"}', 'incorrect'),
    ('{"verdict":"maybe"}', None),
])
def test_parse_verdict_takes_last_valid_object(text, expected):
    got = llm_judge.parse_verdict(text)
    assert (got[0] if got else None) == expected


def test_graded_attempt_selection_and_no_answer(tmp_path):
    run = tmp_path / 'run'
    for n, text in ((1, 'first'), (2, 'second')):
        d = run / 'trials' / 't1' / 'attempts' / ('%02d-abc' % n)
        d.mkdir(parents=True)
        (d / 'result.json').write_text(json.dumps({'final_text': text}))
    assert grade_run_llm.graded_attempt_text(run, {'trial_id': 't1', 'attempt': 1})[0] == 'first'
    assert grade_run_llm.graded_attempt_text(run, {'trial_id': 't1', 'attempt': 2})[0] == 'second'
    assert grade_run_llm.graded_attempt_text(run, {'trial_id': 'none'})[0] == ''


def test_grade_run_never_calls_model_without_answer_and_resumes(tmp_path):
    run = tmp_path / 'run'
    run.mkdir()
    rows = [{'trial_id': 'fin-l1-bctc-01__dsh__r1', 'task': 'fin-l1-bctc-01', 'arm': 'dsh', 'run': 1,
             'attempt': 1, 'success': True},
            {'trial_id': 'fin-l1-bctc-01__opencode__r1', 'task': 'fin-l1-bctc-01', 'arm': 'opencode', 'run': 1,
             'attempt': 1, 'success': False}]
    (run / 'trials.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    d = run / 'trials' / rows[0]['trial_id'] / 'attempts' / '01-x'
    d.mkdir(parents=True)
    (d / 'result.json').write_text(json.dumps({'final_text': '{"value": 14550.96}'}))
    calls = []
    s = grade_run_llm.grade_run(run, pause=0, call=fake_call(calls))
    assert len(calls) == 1 and s['verdicts'] == {'correct': 1, 'no_answer': 1}
    assert s['disagreements']['content_fail_judge_correct'] == 0 and s['judged_trials'] == 1
    s2 = grade_run_llm.grade_run(run, pause=0, resume=True, call=fake_call(calls))
    assert len(calls) == 1 and s2['trials'] == 2


def test_free_model_falls_back_to_paid_on_quota(monkeypatch):
    import urllib.error
    seen = []
    def post(body, key, timeout):
        seen.append(body['model'])
        if body['model'].endswith(':free'):
            raise urllib.error.HTTPError('u', 429, 'quota', {}, None)
        return {'model': body['model'], 'choices': [{'message': {'content': '{"verdict":"correct","reason":"ok"}'},
                                                     'finish_reason': 'stop'}], 'usage': {}}
    import llm_judge as j
    monkeypatch.setattr(j.time, 'sleep', lambda s: None)
    r = j.call_judge('x', model=j.JUDGE_MODEL_PAID + ':free', key='k', retries=1, post=post)
    assert r['verdict'] == 'correct' and r['returned_model'] == j.JUDGE_MODEL_PAID and r['fallback_from'].endswith(':free')
    assert seen[-1] == j.JUDGE_MODEL_PAID


def test_holdout_judge_never_uses_free_endpoint_and_denies_data_collection():
    import llm_judge as j
    bodies = []
    def post(body, key, timeout):
        bodies.append(body)
        return {'model': body['model'], 'choices': [{'message': {'content': '{"verdict":"correct","reason":"ok"}'},
                                                     'finish_reason': 'stop'}], 'usage': {}}
    r = j.call_judge('x', model=j.JUDGE_MODEL_PAID + ':free', key='k', post=post, deny_data_collection=True)
    assert r['verdict'] == 'correct'
    assert bodies[0]['model'] == j.JUDGE_MODEL_PAID and bodies[0]['provider'] == {'data_collection': 'deny'}
