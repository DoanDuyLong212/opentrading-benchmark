import hashlib,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/runners'),str(ROOT/'tools')]
from memory_runner import validate_operations
from memory_snapshot_server import read_notebook
BUN=ROOT.parent/'toolchains/bun-1.4.4/bun'
def test_user_operation_requires_verbatim_explicit_consent():
 state={'entries':{}};text='Nhớ ROE phải trên 12%.';op={'id':'roe','op':'put','kind':'constraint','text':text,'source_text':text,'consent':'explicit_user_request'}
 validate_operations(text,[op],state)
 with pytest.raises(ValueError):validate_operations('Assistant suggested threshold12',[op],state)
 with pytest.raises(ValueError):validate_operations(text,[dict(op,text='ROE 25%')],state)
 with pytest.raises(ValueError):validate_operations(text,[dict(op,consent='assistant_card')],state)
def test_read_notebook_exposes_only_active_user_facts_with_separate_trace(tmp_path):
 notebook=tmp_path/'facts.json';trace=tmp_path/'trace.jsonl';notebook.write_text(json.dumps({'entries':{'a':{'id':'a','text':'active user preference'},'b':{'id':'b','text':'forgotten','deleted':True}}}))
 response=read_notebook({},notebook,trace);assert response['facts']==[{'id':'a','text':'active user preference'}]
 row=json.loads(trace.read_text());assert row['response']==response;assert 'benchmark_evidence'not in response
 assert row['response_sha256']==hashlib.sha256(json.dumps(response,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_native_user_forms_revision_revoke_and_readonly_audit(tmp_path):
 home=tmp_path/'runner/ot-home'
 def call(ops,text='',audit=False):
  r=subprocess.run([str(BUN),str(ROOT/'tools/runners/ot_memory_admin.ts')],input=json.dumps({'home':str(home),'operations':ops,'user_text':text,'audit_only':audit}),text=True,capture_output=True)
  assert r.returncode==0,r.stderr;return json.loads(r.stdout)
 def put(text):return{'op':'put','id':'roe','kind':'constraint','text':text,'source_text':text,'consent':'explicit_user_request'}
 first=call([put('Nhớ ROE trên 12%.')],'Nhớ ROE trên 12%.');assert first['normalized_actual_entries'][0]['version']==1
 second=call([put('Cập nhật ROE trên 20%.')],'Cập nhật ROE trên 20%.');assert second['normalized_actual_entries'][0]['version']==2
 mapping=home/'authorized-memory-map.json';before=mapping.read_bytes();audit=call([],audit=True);assert mapping.read_bytes()==before;assert audit['normalized_actual_entries'][0]['text']=='Cập nhật ROE trên 20%.'
 done=call([{'op':'delete','id':'roe','source_text':'Quên ROE.','consent':'explicit_user_request'}],'Quên ROE.');assert done['entries']==[];assert done['authorized_map']=={}
