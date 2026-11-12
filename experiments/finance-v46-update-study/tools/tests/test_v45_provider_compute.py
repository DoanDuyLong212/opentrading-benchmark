import io,json,sys,time,threading,urllib.error
from pathlib import Path
from unittest.mock import patch
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runners.provider import ProviderGateway,retry_delay,aggregate_usage,DEFAULT_MODEL
from analytics_compute import compute,numeric_candidates,SCHEMA

class Handler:
 path='/v1/chat/completions'
 def __init__(self,body):
  self.rfile=io.BytesIO(json.dumps(body).encode());self.headers={'Content-Length':str(len(self.rfile.getvalue())),'Authorization':'Bearer local'};self.wfile=io.BytesIO();self.status=None
 def send_response(self,status):self.status=status
 def send_header(self,*args):pass
 def end_headers(self):pass
class Response:
 status=200;headers={'Content-Type':'application/json'}
 def __init__(self,payload):self.buf=io.BytesIO(json.dumps(payload).encode())
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read1(self,n):return self.buf.read(n)
def setup(tmp_path,**options):
 g=ProviderGateway.__new__(ProviderGateway);g.options={'max_requests':24,'max_total_tokens':1000000,'request_interval_s':0,'max_output_tokens':128,'allowed_tool_names':['opentrading_select'],'snapshot_tool_definitions':[{'name':'select','inputSchema':{'type':'object'}}],**options};g.model=DEFAULT_MODEL;g.key='secret-real';g.token='local';g.ledger=tmp_path/'ledger';g.rows=[];g.lock=threading.Lock();g.request_count=0;g.logical_count=0;g.deadline=time.monotonic()+100
 body={'model':DEFAULT_MODEL,'messages':[{'role':'user','content':'test'}],'tools':[{'type':'function','function':{'name':'opentrading_select','parameters':{'type':'object'}}}]}
 return g,Handler(body)
def success(model=DEFAULT_MODEL):return Response({'model':model,'choices':[{'message':{'content':'ok'},'finish_reason':'stop'}],'usage':{'prompt_tokens':10,'completion_tokens':2}})
def test_success_captures_metadata_sampling(tmp_path):
 g,h=setup(tmp_path)
 with patch('urllib.request.urlopen',return_value=success()):g.handle(h)
 assert h.status==200;row=g.rows[0];assert row['finish_reasons']==['stop'];assert row['logical_final'];assert row['raw_response_capture']['bytes']>0
 effective=json.loads(Path(row['effective_request_capture']['path']).read_text());assert effective['temperature']==1 and effective['top_p']==.95
 assert 'secret-real' not in ''.join(p.read_text() for p in tmp_path.rglob('*') if p.is_file())
def test_http503_recovers_one_owner_same_payload(tmp_path):
 g,h=setup(tmp_path,failed_attempt_token_reservation=2000)
 error=urllib.error.HTTPError('url',503,'busy',{},io.BytesIO(b'{"error":"busy"}'))
 with patch('urllib.request.urlopen',side_effect=[error,success()]) as upstream,patch('runners.provider.time.sleep'):
  g.handle(h)
 assert h.status==200 and upstream.call_count==2
 assert [r['logical_final'] for r in g.rows]==[False,True]
 assert [r['transport_attempt'] for r in g.rows]==[1,2]
 assert g.rows[0]['token_reservation']==2000 and 'usage' not in g.rows[0]
 assert aggregate_usage(g.rows)['complete'] is False
 assert upstream.call_args_list[0].args[0].data==upstream.call_args_list[1].args[0].data
@pytest.mark.parametrize('status,body',[(401,b'badkey'),(403,b'forbidden'),(429,b'daily quota exhausted'),(400,b'bad schema')])
def test_never_retry_auth_daily_badrequest(tmp_path,status,body):
 g,h=setup(tmp_path,failed_attempt_token_reservation=2000)
 with patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('url',status,'fail',{},io.BytesIO(body))) as upstream,patch('runners.provider.time.sleep'):
  g.handle(h)
 assert upstream.call_count==1 and len(g.rows)==1 and g.rows[0]['logical_final']
