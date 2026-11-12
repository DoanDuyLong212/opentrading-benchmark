import copy,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import v44_gate as gate
import v44_supervisor as supervisor
import metrics
ROOT=Path(__file__).resolve().parents[2]
LEGACY=ROOT.parent/'finance-v44-study'

def test_four_phase_commands_and_budgets():
 for split in ('smoke','pilot'):
  for name,filename,_ in gate.STRATA:
   config=json.loads((LEGACY/'tools'/filename).read_text());item={'split':split,'config':str(LEGACY/'tools'/filename),'out':'/tmp/output'}
   command=supervisor.command(item,'/tmp/seal')
   assert command[command.index('--split')+1]==split and '--v44-seal' in command
   assert command[command.index('--retry')+1]=='0'
   assert gate.registered_settings(config,split)['split']==split

@pytest.mark.parametrize('answer,source,status,expected_fr,expected_dnf',[
 ({'value':None,'reason':'missing'},'final_json','ok',1,0),
 ({'values':{'total':None},'reason':'missing'},'final_json','ok',1,0),
 ({'reason':'not formatted'},'final_json','ok',0,0),
 (None,'missing','ok',0,1),
 (None,'missing','timeout',0,1),
 ({'value':21},'final_json','ok',0,0),
])
def test_gate_real_trial_shape_answer_path(tmp_path,monkeypatch,answer,source,status,expected_fr,expected_dnf):
 rows=[]
 contracts={'smoke-agg-01':{'scoring':'values','answerable_fields':['values.total']},'smoke-quote-01':{'scoring':'value','answerable_fields':['value']},'smoke-trap-01':{'scoring':'refusal','answerable_fields':[]}}
 for arm in gate.ARMS:
  for task in gate.TASKS:
   for repetition in range(2):
    row={'arm':arm,'task':task,'run':repetition+1,'success':True,'status':'ok','timely':True,'answer_source':'final_json','attempts':[]}
    if arm=='opentrading_finance' and task=='smoke-agg-01' and repetition==0:
     row.update(success=False,status=status,answer_source=source)
     if answer is not None:
      ap=tmp_path/'answer.json';ap.write_text(json.dumps(answer));row['answer_path']=str(ap)
    rows.append(row)
 config=json.loads((LEGACY/'tools/bench_config.json').read_text())
 manifest={'plan':{'tasks':gate.TASKS,'settings':gate.registered_settings(config),'config':config,'task_contracts':contracts}}
 (tmp_path/'manifest.json').write_text(json.dumps(manifest))
 monkeypatch.setattr(metrics,'load_trials',lambda _:copy.deepcopy(rows));monkeypatch.setattr(gate,'validate_trial_rows',lambda *_:True)
 result=gate.diagnostic_quality(tmp_path)
 assert result['candidate_false_refusals']==expected_fr and result['candidate_dnf']==expected_dnf

def test_pilot_fails_closed_without_both_smokes(tmp_path):
 item={'split':'pilot','stratum':'bolt'}
 seal={'runs':[{'split':'smoke','stratum':'bolt','out':str(tmp_path),'manifest_sha256':'frozen'}],'audit_script':{'sha256':'auditor'}}
 with pytest.raises(FileNotFoundError):gate.require_pilot_authorization(seal,item)

