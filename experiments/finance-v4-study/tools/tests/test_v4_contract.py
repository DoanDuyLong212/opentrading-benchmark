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
  assert path.read_text()==GRADER_TMPL
 assert (ROOT/'tools/frozen_v3_grader.py').read_bytes()==(ROOT.parents[1]/'tasks/pilot/fin-l1-quote-01/tests/grader.py').read_bytes()
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
 defs=[{'name':'quote','inputSchema':{'type':'object','properties':{'days':{'type':'integer'}}}}]
 return verify_local_rejections, attempt, provider, defs, log, wire, event, body

def test_local_rejection_requires_generated_id_invalidargs_and_consumederror(tmp_path):
 verify,attempt,provider,defs,*_= _local_fixture(tmp_path)
 assert verify(attempt,provider,defs,True)==['generated-1']
 with pytest.raises(ValueError,match='outside candidate'):verify(attempt,provider,defs,False)

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
   original=contracts[item['name']]
   assert item['description'].startswith(original['description'])
   for key in ('inputSchema','outputSchema','annotations','_meta'):
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

def test_study_driver_rejects_non_bolt_model_before_any_provider(tmp_path):
 import subprocess,sys
 result=subprocess.run([sys.executable,str(ROOT/'tools/run_benchmark.py'),'--model','nvidia/deepseek-ai/deepseek-v4.1-flash','--list-only'],capture_output=True,text=True)
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
 with pytest.raises(ValueError,match='verified NVIDIA'):
  provider.ProviderGateway('nvidia/deepseek-ai/deepseek-v4.1-flash',tmp_path/'provider.jsonl',{})
 assert not list(tmp_path.iterdir())
