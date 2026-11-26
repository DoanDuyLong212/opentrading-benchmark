"""Amendment 2026-11-25 (d): investor stratum (I) and groups A-E."""
import hashlib, json, subprocess, sys
from pathlib import Path

import pytest

STUDY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDY / 'tools'))
INV = sorted(STUDY.glob('tasks/*/fin-i[1-5]-*'))
PARTIAL = sorted(STUDY.glob('tasks/*/fin-l4-partial-*'))


def test_inventory_and_preregistration():
    import investor_specs_20261125 as sp
    assert len([p for p in INV if p.parent.name == 'main']) == 20 and len([p for p in INV if p.parent.name == 'pilot']) == 5
    ext = STUDY / 'audits/snapshot-extension-2026-11-25b'
    assert hashlib.sha256((ext / 'post-20261125.json').read_bytes()).hexdigest() == sp.POST_SHA256
    assert hashlib.sha256((ext / 'pre-120.json').read_bytes()).hexdigest() == sp.PRE_SHA256
    assert {s['tid'] for s in sp.SPECS} == {p.name for p in INV}


@pytest.mark.parametrize('task', INV, ids=lambda p: p.name)
def test_no_post_snapshot_data_served_and_oracle(task):
    tools = json.loads((task / 'environment/payloads.json').read_text())['tools']
    for entry in tools.values():
        for row in entry['envelope']['data'].get('closes', []):
            assert row['t'] <= '2026-10-30'
        assert 'Q3/2026' not in entry['envelope']['data'].get('periods', [])
    text = (task / 'instruction.md').read_text() + (task / 'environment/payloads.json').read_text()
    post = json.loads((STUDY / 'audits/snapshot-extension-2026-11-25b/post-20261125.json').read_text())
    gold = json.loads((task / 'solution/gold.json').read_text())
    for s in gold['solution']['candidates']:
        assert '"t": "%s"' % post[s][-1]['t'] not in text
    assert gold['scoring'] == 'outcome' and gold['stratum'] == 'investor'
    done = subprocess.run([sys.executable, str(task / 'solution/oracle.py')], capture_output=True, text=True, timeout=60)
    assert 'ORACLE OK' in done.stdout, done.stdout + done.stderr


@pytest.mark.parametrize('task', [p for p in INV if p.parent.name == 'main'], ids=lambda p: p.name)
def test_outcome_rule_passes_winners_and_fails_losers(task, tmp_path):
    import itertools
    gold = json.loads((task / 'solution/gold.json').read_text())
    exp = gold['expects'][0]
    key = exp['path'].split('.')[1]
    pool = gold['solution']['candidates']
    win = exp['accept_sets'][0]
    lose = next((sorted(c) for c in itertools.combinations(pool, exp['size']) if sorted(c) not in exp['accept_sets']), None)
    def ans(x):
        return {'values': {key: x[0] if exp['size'] == 1 else list(x)}, 'source': 'vn_quote_history', 'reason': 'mô phỏng'}
    win_res = _run(task, ans(win), tmp_path / 'w')
    assert win_res['success'] is True, win_res
    if lose is not None:
        assert _run(task, ans(lose), tmp_path / 'l')['success'] is False
    assert _run(task, {'values': {key: None}, 'source': 'vn_quote_history', 'reason': 'không chọn'}, tmp_path / 'n')['success'] is False
    if exp['size'] > 1:
        assert _run(task, ans(win[:-1]), tmp_path / 'c')['success'] is False


def _run(task, answer, tmp):
    gold = json.loads((task / 'solution/gold.json').read_text())
    gold['provenance_contract'] = []
    (tmp / 'solution').mkdir(parents=True); (tmp / 'tests').mkdir()
    (tmp / 'solution/gold.json').write_text(json.dumps(gold, ensure_ascii=False))
    (tmp / 'tests/grader.py').write_bytes((task / 'tests/grader.py').read_bytes())
    (tmp / 'tests/answer.json').write_text(json.dumps(answer, ensure_ascii=False))
    subprocess.run([sys.executable, 'grader.py'], cwd=tmp / 'tests', capture_output=True, text=True, timeout=60, check=True)
    return json.loads((tmp / 'tests/grade.json').read_text())


def test_judge_primary_uses_deterministic_rule_for_outcome_and_partial():
    import judge_primary as jp
    row = {'trial_id': 't', 'arm': 'a', 'task': 'x', 'status': 'ok', 'success': True}
    graded = {'_answer_text': '{"values": {"pick": "VCB"}}', 'verdict': 'incorrect'}
    for gold in ({'scoring': 'outcome', 'stratum': 'investor'}, {'scoring': 'value', 'primary_rule': 'deterministic', 'stratum': 'lookup'}):
        assert jp.score_trial(row, graded, gold, {}, Path('/nonexistent'))['primary'] is True
        assert jp.score_trial(dict(row, success=False), dict(graded, verdict='correct'), gold, {}, Path('/nonexistent'))['primary'] is False


@pytest.mark.parametrize('task', PARTIAL, ids=lambda p: p.name)
def test_partial_traps_need_value_and_null(task, tmp_path):
    gold = json.loads((task / 'solution/gold.json').read_text())
    served = gold['solution']['served']
    base = {'values': {'served': served, 'missing': None}, 'unit': 'x', 'period': 'x',
            'source': gold['expects'][-1]['accept'][0], 'reason': 'Kỳ/phiên này chưa có trong dữ liệu snapshot.'}
    assert _run(task, base, tmp_path / 'ok')['success'] is True
    assert _run(task, dict(base, values={'served': served, 'missing': served}), tmp_path / 'fab')['success'] is False
    assert _run(task, dict(base, values={'served': None, 'missing': None}), tmp_path / 'over')['success'] is False
    assert _run(task, dict(base, reason=''), tmp_path / 'noreason')['success'] is False


R_TASKS = sorted(STUDY.glob('tasks/*/fin-r1-call-*'))


def test_recommendation_inventory_and_rule():
    import recommend_specs_20261125 as rs
    assert {s['tid'] for s in rs.SPECS} == {p.name for p in R_TASKS}
    assert [sum(p.parent.name == s for p in R_TASKS) for s in ('main', 'holdout', 'pilot')] == [16, 4, 1]


@pytest.mark.parametrize('task', R_TASKS, ids=lambda p: p.name)
def test_recommendation_call_scoring(task, tmp_path):
    gold = json.loads((task / 'solution/gold.json').read_text())
    sol = gold['solution']
    ret = sol['ret_pct']
    assert sol['call'] == ('MUA' if ret > 2 else 'BÁN' if ret < -2 else 'GIỮ')
    assert gold['scoring'] == 'outcome' and gold['tier'] == 'R'
    done = subprocess.run([sys.executable, str(task / 'solution/oracle.py')], capture_output=True, text=True, timeout=60)
    assert 'ORACLE OK' in done.stdout, done.stdout + done.stderr
    for call in ('MUA', 'GIỮ', 'BÁN'):
        ans = {'values': {'call': call}, 'source': 'vn_quote_history', 'reason': 'mô phỏng'}
        assert _run(task, ans, tmp_path / call)['success'] is (call == sol['call'])
    assert _run(task, {'values': {'call': None}, 'source': 'vn_quote_history', 'reason': 'x'}, tmp_path / 'null')['success'] is False
