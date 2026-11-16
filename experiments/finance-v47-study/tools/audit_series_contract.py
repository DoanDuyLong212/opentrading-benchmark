#!/usr/bin/env python3
"""Offline regeneration audit of #12: dates, n+1 counts, base gold diff, all oracles."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from build_compute_series_20261116 import STUDY, build, CALENDAR
from series_contract import dated_closes


def audit(base='4bbfd38', all_oracles=False):
    root = STUDY.parents[1]
    rows = []
    for spec in build():
        task = STUDY / 'tasks/main' / spec['tid']
        payload = json.loads((task / 'environment/payloads.json').read_text())
        n = 119 if '-dd-' in spec['tid'] else 60
        dates = []
        for sym in spec['syms']:
            key = ('idx:' if sym in ('VNINDEX', 'VN30') else 'hist:') + sym
            raw = payload['tools'][key]['envelope']['data']['closes']
            window = dated_closes(raw, n, calendar=CALENDAR)
            dates.append({'symbol': sym, 'payload_count': len(raw), 'window_closes': len(window),
                          'returns': n, 'start': window[0][0], 'end': window[-1][0],
                          'date_sha256': hashlib.sha256(json.dumps([d for d, p in window]).encode()).hexdigest()})
        gold_path = task / 'solution/gold.json'
        current = gold_path.read_bytes()
        old = subprocess.check_output(['git', 'show', base + ':' + str(gold_path.relative_to(root))], cwd=root)
        rows.append({'task': spec['tid'], 'dates': dates, 'gold_changed': current != old,
                     'gold_sha256': hashlib.sha256(current).hexdigest(),
                     'recomputed_solution_matches': json.loads(current)['solution'] == spec['solution']})
    paths = sorted((STUDY / 'tasks').glob('*/**/solution/oracle.py')) if all_oracles else [STUDY / 'tasks/main' / r['task'] / 'solution/oracle.py' for r in rows]
    failures = []
    for path in paths:
        result = subprocess.run(['python3', str(path)], capture_output=True, text=True)
        if result.returncode:
            failures.append({'oracle': str(path.relative_to(STUDY)), 'returncode': result.returncode,
                             'output': (result.stdout + result.stderr)[-3000:]})
    return {'base': base, 'tasks': rows, 'oracle_count': len(paths), 'oracle_failures': failures,
            'passed': not failures and all(not r['gold_changed'] and r['recomputed_solution_matches'] for r in rows)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='4bbfd38')
    parser.add_argument('--all-oracles', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.base, args.all_oracles)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'tasks': len(report['tasks']),
                      'oracles': report['oracle_count'], 'failures': len(report['oracle_failures'])}))
    raise SystemExit(0 if report['passed'] else 1)
