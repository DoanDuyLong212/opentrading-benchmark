import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from v45_call_binding import CallBindings

def generated(tmp_path,n,tool,args,context):
 raw=tmp_path/f'response{n}.json';cap=tmp_path/f'request{n}.json'
 raw.write_text(json.dumps({'choices':[{'message':{'tool_calls':[{'id':'same-id','function':{'name':'opentrading_'+tool,'arguments':json.dumps(args)}}]}}]}));cap.write_text(json.dumps({'messages':context}))
 return {'status':200,'raw_response_capture':{'path':str(raw),'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest()},'native_request_capture':{'path':str(cap)}}
def result(tool,args,receipt):return[{'role':'assistant','tool_calls':[{'id':'same-id','function':{'name':'opentrading_'+tool,'arguments':json.dumps(args)}}]},{'role':'tool','tool_call_id':'same-id','content':json.dumps({'receipt':receipt})}]

def test_repeated_sdkid_fresh_sessions_and_steps_bind_independent_occurrences(tmp_path):
 a=result('quote',{'symbol':'A'},'uuid-A');b=result('statements',{'symbol':'B'},'uuid-B')
 rows=[generated(tmp_path,0,'quote',{'symbol':'A'},[]),generated(tmp_path,1,'quote',{'symbol':'finishA'},a),generated(tmp_path,2,'statements',{'symbol':'B'},[]),generated(tmp_path,3,'quote',{'symbol':'finishB'},b)]
 bind=CallBindings(rows,{0:'A',1:'A',2:'B',3:'B'})
 assert bind.claim('same-id','quote',{'symbol':'A'},lambda c:'uuid-A'in c['content'])=='0:0:0'
 assert bind.claim('same-id','statements',{'symbol':'B'},lambda c:'uuid-B'in c['content'])=='2:0:0'
 # Same session two assistant steps: fullcontextdisambiguates reusedID.
 rows=[generated(tmp_path,0,'quote',{'symbol':'A'},[]),generated(tmp_path,1,'statements',{'symbol':'B'},a),generated(tmp_path,2,'quote',{'symbol':'C'},a+b)]
 bind=CallBindings(rows)
 assert bind.claim('same-id','quote',{'symbol':'A'},lambda c:'uuid-A'in c['content'])
 assert bind.claim('same-id','statements',{'symbol':'B'},lambda c:'uuid-B'in c['content'])
 assert not bind.claim('same-id','quote',{'symbol':'A'},lambda c:'uuid-B'in c['content'])


def test_repeated_equal_signature_still_requires_two_executions(tmp_path):
 a=result('quote',{'symbol':'A'},'one');b=result('quote',{'symbol':'A'},'two')
 rows=[generated(tmp_path,0,'quote',{'symbol':'A'},[]),generated(tmp_path,1,'quote',{'symbol':'A'},a),generated(tmp_path,2,'quote',{'symbol':'B'},a+b)]
 bind=CallBindings(rows);assert bind.claim('same-id','quote',{'symbol':'A'},lambda c:'one'in c['content'])
 assert len(bind.pending())==2
 assert bind.claim('same-id','quote',{'symbol':'A'},lambda c:'two'in c['content'])
 assert len(bind.pending())==1


def test_stream_fragments_keep_request_occurrences_without_rewriting_ids(tmp_path):
 from v45_call_binding import response_calls
 p=tmp_path/'stream';p.write_text('data: '+json.dumps({'choices':[{'index':0,'delta':{'tool_calls':[{'index':0,'id':'callX','function':{'name':'opentrading_quote','arguments':'{"symbol":'}}]}}]})+'\n\ndata: '+json.dumps({'choices':[{'index':0,'delta':{'tool_calls':[{'index':0,'function':{'arguments':'"A"}'}}]}}]})+'\n\ndata: [DONE]\n\n')
 calls=response_calls([{'status':200,'raw_response_capture':{'path':str(p),'raw_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}]);assert calls==[{'key':'0:0:0','request':0,'provider_index':1,'id':'callX','tool':'quote','arguments':{'symbol':'A'}}]


def test_identical_args_across_fresh_sessions_never_bind_earlier_rejection(tmp_path):
 rejected=result('quote',{'symbol':'A'},'local-error');answered=result('quote',{'symbol':'A'},'receipt-B')
 rows=[generated(tmp_path,0,'quote',{'symbol':'A'},[]),generated(tmp_path,1,'other',{},rejected),generated(tmp_path,2,'quote',{'symbol':'A'},[]),generated(tmp_path,3,'other',{},answered)]
 bind=CallBindings(rows,{0:'A',1:'A',2:'B',3:'B'})
 assert bind.claim('same-id','quote',{'symbol':'A'},lambda c:'receipt-B'in c['content'])=='2:0:0'
 assert any(g['key']=='0:0:0'for g in bind.pending())

def test_changed_actual_response_bytes_are_rejected(tmp_path):
 import pytest
 row=generated(tmp_path,0,'quote',{},[]);Path(row['raw_response_capture']['path']).write_text('{}')
 with pytest.raises(ValueError,match='hash'):CallBindings([row])


def test_native_execution_and_local_rejection_require_actual_scope_turn_generation(tmp_path):
 a=result('calculate',{'expression':'same'},'local-rejection');b=result('calculate',{'expression':'same'},'native-result')
 rows=[generated(tmp_path,0,'calculate',{'expression':'same'},[]),generated(tmp_path,1,'other',{},a),generated(tmp_path,2,'calculate',{'expression':'same'},[]),generated(tmp_path,3,'other',{},b)]
 bind=CallBindings(rows,{0:'A',1:'A',2:'B',3:'B'})
 assert bind.claim('same-id','calculate',{'expression':'same'})is None # no guessingwithoutproof
 assert bind.claim('same-id','calculate',{'expression':'same'},scope='B',request_bounds=(2,4),provider_index=3)=='2:0:0'
 assert bind.claim('same-id','calculate',{'expression':'same'},scope='A',request_bounds=(0,2),provider_index=1)=='0:0:0'
 # Withinoneconversation, actualprovider requestindex still disambiguatessteps.
 rows=[generated(tmp_path,0,'calculate',{'expression':'same'},[]),generated(tmp_path,1,'calculate',{'expression':'same'},a),generated(tmp_path,2,'other',{},a+b)]
 bind=CallBindings(rows)
 assert bind.claim('same-id','calculate',{'expression':'same'},provider_index=2)=='1:0:0'
 assert bind.claim('same-id','calculate',{'expression':'same'},provider_index=1)=='0:0:0'
