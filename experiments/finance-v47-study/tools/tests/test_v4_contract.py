"""Temporal scope and frozen-grader sensitivity are shared by every arm."""
import runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0,str(ROOT/"tools"))
V4=runpy.run_path(str(ROOT/'tasks/pilot/fin-l1-quote-01/tests/grader.py'))
V3=runpy.run_path(str(ROOT/'tools/frozen_v3_grader.py'))
@pytest.mark.parametrize('text,accept',[
 ('2026; không phải bội số hiện tại',['2026']),
 ('2026, not current trading multiple',['2026']),
 ('Q3/2026; không bao gồm dự báo',['Q3/2026']),
 ('30/10/2026; không phải giá trong ngày',['30/10/2026']),
])
def test_non_temporal_negation_does_not_erase_period(text,accept):
 assert V4['period_hit'](text,accept)
 assert not V3['period_hit'](text,accept)
@pytest.mark.parametrize('text,accept',[
 ('không phải năm 2026',['2026']),('not 2026',['2026']),
 ('không phải Q3/2026',['Q3/2026']),('không phải quý 3/2026',['Q3/2026']),
 ('không phải 30/10/2026',['30/10/2026']),
 ('Q1/1900 không phải Q3/2026',['Q3/2026']),
 ('Q3/2026 so với Q1/2026',['Q3/2026']),
 ('2026 không đúng',['2026']),('2025, không phải bội số hiện tại',['2026']),
 ('30/10/2026 và 29/10/2026',['30/10/2026']),
])
def test_temporal_negation_and_wrong_period_still_fail(text,accept):
 assert not V4['period_hit'](text,accept)
def test_all_copied_graders_match_template_and_frozen_is_original():
 from _gen_templates import GRADER_TMPL
 for path in (ROOT/'tasks').glob('*/*/tests/grader.py'):
  expected=GRADER_TMPL.replace('("evidence","source_evidence")','("evidence","source_evidence","memory_evidence")')if(path.parents[1]/'environment/turns.json').exists()else GRADER_TMPL
  assert path.read_text()==expected
 assert (ROOT/'tools/frozen_v3_grader.py').read_bytes()==(ROOT.parents[1]/'experiments/finance-v44-study/tools/frozen_v3_grader.py').read_bytes()
def test_condition_policy_is_explicit_and_shared_runtime():
 from experiment_conditions import condition
 assert condition('opentrading_baseline')['finance_policy'] is False
 assert condition('opentrading_finance')['finance_policy'] is True
 assert condition('opencode')['finance_policy'] is False

def _local_fixture(tmp_path):
 import json
 from ready_check import verify_local_rejections
 log=tmp_path/'events.log'
 event={'type':'tool-end','callId':'generated-1','ok':False,'localRejection':{'code':'invalid_tool_input','tool':'opentrading_quote','rawInput':'{"days":"bad"}'}}
 log.write_text(json.dumps(event)+'\n')
 wire=tmp_path/'native.json'
 body={'messages':[{'role':'assistant','tool_calls':[{'id':'generated-1','function':{'name':'opentrading_quote','arguments':'{"days":"bad"}'}}]},{'role':'tool','tool_call_id':'generated-1','content':'Invalid input for tool quote: days must be number'}]}
 wire.write_text(json.dumps(body))
 attempt={'log_path':str(log)}
 provider=[{'response_tool_call_ids':['generated-1'],'native_request_capture':{'path':str(wire)}}]
 defs=[{'name':'quote','annotations':{'readOnlyHint':True},'inputSchema':{'type':'object','properties':{'days':{'type':'integer'}}}}]
 return verify_local_rejections, attempt, provider, defs, log, wire, event, body

def test_local_rejection_requires_generated_id_invalidargs_and_consumederror(tmp_path):
 verify,attempt,provider,defs,*_= _local_fixture(tmp_path)
 assert verify(attempt,provider,defs,True)==['generated-1']
 # v4.6-update validates authoritative schemas in B0 and B1 alike.
 assert verify(attempt,provider,defs,False)==['generated-1']


def test_baseline_cannot_claim_candidate_finance_policy_guard(tmp_path):
 import json
 verify,attempt,provider,defs,log,wire,event,body=_local_fixture(tmp_path)
 event['localRejection']['code']='policy_guard_rejected'
 event['localRejection']['reason']='Candidate-only policy guard'
 log.write_text(json.dumps(event)+'\n')
 with pytest.raises(ValueError,match='outside candidate policy'):verify(attempt,provider,defs,False)

