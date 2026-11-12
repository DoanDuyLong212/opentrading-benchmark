import copy,json,sys,os,fcntl
from pathlib import Path
import pytest
TOOLS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TOOLS))
import run_benchmark as rb
from v45_gate import quality_gate,build_settings
from v45_metrics import summarize
from v45_control import PauseController


def candidate(split='devsmoke'):
    n=24 if split=='devsmoke' else 44
    return {'scheduled':n,'observed':n,'strict_grounded_success':24 if n==24 else 40,'grounded_financial_correctness':24 if n==24 else 41,'answerable_grounded':18 if n==24 else 37,'trap_grounded':6 if n==24 else 4,'raw_contract_valid':n,'dnf':0,'false_refusals':0,'false_positives':0,'fabricated_evidence_accepted':0,'evidence_grounded':n,'per_family':{x:{'answerable_grounded':1} for x in ['growth','margin','scale','ratio','aggregate','cross-source','chain']}}


def summary(split='devsmoke'):
    b=candidate(split);controls={x:copy.deepcopy(b) for x in ['opentrading_baseline','opencode','dsh']}
    if split=='pilot':
        for control in controls.values():control.update(strict_grounded_success=35,grounded_financial_correctness=36)
    return {'financial_v45':{'complete':True,'manual_financial_review':{'review_complete':True,'accepted_financial_fabrications':0},'arms':{'opentrading_finance':b,**controls}}}


@pytest.mark.parametrize('split',['devsmoke','pilot'])
def test_gate_expected_good(split):assert quality_gate(summary(split),{'pass':True,'fabricated_evidence_accepted':0},split)['pass']

@pytest.mark.parametrize('mutation',['denominator','audit','fabrication','incomplete','dnf','fp','numeric','baseline'])
def test_smoke_gate_failclosed(mutation):
    s=summary();audit={'pass':True,'fabricated_evidence_accepted':0};b=s['financial_v45']['arms']['opentrading_finance']
    if mutation=='denominator':b['scheduled']=23
    if mutation=='audit':audit['pass']=False
    if mutation=='fabrication':audit['fabricated_evidence_accepted']=1
    if mutation=='incomplete':s['financial_v45']['complete']=False
    if mutation=='dnf':b['dnf']=2
    if mutation=='fp':b['false_positives']=1
    if mutation=='numeric':b['per_family']['growth']['answerable_grounded']=0
    if mutation=='baseline':s['financial_v45']['arms']['opentrading_baseline']['strict_grounded_success']=25
    assert not quality_gate(s,audit,'devsmoke')['pass']

@pytest.mark.parametrize('metric',['strict_grounded_success','grounded_financial_correctness'])
@pytest.mark.parametrize('opponent',['opencode','dsh','opentrading_baseline'])
def test_pilot_requires_margin_each_endpoint_opponent(metric,opponent):
    s=summary('pilot');s['financial_v45']['arms'][opponent][metric]=s['financial_v45']['arms']['opentrading_finance'][metric]-2
    assert not quality_gate(s,{'pass':True,'fabricated_evidence_accepted':0},'pilot')['pass']


def test_manifest_metric_denominators_include_pending_and_traps(tmp_path):
    task=tmp_path/'tasks/devsmoke/a';task.mkdir(parents=True);(task/'task.toml').write_text('level="L1"\nfamily="quote"\n')
    plan={'settings':{'arms':['opencode'],'runs':2},'schedule':[{'trial_id':'a1','task':'a','arm':'opencode'},{'trial_id':'a2','task':'a','arm':'opencode'}],'task_contracts':{'a':{'scoring':'value'}}}
    rows=[{'trial_id':'a1','task':'a','arm':'opencode','model':'M','status':'timeout','success':False,'answer_source':'missing','false_refusal':True}]
    m=summarize(rows,{'plan':plan},tmp_path)['arms']['opencode']
    assert m['scheduled']==2 and m['observed']==1 and m['dnf']==1 and m['false_refusal_rate_scheduled']==.5
    assert m['stable']['label']=='2/2' and m['stable']['strict_all_repeats']==0


