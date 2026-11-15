"""V3 diagnostic identity, counterbalance and wire capture tamper guards."""
import json
from collections import Counter
from pathlib import Path
import sys

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_manifest as rm
from experiment_conditions import condition, prompt_directory


def test_explicit_aliases_keep_native_agent_and_distinct_prompts():
    assert condition('opentrading_baseline') == {'native_arm': 'opentrading', 'prompt_variant': 'baseline', 'finance_policy': False}
    assert condition('opentrading_finance') == condition('opentrading')
    assert prompt_directory('baseline') != prompt_directory('finance')
    with pytest.raises(ValueError): condition('opentrading_unregistered')
    with pytest.raises(ValueError): prompt_directory('../../etc')


def test_default_all_arms_remains_canonical_three_for_18_trial_smoke():
    from run_benchmark import ARMS
    assert ARMS == ('opencode', 'dsh', 'opentrading')
    tasks = [Path('smoke-%d' % n) for n in range(3)]
    schedule = rm.build_schedule(tasks, list(ARMS), 2, 20261105)
    assert len(schedule) == 18
    assert {r['arm'] for r in schedule} == set(ARMS)


def test_compact_pilot_schedule_exactly_balances_all_four_positions():
    arms = ['opentrading_baseline', 'opentrading_finance', 'opencode', 'dsh']
    tasks = [Path('task-%02d' % n) for n in range(22)]
    schedule = rm.build_schedule(tasks, arms, 2, 20261105)
    assert len(schedule) == 176 and len({r['trial_id'] for r in schedule}) == 176
    assert schedule == rm.build_schedule(tasks, arms, 2, 20261105)
    counts = Counter((row['arm'], index % 4) for index, row in enumerate(schedule))
    assert set(counts.values()) == {11}
    for offset in range(0, len(schedule), 4):
        block = schedule[offset:offset+4]
        assert {r['arm'] for r in block} == set(arms)
        assert len({(r['task'], r['run']) for r in block}) == 1


def test_protocol_hash_changes_on_one_byte(tmp_path, monkeypatch):
    monkeypatch.setattr(rm, 'ROOT', tmp_path)
    (tmp_path/'plans').mkdir()
    protocol = tmp_path/'plans/protocol.md'
    protocol.write_text('frozen')
    config = {'experiment_protocol': 'plans/protocol.md'}
    before = rm.protocol_fingerprint(config)
    protocol.write_text('frozen!')
    assert before != rm.protocol_fingerprint(config)
    with pytest.raises(ValueError): rm.protocol_fingerprint({'experiment_protocol': '../outside.md'})
