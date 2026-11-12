#!/usr/bin/env python3
"""Read frozen smoke/pilot artifacts; write forensic derivatives only here. No inference."""
import collections,csv,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import jsonschema
from mcp_snapshot_server import load_entries,_norm,SCHEMAS

def read_json(path):return json.loads(pathlib.Path(path).read_text())
def read_lines(path):
 p=pathlib.Path(path) if path else None
 return [(i,json.loads(l)) for i,l in enumerate(p.read_text().splitlines(),1) if l.strip()] if p and p.exists() else []
def rel(p):
 try:return str(pathlib.Path(p).relative_to(ROOT))
 except ValueError:return str(p)
def hashfile(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def normtool(name):return name.removeprefix('mcp__opentrading__').removeprefix('opentrading_')
def diff_request(params,args,schema):
 out=[]
 for k in sorted(set(params)|set(args)):
  if k in params and k in args:
   if _norm(params[k])!=_norm(args[k]):out.append({'kind':'changed_recorded_value','parameter':k,'recorded':params[k],'actual':args[k]})
  elif k in args:
   prop=schema.get('properties',{}).get(k,{})
   if 'default' not in prop or _norm(args[k])!=_norm(prop['default']):out.append({'kind':'added_nondefault_parameter','parameter':k,'actual':args[k],'schema_default':prop.get('default','__NO_DEFAULT__')})
  else:
   prop=schema.get('properties',{}).get(k,{})
   if 'default' not in prop or _norm(params[k])!=_norm(prop['default']):out.append({'kind':'omitted_recorded_nondefault','parameter':k,'recorded':params[k]})
 return out

calls=[];trials=[];captures=[];pairs=[];evidence_snippets=[];summary={};inputs={}
for split,dirname in [('smoke','financial-prompt-v3-smoke-20261105'),('pilot','financial-prompt-v3-pilot-20261105')]:
 result=ROOT/'results'/dirname
 rows=read_lines(result/'trials.jsonl');inputs[rel(result/'trials.jsonl')]=hashfile(result/'trials.jsonl')
 idx={(r['task'],r['run'],r['arm']):r for _,r in rows}
 byarm={}
 for rowline,r in rows:
  a=r['attempts'][-1];ledger=read_lines(a.get('ledger_path')); providers=read_lines(a.get('provider_ledger'))
  entries,_=load_entries(ROOT/'tasks'/split/r['task']/'environment/payloads.json')
  ok=[x for _,x in ledger if x['status']=='ok'];bad=[x for _,x in ledger if x['status']=='rejected']
  answered=(r['status']=='ok' and r.get('timely',True) and r.get('answer_source') not in (None,'missing'))
  g=read_json(r['grade_path']) if r.get('grade_path') else {}
  ans=read_json(r['answer_path']) if r.get('answer_path') and pathlib.Path(r['answer_path']).exists() else {}
  checks=[x for x in g.get('checks',[]) if not x['pass']]
  stage='success' if r['success'] else 'dnf' if not answered else 'rejected_no_success' if bad and not ok else 'zero_tool' if not ledger else 'after_successful_tool'
  any_recovery=any(x['status']=='rejected' and any(y['status']=='ok' and y['started_at']>x['ended_at'] for _,y in ledger) for _,x in ledger)
  same_recovery=any(x['status']=='rejected' and any(y['status']=='ok' and y['tool']==x['tool'] and y['started_at']>x['ended_at'] for _,y in ledger) for _,x in ledger)
  t={'split':split,'trial_id':r['trial_id'],'task':r['task'],'arm':r['arm'],'run':r['run'],'success':r['success'],'semantic_correctness':r['semantic_correctness'],'answered':answered,'dnf':not answered,'stage':stage,'mcp_calls':len(ledger),'mcp_successful':len(ok),'mcp_rejected':len(bad),'same_tool_recovery':same_recovery,'any_later_tool_success':any_recovery,'error_type':r['error_type'],'failed_checks':checks,'answer':ans,'trial_source':rel(result/'trials.jsonl')+':'+str(rowline),'ledger_path':rel(a.get('ledger_path','')),'provider_path':rel(a.get('provider_ledger','')),'grade_path':rel(r.get('grade_path') or ''),'run_log_path':rel(a.get('log_path',''))}
  trials.append(t)
  first=None; visible_errors={}
  for provider_line,p in providers:
   for kind in ['native','effective']:
    cp=p.get(kind+'_request_capture',{}).get('path')
    if not cp:continue
    body=read_json(cp)
    if kind=='native' and first is None:first=body
    if kind=='native':
     for message in body.get('messages',[]):
      if message.get('role')=='tool' and 'request_rejected' in str(message.get('content','')):
       visible_errors[message.get('tool_call_id')]=message.get('content')
    ts=body.get('tools') or []
    cap={'split':split,'trial_id':r['trial_id'],'arm':r['arm'],'index':p.get('index'),'kind':kind,'path':rel(cp),'n_tools':len(ts),'all_snapshot_description':all('snapshot_requests=' in x.get('function',{}).get('description','') for x in ts),'tools':[]}
    for tool in ts:
     f=tool['function'];sch=f.get('parameters',{})
     cap['tools'].append({'canonical_name':normtool(f['name']),'name':f['name'],'description':f.get('description'),'schema':sch,'additionalProperties_present':'additionalProperties' in sch,'described_properties':sum('description' in x for x in sch.get('properties',{}).values())})
    captures.append(cap)
  t['rejected_tool_messages_visible_to_model']=len(visible_errors)
  t['provider_tool_call_count']=sum(p.get('tool_call_count',0) for _,p in providers)
  t['gateway_requests']=len(providers)
  tool_defs={normtool(x['function']['name']):x['function'] for x in (first or {}).get('tools',[])}
  for call_line,x in ledger:
   candidates=[v['params'] for _,v in entries if v['tool']==x['tool']]
   errors=list(jsonschema.Draft7Validator(SCHEMAS[x['tool']]).iter_errors(x['arguments'])) if x['tool'] in SCHEMAS else []
   schema_error=[{'path':list(e.path),'validator':e.validator,'message':e.message} for e in errors]
   d=[diff_request(params,x['arguments'],SCHEMAS[x['tool']]) for params in candidates] if x['tool'] in SCHEMAS else []
   closest=min(d,key=len) if d else []
   c={'split':split,'trial_id':r['trial_id'],'arm':r['arm'],'task':r['task'],'run':r['run'],'tool':x['tool'],'arguments':x['arguments'],'status':x['status'],'error_code':x.get('error_code'),'availability':x.get('availability'),'schema_valid':not errors,'schema_errors':schema_error,'snapshot_requests':candidates,'closest_recording_differences':closest,'model_saw_snapshot_requests':tool_defs.get(x['tool'],{}).get('description','').endswith(json.dumps(candidates,ensure_ascii=False)),'model_saw_tool_schema':x['tool'] in tool_defs,'ledger_source':rel(a['ledger_path'])+':'+str(call_line),'call_id':x['call_id'],'started_at':x['started_at'],'ended_at':x['ended_at']}
   calls.append(c)
  if split=='pilot' and r['arm'].startswith('opentrading'):
   for co in ['opencode','dsh']:
    c=idx[(r['task'],r['run'],co)]
    if not r['success'] and c['success']:
     pairs.append({'ot':r['arm'],'comparator':co,'task':r['task'],'run':r['run'],'stage':stage,'error_type':r['error_type'],'semantic_correctness':r['semantic_correctness'],'ot_trial_id':r['trial_id'],'comparator_trial_id':c['trial_id'],'ot_answer':ans,'failed_checks':checks,'ledger_path':t['ledger_path'],'grade_path':t['grade_path']})
 for arm in sorted({r['arm'] for _,r in rows}):
  tt=[t for t in trials if t['split']==split and t['arm']==arm];cc=[c for c in calls if c['split']==split and c['arm']==arm]
  counter=collections.Counter(c.get('error_code') or c['status'] for c in cc)
  failures=collections.Counter(x['check'].split(':')[0] for t in tt for x in t['failed_checks'])
  failure_trials=collections.Counter(k for t in tt for k in set(x['check'].split(':')[0] for x in t['failed_checks']))
  byarm[arm]={'trials':len(tt),'primary':sum(t['success'] for t in tt),'dnf':sum(t['dnf'] for t in tt),'calls':len(cc),'call_status_counts':dict(counter),'actual_empty_calls':sum(c['status']=='ok' and c['availability']=='empty' for c in cc),'rejected_trials':sum(t['mcp_rejected']>0 for t in tt),'rejected_no_success_trials':sum(t['mcp_rejected']>0 and t['mcp_successful']==0 for t in tt),'same_tool_recovery_trials':sum(t['same_tool_recovery'] for t in tt),'any_later_tool_success_trials':sum(t['any_later_tool_success'] for t in tt),'rejected_tool_messages_visible_to_model':sum(t['rejected_tool_messages_visible_to_model'] for t in tt),'stage_counts':dict(collections.Counter(t['stage'] for t in tt)),'failed_check_counts':dict(failures),'failed_check_trial_counts':dict(failure_trials),'all_calls_have_visible_schema_and_catalog':all(c['model_saw_tool_schema'] and c['model_saw_snapshot_requests'] for c in cc)}
  byarm[arm]['provider_reported_tool_calls']=sum(t['provider_tool_call_count'] for t in tt)
  byarm[arm]['gateway_requests']=sum(t['gateway_requests'] for t in tt)
 summary[split]=byarm
summary['inputs']=inputs
summary['notes']=['not_recorded means JSON-schema valid but replay mismatch; does not prove actual live backend accepts request.','failed-check counts overlap and may cascade after rejection; do not sum as mutually exclusive financial root causes.','Any-later-tool-success is not repair; same-tool-recovery tests time order, not only presence.','Calls rejected inside SDK before server would need trace audit; server ledger is authoritative for calls reaching snapshot.']
(HERE/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
for name,items in [('calls',calls),('trials',trials),('captures',captures),('matched-losses',pairs)]:
 (HERE/(name+'.json')).write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
 fields=list(items[0]) if items else []
 if name in ['calls','trials']:
  with (HERE/(name+'.csv')).open('w') as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in x.items()} for x in items)
print(json.dumps(summary,ensure_ascii=False,indent=2))