@pytest.mark.parametrize('tamper',['id','validargs','missingresult','evidence','duplicate'])
def test_local_rejection_cannot_hide_unexecuted_calls(tmp_path,tamper):
 import json
 verify,attempt,provider,defs,log,wire,event,body=_local_fixture(tmp_path)
 if tamper=='id':provider[0]['response_tool_call_ids']=['other']
 if tamper=='validargs':event['localRejection']['rawInput']='{"days":2}'
 if tamper=='missingresult':body['messages'].pop()
 if tamper=='evidence':body['messages'][-1]['content']+=' benchmark_evidence'
 log.write_text(json.dumps(event)+'\n'+(json.dumps(event)+'\n' if tamper=='duplicate' else ''))
 wire.write_text(json.dumps(body))
 with pytest.raises(ValueError):verify(attempt,provider,defs,True)

def test_all_model_catalog_schemas_preserve_recorded_requests_and_metadata():
 import json,jsonschema
 from mcp_snapshot_server import load_entries,build_tool_defs
 catalog=json.loads((ROOT/'tools/tool_contracts_v4.json').read_text())
 contracts={d['name']:d for d in catalog['tools']}
 for path in (ROOT/'tasks').glob('*/*/environment/payloads.json'):
  entries,_=load_entries(path)
  for _,entry in entries:
   jsonschema.validate(entry['params'],contracts[entry['tool']]['inputSchema'])
  for item in build_tool_defs(entries):
   if item['name']=='analytics_compute':
    from analytics_compute import DEFINITION
    assert item==DEFINITION
    continue
   if item['name']=='analytics_calculate':
    from analytics_calculate import DEFINITION
    assert item==DEFINITION
    continue
   original=contracts[item['name']]
   assert item['description'].startswith('FINITE SNAPSHOT SUPPORT:')
   assert item['description'].endswith(original['description'])
   assert 'PRODUCTION API METADATA' in item['description']
   assert item['inputSchema']['x-opentrading-schema-profile']=='finite-replay-c2'
   assert item['inputSchema']['properties']==original['inputSchema']['properties']
   for key in ('outputSchema','annotations','_meta'):
    assert item.get(key)==original.get(key)

@pytest.mark.parametrize('args,kind',[
 ({'symbol':'HPG','interval':'day'},'v4_domain_constraint'),
 ({'symbol':'HPG','columns':['close']},'v4_domain_constraint'),
 ({'symbol':'HPG','days':0},'v4_domain_constraint'),
 ({'symbol':'HPG','columns':'close'},'frozen_v3_type_or_shape'),
])
def test_authoritative_common_c1_rejects_invaliddomains_without_data(tmp_path,args,kind):
 from mcp_snapshot_server import replay_call,load_entries
 import json
 task=ROOT/'tasks/smoke/smoke-quote-01/environment/payloads.json'
 entries,_=load_entries(task)
 ledger=tmp_path/'ledger.jsonl'
 env=replay_call(entries,'vn_quote_history',args,'payload-fixture',str(ledger))
 assert json.loads(ledger.read_text())['schema_failure_class']==kind
 assert env['request_rejected'] is True
 assert env['error']['code']=='invalid_request'
 assert not ({'benchmark_evidence','data','availability'} & env.keys())

def test_policy_guard_has_actual_same_tool_failed_intent_and_wire_error(tmp_path):
 import json
 verify,attempt,provider,defs,log,wire,event,body=_local_fixture(tmp_path)
 prior={'type':'tool-end','callId':'generated-1','ok':False,'output':'not_recorded: request unavailable in snapshot'}
 guard={'type':'tool-end','callId':'generated-2','ok':False,'localRejection':{'code':'policy_guard_rejected','tool':'opentrading_quote','rawInput':'{"days":2}','reason':'Tool correction exhausted or repeated rejected arguments; do not replay this request.'}}
 log.write_text(json.dumps({'type':'tool-start','callId':'generated-1','name':'opentrading_quote','input':{'days':2}})+'\n'+json.dumps(prior)+'\n'+json.dumps(guard)+'\n')
 provider[0]['response_tool_call_ids'].append('generated-2')
 body['messages'].extend([{'role':'assistant','tool_calls':[{'id':'generated-2','function':{'name':'opentrading_quote','arguments':'{"days":2}'}}]},{'role':'tool','tool_call_id':'generated-2','content':guard['localRejection']['reason']}])
 wire.write_text(json.dumps(body))
 assert verify(attempt,provider,defs,True)==['generated-2']
 log.write_text(json.dumps(guard)+'\n')
 with pytest.raises(ValueError,match='preceding failed'):verify(attempt,provider,defs,True)

