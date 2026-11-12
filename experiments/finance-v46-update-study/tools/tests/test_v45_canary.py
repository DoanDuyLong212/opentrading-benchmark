import importlib.util,json,sys
from pathlib import Path
from unittest.mock import patch
import pytest
PATH=Path(__file__).resolve().parents[1]/'verify_nvidia.py'
def module():
 spec=importlib.util.spec_from_file_location('v45_canary',PATH);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_schedule_exact_caps_and_acceptance(tmp_path):
 m=module();out=tmp_path/'canary.json';requests=[]
 def fake(path,body,deadline):
  requests.append((path,body))
  if body is None:return {'status':200},{'data':[{'id':model} for model in m.AUTHORIZED_MODELS]}
  common={'status':200,'response_model':body['model'],'usage':{'prompt_tokens':10,'completion_tokens':4}}
  if len(body['messages'])==1:return common,{'choices':[{'message':{'role':'assistant','tool_calls':[{'id':'sdk1','type':'function','function':{'name':'select_numeric','arguments':'{"path":"/data/point"}'}}]}}]}
  return common,{'choices':[{'message':{'role':'assistant','content':'{"value":17}'}}]}
 with patch.object(m,'request',side_effect=fake),patch.object(sys,'argv',['canary','--execute','--approved-manifest-sha256',m.digest(m.manifest()),'--out',str(out)]):assert m.main()==0
 assert len(requests)==25 and sum(body is not None for _,body in requests)==24
 results=json.loads(out.read_text());assert len(results['cases'])==12 and results['chat_requests']==24
 assert all(r['state']=='completed' for r in results['cases'])
 for model in m.AUTHORIZED_MODELS:assert json.loads((tmp_path/(model.replace('/','__')+'.json')).read_text())['function_call_verified']
 # Interrupted/completed output cannot repeat a request.
 with patch.object(m,'request') as req,patch.object(sys,'argv',['canary','--execute','--approved-manifest-sha256',m.digest(m.manifest()),'--out',str(out)]),pytest.raises(SystemExit):m.main()
 assert not req.called

def test_no_run_without_manifest_or_explicit_execution():
 m=module()
 with patch.object(m,'request') as req,patch.object(sys,'argv',['canary']):assert m.main()==0
 assert not req.called
 with patch.object(m,'request') as req,patch.object(sys,'argv',['canary','--execute','--approved-manifest-sha256','wrong']),pytest.raises(SystemExit):m.main()
 assert not req.called

def test_counter_hardcaps_before_network():
 m=module();m.REQUEST_COUNT={'chat':24,'catalog':1}
 with patch.object(m.urllib.request,'urlopen') as req,pytest.raises(RuntimeError):m.request('/chat/completions',{},999999999)
 assert not req.called
 assert m.exact_answer('{"value":17}') and not m.exact_answer('1717') and not m.exact_answer('{"value":1717}')

def test_deadline_no_dispatch_and_malformed_message():
 m=module()
 with patch.object(m.urllib.request,'urlopen') as req,pytest.raises(RuntimeError,match='deadline'):m.request('/chat/completions',{},0)
 assert not req.called and m.REQUEST_COUNT=={'chat':0,'catalog':0}
 for bad in [None,[],{}, {'choices':None},{'choices':[]},{'choices':[None]},{'choices':[{'message':None}]}]:assert m.first_message(bad)=={}