def test_crash_resume_terminal_no_call(tmp_path,monkeypatch):
    task=TOOLS.parent/'tasks/devsmoke/v45-dev-01-quote';item={'trial_id':'crash','task':task.name,'arm':'opencode','run':1}
    t=tmp_path/'trials/crash';(t/'attempts/01-crashed/ws').mkdir(parents=True)
    (t/'state.json').write_text(json.dumps({'trial_id':'crash','timeout_s':900,'started_at':'2026-11-08T00:00:00Z','started_epoch':__import__('time').time()}))
    monkeypatch.setattr(rb,'run_trial',lambda *a,**k:pytest.fail('Resume must not retry an in-flight attempt'))
    row=rb.execute_trial(item,str(task),str(tmp_path),'nvidia/deepseek-ai/deepseek-v4.1-flash',900,0,4,{})
    assert row['status']=='interrupted' and row['tokens'] is None and not row['success'] and len(row['attempts'])==1


def cli_fixture(tmp_path,monkeypatch):
    import run_manifest
    task=TOOLS.parent/'tasks/devsmoke/v45-dev-01-quote';out=tmp_path/'run';cfg=tmp_path/'config.json';cfg.write_text(json.dumps({'model':'nvidia/deepseek-ai/deepseek-v4.1-flash','price_per_1m':None}))
    monkeypatch.setattr(rb,'select_tasks',lambda *a,**k:[str(task)])
    monkeypatch.setattr(run_manifest,'harness_inventory',lambda config:{})
    monkeypatch.setattr(run_manifest,'code_fingerprint',lambda:{})
    monkeypatch.setattr(PauseController,'install',lambda self:None)
    calls=[]
    def stub(arm,ws,instruction,task_dir,model,timeout_s,log_path,options=None):
        calls.append(arm);Path(log_path).write_text('offline interceptor\n');return {'status':'ok','final_text':'{"value":0,"unit":"nghìn đồng","period":"2026-10-29","source":"vn_quote_history","evidence":[]}','provider_requests':0,'tokens':None,'session_id':'fixture'}
    monkeypatch.setattr(rb,'run_trial',stub)
    argv=['driver','--split','devsmoke','--arms','opencode','--runs','2','--retry','0','--pause','0','--timeout','900','--config',str(cfg),'--out',str(out)]
    return out,calls,argv


def test_actual_cli_completed_resume_zero_calls_and_bytes(tmp_path,monkeypatch):
    out,calls,argv=cli_fixture(tmp_path,monkeypatch);monkeypatch.setattr(sys,'argv',argv);rb.main();assert len(calls)==2
    protected={str(p):p.read_bytes() for p in (out/'trials').rglob('*') if p.is_file()}
    monkeypatch.setattr(sys,'argv',argv+['--resume']);rb.main();assert len(calls)==2
    assert {str(p):p.read_bytes() for p in (out/'trials').rglob('*') if p.is_file()}==protected


def test_actual_cli_pause_before_first_trial_then_continue(tmp_path,monkeypatch):
    out,calls,argv=cli_fixture(tmp_path,monkeypatch);out.mkdir();(out/'PAUSE').write_text('{}');monkeypatch.setattr(sys,'argv',argv);rb.main()
    assert calls==[] and json.loads((out/'control-state.json').read_text())['stage']=='paused'
    (out/'PAUSE').unlink();monkeypatch.setattr(sys,'argv',argv+['--resume']);rb.main();assert len(calls)==2


