import pathlib,json,hashlib,collections
ROOT=pathlib.Path('/home/doanlong/extra/benchmark'); out=pathlib.Path('/tmp/v44-final-forensics'); evidence={'scope':'read-only supplementary forensic examination; frozen audit remains FAIL; no inference/tests/retry','inputs':{},'models':{},'local_duplicate_proofs':[]}
def read(p):
 b=p.read_bytes();evidence['inputs'][str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return b.decode()
def js(p):return json.loads(read(p))
def jl(p):return [] if not p.exists() else [json.loads(l) for l in read(p).splitlines() if l.strip()]
def events(p):
 es=[]
 for i,l in enumerate(read(p).splitlines(),1):
  try:x=json.loads(l)
  except ValueError:continue
  x['_line']=i;es.append(x)
 return es
pinned=js(ROOT/'audits/financial-prompt-v44/independent-evidence.json')
for model in ['bolt','deepseek']:
 p=ROOT/f'experiments/finance-v44-study/results/financial-v44-smoke-{model}-20261107-startupfix1'; trials=jl(p/'trials.jsonl');stat={'trials':[],'provider_error_counts':{},'compute_error_counts':{},'mcp_status_counts':{},'finish_reasons_recorded_in_runtime':{},'local_events':[]};pc=collections.Counter();cc=collections.Counter();mc=collections.Counter();fr=collections.Counter();allcomputes=[]
 for t in trials:
  a=next((p/'trials'/t['trial_id']/'attempts').iterdir());rows=jl(a/'mcp.jsonl');provider=jl(a/'provider.jsonl');es=events(a/'run.log');comps=[r for r in rows if r['tool']=='analytics_compute'];allcomputes.extend([{'trial_id':t['trial_id'],'path':str(a/'mcp.jsonl'),**r} for r in comps]);mc.update((r['tool']+':'+r['status']) for r in rows);cc.update(r.get('error','ok') for r in comps);pc.update(r['error'] for r in provider if r.get('error'))
  for e in es:
   if e.get('type')=='step_finish':fr[e.get('part',{}).get('reason','unknown')]+=1
  entry={k:t.get(k) for k in ['trial_id','status','success','semantic_correctness','public_contract_valid','public_contract_errors','native_completion','tokens','requests','execution_error']};entry.update(final_text=t['attempts'][0].get('final_text'),provider_errors=[{'index':r['index'],'error':r['error'],'upstream_attempted':r.get('upstream_attempted'),'status':r.get('status'),'response_models':r.get('response_models'),'duration_s':r.get('duration_s')} for r in provider if r.get('error')],mcp_calls=len(rows),compute_calls=len(comps));stat['trials'].append(entry)
  for e in es:
   if not e.get('localRejection'):continue
   stat['local_events'].append({'trial_id':t['trial_id'],'path':str(a/'run.log'),**e})
   if model!='deepseek' or t['task']!='smoke-agg-01' or t['arm']!='opentrading_finance':continue
   start=next(z for z in es if z.get('type')=='tool-start' and z.get('callId')==e['callId']);orig_id=e['financeIntent']['original_sdk_call_id'];orig=next(z for z in es if z.get('type')=='tool-start' and z.get('callId')==orig_id);orig_end=next(z for z in es if z.get('type')=='tool-end' and z.get('callId')==orig_id);generating=next(r for r in provider if e['callId'] in r.get('response_tool_call_ids',[]));gen_orig=next(r for r in provider if orig_id in r.get('response_tool_call_ids',[]));captures=[];wire_dup=False;wire_original=False;wire_local_result=False
   for r in provider:
    cap=r.get('native_request_capture',{}).get('path')
    if not cap:continue
    cap=pathlib.Path(cap)
    if not cap.exists():continue
    body=js(cap);msgs=body.get('messages',[])
    for msg in msgs:
     for call in msg.get('tool_calls',[]):
      if call.get('id') in (e['callId'],orig_id):
       same=json.loads(call['function']['arguments'])==start['input'] and call['function']['name']==start['name'];wire_dup|=call['id']==e['callId'] and same;wire_original|=call['id']==orig_id and same;captures.append({'path':str(cap),'call_id':call['id'],'matches_exact_args':same})
     if msg.get('role')=='tool' and msg.get('tool_call_id')==e['callId']:wire_local_result|=e['output'] in str(msg.get('content'))
   exact=[r for r in rows if r['tool']=='analytics_compute' and r['arguments']==start['input']]
   source_ids={r['call_id'] for r in rows if r['status']=='ok' and r['tool']!='analytics_compute'}
   proof={'trial_id':t['trial_id'],'log_path':str(a/'run.log'),'ledger_path':str(a/'mcp.jsonl'),'duplicate_sdk_call_id':e['callId'],'original_sdk_call_id':orig_id,'duplicate_start_line':start['_line'],'duplicate_end_line':e['_line'],'original_start_line':orig['_line'],'original_end_line':orig_end['_line'],'duplicate_generating_provider_index':generating['index'],'original_generating_provider_index':gen_orig['index'],'exact_same_name_and_args':orig['name']==start['name'] and orig['input']==start['input'],'raw_local_args_equal':json.loads(e['localRejection']['rawInput'])==start['input'],'same_intent_id':orig_end['financeIntent']['intent_id']==e['financeIntent']['intent_id'],'wire_duplicate_and_original_args_proven':wire_dup and wire_original,'wire_local_error_visible':wire_local_result,'matching_mcp_rows':len(exact),'matching_mcp_call_id':exact[0]['call_id'],'matching_mcp_status':exact[0]['status'],'all_operand_source_ids_are_successful_same_trial':all(r['call_id'] in source_ids for r in start['input']['operands']),'ledger_total':len(rows),'generated_sdk_ids':sum(len(r.get('response_tool_call_ids',[])) for r in provider),'local_rejections':sum(bool(z.get('localRejection')) for z in es),'reason':e['localRejection']['reason'],'arguments':start['input'],'wire_capture_refs':captures}
   assert all(proof[k] for k in ['exact_same_name_and_args','raw_local_args_equal','same_intent_id','wire_duplicate_and_original_args_proven','wire_local_error_visible','all_operand_source_ids_are_successful_same_trial'])
   assert proof['matching_mcp_rows']==1 and proof['generated_sdk_ids']==proof['ledger_total']+proof['local_rejections'];evidence['local_duplicate_proofs'].append(proof)
 stat.update(provider_error_counts=dict(pc),compute_error_counts=dict(cc),mcp_status_counts=dict(mc),finish_reasons_recorded_in_runtime=dict(fr),compute_rows=allcomputes);evidence['models'][model]=stat
for f in ['tools/analytics_compute.py','tools/ready_check.py','tools/intent_audit.py','tools/runners/provider.py','experiments/opentrading-runtime/src/core/finance-policy.ts','experiments/opentrading-runtime/src/core/tools/registry.ts']:
 read(ROOT/'experiments/finance-v44-study'/f)
evidence['frozen_audit_errors']={k:v['errors'] for k,v in pinned['completed_runs'].items()};(out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:{a:v[a] for a in ['provider_error_counts','compute_error_counts','mcp_status_counts','finish_reasons_recorded_in_runtime']} for k,v in evidence['models'].items()},ensure_ascii=False,indent=2));print('proofs',len(evidence['local_duplicate_proofs']))