def test_supervisor_both_smokes_before_eligible_pilot_and_completed_resume(tmp_path,monkeypatch):
 items=[]
 for split in ('smoke','pilot'):
  for name,filename,_ in gate.STRATA:
   config=tmp_path/(name+'.json');config.write_text((LEGACY/'tools'/filename).read_text());out=tmp_path/(split+'-'+name);out.mkdir()
   (out/'trials.jsonl').write_text('retained exact trials\n')
   items.append({'split':split,'stratum':name,'key':split+'-'+name,'config':str(config),'out':str(out),'manifest_sha256':'frozen','trials':24 if split=='smoke' else 176})
 seal=tmp_path/'seal';seal.write_text('{}');audit_script=tmp_path/'auditor.py';audit_script.write_text('# pinned audit\n');report=tmp_path/'audit.json';state=tmp_path/'state.json'
 receipt={'runs':items,'audit_script':{'path':str(audit_script),'sha256':'auditor'}};calls=[]
 monkeypatch.setattr(supervisor,'validate_seal',lambda _:receipt)
 def authorize(_,item):
  if item['stratum']=='bolt':raise ValueError('smoke quality gate failed')
 monkeypatch.setattr(supervisor,'require_pilot_authorization',authorize)
 monkeypatch.setattr(supervisor,'diagnostic_quality',lambda _: {'quality_pass':True})
 def child(command,log,state_value,state_path,stage):
  calls.append(stage)
  if stage.endswith('-audit'):
   data={'completed_runs':{item['split']+'-'+json.loads(Path(item['config']).read_text())['model']:{'audit_controls_pass':True,'zero_accepted_fabrication':True,'smoke_financial_canary_pass':True,'errors':[]} for item in items}}
   report.write_text(json.dumps(data))
  return 0
 monkeypatch.setattr(supervisor,'run_child',child)
 monkeypatch.setattr(sys,'argv',['supervisor','--seal',str(seal),'--state',str(state),'--audit-script',str(audit_script),'--audit-output',str(report)])
 assert supervisor.main()==0
 assert calls==['smoke-bolt-driver','smoke-bolt-audit','smoke-deepseek-driver','smoke-deepseek-audit','pilot-deepseek-driver','pilot-deepseek-audit']
 before=list(calls);assert supervisor.main()==0 and calls==before
 assert json.loads(state.read_text())['runs']['pilot-bolt']['status']=='skipped_quality_gate'

def test_pilot_independent_financial_canary_failclosed(tmp_path,monkeypatch):
 items=[]
 for stratum in ('bolt','deepseek'):
  out=tmp_path/stratum;out.mkdir();(out/'manifest.json').write_text('{}');(out/'trials.jsonl').write_text('')
  item={'split':'smoke','stratum':stratum,'out':str(out),'manifest_sha256':'frozen'};items.append(item)
  receipt={'manifest_sha256':'frozen','trials_sha256':gate.hash_file(out/'trials.jsonl'),'audit_controls_pass':True,'zero_accepted_fabrication':True,'auditor_sha256':'auditor','smoke_financial_canary_pass':True}
  (out/'v44-audit-controls.json').write_text(json.dumps(receipt))
 seal={'runs':items,'audit_script':{'sha256':'auditor'}};pilot={'split':'pilot','stratum':'bolt'}
 monkeypatch.setattr(gate,'validate_trial_rows',lambda *_:True);monkeypatch.setattr(metrics,'load_trials',lambda _:[])
 monkeypatch.setattr(gate,'diagnostic_quality',lambda _: {'quality_pass':True})
 assert gate.require_pilot_authorization(seal,pilot)['smoke_financial_canary_pass'] is True
 controls=Path(items[0]['out'])/'v44-audit-controls.json';receipt=json.loads(controls.read_text());receipt['smoke_financial_canary_pass']=False;controls.write_text(json.dumps(receipt))
 with pytest.raises(ValueError,match='financial canary'):gate.require_pilot_authorization(seal,pilot)


@pytest.mark.parametrize('split', ['smoke', 'pilot'])
@pytest.mark.parametrize('stratum', ['bolt', 'deepseek'])
def test_supervisor_actual_driver_cli_matches_presealed_manifest(tmp_path, monkeypatch, split, stratum):
 """Run the real argparse/settings path and real manifest resume, stopping before trials.

 Python equality accepts int 4 == float 4.0, while sealed JSON digests differ.
 This checks the actual full comparable fingerprint rather than rebuilding CLI settings.
 """
 # Execute the actual immutable v4.4 fixture and driver in a fresh interpreter.
 # Importing it into this process would bind its sibling imports to v4.5's
 # already-cached run_benchmark/run_manifest modules, defeating this regression.
 import subprocess
 code="""import importlib.util,sys
from pathlib import Path
import pytest
legacy=Path(sys.argv[1]);sys.path.insert(0,str(legacy/'tools'))
spec=importlib.util.spec_from_file_location('immutable_v44_fixture',legacy/'tools/tests/test_v44_gate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
with pytest.MonkeyPatch.context()as patch:
 module.test_supervisor_actual_driver_cli_matches_presealed_manifest(Path(sys.argv[2]),patch,sys.argv[3],sys.argv[4])
"""
 completed=subprocess.run([sys.executable,'-c',code,str(LEGACY),str(tmp_path),split,stratum],capture_output=True,text=True,timeout=180)
 assert completed.returncode==0,completed.stdout+'\n'+completed.stderr