def test_study_driver_rejects_unregistered_model_before_any_provider(tmp_path):
 import subprocess,sys
 result=subprocess.run([sys.executable,str(ROOT/'tools/run_benchmark.py'),'--model','nvidia/unregistered-model','--list-only'],capture_output=True,text=True)
 assert result.returncode==2
 assert 'outside this study allowlist' in result.stderr
 assert not list(tmp_path.iterdir())

def test_frozen_grading_sensitivity_is_persisted_for_same_answer(tmp_path):
 import json
 from run_benchmark import grade_answer
 task=tmp_path/'task';(task/'tests').mkdir(parents=True);(task/'solution').mkdir()
 (task/'tests/grader.py').write_bytes((ROOT/'tasks/pilot/fin-l1-quote-01/tests/grader.py').read_bytes())
 (task/'solution/gold.json').write_text(json.dumps({'expects':[{'type':'period','path':'period','accept':['2026']}]}))
 answer=tmp_path/'answer.json';answer.write_text(json.dumps({'period':'2026; không phải bội số hiện tại'}))
 now=grade_answer(str(answer),str(task),str(tmp_path))
 frozen=grade_answer(str(answer),str(task),str(tmp_path),frozen_v3=True)
 assert now['success'] and not frozen['success']
 assert Path(now['grade_path']).name=='grade.json'
 assert Path(frozen['grade_path']).name=='grade-frozen-v3.json'

def test_gateway_direct_model_admission_precedes_credentials_and_network(tmp_path,monkeypatch):
 from runners import provider
 def denied():raise AssertionError('Unauthorized model must never access credentials')
 monkeypatch.setattr(provider,'credential',denied)
 with pytest.raises(ValueError,match='user-authorized v45 NVIDIA'):
  provider.ProviderGateway('nvidia/unregistered-model',tmp_path/'provider.jsonl',{})
 assert not list(tmp_path.iterdir())

@pytest.mark.parametrize('newargs',[{'year':2025},{}])
def test_temporal_guard_has_actual_prior_scope_and_wire_error(tmp_path,newargs):
 import json
 verify,attempt,provider,defs,log,wire,event,body=_local_fixture(tmp_path)
 defs[0]['inputSchema']['properties']['year']={'type':'integer'}
 prior={'type':'tool-end','callId':'generated-1','ok':False,'output':'not_recorded'}
 reason='Tool correction changed the original temporal/financial scope; rejected without execution.'
 guard={'type':'tool-end','callId':'generated-2','ok':False,'localRejection':{'code':'policy_guard_rejected','tool':'opentrading_quote','rawInput':json.dumps(newargs),'reason':reason}}
 log.write_text(json.dumps({'type':'tool-start','callId':'generated-1','name':'opentrading_quote','input':{'year':2026}})+'\n'+json.dumps(prior)+'\n'+json.dumps(guard)+'\n')
 provider[0]['response_tool_call_ids'].append('generated-2')
 body['messages'].extend([{'role':'assistant','tool_calls':[{'id':'generated-2','function':{'name':'opentrading_quote','arguments':json.dumps(newargs)}}]},{'role':'tool','tool_call_id':'generated-2','content':reason}])
 wire.write_text(json.dumps(body))
 assert verify(attempt,provider,defs,True)==['generated-2']
 # A valid, unchanged period must never be presented as a scope rejection.
 guard['localRejection']['rawInput']='{"year":2026}'
 log.write_text(json.dumps({'type':'tool-start','callId':'generated-1','name':'opentrading_quote','input':{'year':2026}})+'\n'+json.dumps(prior)+'\n'+json.dumps(guard)+'\n')
 with pytest.raises(ValueError,match='does not actually change'):verify(attempt,provider,defs,True)

