#!/usr/bin/env python3
"""Offline controlled-memory episode audit. No model calls or source/grader tuning."""
import argparse,json,tempfile,hashlib
from pathlib import Path
from run_manifest import hash_file,digest_json
from v45_memory_metrics import evaluate_episode,read_jsonl,telemetry_state,provider_dispatch_accounting
from ready_check import verify_mcp_attempt,verify_request_capture,verify_local_rejections
from mcp_snapshot_server import load_entries,select_envelope,digest,build_tool_defs
from v45_math_audit import verify_common
from run_benchmark import grounded_answer
from audit_v45_run import json_objects,has_receipt
from runners.provider import admission,DEFAULT_MODEL
ROOT=Path(__file__).resolve().parents[1]
def audit(out):
 out=Path(out).resolve();manifest=json.loads((out/'manifest.json').read_text());checks=[];errors=[];rows=[];partials=[]
 def check(tid,name,fn):
  try:value=fn();checks.append({'trial_id':tid,'check':name,'pass':True});return value
  except Exception as e:errors.append({'trial_id':tid,'check':name,'error':str(e)});return None
 def require(ok,why):
  if not ok:raise ValueError(why)
 for cell in manifest['schedule']:
  tid=cell['trial_id'];path=out/'episodes'/tid/'result.json'
  if not path.exists():errors.append({'trial_id':tid,'check':'complete','error':'Scheduled episode missing'});continue
  row=json.loads(path.read_text());rows.append(row);task=ROOT/'tasks'/cell['case'];interrupted=row.get('status')in('interrupted','dnf')
  check(tid,'schedule_identity',lambda:require(all(row.get(k)==cell[k]for k in('trial_id','model','arm','case')),'Episode identity differs from schedule'))
  admitted=check(tid,'model_admission',lambda:admission(cell['model'].removeprefix('nvidia/')))
  provider=check(tid,'provider_telemetry',lambda:read_jsonl(row.get('provider_ledger')))or[]
  for key in('provider_ledger','mcp_ledger','memory_access_ledger'):
   state=telemetry_state(row.get(key))
   if state['partial_tail']:
    partials.append({'trial_id':tid,'kind':key,**state})
    check(tid,'partial_only_failed_episode',lambda:require(interrupted and not row.get('episode_grounded_financial_success')and not row.get('memory_state_correctness'),'Partial telemetry cannot produce accepted win'))
  dispatch=provider_dispatch_accounting(row.get('provider_ledger'),provider)
  if dispatch['pending_dispatches_unknown_usage']:
   partials.append({'trial_id':tid,'kind':'pending_upstream_dispatch_unknown_usage',**dispatch})
   check(tid,'pending_dispatch_failed_episode',lambda:require(interrupted and not row.get('episode_grounded_financial_success')and not row.get('memory_state_correctness'),'Pending provider dispatch cannot produce accepted win'))
  check(tid,'whole_episode_attempt_cap',lambda:require(dispatch['actual_dispatches']<=12,'Episode exceeded12 upstream attempts'))
  turns=row.get('turn_results',row.get('completed_turns',[]))
  if not interrupted:
   check(tid,'all_native_turns_completed',lambda:require(len(turns)==len(cell['turns'])and all(t.get('result',{}).get('status')=='ok'for t in turns),'Missing/failed actual native seed or query turn'))
  seen_sessions=set()
  for turn_index,turn in enumerate(turns):
   if turn_index>=len(cell['turns']):check(tid,'unexpected_turn',lambda:require(False,'Unexpected extra native turn'));continue
   wanted=cell['turns'][turn_index]
   check(tid,'public_user_turn_binding',lambda t=turn,w=wanted:require(t.get('session')==w['session']and t.get('turn')==w['turn']and t.get('user_text')==w['text'],'Native turn/session/user text differs from sealed public turn'))
   start=turn.get('provider_rows_start');end=turn.get('provider_rows_end')
   if turn.get('result',{}).get('status')=='ok':
    check(tid,'actual_turn_provider_dispatch',lambda start=start,end=end:require(isinstance(start,int)and isinstance(end,int)and 0<=start<end<=len(provider)and any(p.get('upstream_attempted')and p.get('status')==200 for p in provider[start:end]),'Completed native turn has no actual successful provider request'))
   if isinstance(start,int)and isinstance(end,int)and 0<=start<end<=len(provider):
    cap=provider[start].get('native_request_capture')or{}
    if cap.get('path')and Path(cap['path']).exists():
     messages=json.loads(Path(cap['path']).read_text()).get('messages',[])
     def user_text(message):
      content=message.get('content','')
      return content if isinstance(content,str)else'\n'.join(part.get('text','')for part in content if isinstance(part,dict))if isinstance(content,list)else''
     users=[user_text(message)for message in messages if message.get('role')=='user']
     def decode_declared_wrapper(text):
      """v4.6: authenticate the ONE declared reversible quote-wrapper (OpenCode
      adapter wraps the public prompt in literal quotes; embedded newlines stay
      raw, inner JSON escapes like \\" remain). Re-escape only the control
      characters strict JSON forbids, then decode exactly one level; arbitrary
      prose is never extracted."""
      if isinstance(text,str)and len(text)>=2 and text[0]=='"' and text[-1]=='"':
       inner=text[1:-1]
       try:
        value=json.loads('"'+inner.replace('\r','\\r').replace('\n','\\n').replace('\t','\\t')+'"')
        if isinstance(value,str):return value
       except ValueError:pass
      return text
     decoded=[decode_declared_wrapper(text)for text in users]
     check(tid,'actual_user_prompt_binding',lambda users=users,decoded=decoded,w=wanted:require(bool(users)and (w['text']in users[-1]or w['text']in decoded[-1]),'Actual native last user request does not contain sealed public turn'))
     if wanted['session']not in seen_sessions:
      prior_user_texts=[earlier['text']for earlier in cell['turns'][:turn_index]if earlier['session']!=wanted['session']]
      check(tid,'fresh_native_session_user_history',lambda users=users,decoded=decoded,prior=prior_user_texts:require(not any(old in message for old in prior for message in users+decoded),'Fresh cross-sessionB inherits raw sessionA user history'))
   seen_sessions.add(wanted['session'])
  options=manifest['options'];reserved=sum(int(p.get('token_reservation',0)or 0)+sum((p.get('usage')or{}).get(k,0)for k in('prompt_tokens','completion_tokens'))for p in provider)+len(dispatch['pending_dispatches_unknown_usage'])*int(options.get('failed_attempt_token_reservation',1056768))
  check(tid,'whole_episode_token_cap',lambda:require(reserved<=int(options['max_total_tokens']),'Whole episode exceeded registered token budget'))
  contexts=[]
  # v4.6 fix: sampling must come from the sealed per-model experiment options,
  # never a hardcoded super/other split (MINI registered 1/.95 for BOTH models).
  def pinned_sampling(model_name):
    per=(manifest.get('model_options')or{}).get(model_name)or options
    return float(per.get('temperature',0)),float(per.get('top_p',1))
  for request in provider:
   if request.get('effective_request_capture'):
    temperature,top_p=pinned_sampling(cell['model'])
    check(tid,'native_effective_capture',lambda r=request,t=temperature,tp=top_p:verify_request_capture(r,t,tp))
   cap=request.get('native_request_capture')or{}
   if cap.get('path')and Path(cap['path']).exists():contexts.extend(json.loads(Path(cap['path']).read_text()).get('messages',[]))
   if request.get('status')==200 and admitted:
    check(tid,'actual_model_identity',lambda r=request:require(r.get('request_model')==cell['model'].removeprefix('nvidia/')and r.get('response_models')==[admitted['accepted_response_model']]and r.get('checkpoint_unverified')==admitted.get('checkpoint_unverified',False)and r.get('admission_contract')==admitted['admission_contract'],'Requested/actual model metadata differs from pinned admission'))
  ledger=check(tid,'mcp_telemetry',lambda:read_jsonl(row.get('mcp_ledger')))or[]
  with tempfile.TemporaryDirectory(prefix='v45-memory-audit-')as temp:
   prefix=Path(temp)/'mcp.jsonl';prefix.write_text(''.join(json.dumps(x)+'\n'for x in ledger));calls=check(tid,'source_and_common_derived_replay',lambda:verify_mcp_attempt(task,{'ledger_path':str(prefix)},allow_empty=True))or[]
   # Regrade into disposable space, preserving all original result/grade bytes.
   recalculated=check(tid,'independent_regrade',lambda:evaluate_episode(row,task,Path(temp)/'regrade'))
   if recalculated:
    for field in('episode_grounded_financial_success','memory_state_correctness','public_contract_valid','controlled_user_state_correctness','user_fact_receipts_valid'):
     check(tid,'grade_'+field,lambda field=field:require(row.get(field)==recalculated[field],'Recorded automatic endpoint differs: '+field))
  from v45_call_binding import CallBindings
  scopes={}
  for turn in turns:
   for i in range(turn.get('provider_rows_start',0),turn.get('provider_rows_end',0)):scopes[i]=turn['session']
  if len(turns)<len(cell['turns']):
   for i in range(max(scopes,default=-1)+1,len(provider)):scopes[i]=cell['turns'][len(turns)]['session']
  bindings=check(tid,'generated_occurrence_inventory',lambda:CallBindings(provider,scopes))or CallBindings([])
  replayed=[]
  source_generations={}
  for record in calls:
   def proof(context,record=record):
    content=context['content']
    if record.get('status')=='rejected':
     from v46_rejection_proof import rejected_context
     return rejected_context(content,record)
    if record.get('tool')in('analytics_compute','analytics_calculate'):return any(obj.get('derived_result')==record.get('derivation')and obj.get('source_evidence')==record.get('source_evidence')for obj in json_objects(content))
    return has_receipt(content,record)
   from v46_rejection_proof import bind_source
   key=bind_source(bindings,record,proof)
   if key:source_generations[record['call_id']]=next(g for g in bindings.generated if g['key']==key)
   elif interrupted:partials.append({'trial_id':tid,'kind':'executed_source_without_final_context','call_id':record['call_id']})
   else:check(tid,'actual_source_sdk_context',lambda:require(False,'Source receipt/function/args not joined to unique generation occurrence'))
  sources={};entries=load_entries(task/'environment/payloads.json')[0];prior={}
  for record in calls:
   if record.get('status')=='ok'and record.get('tool')not in('analytics_compute','analytics_calculate'):
    env=select_envelope(entries,record['tool'],record['arguments']);env['benchmark_evidence']={k:record[k]for k in('call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of')};env['_audit_source_request']=record['arguments'];sources[record['call_id']]=env
   if record.get('status')=='ok'and record.get('tool')=='analytics_calculate':
    checked=check(tid,'independent_decimal_common_math',lambda r=record:verify_common(r,sources,prior))
    if checked is not None:prior['calc:'+record['call_id']]=record
  # Actual common read responses must be hash-bound and visible, never inferred
  # from expected gold or controller final state.
  for access in read_jsonl(row.get('memory_access_ledger')):
   response=access.get('response')
   check(tid,'user_read_response_hash',lambda a=access,r=response:require(isinstance(r,dict)and digest(r)==a.get('response_sha256')and r.get('memory_trace_id')==a.get('trace_id'),'User read response missing/hash differs'))
   contexts=[c for c in bindings.contexts if c['tool']=='benchmark_user_notebook_read'and c['arguments']==access.get('arguments')and any(obj==response for obj in json_objects(c['content']))]
   key=None
   for context in contexts:
    key=bindings.claim(context['id'],'benchmark_user_notebook_read',access['arguments'],lambda c:any(obj==response for obj in json_objects(c['content'])))
    if key:break
   if not key and interrupted:partials.append({'trial_id':tid,'kind':'executed_memory_read_without_final_context','trace_id':access.get('trace_id')})
   else:check(tid,'actual_user_read_context',lambda key=key:require(bool(key),'Executed user read not joined to a distinct actual generation/context'))
  # Native arithmetic can occur in any continuation. Reuse the independent
  # Decimal verifier, retaining per-session execution records and prior proofs.
  native_prior={};runner=out/'episodes'/tid/'runner';persisted=[]
  for evidence in sorted((runner/'ot-home/sessions').glob('*/evidence/results.jsonl')):
   persisted +=[{**record,'_audit_native_session_id':evidence.parents[1].name}for record in read_jsonl(evidence)]
  from v45_math_audit import verify_native
  for native_path in sorted(runner.rglob('native-derived*.jsonl')):
   for record in read_jsonl(native_path):
    if record.get('kind')not in('native_derived','native_utility'):continue
    sdk=record.get('sdk_call_id');logical=record.get('memory_session',record.get('logical_session'));turn_index=record.get('memory_turn')
    active_turn=next((turn for turn in turns if turn.get('session')==logical and turn.get('turn')==turn_index),None)
    check(tid,'native_execution_actual_turn_stamp',lambda:require(active_turn is not None and isinstance(record.get('provider_request_index'),int),'Native execution lacks trusted native session/turn/provider generation stamp'))
    bounds=(active_turn['provider_rows_start'],active_turn['provider_rows_end'])if active_turn else(None,None)
    key=bindings.claim(sdk,record['tool'],record['arguments'],scope=logical,request_bounds=bounds if active_turn else None,provider_index=record.get('provider_request_index'))
    native_generation=next((g for g in bindings.generated if g['key']==key),None)
    if not key and interrupted:partials.append({'trial_id':tid,'kind':'native_execution_without_final_context','sdk_call_id':sdk})
    else:check(tid,'native_execution_sdk_binding',lambda key=key:require(bool(key),'Native execution SDK/tool/args lacks distinct generation occurrence'))
    if record.get('status')!='ok'or record.get('kind')!='native_derived':continue
    verified=check(tid,'independent_decimal_native_math',lambda r=record:verify_native(r,sources,native_prior.setdefault(r.get('native_session_id','missing-native-session'),{})))
    if verified is not None:native_prior.setdefault(record.get('native_session_id','missing-native-session'),{})[sdk]=record
    check(tid,'native_source_receipts_actual',lambda r=record:require(bool(r.get('source_receipts'))and grounded_answer({'evidence':r['source_receipts']},calls),'Native receipts not actual retrieved market sources'))
    for leaf in record['result']['derived_result'].get('inputs',[]):
     def bind_raw(leaf=leaf):
      hits=[x for x in persisted if x.get('callId')==leaf.get('sdk_call_id')and x.get('ref')==leaf.get('ref')and x.get('rawSha256')==leaf.get('raw_source_sha256')and x.get('_audit_native_session_id')==record.get('native_session_id')]
      require(len(hits)==1,'Native root lacks unique persisted SDK/ref')
      stored=hits[0]
      require(isinstance(stored.get('rawText'),str)and hashlib.sha256(stored['rawText'].encode()).hexdigest()==stored.get('rawSha256')==leaf.get('raw_source_sha256'),'Raw source bytes/hash mismatch')
      require(isinstance(stored.get('text'),str)and hashlib.sha256(stored['text'].encode()).hexdigest()==stored.get('visibleSha256')==leaf.get('normalized_visible_sha256'),'Visible normalized bytes/hash mismatch')
      require(stored.get('sourceInput',stored.get('input'))==leaf.get('query_context')==sources[leaf['call_id']].get('_audit_source_request'),'Persisted native query differs from actual market call')
      require(any(obj.get('benchmark_evidence')==leaf['receipt']and digest({k:v for k,v in obj.items()if k!='benchmark_evidence'})==leaf['receipt']['response_sha256']for obj in json_objects(stored['rawText'])),'Raw source envelope differs from original receipt')
     check(tid,'native_raw_visible_source_binding',bind_raw)
     source_index=(source_generations.get(leaf['call_id'])or{}).get('request');native_index=(native_generation or{}).get('request')
     check(tid,'native_prior_actual_source_context',lambda si=source_index,ni=native_index,leaf=leaf:require(si is not None and ni is not None and si<ni and any(c['id']==leaf.get('sdk_call_id')and has_receipt(c['content'],leaf['receipt'])for c in bindings.contexts),'Native arithmetic source not prior actual model-visible occurrence'))
  localdefs=build_tool_defs(entries)
  from runners.memory_snapshot_server import DEFINITION
  localdefs.append(DEFINITION)
  crash_seen={}
  for index,turn in enumerate(row.get('turn_results',row.get('completed_turns',[]))):
   result=turn.get('result',{});inventory=result.get('inventory_path');defs=list(localdefs)
   if inventory and Path(inventory).exists():
    inv=json.loads(Path(inventory).read_text());defs +=[{'name':x['name'],'inputSchema':x['input'],'native_utility':True,'annotations':{'readOnlyHint':True}}for x in(inv.get('native_inventory')or{}).get('tools',[])]
   # v4.6: collect SDK/validator-crash tool-ends (infrastructure admission
   # failures: never reach MCP, no localRejection notice). Reconciliation
   # happens AFTER the local-rejection bindings so the two paths never compete
   # for the same generated occurrence.
   turn_log=runner/('turn-%02d.log'%index)
   if turn_log and turn_log.is_file():
    for line in turn_log.read_text(errors='replace').splitlines():
     try:event=json.loads(line)
     except ValueError:continue
     if(event.get('type')=='tool-end'and event.get('ok')is False and any(marker in str(event.get('output',''))for marker in
        ('invalid escaped character for Unicode pattern','Invalid regular expression'))):
      crash_seen.setdefault(event.get('callId'),{'event':event,'turn':index})
   rejected=check(tid,'local_rejection_proofs',lambda index=index,defs=defs:verify_local_rejections({'log_path':str(runner/('turn-%02d.log'%index))},provider,defs,row['arm'].startswith('ot_'),return_records=True))
   for rejection in rejected or[]:
    def bind_rejection(rejection=rejection):
     origin=rejection.get('origin_provider_request_index',rejection.get('provider_request_index'))
     origin_session=rejection.get('origin_memory_session',turn['session'])
     origin_turn=rejection.get('origin_memory_turn',index)
     require(isinstance(origin,int),'Local rejection lacks immutable origin generation')
     if origin_turn!=index or origin_session!=turn['session']:
      prior=[claim['generation'] for claim in bindings.claims if claim['generation']['id']==rejection['sdk_call_id'] and claim['generation']['tool']==__import__('v45_call_binding').canonical(rejection['tool']) and claim['generation']['arguments']==rejection['arguments'] and claim['generation']['provider_index']==origin and claim['generation']['scope']==origin_session]
      require(len(prior)==1,'Replayed rejection lacks previously authenticated exact origin')
      replayed.append({'sdk_call_id':rejection['sdk_call_id'],'notice_session':turn['session'],'notice_turn':index,'original_key':prior[0]['key']})
      return prior[0]['key']
     key=bindings.claim(rejection['sdk_call_id'],rejection['tool'],rejection['arguments'],scope=turn['session'],request_bounds=(turn['provider_rows_start'],turn['provider_rows_end']),provider_index=origin)
     require(bool(key),'Local rejection lacks distinct generated occurrence within original turn')
     return key
    check(tid,'local_rejection_occurrence',bind_rejection)
  # v4.6: reconcile "unknown tool" calls as infrastructure admission failures:
  # the call was generated against the sealed catalog but the turn's process
  # did not expose it (registration/transport gap). The model-visible error is
  # the proof; the call stays failed and cost-preserved; never evidence.
  for p_call in[g for g in bindings.pending()]:
   def unk_proof(context,p_call=p_call):
    if context['tool']!=p_call['tool']or context['arguments']!=p_call['arguments']:return False
    from v46_rejection_proof import unknown_context
    return unknown_context(context['content'],p_call['tool'])
   unk_matches=[c for c in bindings.contexts if unk_proof(c)]
   if unk_matches:
    try:
     key=bindings.claim(unk_matches[0]['id'],p_call['tool'],p_call['arguments'],unk_proof)
     check(tid,'tool_unavailable_reconciled',lambda k=key:require(bool(k),'Unknown-tool call lacks distinct generated occurrence'))
    except ValueError as ue:
     check(tid,'tool_unavailable_reconciled',lambda e=ue:require(False,'Unknown-tool reconciliation: '+str(ue)))
  # Missing notebook access telemetry or validator compilation failures stay
  # uncertified. Do not reconstruct execution from broad prose/SDK-ID matches.
  pending=bindings.pending()
  if pending and interrupted:partials.append({'trial_id':tid,'kind':'unexecuted_or_unconsumed_generated_calls','generation_occurrences':pending,'financial_evidence':False})
  else:check(tid,'all_generated_calls_reconciled',lambda:require(not pending,'Generated calls not executed or independently rejected: '+str(pending)))
 resume=out/'completed-resume-proof.json'
 if not resume.exists():errors.append({'check':'completed_resume','error':'Missing actual completed-resume interceptor proof'})
 else:
  proof=json.loads(resume.read_text())
  from verify_v45_memory_resume import snapshot
  check('cohort','completed_resume',lambda:require(proof.get('pass')is True and proof.get('new_model_calls')==0 and proof.get('new_episode_or_gateway_constructors')==0 and proof.get('manifest_sha256')==hash_file(out/'manifest.json')and proof.get('after')==snapshot(out),'Invalid/changed completed-resume proof'))
 return {'study_version':'v4.6-update','schema':'memory-audit-v45','pass':not errors,'observed':len(rows),'scheduled':len(manifest['schedule']),'errors':errors,'checks':checks,'partial_telemetry':partials,'external_model_calls':0,'financial_narrative_review':'separate mandatory hash-bound memory-financial-review.json, all automatic wins in all arms','native_causal_memory_superiority':'not established by this diagnostic'}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);args=ap.parse_args();out=Path(args.run);result=audit(out);(out/'memory-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('checks','errors')}));raise SystemExit(0 if result['pass']else 1)
