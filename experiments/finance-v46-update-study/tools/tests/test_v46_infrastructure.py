import json,sys,hashlib
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from provider_response import response_chunks
from v46_rejection_proof import rejected_context,unknown_context,bind_source
from v45_call_binding import CallBindings
from runners.run_opentrading import native_result_status

@pytest.mark.parametrize('prefix',[':\n\n',': heartbeat\r\n\r\n','event: message\nid: 4\n','retry: 3000\n'])
def test_sse_comments_and_metadata(prefix):
 assert response_chunks(prefix+'data:{"choices":[]}\n\ndata: [DONE]\n\n')==[{'choices':[]}]
def test_sse_multiline_data():
 assert response_chunks('data: {"choices":\ndata: []}\n\n')==[{'choices':[]}]
@pytest.mark.parametrize('value',['data: invalid\n\n','data: {}','data: []\n\n','data: {}\n\ndata: [DONE]\n\ndata: {}\n\n',': comment\n\n'])
def test_malformed_stream_fail_closed(value):
 with pytest.raises(ValueError):response_chunks(value)
@pytest.mark.parametrize('code',['invalid_request','unsupported_snapshot_query','invalid_derivation'])
def test_exact_negative_result(code):
 rec={'error_code':code};message=json.dumps({'request_rejected':True,'error':{'code':code}})
 assert rejected_context(message,rec)
 assert not rejected_context(message,{'error_code':'different'})
 assert not rejected_context(json.dumps({'error':{'code':code}}),rec)
 assert not rejected_context(json.dumps({'request_rejected':True,'error':{'code':code},'benchmark_evidence':{'call_id':'forged'}}),rec)
