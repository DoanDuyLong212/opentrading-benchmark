#!/usr/bin/env python3
"""Offline v4.2 failure-stage/finite-support/intent audit. Never reruns a model."""
import argparse,collections,json
from pathlib import Path
import jsonschema
from metrics import load_trials
from mcp_snapshot_server import FROZEN_V3_SCHEMAS,SCHEMAS,load_entries,finite_input_schema
ROOT=Path(__file__).resolve().parents[1]

def rejection_class(name,args,entries):
    if name not in SCHEMAS:return 'unknown_tool'
    for label,schema in [('type_or_shape',FROZEN_V3_SCHEMAS[name]),('production_domain',SCHEMAS[name]),('finite_support',finite_input_schema(entries,name))]:
        if not jsonschema.Draft7Validator(schema).is_valid(args):return label
    return 'schema_valid'

def analyze(directory):
    rows=load_trials(directory);details=[]
    for row in rows:
        task=next((ROOT/'tasks'/split/row['task'] for split in ('smoke','pilot') if (ROOT/'tasks'/split/row['task']).is_dir()),None)
        entries,_=load_entries(task/'environment/payloads.json')
        grade=json.loads(Path(row['grade_path']).read_text()) if row.get('grade_path') and Path(row['grade_path']).exists() else {}
        failed=[c.get('check') for c in grade.get('checks',[]) if not c.get('pass')]
        calls=[];local=[];intents=[]
        for attempt in row.get('attempts',[]):
            ledger=attempt.get('ledger_path')
            if ledger and Path(ledger).exists():calls.extend(json.loads(line) for line in Path(ledger).read_text().splitlines() if line.strip())
            log=attempt.get('log_path')
            if log and Path(log).exists():
                for line in Path(log).read_text(errors='replace').splitlines():
                    try:event=json.loads(line)
                    except ValueError:continue
                    if not isinstance(event,dict):continue
                    if event.get('financeIntent'):intents.append({'call_id':event.get('callId'),'ok':event.get('ok'),**event['financeIntent']})
                    rejection=event.get('localRejection')
                    if rejection:
                        name=rejection.get('tool','')
                        for prefix in ('mcp__opentrading__','mcp_opentrading_','opentrading_'):
                            if name.startswith(prefix):name=name[len(prefix):];break
                        args=rejection.get('rawInput')
                        try:args=json.loads(args) if isinstance(args,str) else args
                        except ValueError:pass
                        local.append({'call_id':event.get('callId'),'tool':name,'class':rejection_class(name,args,entries),'code':rejection.get('code')})
        stages=[]
        if row.get('status')!='ok' or not row.get('timely'):stages.append('native_or_execution_dnf')
        if not row.get('answer_path'):stages.append('missing_or_invalid_final_json')
        if not any(c.get('status')=='ok' for c in calls):stages.append('no_successful_financial_or_resolver_retrieval')
        if any('unit' in str(x) for x in failed):stages.append('unit')
        if any('period' in str(x) for x in failed):stages.append('period')
        if any(any(term in str(x) for term in ('evidence','source','provenance')) for x in failed) or not row.get('evidence_grounded'):stages.append('evidence_or_provenance')
        if any('value' in str(x) for x in failed):stages.append('numeric_value_or_required_coverage')
        if any('refusal' in str(x) for x in failed):stages.append('refusal_semantics_or_conflict')
        details.append({'trial_id':row['trial_id'],'task':row['task'],'run':row['run'],'arm':row['arm'],'primary':row['success'],'semantic':row.get('semantic_correctness'),'frozen_v41':row.get('frozen_v41_success'),'stages':stages,'failed_checks':failed,'mcp_rejection_classes':dict(collections.Counter(rejection_class(c['tool'],c.get('arguments'),entries) for c in calls if c.get('status')=='rejected')),'local_rejections':local,'finance_intents':intents})
    return {'note':'Diagnostic stages may overlap. Numeric-value failure alone cannot identify arithmetic versus missing operands; review actual stored answers/receipts before causal claims. Same-intent correction success is not primary recovery. Finite-support rejection is not production invalidity.','trials':details,'paired_task_run':{task+'__r'+str(run):{d['arm']:{'primary':d['primary'],'stages':d['stages']} for d in details if d['task']==task and d['run']==run} for task,run in sorted({(d['task'],d['run']) for d in details})}}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('directory');ap.add_argument('--out',required=True);args=ap.parse_args()
    Path(args.out).write_text(json.dumps(analyze(args.directory),ensure_ascii=False,indent=2)+'\n')
