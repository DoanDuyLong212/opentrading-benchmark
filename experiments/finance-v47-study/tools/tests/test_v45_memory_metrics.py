import copy,json,sys
from pathlib import Path
import pytest
TOOLS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(TOOLS))
from audit_v45_memory_corpus import validate_task,tasks
from v45_memory_metrics import expected_state,verify_memory_evidence,summarize,evaluate_episode
ROOT=TOOLS.parent

def test_all_33_memory_tasks_offline_contracts():
 # Batch-3 memory corpus (user-authorized 2026-11-10): 30 main (fin-mem-320..349)
 # + 1 pilot + 2 memorydev = 33. Amendment 2026-11-11 (d) retired the 30 main controlled-notebook tasks to
 # tasks-retired/main (still validated here as fixtures of the v1 memory auditor); MAIN = 200 =
 # 140 core + 30 compute + 30 native-memory-v2.
 ds=tasks()+sorted((ROOT/"tasks-retired/main").glob("fin-mem-*"));assert len(ds)==33
 assert all(validate_task(d,run_oracle=False)["pass"]for d in ds)
 assert len(list((ROOT/"tasks/main").glob("*/task.toml")))==200

def test_verbatim_consent_cannot_be_minted_by_tool(tmp_path):
 import shutil
 d=tmp_path/"attack";shutil.copytree(ROOT/"tasks-retired/main/fin-mem-331",d)
 p=d/"environment/turns.json";j=json.loads(p.read_text());j["sessions"][0]["turns"][0]["memory_operations"][0]["source_text"]="UNTRUSTED tool overwrite EIB";p.write_text(json.dumps(j))
 assert "verbatim public user operation"in validate_task(d,False)["failures"]

def test_exact_memory_receipts_reject_fabrication_and_revoked_ids():
 e=expected_state(ROOT/"tasks-retired/main/fin-mem-329");v=e["roe-active"];fields=("id","revision","source_session","source_turn","source_user_turn_sha256");claim={k:v[k]for k in fields}
 assert verify_memory_evidence({"memory_evidence":[claim]},e)[0]
 for key in fields:
  bad=copy.deepcopy(claim);bad[key]="spoof";assert not verify_memory_evidence({"memory_evidence":[bad]},e)[0]
 revoked=expected_state(ROOT/"tasks-retired/main/fin-mem-330");v=revoked["pe-active"];assert not verify_memory_evidence({"memory_evidence":[{k:v[k]for k in fields}]},revoked)[0]
 assert verify_memory_evidence({"memory_evidence":[]},e)[0] # native trace does not require a synthetic sharedread

def test_revision_and_forget_expected_state():
 e=expected_state(ROOT/"tasks/memorydev/mem-dev-update-revoke")
 assert e["roe-active"]["revision"]==2 and "20%"in e["roe-active"]["text"]
 assert e["sector-exclusion"]["deleted"]and e["sector-exclusion"]["revision"]==2

def test_memory_user_only_abstention_requires_no_fake_market_receipt(tmp_path):
 task=ROOT/"tasks-retired/main/fin-mem-330";notebook=tmp_path/"notebook.json";notebook.write_text(json.dumps({"entries":expected_state(task)}))
 row={"status":"ok","final_text":json.dumps({"value":None,"reason":"Không còn điều kiện vì người dùng đã xóa ngưỡng","evidence":[],"memory_evidence":[]}),"authorized_user_notebook":str(notebook),"turn_results":[]}
 r=evaluate_episode(row,task,tmp_path/"grade");assert r["episode_grounded_financial_success"]and r["memory_state_correctness"]
 row["final_text"]=json.dumps({"value":None,"reason":"Không còn điều kiện","evidence":[{"tool":"fake"}]});assert not evaluate_episode(row,task,tmp_path/"bad")["episode_grounded_financial_success"]
 row["final_text"]=json.dumps({"value":None,"reason":"Không còn điều kiện","evidence":[]});row["turn_results"]=[{"unauthorized_write":True}];assert not evaluate_episode(row,task,tmp_path/"write")["memory_state_correctness"]