def make_row(tmp,n,ids,messages):
 raw=tmp/f'response{n}';cap=tmp/f'request{n}'
 raw.write_text(json.dumps({'choices':[{'message':{'tool_calls':[{'id':i,'function':{'name':'opentrading_quote','arguments':'{"x":1}'}}for i in ids]}}]}));cap.write_text(json.dumps({'messages':messages}))
 return {'index':n+1,'status':200,'raw_response_capture':{'path':str(raw),'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest()},'native_request_capture':{'path':str(cap)}}
def context(i):return [{'role':'assistant','tool_calls':[{'id':i,'function':{'name':'opentrading_quote','arguments':'{"x":1}'}}]},{'role':'tool','tool_call_id':i,'content':'{"request_rejected":true,"error":{"code":"invalid_request"}}'}]
def test_one_negative_ledger_cannot_cover_two_generations(tmp_path):
 rows=[make_row(tmp_path,0,['a'],[]),make_row(tmp_path,1,['b'],context('a')),make_row(tmp_path,2,[],context('a')+context('b'))]
 bindings=CallBindings(rows);record={'tool':'quote','arguments':{'x':1},'error_code':'invalid_request'}
 assert bind_source(bindings,record,lambda c:rejected_context(c['content'],record))is None
 assert len(bindings.pending())==2

def test_negative_record_consumes_only_exact_occurrence(tmp_path):
 rows=[make_row(tmp_path,0,['a'],[]),make_row(tmp_path,1,[],context('a'))]
 bindings=CallBindings(rows);record={'tool':'quote','arguments':{'x':1},'error_code':'invalid_request'}
 assert bind_source(bindings,record,lambda c:rejected_context(c['content'],record))=='0:0:0'
 assert bind_source(bindings,record,lambda c:rejected_context(c['content'],record))is None
 assert not bindings.pending()
def test_unknown_tool_actual_vietnamese_never_fuzzy():
 assert unknown_context('Không có tool "typo".','typo')
 assert not unknown_context('Không có tool "typo".','correct')
 assert not unknown_context('story mentions unknown tool "typo"','typo')
def test_unknown_tool_runtime_error_prefix_matches_full_name_only():
 # Runtime tool_result lines carry an 'Error: ' prefix; the generated tool
 # name must still match completely (no fuzzy/canonical repair).
 assert unknown_context('Error: unknown tool "mcp__openttradng__financial_statements"','mcp__openttradng__financial_statements')
 assert unknown_context('Error: unknown tool "analytics_calculate"','analytics_calculate')
 assert not unknown_context('Error: unknown tool "mcp__openttradng__financial_statements"','mcp__opentrading__financial_statements')
 assert not unknown_context('Error: unknown tool "analytics_calculate"','analytics_calc')
 assert not unknown_context('Error: unknown tool "analytics_calculate"','analytics_compute')
def test_unknown_tool_opencode_v2_sentence_form():
 # OpenCode v2 permission/unknown-tool sentence (pilot fin-l2-crypto-01 OC r2).
 msg='No tool named "execute" is currently available. Please use a tool from the available tool list.'
 assert unknown_context(msg,'execute')
 assert not unknown_context(msg,'shell')
 assert not unknown_context(msg,'exec')
def test_invalid_final_not_completed_even_when_native_done_completed():
 log='\n'.join(map(json.dumps,[{'type':'notice','text':json.dumps({'event':'financial_contract_invalid','issues':['bad receipt']})},{'type':'done','outcome':'completed'}]))
 assert native_result_status(0,log,False)['status']=='native_contract_invalid'
 assert native_result_status(0,log,True)['status']=='timeout'
def test_corrected_final_after_interim_rejection_can_complete():
 log='\n'.join(map(json.dumps,[{'type':'notice','text':json.dumps({'event':'financial_rejected_final','issues':['initial bad format']})},{'type':'done','outcome':'completed'}]))
 assert native_result_status(0,log,False)['status']=='ok'

@pytest.mark.parametrize('arm',['opentrading_baseline','opentrading_finance','opencode','dsh'])
@pytest.mark.parametrize('status,raw,expected',[('ok','{"value":1}',True),('ok','```json\n{"value":1}\n```',True),('error','{"value":1}',False),('native_contract_invalid','{"value":1}',False),('timeout','partial',False),('ok','',False)])
def test_native_completion_all_arms_status_and_raw_format_independent(arm,status,raw,expected):
 from runners.isolated import normalize_native_completion
 r=normalize_native_completion({'arm':arm,'status':status,'final_text':raw,'native_completion':{'outcome':'completed'}})
 assert r['native_completed'] is expected
 assert r['native_completion']['accepted'] is expected
 assert r['final_text']==raw

def test_native_completion_missing_terminal_proof_is_not_success():
 from runners.isolated import normalize_native_completion
 assert not normalize_native_completion({'status':'ok','final_text':'{"value":1}'})['native_completed']

def test_empty_or_malformed_tool_arguments_are_never_normalized():
 from v45_call_binding import arguments
 assert arguments('null')is None
 assert arguments('{"days":"365"}')=={'days':'365'}
 assert arguments('')==('invalid_raw_arguments','')

def test_sse_does_not_invent_finish_or_tool_calls():
 chunks=response_chunks(': heartbeat\n\ndata: {"choices":[{"delta":{"content":"partial"}}]}\n\n')
 assert not any(c.get('finish_reason') for x in chunks for c in x.get('choices',[]))
 assert not any((c.get('delta')or{}).get('tool_calls') for x in chunks for c in x.get('choices',[]))

def test_protocol_alias_is_exact_and_main_is_out_of_scope():
 from protocol_compat import FINANCIAL_PROTOCOL,is_financial_protocol,AUTHORIZED_SPLITS
 assert is_financial_protocol(FINANCIAL_PROTOCOL)
 assert not is_financial_protocol('financial_product_v46')
 assert AUTHORIZED_SPLITS=={'devsmoke','pilot'}

def test_negative_ledger_generation_window_disambiguates_equal_calls(tmp_path):
 from datetime import datetime,timezone
 rows=[make_row(tmp_path,0,['a'],[]),make_row(tmp_path,1,['b'],context('a')),make_row(tmp_path,2,[],context('a')+context('b'))]
 for i,r in enumerate(rows):r['started_at']=100.+i*10
 b=CallBindings(rows)
 rec={'tool':'quote','arguments':{'x':1},'error_code':'invalid_request','started_at':datetime.fromtimestamp(105,tz=timezone.utc).isoformat()}
 assert bind_source(b,rec,lambda c:rejected_context(c['content'],rec))=='0:0:0'
 rec['started_at']=datetime.fromtimestamp(115,tz=timezone.utc).isoformat()
 assert bind_source(b,rec,lambda c:rejected_context(c['content'],rec))=='1:0:0'
 assert not b.pending()

def test_negative_ledger_wrong_generation_timestamp_rejected(tmp_path):
 from datetime import datetime,timezone
 rows=[make_row(tmp_path,0,['a'],[]),make_row(tmp_path,1,[],context('a'))]
 for i,r in enumerate(rows):r['started_at']=100.+i*10
 b=CallBindings(rows);rec={'tool':'quote','arguments':{'x':1},'error_code':'invalid_request','started_at':datetime.fromtimestamp(99,tz=timezone.utc).isoformat()}
 assert bind_source(b,rec,lambda c:rejected_context(c['content'],rec))is None
 assert len(b.pending())==1

def test_seal_cannot_self_authorize_diagnostic_pilot_or_main(tmp_path):
 from v45_gate import validate_seal
 from run_manifest import hash_file
 approval=tmp_path/'approval.json';approval.write_text('{"approved":true}')
 seal={'protocol':'financial_product_v45','study_version':'v4.6-update','engineering_approved':True,'approval':str(approval),'main_authorized_by_user':False,'diagnostic_pilot_authorized':False,'protected_files':{str(approval):hash_file(approval)},'runs':[]}
 p=tmp_path/'seal.json';p.write_text(json.dumps(seal));assert validate_seal(p)
 seal['diagnostic_pilot_authorized']=True;p.write_text(json.dumps(seal))
 with pytest.raises(ValueError,match='Diagnostic pilot authorization'):validate_seal(p)
 seal['diagnostic_pilot_authorized']=False;seal['runs']=[{'split':'main'}];p.write_text(json.dumps(seal))
 with pytest.raises(ValueError,match='smoke/pilot only'):validate_seal(p)
