#!/usr/bin/env python3
"""Bounded, predeclared native memory mini; planning never calls a model."""
import argparse,hashlib,json,signal,sys,time,fcntl,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/runners')]
from memory_runner import MemoryEpisode,ARMS,save,digest
from v45_memory_metrics import evaluate_episode,summarize
from run_manifest import harness_inventory
from provider import admission
CASES=['pilot/fin-mem-p01','memorydev/mem-dev-update-revoke','memorydev/mem-dev-stale-current']
def turns_for(task):
 spec=json.loads((task/'environment/turns.json').read_text());result=[]
 for session in spec['sessions']:
  for n,turn in enumerate(session['turns']):result.append({**turn,'session':session['id'],'turn':n,'final':bool(turn.get('final'))})
 if sum(x['final']for x in result)!=1 or not result[-1]['final']:raise ValueError('Exactly one final graded turn must end episode')
 return result
PROTOCOL_FILES=('2026-11-08-v45-memory-mini-protocol.md','2026-11-08-v45-execution-protocol.md')
def fingerprints():
 result={}
 for name in PROTOCOL_FILES:
  path=ROOT/'plans'/name
  if not path.is_file():raise ValueError('Required registered memory protocol missing: '+name)
  result[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
 for base in [ROOT/'audits/model-admission',ROOT/'tools',ROOT/'experiments/opentrading-runtime/src',ROOT/'experiments/opentrading-runtime/prompts',ROOT/'tasks']:
  for p in sorted(base.rglob('*')):
   if p.is_file()and '__pycache__'not in p.parts and p.suffix not in('.pyc',):result[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
 for name in ['package.json','bun.lock']:
  p=ROOT/'experiments/opentrading-runtime'/name
  if p.exists():result[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
 return result
def manifest(config):
 models=config['allowed_models'];rows=[]
 for model in models:
  for case in CASES:
   task=ROOT/'tasks'/case
   for arm in ARMS:
    rows.append({'trial_id':digest([model,case,arm])[:20],'model':model,'arm':arm,'case':case,'turns_sha256':hashlib.sha256((task/'environment/turns.json').read_bytes()).hexdigest(),'turns':turns_for(task)})
 return {'harness_inventory':harness_inventory(config),'model_admissions':{model:admission(model[7:])for model in models},'harness_config':{'opentrading_runtime_root':config['opentrading_runtime_root'],'provider_options':config['provider_options']},'fingerprints':fingerprints(),'version':1,'track':'controlled-memory-mini-v1','main_inference':False,'schedule':rows,'options':{**config['provider_options'],'opentrading_runtime_root':config['opentrading_runtime_root'],'max_requests':12,'timeout_s':900,'max_output_tokens':8192,'context_window':1048576,'max_total_tokens':3600000},'limits':{'episodes':24,'upstream_attempts_per_episode':12,'max_upstream_attempts':288},'interpretation':'One repeat per condition/model/case; preliminary diagnostic, not long-term memory superiority.'}
def summary(rows,m,out):
 from v45_memory_review import apply_review
 rows,review=apply_review(out,rows,m)
 return {'review':review,'stage':'await_root_review'if len(rows)==len(m['schedule'])else'in_progress','models':{model:summarize([r for r in rows if r['model']==model],{**m,'schedule':[x for x in m['schedule']if x['model']==model]})for model in sorted({x['model']for x in m['schedule']})}}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);ap.add_argument('--config',default=str(ROOT/'tools/bench_config.json'));ap.add_argument('--plan',action='store_true');ap.add_argument('--execute',action='store_true');ap.add_argument('--approved-manifest-sha256');ap.add_argument('--engineering-approval');ap.add_argument('--stop-after-turns',type=int);a=ap.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);mp=out/'manifest.json'
 if a.plan:
  candidate=manifest(json.loads(Path(a.config).read_text()))
  if mp.exists()and json.loads(mp.read_text())!=candidate:raise SystemExit('Existing manifest differs; preserve original and use a separate experiment')
  if not mp.exists():save(mp,candidate)
  print(hashlib.sha256(mp.read_bytes()).hexdigest());return
 if not a.execute:raise SystemExit('Use --plan (zero inference), or --execute with approved manifest hash')
 if not mp.exists()or hashlib.sha256(mp.read_bytes()).hexdigest()!=a.approved_manifest_sha256:raise SystemExit('Exact preapproved manifest hash required')
 m=json.loads(mp.read_text())
 if m['harness_inventory']!=harness_inventory(m['harness_config']):raise SystemExit('Actual harness/runtime/dependencies changed after pin')
 if m['model_admissions']!={model:admission(model[7:])for model in m['model_admissions']}:raise SystemExit('Model admission changed after pin')
 if m['fingerprints']!=fingerprints():raise SystemExit('Source/config/corpus changed after pin; preserve run and re-review a separate pre-inference manifest')
 if not a.engineering_approval:raise SystemExit('Independent engineering approval artifact required before inference')
 approval=json.loads(Path(a.engineering_approval).read_text())
 if approval.get('status')!='approved'or approval.get('manifest_sha256')!=a.approved_manifest_sha256:raise SystemExit('Engineering approval does not bind exact manifest')
 lock=(out/'run.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 flag=out/'memory-control.json' 
 def pause(*_):save(flag,{'pause':True,'reason':'user signal','epoch':time.time()})
 signal.signal(signal.SIGINT,pause);signal.signal(signal.SIGTERM,pause)
 rows=[]
 for item in m['schedule']:
  trial=out/'episodes'/item['trial_id'];resultfile=trial/'result.json';statefile=trial/'runner/memory-controller.json'
  if resultfile.exists():rows.append(json.loads(resultfile.read_text()));continue
  if flag.exists()and any(json.loads(flag.read_text()).get(k)for k in('pause','hard_stop','pause_after_turn')):break
  task=ROOT/'tasks'/item['case']
  if hashlib.sha256((task/'environment/turns.json').read_bytes()).hexdigest()!=item['turns_sha256']:raise RuntimeError('Task changed after schedule pin')
  prior=json.loads(statefile.read_text())if statefile.exists()else None
  # A terminal/completed resume does not even construct a gateway or rewrite captures.
  if prior and prior['status']in('completed','dnf','interrupted'):row=prior
  else:
   try:row=MemoryEpisode(trial/'ws',task,item['model'],item['arm'],m['options'],flag).run(item['turns'],a.stop_after_turns)
   except Exception as exc:
    row=json.loads(statefile.read_text())if statefile.exists()else{}
    row.update(status='interrupted',error={'type':type(exc).__name__,'message':str(exc)})
    trial.mkdir(parents=True,exist_ok=True);save(statefile,row)
  if row['status']=='paused':break
  row.update(trial_id=item['trial_id'],model=item['model'],arm=item['arm'],case=item['case'])
  row.update(evaluate_episode(row,task,trial));save(resultfile,row);rows.append(row)
  save(out/'summary.json',summary(rows,m,out))
 save(out/'summary.json',summary(rows,m,out));print(json.dumps({'completed':len(rows),'scheduled':len(m['schedule']),'paused':flag.exists()},ensure_ascii=False))
if __name__=='__main__':main()