def test_unknown_usage_failclosed(tmp_path):
 g,h=setup(tmp_path)
 with patch('urllib.request.urlopen',side_effect=TimeoutError) as upstream:g.handle(h)
 assert upstream.call_count==1 and h.status==424
 g,h2=g,Handler({'model':DEFAULT_MODEL,'messages':[],'tools':[{'type':'function','function':{'name':'opentrading_select','parameters':{'type':'object'}}}]})
 with patch('urllib.request.urlopen') as upstream:g.handle(h2)
 assert upstream.call_count==0 and h2.status==424 and g.rows[-1]['error']=='previous_upstream_usage_unknown'
@pytest.mark.parametrize('model,code',[(None,'provider_response_model_missing'),('other','provider_response_model_mismatch')])
def test_missing_metadata_no_retry(tmp_path,model,code):
 g,h=setup(tmp_path,failed_attempt_token_reservation=2000)
 with patch('urllib.request.urlopen',return_value=success(model)) as upstream:g.handle(h)
 assert upstream.call_count==1 and h.status==424 and g.rows[0]['error']==code
 assert g.rows[0]['error_origin']=='upstream_protocol'
def test_local_budget_is_not_auth(tmp_path):
 g,h=setup(tmp_path,max_total_tokens=1)
 with patch('urllib.request.urlopen') as upstream:g.handle(h)
 assert h.status==424 and not upstream.called and g.rows[0]['error_origin']=='local_policy'
@pytest.mark.parametrize('status,text,after,attempt,remaining,expected',[(429,'busy','12',1,60,12),(429,'busy','61',1,80,None),(503,'','',2,20,8),(503,'','',3,20,None),(503,'','',1,3,None),(429,'daily quota','',1,30,None),(200,'','',1,30,None)])
def test_retry_policy(status,text,after,attempt,remaining,expected):assert retry_delay(status,text,after,attempt,remaining)==expected

def source(cid,value,unit='VND',period='2026-01-01',entity='AAA',scope=None):
 data={'symbol':entity,'date':period,'last':value}
 if scope:data['scope']=scope
 return {'data':data,'units':{'last':unit},'benchmark_evidence':{'call_id':cid,'response_sha256':'r','payload_sha256':'p'}}
def arg(op,ids=('a','b'),unit='VND',out='VND'):return {'operation':op,'operands':[{'call_id':cid,'path':'/data/last'} for cid in ids],'input_unit':unit,'output_unit':out}
@pytest.mark.parametrize('op,out,expected',[('ratio','dimensionless',2),('absolute_difference','VND',50),('relative_difference_pct','%',100)])
def test_extended_operations(op,out,expected):assert compute(arg(op,out=out),{'a':source('a',100),'b':source('b',50)})['derived_result']['value']==expected
@pytest.mark.parametrize('path',['/data','/data/','/data//last','/data/~2'])
def test_schema_parent_nonleaf_reject(path):
 import jsonschema
 a=arg('scale',('a',));a['operands'][0]['path']=path
 with pytest.raises(jsonschema.ValidationError):compute(a,{'a':source('a',1)})
def test_unit_scale_scope_and_hints():
 a=arg('scale',('a',),'nghìn đồng/cổ phiếu','VND/cổ phiếu');s={'a':source('a',21,'nghìn đồng/cổ phiếu')}
 assert compute(a,s)['derived_result']['value']==21000
 a['operands'][0]['path']='/data/'
 assert numeric_candidates(a,s)==[{'call_id':'a','path':'/data/last','unit':'nghìn đồng/cổ phiếu'}]
 with pytest.raises(ValueError,match='scope mismatch'):compute(arg('mean'),{'a':source('a',1,scope='consolidated'),'b':source('b',2,scope='separate')})


def test_terminal_sdk_redelivery_no_extra_upstream(tmp_path):
 g,h=setup(tmp_path,failed_attempt_token_reservation=2000)
 error=urllib.error.HTTPError('url',503,'busy',{},io.BytesIO(b'busy'))
 with patch('urllib.request.urlopen',side_effect=[error,error,error]) as upstream,patch('runners.provider.time.sleep'):
  g.handle(h)
 assert upstream.call_count==3 and h.status==424
 body=json.loads(h.rfile.getvalue())
 with patch('urllib.request.urlopen') as upstream:g.handle(Handler(body))
 assert not upstream.called and g.rows[-1]['error']=='terminal_logical_request_redelivery'
 assert g.rows[-1]['terminal_redelivery_of']==1

