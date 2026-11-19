"""Tests for heterogeneous schedule by stratum and check_change diagnostic checker."""
import json
import pytest
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from stratum_policy import task_stratum, runs_for_task, DEFAULT_RUNS_BY_STRATUM
import run_manifest as rm
import check_change

def test_stratum_policy_mappings():
    assert task_stratum('fin-l1-quote-001') == 'lookup'
    assert task_stratum('fin-c1-pct-401') == 'compute'
    assert task_stratum('fin-m1-screen-501') == 'memory'
    assert task_stratum('fin-s1-pick-461') == 'safety'
    
    assert runs_for_task('fin-l1-quote-001', DEFAULT_RUNS_BY_STRATUM) == 1
    assert runs_for_task('fin-c1-pct-401', DEFAULT_RUNS_BY_STRATUM) == 2
    assert runs_for_task('fin-m1-screen-501', DEFAULT_RUNS_BY_STRATUM) == 2
    assert runs_for_task('fin-s1-pick-461', DEFAULT_RUNS_BY_STRATUM) == 2

def test_heterogeneous_schedule_generation():
    # 2 lookup tasks, 1 compute, 1 memory, 1 safety
    tasks = ['fin-l1-test1', 'fin-l1-test2', 'fin-c1-test', 'fin-m1-test', 'fin-s1-test']
    arms = ['opentrading_machine', 'opencode', 'dsh']
    # 2 L * 1 run * 3 arms = 6
    # 1 C * 2 runs * 3 arms = 6
    # 1 M * 2 runs * 3 arms = 6
    # 1 S * 2 runs * 3 arms = 6
    # Total = 24 cells
    schedule = rm.build_schedule(tasks, arms, 1, 20261108, runs_by_stratum=DEFAULT_RUNS_BY_STRATUM)
    assert len(schedule) == 24
    
    arm_counts = {}
    for cell in schedule:
        arm_counts[cell['arm']] = arm_counts.get(cell['arm'], 0) + 1
    assert arm_counts == {'opentrading_machine': 8, 'opencode': 8, 'dsh': 8}

def test_check_change_dry_run_cap():
    # Over 60 cells must fail
    tasks = [f'task_{i}' for i in range(25)]
    arms = ['a', 'b', 'c']
    args = check_change.parse_args(['--tasks'] + tasks + ['--arms'] + arms + ['--runs', '1', '--dry-run'])
    with pytest.raises(ValueError, match='Diagnostic trial count 75 exceeds limit 60'):
        check_change.build_diagnostic_plan(args)

def test_check_change_dry_run_valid():
    args = check_change.parse_args(['--dry-run'])
    plan = check_change.build_diagnostic_plan(args)
    assert plan['total_trial_cells'] == 9
    assert plan['dry_run'] is True
