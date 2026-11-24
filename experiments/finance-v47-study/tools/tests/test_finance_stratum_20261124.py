"""Amendment 2026-11-24: fundamental compute (C5), finance memory (M6), PRUNE2 and the statement extension."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

STUDY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDY / 'tools'))
NEW = sorted(list((STUDY / 'tasks').glob('*/fin-c5-*')) + list((STUDY / 'tasks').glob('*/fin-m6-*')))
QUARTERS = {'Q3/2024', 'Q4/2024', 'Q1/2025', 'Q2/2025', 'Q3/2025', 'Q4/2025', 'Q1/2026', 'Q2/2026'}
YEARS = {'2021', '2022', '2023', '2024', '2025'}


def test_inventory():
    names = {p.name for p in NEW}
    assert sum(1 for p in NEW if p.parent.name == 'main') == 26 and sum(1 for p in NEW if p.parent.name == 'pilot') == 6
    assert len(names) == 32


@pytest.mark.parametrize('task', NEW, ids=lambda p: p.name)
def test_oracle_and_payload_rules(task):
    done = subprocess.run([sys.executable, str(task / 'solution/oracle.py')], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0 and 'ORACLE OK' in done.stdout, done.stdout + done.stderr
    tools = json.loads((task / 'environment/payloads.json').read_text())['tools']
    assert tools and all(e['tool'] == 'financial_statements' for e in tools.values())
    for entry in tools.values():
        data = entry['envelope']['data']
        assert entry['params']['statement'] in ('KQKD', 'CDKT')
        assert set(data['periods']) <= (QUARTERS if entry['params']['period'] == 'quarter' else YEARS)
        assert list(data['statements']) == [{'KQKD': 'Kết quả kinh doanh', 'CDKT': 'Báo cáo tình hình tài chính'}[entry['params']['statement']]]
        for rows in data['statements'].values():
            for row in rows:
                assert set(row['values']) == set(data['periods'])
    gold = json.loads((task / 'solution/gold.json').read_text())
    assert not any(e['type'] == 'period' for e in gold['expects'])


def test_m6_answers_depend_on_memory():
    """Using the other ROE convention, or ignoring an update/revoke, changes the graded pass set."""
    import build_finance_stratum_20261124 as b
    main, pilot = b.build()
    for t in main + pilot:
        if t['kind'] != 'M6':
            continue
        sol = t['q']['solution']
        syms = list(sol['values'])
        c = b.Ctx(b.payloads(syms, {('q', 'KQKD'), ('q', 'CDKT'), ('y', 'KQKD'), ('y', 'CDKT')}))
        other = 'fy' if sol['convention'] == 'ttm' else 'ttm'
        dr = {s: c.debt_ratio(s) for s in syms}
        wrong = sorted(s for s in syms if b.roe_by(c, other, s) > sol['roe_min'] and (sol['debt_max'] is None or dr[s] < sol['debt_max']))
        assert wrong != sol['pass'], t['tid']
        last = t['sessions'][-1]['turns'][-1]
        assert last.get('final') and 'theo đúng cách tính tôi đã dặn' in last['text']


def test_prune2_receipt():
    import prune_saturated_20261124 as p2
    result = p2.validate()
    assert result['valid'] and result['retired'] == 120 and result['main'] == 106
    assert result['composition'] == {'compute': 39, 'lookup': 10, 'memory': 27, 'safety': 30}


def test_statement_extension_receipt():
    receipt = json.loads((STUDY / 'audits/snapshot-extension-2026-11-24/RECEIPT.json').read_text())
    check = receipt['cross_check']
    assert check['matches'] > 100 and check['mismatches_with_real_snapshot'] == 0
    assert all(any(s.startswith('synthetic') for s in m['frozen_source']) for m in check['mismatches'])