def test_actual_cli_lock_before_any_call(tmp_path,monkeypatch):
    out,calls,argv=cli_fixture(tmp_path,monkeypatch);out.mkdir()
    with (out/'.driver.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);monkeypatch.setattr(sys,'argv',argv)
        with pytest.raises(SystemExit,match='Another driver'):rb.main()
    assert calls==[]


def subprocess_fixture(tmp_path):
    script=tmp_path/'run_benchmark.py';out=tmp_path/'out';cfg=tmp_path/'cfg.json';calls=tmp_path/'calls.jsonl'
    cfg.write_text(json.dumps({'model':'nvidia/deepseek-ai/deepseek-v4.1-flash'}))
    script.write_text('''import sys,time,json,os
from pathlib import Path
sys.path.insert(0,TOOLS)
import run_benchmark as rb,run_manifest
rb.select_tasks=lambda *a,**k:[TASK]
run_manifest.harness_inventory=lambda c:{}
run_manifest.code_fingerprint=lambda:{}
def stub(arm,ws,instruction,task_dir,model,timeout_s,log_path,options=None):
 with open(CALLS,'a') as f:f.write(json.dumps({'arm':arm,'workspace':ws})+'\\n');f.flush();os.fsync(f.fileno())
 if os.environ.get('FIXTURE_WAIT_PAUSE')=='1':
  until=time.monotonic()+10
  while not (Path(ws).parents[4]/'PAUSE').exists():
   if time.monotonic()>until:raise RuntimeError('Fixture pause never arrived')
   time.sleep(.01)
 time.sleep(float(os.environ.get('FIXTURE_STALL','0')))
 Path(log_path).write_text('offline fixture')
 return {'status':'ok','final_text':'{"value":0,"evidence":[]}','provider_requests':0,'tokens':None}
rb.run_trial=stub
# Control fixture avoids grader/process startup latency and external dependencies.
rb.grade_answer=lambda *a,**k:{'success':False,'fp':0,'error_type':'fixture','raw':{}}
import mcp_snapshot_server
rb.main()
'''.replace('TOOLS',repr(str(TOOLS))).replace('TASK',repr(str(TOOLS.parent/'tasks/devsmoke/v45-dev-01-quote'))).replace('CALLS',repr(str(calls))))
    cmd=[sys.executable,str(script),'--split','devsmoke','--arms','opencode','--runs','2','--retry','0','--pause','0','--timeout','900','--config',str(cfg),'--out',str(out)]
    return out,calls,cmd


def wait_file(path,condition=lambda p:True,timeout=30):
    import time
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        if path.exists() and condition(path):return
        time.sleep(.02)
    raise AssertionError('Fixture did not reach expected durable boundary: '+str(path))


def test_real_subprocess_graceful_pause_resume(tmp_path):
    import subprocess
    out,calls,cmd=subprocess_fixture(tmp_path)
    with (tmp_path/'process.log').open('w') as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=log,env={**os.environ,'FIXTURE_WAIT_PAUSE':'1'})
        try:
            wait_file(calls,lambda f:len(f.read_text().splitlines())==1)
            subprocess.run([sys.executable,str(TOOLS/'v45_control.py'),'pause','--out',str(out)],check=True,capture_output=True)
            assert p.wait(timeout=10)==0
            assert len(calls.read_text().splitlines())==1
            assert json.loads((out/'control-state.json').read_text())['stage']=='paused'
            subprocess.run([sys.executable,str(TOOLS/'v45_control.py'),'continue','--out',str(out)],check=True,capture_output=True)
            result=subprocess.run(cmd+['--resume'],stdout=log,stderr=log,timeout=15)
            assert result.returncode==0 and len(calls.read_text().splitlines())==2
        finally:
            if p.poll() is None:p.kill();p.wait()


def test_real_subprocess_hard_stop_resume_preserves_interrupted(tmp_path):
    import subprocess
    out,calls,cmd=subprocess_fixture(tmp_path)
    with (tmp_path/'process.log').open('w') as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=log,env={**os.environ,'FIXTURE_STALL':'60'})
        try:
            wait_file(calls,lambda f:len(f.read_text().splitlines())==1)
            subprocess.run([sys.executable,str(TOOLS/'v45_control.py'),'hard-stop','--out',str(out)],check=True,capture_output=True)
            p.wait(timeout=5);assert p.returncode<0
            subprocess.run([sys.executable,str(TOOLS/'v45_control.py'),'continue','--out',str(out)],check=True,capture_output=True)
            r=subprocess.run(cmd+['--resume'],stdout=log,stderr=log,timeout=15)
            assert r.returncode==0
            rows=[json.loads(x) for x in (out/'trials.jsonl').read_text().splitlines()]
            assert len(rows)==2 and rows[0]['status']=='interrupted' and rows[0]['tokens'] is None
            assert len(calls.read_text().splitlines())==2 # interrupted first call never repeated; second scheduled call only
        finally:
            if p.poll() is None:p.kill();p.wait()