def test_completed_native_text_replaces_discarded_deltas_without_json_rescue(tmp_path):
 import json,subprocess
 helper=ROOT/'tools/runners/native_final.ts'
 script=tmp_path/'check.ts'
 script.write_text('import {completedFinalText} from '+json.dumps(str(helper))+';\n'+'''
 const run = (candidate: boolean, final: any) => {
   let text = '';
   const deltas = candidate ? [] : ['I will query the data first.'];
   for (const delta of deltas) text += delta;
   const completed = completedFinalText(final);
   if (completed !== undefined) text = completed;
   return text;
 };
 const event = (content: any) => ({type:'done',outcome:'completed',messages:[{role:'assistant',content:'old answer'},{role:'assistant',content}]});
 console.log(JSON.stringify({
   baseline:run(false,event([{type:'text',text:'{"value":2}'}])),
   candidate:run(true,event([{type:'text',text:'{"value":2}'}])),
   badProse:run(false,event('Still only prose.')),
   badJson:run(false,event('{"value":')),
   noEarlierFallback:run(false,{type:'done',outcome:'completed',messages:[{role:'assistant',content:'earlier JSON'},{role:'tool',content:[]}]}),
   failedKeepsPartial:run(false,{type:'done',outcome:'failed',messages:[]}),
 }));
 ''')
 result=subprocess.run([str(Path.home()/'.bun/bin/bun'),str(script)],capture_output=True,text=True,check=True)
 actual=json.loads(result.stdout)
 assert actual=={'baseline':'{"value":2}','candidate':'{"value":2}','badProse':'Still only prose.','badJson':'{"value":','noEarlierFallback':'','failedKeepsPartial':'I will query the data first.'}

def test_bounded_correction_localguard_requires_actual_failed_tools_and_phase(tmp_path):
 import copy,json
 verify,attempt,_provider,defs,log,wire,_event,_body=_local_fixture(tmp_path)
 defs.append({'name':'other','annotations':{'readOnlyHint':True},'inputSchema':{'type':'object','properties':{}}})
 reason='Bounded finance correction allows one execution of each originally failed read-only tool only.'
 event={'type':'tool-end','callId':'call-guard','ok':False,'localRejection':{'code':'policy_guard_rejected','tool':'opentrading_other','rawInput':'{}','reason':reason,'phase':'bounded_finance_correction','allowedTools':['opentrading_quote']}}
 def write_log():
  log.write_text('\n'.join(json.dumps(x) for x in [{'type':'tool-start','callId':'prior','name':'opentrading_quote','input':{'days':2}},{'type':'tool-end','callId':'prior','ok':False,'output':'not_recorded'},event])+'\n')
 write_log()
 phase={'messages':[{'role':'assistant','tool_calls':[{'id':'prior','function':{'name':'opentrading_quote','arguments':'{\"days\":2}'}}]},{'role':'tool','tool_call_id':'prior','content':'not_recorded'},{'role':'user','content':'One bounded correction. Correct only the failed request.'}]}
 phasewire=tmp_path/'phase.json';phasewire.write_text(json.dumps(phase))
 consumed=copy.deepcopy(phase)
 consumed['messages'].extend([{'role':'assistant','tool_calls':[{'id':'call-guard','function':{'name':'opentrading_other','arguments':'{}'}}]},{'role':'tool','tool_call_id':'call-guard','content':reason}])
 wire.write_text(json.dumps(consumed))
 provider=[{'response_tool_call_ids':['call-guard'],'native_request_capture':{'path':str(phasewire)}},{'response_tool_call_ids':[],'native_request_capture':{'path':str(wire)}}]
 assert verify(attempt,provider,defs,True)==['call-guard']
 event['localRejection']['allowedTools']=['opentrading_other'];write_log()
 with pytest.raises(ValueError,match='prior failed'):verify(attempt,provider,defs,True)
 event['localRejection']['allowedTools']=['opentrading_quote'];write_log()
 phasewire.write_text(json.dumps({'messages':[]}))
 with pytest.raises(ValueError,match='phase/repetition'):verify(attempt,provider,defs,True)

@pytest.mark.parametrize('outcome,rc,timed_out,error,status',[
 ('completed',0,False,None,'ok'),('failed',0,False,None,'error'),
 ('aborted',0,False,None,'aborted'),('completed',1,False,None,'error'),
 ('completed',0,True,None,'timeout'),('completed',0,False,'native failure','error'),
 (None,0,False,None,'error'),
])
def test_native_completion_outcome_cannot_hide_failure(outcome,rc,timed_out,error,status):
 import json
 from runners.run_opentrading import native_result_status
 events=[]
 if error:events.append({'type':'error','message':error})
 if outcome:events.append({'type':'done','outcome':outcome,'unanswered':True,'recoveries':[{'kind':'promise','attempt':1}]})
 result=native_result_status(rc,'\n'.join(json.dumps(e) for e in events),timed_out)
 assert result['status']==status
 if outcome:
  assert result['native_completion']['unanswered'] is True
  assert result['native_completion']['recoveries']==[{'kind':'promise','attempt':1}]