def test_explicit_crossentity_ratio_no_blanket_deny():
 sources={'a':source('a',20,entity='AAA'),'b':source('b',10,entity='BBB')};a=arg('ratio',out='dimensionless')
 with pytest.raises(ValueError,match='same explicit recorded entity'):compute(a,sources)
 a['entity_policy']='cross_entity';assert compute(a,sources)['derived_result']['value']==2
 a['operation']='relative_difference_pct';a['output_unit']='%'
 with pytest.raises(ValueError,match='cross_entity policy'):compute(a,sources)

def test_registered_usage_bound_violation_fatal(tmp_path):
 g,h=setup(tmp_path,failed_attempt_context_bound=1,max_output_tokens=1)
 with patch('urllib.request.urlopen',return_value=success()) as upstream:g.handle(h)
 assert h.status==424 and upstream.call_count==1 and g.rows[0]['error']=='observed_usage_exceeds_registered_context_bound'


def test_memory_native_whitelist_is_profile_condition_specific():
 from runners.provider import native_tool_allowlist
 assert native_tool_allowlist({})=={'calculate','compute','read_result'}
 valid={'memory_profile':'controlled-memory-v1','condition':'ot_memory_on','native_arm':'opentrading'}
 assert native_tool_allowlist(valid)=={'calculate','compute','read_result','memory_read'}
 for key in valid:
  bad=dict(valid);bad[key]='wrong';assert 'memory_read'not in native_tool_allowlist(bad)

def test_pause_before_initial_dispatch_is_zero_call(tmp_path):
 flag=tmp_path/'control';flag.write_text('{"pause":true}')
 g,h=setup(tmp_path,control_file=str(flag))
 with patch('urllib.request.urlopen')as upstream:g.handle(h)
 assert upstream.call_count==0 and h.status==424 and g.request_count==0
 assert g.rows[-1]['error']=='user_pause_requested'and not g.rows[-1]['upstream_attempted']

def test_pause_during_rate_wait_blocks_dispatch(tmp_path):
 flag=tmp_path/'control';g,h=setup(tmp_path,control_file=str(flag),request_interval_s=10)
 def stop_in_wait(delay):flag.write_text('{"pause":true}')
 g.controlled_wait=stop_in_wait
 with open('/tmp/benchmark-nvidia-rate.lock','w')as f:f.write(str(time.time()))
 with patch('urllib.request.urlopen')as upstream:g.handle(h)
 assert upstream.call_count==0 and g.rows[-1]['error']=='user_pause_requested'

def test_pause_after_failed_transport_never_dispatches_retry(tmp_path):
 flag=tmp_path/'control';g,h=setup(tmp_path,control_file=str(flag),failed_attempt_token_reservation=2000)
 def failed(*args,**kwargs):
  flag.write_text('{"pause":true}')
  raise urllib.error.HTTPError('url',503,'busy',{},io.BytesIO(b'{"error":"busy"}'))
 with patch('urllib.request.urlopen',side_effect=failed)as upstream:g.handle(h)
 assert upstream.call_count==1 and h.status==424 and g.request_count==1
 assert len(g.rows)==2 and g.rows[0]['token_reservation']==2000 and g.rows[-1]['error']=='user_pause_requested'and not g.rows[-1]['upstream_attempted']
 assert g.rows[0]['index']!=g.rows[-1]['index']

def test_malformed_user_control_fails_closed(tmp_path):
 flag=tmp_path/'control';flag.write_text('{')
 g,h=setup(tmp_path,control_file=str(flag))
 with patch('urllib.request.urlopen')as upstream:g.handle(h)
 assert not upstream.called and g.rows[-1]['error']=='invalid_user_control_state'


def test_graceful_boundary_pause_does_not_abort_current_request(tmp_path):
 flag=tmp_path/'control';flag.write_text('{"pause_after_turn":true}')
 g,h=setup(tmp_path,control_file=str(flag))
 with patch('urllib.request.urlopen',return_value=success())as upstream:g.handle(h)
 assert upstream.call_count==1 and h.status==200

def test_explicit_hardstop_blocks_current_retry_dispatch(tmp_path):
 flag=tmp_path/'control';flag.write_text('{"hard_stop":true}')
 g,h=setup(tmp_path,control_file=str(flag))
 with patch('urllib.request.urlopen')as upstream:g.handle(h)
 assert not upstream.called and h.status==424
