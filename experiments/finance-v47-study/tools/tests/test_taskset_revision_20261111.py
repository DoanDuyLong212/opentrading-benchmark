"""Amendment 2026-11-11 (d): task-set revision, compute stratum, native-memory stratum."""
import json
import tomllib
from historical_fixtures import LEGACY_STUDY, RETIRED
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/runners')]
from run_manifest import task_eligibility  # noqa: E402
from provider import native_tool_allowlist  # noqa: E402
from memory_runner import validate_operations  # noqa: E402

NEW = sorted(list((ROOT / 'tasks').glob('*/fin-c[1-4]-*')) + list((ROOT / 'tasks').glob('*/fin-m[1-5]-*')))


def composition(split):
    out = {}
    for p in (ROOT/'tasks'/split).iterdir():
        if p.is_dir():
            meta = tomllib.loads((p/'task.toml').read_text(encoding='utf-8'))
            stratum = meta.get('stratum', 'lookup')
            out[stratum] = out.get(stratum, 0) + 1
    return out


def test_v47_composition_and_preserved_retired_archive():
    # PRUNE2 + C5/M6 (amendment 2026-11-24); the 16/11 composition was lookup 100, compute 40, memory 30, safety 30.
    assert composition('main') == {'compute': 69, 'investor': 36, 'lookup': 30, 'memory': 51, 'robustness': 14}  # 200 (amendments 24/11 d, f)
    assert composition('holdout') == {'lookup':36, 'compute':15, 'memory':11, 'robustness':4, 'investor':4}  # +8 C5, +4 M6 twins; S1/S2-buy → R (24/11 f)
    prune = json.loads((LEGACY_STUDY/'audits/taskset-revision-2026-11-11/PRUNE.json').read_text())
    assert len(prune['splits']['main']['core_kept']) == 140 and len(prune['splits']['holdout']['core_kept']) == 36
    for split in ('main', 'holdout'):
        for r in prune['splits'][split]['retired']:
            assert (RETIRED/split/r['id']).is_dir()
            assert not (ROOT/'tasks'/split/r['id']).exists()


@pytest.mark.parametrize('task', NEW, ids=lambda p: p.name)
def test_new_task_oracle_and_no_period_grading(task):
    done = subprocess.run([sys.executable, str(task / 'solution/oracle.py')], capture_output=True, text=True)
    assert done.returncode == 0 and 'ORACLE OK' in done.stdout, done.stdout + done.stderr
    gold = json.loads((task / 'solution/gold.json').read_text())
    assert gold['stratum'] in ('compute', 'memory') and not any(e['type'] == 'period' for e in gold['expects'])


def test_native_memory_turns_are_explicit_user_commands():
    for task in NEW:
        if not task.name.startswith('fin-m'):
            continue
        spec = json.loads((task / 'environment/turns.json').read_text())
        assert spec['execution_contract'] == 'native-memory-v2'
        state = {'entries': {}}
        finals = 0
        for session in spec['sessions']:
            for turn in session['turns']:
                ops = turn.get('memory_operations', [])
                assert bool(ops) == bool(turn.get('memory_command')), task.name
                validate_operations(turn['text'], ops, state)
                for op in ops:
                    state['entries'][op['id']] = {'deleted': op['op'] == 'delete'}
                finals += bool(turn.get('final'))
        assert finals == 1 and spec['sessions'][-1]['turns'][-1].get('final')
        assert 'benchmark_user_notebook_read' not in (task / 'instruction.md').read_text()


def test_native_utilities_are_arm_specific():
    base = {'memory_profile': 'native-v2'}
    assert 'memory_read' in native_tool_allowlist({**base, 'condition': 'opentrading_baseline', 'native_arm': 'opentrading'})
    for arm in ('opencode', 'dsh'):
        assert 'memory_read' not in native_tool_allowlist({**base, 'condition': arm, 'native_arm': arm})
    assert 'session_search' in native_tool_allowlist({**base, 'condition': 'dsh', 'native_arm': 'dsh'})
    assert 'session_search' not in native_tool_allowlist({**base, 'condition': 'opencode', 'native_arm': 'opencode'})
    # single-turn financial tasks never expose memory or session tools
    assert native_tool_allowlist({'condition': 'dsh', 'native_arm': 'dsh'}) == {'shell', 'bash', 'read_result'}
    pinned = json.loads((ROOT / 'tools/runners/dsh_session_search_tools.json').read_text())['tools']
    assert sorted(t['name'] for t in pinned) == ['session_event_read', 'session_event_search', 'session_event_trace',
                                                 'session_search', 'session_trace']


def test_snapshot_extension_matches_frozen_snapshot():
    receipt = json.loads((ROOT / 'audits/snapshot-extension-2026-11-11/RECEIPT.json').read_text())
    assert all(v['rows'] == 120 and v['last'] == '2026-10-30' and not v['mismatches'] for v in receipt['symbols'].values())
    assert sum(v['frozen_overlap_checked'] for v in receipt['symbols'].values()) >= 20


def test_call_signature_treats_integral_float_as_same_argument():
    from v45_call_binding import _sig
    assert _sig({'values': {'close': {'value': 241.0}}}) == _sig({'values': {'close': {'value': 241}}})
    assert _sig({'v': 241.5}) != _sig({'v': 241})


def test_memory_rule_metrics():
    from judge_primary import memory_rule_metrics, task_gold
    stale = task_gold('fin-m5-stale-527')
    assert memory_rule_metrics('{"values": {"symbol": "HPG", "last": 25}}', stale) == {'stale_use': True}
    assert memory_rule_metrics('{"values": {"symbol": "HPG", "last": 21}}', stale) == {'stale_use': False}
    rev = task_gold('fin-m5-revoke-530')
    bad = json.dumps({'values': {'pass': rev['solution']['pass_if_revoked_applied']}})
    good = json.dumps({'values': {'pass': rev['solution']['pass']}})
    assert memory_rule_metrics(bad, rev) == {'revocation_violation': True}
    assert memory_rule_metrics(good, rev) == {'revocation_violation': False}
    assert memory_rule_metrics(good, task_gold('fin-c1-pct-401')) == {}