def test_pipeline_continue_clears_only_propagated_pause(tmp_path):
    import subprocess
    parent=tmp_path/'pipeline';child=tmp_path/'cohort';parent.mkdir();child.mkdir()
    (parent/'state.json').write_text(json.dumps({'active_out':str(child)}));(parent/'PAUSE').write_text('{}');(child/'PAUSE').write_text(json.dumps({'origin':'pipeline'}))
    subprocess.run([sys.executable,str(TOOLS/'v45_control.py'),'continue','--out',str(parent)],check=True,capture_output=True)
    assert not (parent/'PAUSE').exists() and not (child/'PAUSE').exists()
    (child/'PAUSE').write_text(json.dumps({'origin':'user'}))
    subprocess.run([sys.executable,str(TOOLS/'v45_control.py'),'continue','--out',str(parent)],check=True,capture_output=True)
    assert (child/'PAUSE').exists()


def test_manual_review_required_before_quality_gate():
    s=summary();s['financial_v45'].pop('manual_financial_review')
    assert not quality_gate(s,{'pass':True,'fabricated_evidence_accepted':0},'devsmoke')['pass']


def test_manual_all_arm_hash_binding_can_only_remove_win(tmp_path):
    from v45_review import apply_review,protected_artifacts,REVIEW_CHECKS
    from run_manifest import hash_file
    out=tmp_path/'review';out.mkdir();manifest={'fingerprint':'fixture-manifest'};(out/'manifest.json').write_text(json.dumps(manifest));(out/'audit-v45.json').write_text('{"pass":true}')
    rows=[{'trial_id':'candidate','arm':'opentrading_finance','success':True,'grounded_financial_correctness':True},{'trial_id':'control','arm':'opencode','success':True,'grounded_financial_correctness':True},{'trial_id':'failure','arm':'dsh','success':False,'grounded_financial_correctness':False}]
    (out/'trials.jsonl').write_text('\n'.join(map(json.dumps,rows))+'\n');checks={k:True for k in REVIEW_CHECKS}
    review={'schema':'independent-financial-review-v45','manifest_sha256':manifest['fingerprint'],'protected_artifacts_sha256':protected_artifacts(out),'automatic_audit_sha256':hash_file(out/'audit-v45.json'),'reviewer':'independent fixture reviewer','independent':True,'decisions':{'candidate':{'pass':False,'checks':{**checks,'narrative_claims':False},'evidence_notes':'Fabricated revenue99999 unsupported by actual source'},'control':{'pass':True,'checks':checks,'evidence_notes':'Each requested/narrative financial claim verified'}}}
    (out/'financial-review.json').write_text(json.dumps(review));changed,status=apply_review(out,rows,manifest)
    assert not changed[0]['success'] and changed[1]['success'] and not changed[2]['success']
    assert rows[0]['success'] is True and status['rejected_automatic_wins']==1
    (out/'trials.jsonl').write_text('mutated')
    with pytest.raises(ValueError,match='binding'):apply_review(out,rows,manifest)


def test_receipt_requires_actual_json_all_seven_fields():
    from audit_v45_run import has_receipt
    receipt={k:k+'-value' for k in ['call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of']}
    assert not has_receipt(' '.join(receipt.values()),receipt)
    assert has_receipt(json.dumps({'content':[{'type':'text','text':json.dumps({'benchmark_evidence':receipt})}]}),receipt)
    assert not has_receipt(json.dumps({'benchmark_evidence':{**receipt,'source':'forged'}}),receipt)
