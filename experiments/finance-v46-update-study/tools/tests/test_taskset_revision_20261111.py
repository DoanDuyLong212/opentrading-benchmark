"""Amendment 2026-11-11 (d): task-set revision, compute stratum, native-memory stratum."""
import json
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
    out = {'core': 0, 'compute': 0, 'memory': 0}
    for p in (ROOT / 'tasks' / split).iterdir():
        if p.is_dir() and task_eligibility(p)['confirmatory_eligible']:
            e = task_eligibility(p)
            out['memory' if e.get('memory_native_v2') else 'compute' if p.name.startswith('fin-c') else 'core'] += 1
    return out


def test_main_200_and_holdout_50_composition():
    assert composition('main') == {'core': 140, 'compute': 30, 'memory': 30}
    assert composition('holdout') == {'core': 36, 'compute': 7, 'memory': 7}
    prune = json.loads((ROOT / 'audits/taskset-revision-2026-11-11/PRUNE.json').read_text())
    assert len(prune['splits']['main']['core_kept']) == 140 and len(prune['splits']['holdout']['core_kept']) == 36
    for split in ('main', 'holdout'):
        for r in prune['splits'][split]['retired']:
            assert (ROOT / 'tasks-retired' / split / r['id']).is_dir() and not (ROOT / 'tasks' / split / r['id']).exists()


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
    assert native_tool_allowlist({'condition': 'dsh', 'native_arm': 'dsh'}) == {'calculate', 'compute', 'read_result'}
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
