#!/usr/bin/env python3
"""Explanatory stages from immutable results; never changes primary or reruns inference."""
import argparse
import collections
import json
from pathlib import Path
from metrics import load_trials,resolve_task_dir
from analyze_v42_errors import analyze as inherited_analysis


def analyze(directory):
    result=inherited_analysis(directory)
    byid={row['trial_id']:row for row in load_trials(directory)}
    for detail in result['trials']:
        row=byid[detail['trial_id']];phases=[];calls=[]
        for attempt in row.get('attempts',[]):
            path=attempt.get('log_path')
            if path and Path(path).is_file():
                for line in Path(path).read_text(errors='replace').splitlines():
                    try:event=json.loads(line)
                    except ValueError:continue
                    if isinstance(event,dict) and event.get('type')=='finance-phase':phases.append(event)
            path=attempt.get('ledger_path')
            if path and Path(path).is_file():calls.extend(json.loads(l) for l in Path(path).read_text().splitlines() if l.strip())
        gold_path=Path(resolve_task_dir(row['task']))/'solution/gold.json'
        gold=json.loads(gold_path.read_text());required=gold.get('provenance_contract',[])
        identity=('tool','matched_entry_id','response_sha256','source','as_of')
        successful={tuple(c.get(k) for k in identity) for c in calls if c.get('status')=='ok'}
        coverage=[{'check':'required_actual_response','pass':tuple(c.get(k) for k in identity) in successful,
                   'response_identity':{k:c.get(k) for k in identity}} for c in required]
        detail['acquisition_events']=phases
        detail['zero_actual_calls']=not calls
        detail['required_coverage_checks']=coverage
        detail['required_retrieval_complete']=all(c.get('pass') for c in coverage) if coverage else None
        detail['unsupported_snapshot_queries']=sum(c.get('error_code')=='unsupported_snapshot_query' for c in calls)
        detail['successful_executions']=sum(c.get('status')=='ok' for c in calls)
        if coverage and not detail['required_retrieval_complete']:
            detail['failure_stage']='required_retrieval_incomplete'
        elif not calls and not row.get('success'):
            detail['failure_stage']='zero_call_final_or_dnf'
        elif row.get('success'):
            detail['failure_stage']='primary_correct'
        else:detail['failure_stage']='post_attempt_failure_review_needed'
    result['v43_note']='Stages are explanatory only. Missing operands do not demonstrate arithmetic failure; no primary/grader field changed.'
    result['failure_stage_counts']=dict(collections.Counter(d['failure_stage'] for d in result['trials']))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory');ap.add_argument('--out',required=True);a=ap.parse_args()
    Path(a.out).write_text(json.dumps(analyze(a.directory),indent=2,ensure_ascii=False)+'\n')