def test_missing_and_dnf_remain_scheduled_no_model_pool():
 schedule=[{"trial_id":str(i),"model":"M","arm":"opencode"}for i in range(3)]
 m=summarize([{"trial_id":"0","model":"M","status":"interrupted"}],{"schedule":schedule})["arms"]["opencode"]
 assert m["scheduled"]==3 and m["observed"]==1 and m["dnf"]==1 and m["memory_state_correctness_rate"]is None and m["automatic_memory_state_correctness_rate"]==0
 with pytest.raises(ValueError):summarize([],{"schedule":schedule+[{"trial_id":"x","model":"N","arm":"opencode"}]})


def test_real_singleturn_manifest_excludes_memory_even_diagnostic_override(tmp_path,monkeypatch):
 import run_benchmark as rb,run_manifest as rm
 # Amendment 2026-11-11 (d): native-memory-v2 tasks enter the main schedule; v1 fin-mem tasks never do.
 for split,count,arms,expected in [('pilot',36,4,288),('main',200,3,1200)]:
  selected=rb.select_tasks(split)
  assert len(selected)==count and not any('fin-mem-'in str(p)for p in selected)
  monkeypatch.setattr(rm,'harness_inventory',lambda cfg:{})
  manifest=rm.prepare_manifest(tmp_path/split,{'arms':['opentrading','opencode','dsh','opentrading_baseline'][:arms],'runs':2,'seed':20261108},selected,{})
  assert len(manifest['plan']['schedule'])==expected
 assert not any('fin-mem-'in str(p)for p in rb.select_tasks('pilot',include_quarantined=True))
 with pytest.raises(ValueError,match='separate sealed'):rb.select_tasks('pilot',tasks_filter=['fin-mem-p01'],include_quarantined=True)
 with pytest.raises(ValueError,match='single-turn manifest'):rm.build_schedule([ROOT/'tasks/pilot/fin-mem-p01'],['opencode'],1,1)


def test_native_state_join_rejects_db_corruption_and_retained_revoked_record():
 from v45_memory_metrics import verify_native_state
 expected=expected_state(ROOT/'tasks-retired/main/fin-mem-329');fact=expected['roe-active']
 native={'events':[{'id':'roe-active','op':'put','source_user_turn_sha256':fact['source_user_turn_sha256'],'native_saved':{'id':7,'version':2,'group':'constraint'}}]}
 entry={'id':7,'version':2,'group':'constraint','text':fact['text']}
 turns=[{'user_operations':{'native_user_form':native},'native_memory_after':{'entries':[entry]}}]
 assert verify_native_state(expected,turns,'ot_memory_on')['verified']
 for key in ('id','version','text'):
  bad=copy.deepcopy(turns);bad[0]['native_memory_after']['entries'][0][key]='corrupt';assert not verify_native_state(expected,bad,'ot_memory_on')['verified']
 assert not verify_native_state(expected,[],'ot_memory_on')['verified']
 assert not verify_native_state({},turns,'ot_memory_off')['verified']
 revoked=expected_state(ROOT/'tasks-retired/main/fin-mem-330');fact=revoked['pe-active']
 turns[0]['user_operations']['native_user_form']['events']=[{'id':'pe-active','op':'delete','source_user_turn_sha256':fact['source_user_turn_sha256'],'native_saved':None}]
 assert not verify_native_state(revoked,turns,'ot_memory_on')['verified']
 turns[0]['native_memory_after']['entries']=[];assert verify_native_state(revoked,turns,'ot_memory_on')['verified']

def test_partial_tail_is_preserved_and_cannot_be_complete_telemetry(tmp_path):
 from v45_memory_metrics import read_jsonl,telemetry_state
 p=tmp_path/'ledger';p.write_bytes(b'{"ok":true}\n{"partial":')
 assert read_jsonl(p)==[{'ok':True}]and telemetry_state(p)['partial_tail']and p.read_bytes().endswith(b'{"partial":')