def test_native_source_inventory_includes_tsx_and_tracks_byte_changes(tmp_path):
 from run_manifest import native_source_fingerprint
 (tmp_path/'src').mkdir()
 path=tmp_path/'src/view.tsx';path.write_text('export const view = <span>A</span>')
 (tmp_path/'src/core.ts').write_text('export const n = 1')
 before=native_source_fingerprint(tmp_path)
 assert set(before)=={'src/view.tsx','src/core.ts'}
 path.write_text('export const view = <span>B</span>')
 assert native_source_fingerprint(tmp_path)!=before

def test_parallel_duplicate_guard_requires_same_batch_and_actual_other_mcp_execution(tmp_path):
 import copy,json
 verify,attempt,_provider,defs,log,wire,_event,_body=_local_fixture(tmp_path)
 reason='Bounded finance correction allows one execution of each originally failed read-only tool only.'
 event={'type':'tool-end','callId':'guard','ok':False,'localRejection':{'code':'policy_guard_rejected','tool':'opentrading_quote','rawInput':'{"days":2}','reason':reason,'phase':'bounded_finance_correction','allowedTools':['opentrading_quote']}}
 events=[{'type':'tool-start','callId':'prior','name':'opentrading_quote','input':{'days':1}},{'type':'tool-end','callId':'prior','ok':False,'output':'not_recorded'},
         {'type':'tool-start','callId':'executed','name':'opentrading_quote','input':{'days':2}},{'type':'tool-end','callId':'executed','ok':True,'output':'actual response'},event]
 log.write_text('\n'.join(json.dumps(e) for e in events)+'\n')
 phase={'messages':[{'role':'assistant','tool_calls':[{'id':'prior','function':{'name':'opentrading_quote','arguments':'{"days":1}'}}]},{'role':'tool','tool_call_id':'prior','content':'not_recorded'},{'role':'user','content':'One bounded correction.'}]}
 phasewire=tmp_path/'phase.json';phasewire.write_text(json.dumps(phase))
 consumed=copy.deepcopy(phase)
 consumed['messages'].extend([{'role':'assistant','tool_calls':[{'id':'executed','function':{'name':'opentrading_quote','arguments':'{"days":2}'}},{'id':'guard','function':{'name':'opentrading_quote','arguments':'{"days":2}'}}]},{'role':'tool','tool_call_id':'executed','content':'actual response'},{'role':'tool','tool_call_id':'guard','content':reason}])
 wire.write_text(json.dumps(consumed))
 provider=[{'response_tool_call_ids':['executed','guard'],'native_request_capture':{'path':str(phasewire)}},{'response_tool_call_ids':[],'native_request_capture':{'path':str(wire)}}]
 ledger=tmp_path/'mcp.jsonl';ledger.write_text(json.dumps({'tool':'quote','arguments':{'days':2},'status':'ok'})+'\n');attempt['ledger_path']=str(ledger)
 assert verify(attempt,provider,defs,True)==['guard']
 ledger.unlink()
 with pytest.raises(ValueError,match='phase/repetition'):verify(attempt,provider,defs,True)

def test_replayed_notice_cannot_attach_to_later_reused_sdkid(tmp_path):
 import json
 verify,attempt,provider,defs,log,wire,event,body=_local_fixture(tmp_path)
 first={**event,'provider_request_index':1}
 second={'type':'tool-end','callId':'generated-1','ok':True,'provider_request_index':3,'output':'actual response'}
 notice={'event':'financial_local_rejection','sdk_call_id':'generated-1',**event['localRejection'],'origin_provider_request_index':1,'origin_sdk_call_id':'generated-1','replay_of':{'origin_provider_request_index':1,'origin_sdk_call_id':'generated-1'}}
 log.write_text('\n'.join(json.dumps(x)for x in [first,second,{'type':'notice','provider_request_index':3,'text':json.dumps(notice)}])+'\n')
 records=verify(attempt,provider,defs,True,return_records=True)
 assert len(records)==1 and records[0]['origin_provider_request_index']==1
 # If the claimed original generation is absent, latest SDK reuse cannot rescue it.
 notice['origin_provider_request_index']=2
 log.write_text('\n'.join(json.dumps(x)for x in [first,second,{'type':'notice','provider_request_index':3,'text':json.dumps(notice)}])+'\n')
 with pytest.raises(ValueError,match='immutable origin'):verify(attempt,provider,defs,True)
