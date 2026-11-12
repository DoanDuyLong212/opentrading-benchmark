#!/usr/bin/env python3
"""Mechanics dry-run for the amendment 2026-11-11 (d) strata (NOT a cohort, never scored, never used to select
or edit tasks by arm outcome). Checks that the new pipeline pieces execute end to end: native-memory episodes for
all three arms (OT /nho local form, OpenCode/DSH resume, DSH session search) and long-series compute tasks.
Only breakage (runner errors, unserved payloads, contract parse failures) may lead to fixes.

  python3 analysis/mechanics_dryrun_20261111.py OUT task:arm [task:arm ...]
"""
import json, os, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(STUDY / 'tools'), str(STUDY / 'tools/runners')]
import run_benchmark as rb  # noqa: E402

cfg = json.loads((STUDY / 'tools/bench_config_deepseek_openrouter.json').read_text())
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
options = {'effort': 'none', 'max_requests': cfg['max_requests'], 'max_output_tokens': cfg['max_output_tokens'],
           'max_total_tokens': cfg['max_total_tokens'], 'provider_timeout_s': cfg['provider_timeout_s'],
           'opentrading_runtime_root': cfg['opentrading_runtime_root'], **cfg.get('provider_options', {}), 'protocol': cfg['protocol']}
if sys.argv[2:3] == ['--audit-probe']:
    pass
else:
  for spec in sys.argv[2:]:
      task, arm = spec.split(':')
      tdir = next(p for p in (STUDY / 'tasks/main' / task, STUDY / 'tasks/pilot' / task) if p.exists())
      timeout = cfg['memory_trial_timeout_s'] if rb.is_native_memory(str(tdir)) else cfg['trial_timeout_s']
      item = {'trial_id': 'dry-%s-%s' % (task, arm), 'task': task, 'arm': arm, 'run': 1}
      row = rb.execute_trial(item, str(tdir), str(out), cfg['model'], timeout, 0, 0, options)
      keep = {k: row.get(k) for k in ('task', 'arm', 'status', 'semantic_correctness', 'grounded_financial_correctness', 'success',
                                       'error_type', 'requests', 'wall_ms', 'public_contract_valid', 'execution_error')}
      keep['notes'] = (row.get('attempts') or [{}])[-1].get('notes')
      keep['memory_turns'] = (row.get('attempts') or [{}])[-1].get('memory_turns')
      print(json.dumps(keep, ensure_ascii=False), flush=True)
      with open(out / 'dryrun.jsonl', 'a') as f:
          f.write(json.dumps(row, ensure_ascii=False) + '\n')


def audit_probe(out, task_names, arms):
    """Scratch run with a real manifest (no seal; diagnostic only) so audit_v45_run.py can be exercised."""
    from v45_gate import build_settings
    from run_manifest import prepare_manifest
    settings = build_settings(cfg, 'pilot'); settings.update(arms=arms, runs=1)
    settings['conditions'] = {a: settings['conditions'][a] for a in arms}
    tasks = [STUDY / 'tasks/pilot' / t for t in task_names]
    manifest = prepare_manifest(Path(out), settings, tasks, cfg, False)
    by = {t.name: t for t in tasks}
    with open(Path(out) / 'trials.jsonl', 'a') as handle:
        for item in manifest['plan']['schedule']:
            t = by[item['task']]
            timeout = cfg['memory_trial_timeout_s'] if rb.is_native_memory(str(t)) else cfg['trial_timeout_s']
            row = rb.execute_trial(item, str(t), str(out), cfg['model'], timeout, 0, 0, options)
            row['manifest_sha256'] = manifest['fingerprint']
            handle.write(json.dumps(row, ensure_ascii=False) + '\n'); handle.flush()
            print(item['task'], item['arm'], row['status'], row['semantic_correctness'], row['requests'], flush=True)


if sys.argv[2:3] == ['--audit-probe']:
    audit_probe(out, sys.argv[3].split(','), sys.argv[4].split(','))