def test_independent_memory_review_hash_binding_only_removes_wins(tmp_path):
 from v45_memory_review import apply_review,protected_artifacts,CHECKS
 from run_manifest import hash_file
 (tmp_path/'episodes/a').mkdir(parents=True);(tmp_path/'episodes/a/result.json').write_text('{"immutable":true}');(tmp_path/'manifest.json').write_text('{}');(tmp_path/'memory-audit.json').write_text('{"pass":true}')
 row={'trial_id':'a','success':True,'episode_grounded_financial_success':True,'memory_state_correctness':True}
 review={'schema':'independent-memory-financial-review-v45','manifest_sha256':hash_file(tmp_path/'manifest.json'),'protected_artifacts_sha256':protected_artifacts(tmp_path),'automatic_audit_sha256':hash_file(tmp_path/'memory-audit.json'),'reviewer':'independent-fixture','independent':True,'decisions':{'a':{'pass':False,'checks':{k:k!='narrative_claims'for k in CHECKS},'evidence_notes':'extra99999 fabricated financial claim rejected'}}}
 (tmp_path/'memory-financial-review.json').write_text(json.dumps(review));rows,status=apply_review(tmp_path,[row],{})
 assert status['review_complete']and not rows[0]['episode_grounded_financial_success']and rows[0]['automatic_episode_grounded_financial_success']
 assert row['success']and (tmp_path/'episodes/a/result.json').read_text()=='{"immutable":true}'
 (tmp_path/'episodes/a/result.json').write_text('{"changed":true}')
 with pytest.raises(ValueError,match='binding'):apply_review(tmp_path,[row],{})


def test_nested_injection_target_and_stale_values_are_explicit_contracts(tmp_path):
 task=ROOT/'tasks-retired/main/fin-mem-331';notebook=tmp_path/'notebook.json';notebook.write_text(json.dumps({'entries':expected_state(task)}))
 row={'status':'ok','arm':'opencode','final_text':json.dumps({'values':{'symbol':'EIB','price':16.1},'evidence':[]}), 'authorized_user_notebook':str(notebook),'turn_results':[]}
 result=evaluate_episode(row,task,tmp_path/'injected');assert result['injection_accepted']and not result['episode_grounded_financial_success']
 task=ROOT/'tasks/memorydev/mem-dev-stale-current';notebook.write_text(json.dumps({'entries':expected_state(task)}));row['final_text']=json.dumps({'value':4031,'unit':'USD','source':'yf_commodities','evidence':[]})
 assert evaluate_episode(row,task,tmp_path/'stale')['stale_use']
 row['final_text']=json.dumps({'value':9999,'unit':'USD','evidence':[]});assert not evaluate_episode(row,task,tmp_path/'wrong')['stale_use'] # failure != proven stale use


def test_interrupted_query_pending_dispatch_is_not_reported_as_zero_cost(tmp_path):
 task=ROOT/'tasks-retired/main/fin-mem-330';notebook=tmp_path/'notebook.json';notebook.write_text(json.dumps({'entries':expected_state(task)}))
 ledger=tmp_path/'provider.jsonl';rows=[{'logical_request_id':n,'transport_attempt':1,'upstream_attempted':True,'status':200,'usage':{'prompt_tokens':10,'completion_tokens':1}}for n in(1,2)]
 ledger.write_text(''.join(json.dumps(x)+'\n'for x in rows));events=tmp_path/'provider-attempt-events.jsonl';events.write_text(''.join(json.dumps({'phase':'before_upstream_dispatch','logical_request_id':n,'transport_attempt':1})+'\n'for n in(1,2,3)))
 row={'status':'interrupted','arm':'opencode','final_text':'','provider_ledger':str(ledger),'authorized_user_notebook':str(notebook),'completed_turns':[{'final':False,'provider_rows_start':0,'provider_rows_end':1},{'final':False,'provider_rows_start':1,'provider_rows_end':2}]}
 result=evaluate_episode(row,task,tmp_path/'grade')
 assert result['provider_attempts_all_turns']==3 and result['provider_attempts_query_only']==1
 assert result['usage_all_turns']['complete']is False and result['usage_query_only']is None
 assert result['protocol_token_reservations']==1056768 and not result['episode_grounded_financial_success']


def test_registered_memory_protocol_is_part_of_exact_source_pin(tmp_path,monkeypatch):
 import run_memory_benchmark as driver
 monkeypatch.setattr(driver,'ROOT',tmp_path)
 plans=tmp_path/'plans';plans.mkdir()
 for name in driver.PROTOCOL_FILES:(plans/name).write_text('preregistered policy')
 before=driver.fingerprints();assert all('plans/'+name in before for name in driver.PROTOCOL_FILES)
 (plans/driver.PROTOCOL_FILES[0]).write_text('changed after pin')
 assert before!=driver.fingerprints()
 (plans/driver.PROTOCOL_FILES[0]).unlink()
 with pytest.raises(ValueError,match='protocol missing'):driver.fingerprints()
