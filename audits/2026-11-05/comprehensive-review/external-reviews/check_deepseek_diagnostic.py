#!/usr/bin/env python3
"""Independent read-only recheck of diagnostic claims. Derivatives only; no inference."""
import collections,hashlib,json,pathlib,subprocess,sys,tempfile
sys.dont_write_bytecode=True
ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=pathlib.Path(__file__).resolve().parent
DIRS={'A':ROOT/'results/diag-deepseek-flash-20261105','B':ROOT/'results/diag-deepseek-flash-20261105-passB','C1':ROOT/'results/diag-deepseek-flash-20261105-passC','C2':ROOT/'results/diag-deepseek-flash-20261105-passC/driver2.log'}
ARMS=['opentrading_baseline','opentrading_finance','opencode','dsh']
KEYS=('tool','source','as_of','call_id','payload_sha256','matched_entry_id','response_sha256')
MODEL='deepseek-ai/deepseek-v4.1-flash'
def read(p):return json.loads(pathlib.Path(p).read_text())
def rows(p):
 p=pathlib.Path(p) if p else None
 return [(i,json.loads(l)) for i,l in enumerate(p.read_text().splitlines(),1) if l.strip()] if p and p.is_file() else []
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def dig(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rel(p):
 try:return str(pathlib.Path(p).relative_to(ROOT))
 except ValueError:return str(p)
def ident(r):return (r['task'],r['arm'],r['run'])
def count(rr):
 return {'started':len(rr),'status_ok':sum(r['status']=='ok' for r in rr),'primary':sum(bool(r['success']) for r in rr),'errors':sum(r['status']!='ok' for r in rr),'all_started_success_rate':sum(bool(r['success']) for r in rr)/len(rr) if rr else None,'completed_success_rate':sum(bool(r['success']) for r in rr)/sum(r['status']=='ok' for r in rr) if any(r['status']=='ok' for r in rr) else None}
allrows=[];manifests={};by_pass={};integrity={};capture_fail=[];providercounts=collections.Counter();responsemodels=collections.Counter();usagecounts=collections.Counter();regrade=[]
with tempfile.TemporaryDirectory(prefix='independent-diag-regrade-') as tmp:
 for label,d in DIRS.items():
  m=read(d/'manifest.json');manifests[label]=m;rr=rows(d/'trials.jsonl');actual=[]
  check={'manifest_fingerprint_matches':m['fingerprint']==dig(m['plan']),'input_trials_sha256':sha(d/'trials.jsonl'),'manifest_sha256':sha(d/'manifest.json'),'source_hash_mismatches':[],'task_hash_mismatches':[],'capture_count':0,'unique_trial_ids':len({r['trial_id'] for _,r in rr})==len(rr)}
  physical_attempts={str(p.resolve()) for p in d.glob('trials/*/attempts/*') if p.is_dir()}
  recorded_attempts={str(pathlib.Path(a['workspace']).parent.resolve()) for _,r in rr for a in r['attempts']}
  check['physical_attempt_dirs']=len(physical_attempts)
  check['unrecorded_attempt_dirs']=sorted(physical_attempts-recorded_attempts)
  check['recorded_but_missing_attempt_dirs']=sorted(recorded_attempts-physical_attempts)
  for p,h in m['plan']['code'].items():
   q=ROOT/p
   if not q.is_file() or sha(q)!=h:check['source_hash_mismatches'].append(p)
  for task,files in m['plan']['tasks'].items():
   for p,h in files.items():
    q=ROOT/'tasks/pilot'/task/p
    if not q.is_file() or sha(q)!=h:check['task_hash_mismatches'].append(str(q))
  ot=m['plan']['harnesses']['opentrading'];runtime=pathlib.Path(ot['runtime_root'])
  srchashes={str(p.relative_to(runtime)):sha(p) for p in sorted((runtime/'src').rglob('*')) if p.is_file() and p.suffix in ('.ts','.json')}
  check['ot_source_hash_matches']=dig(srchashes)==ot['source_sha256']
  check['ot_prompt_hashes_match']=all(sha(runtime/p)==h for p,h in ot['prompt_files'].items())
  for line,r in rr:
   a=r['attempts'][-1];lp=pathlib.Path(a['log_path']);log=lp.read_text() if lp.exists() else '';pp=rows(a.get('provider_ledger'));led=rows(a.get('ledger_path'));msgs=[];bad=[]
   for pl,p in pp:
    providercounts[(label,str(p.get('status')),p.get('error') or '')]+=1
    if 'response_models' in p:responsemodels[(label,json.dumps(p['response_models']))]+=1
    if p.get('usage'):
     usagecounts[(label,'known_requests')]+=1;u=p['usage'];usagecounts[(label,'positive_reasoning_requests')]+=bool((u.get('completion_tokens_details') or {}).get('reasoning_tokens'));usagecounts[(label,'input_known')]+=u['prompt_tokens'];usagecounts[(label,'output_known')]+=u['completion_tokens'];usagecounts[(label,'reasoning_known')]+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens') or 0
    if p.get('status')!=200 or p.get('error'):bad.append({'source':rel(a['provider_ledger'])+':'+str(pl),'status':p.get('status'),'error':p.get('error'),'response_models':p.get('response_models'),'upstream_attempted':p.get('upstream_attempted')})
    for kind in ('native','effective'):
     meta=p.get(kind+'_request_capture')
     if not meta:continue
     q=pathlib.Path(meta['path']);body=read(q);check['capture_count']+=1
     if sha(q)!=meta['raw_sha256'] or dig(body)!=meta['canonical_sha256']:capture_fail.append(str(q))
     if body.get('model')!=MODEL:capture_fail.append('model:'+str(q))
     if kind=='effective' and (body.get('temperature')!=0 or body.get('top_p')!=1 or body.get('max_tokens')!=2048):capture_fail.append('sampling:'+str(q))
     if kind=='native':msgs.extend(body.get('messages',[]))
   watchdoglines=[i for i,l in enumerate(log.splitlines(),1) if 'Model không gửi dữ liệu trong 120s' in l]
   item={'pass':label,'trial_id':r['trial_id'],'task':r['task'],'arm':r['arm'],'run':r['run'],'status':r['status'],'success':bool(r['success']),'error_type':r.get('error_type'),'attempt_count':len(r.get('attempts',[])),'wall_ms':r.get('wall_ms'),'usage_complete':(r.get('tokens') or {}).get('complete',False),'trial_source':rel(d/'trials.jsonl')+':'+str(line),'manifest_path':rel(d/'manifest.json'),'provider_errors':bad,'native_watchdog_event':bool(watchdoglines),'watchdog_in_primary_notes':'Model không gửi dữ liệu trong 120s' in a.get('notes',''),'watchdog_sources':[rel(lp)+':'+str(i) for i in watchdoglines],'ledger_path':rel(a['ledger_path']),'calls':[{k:x.get(k) for k in ['tool','arguments','status','error_code','availability']} for _,x in led]}
   ans=read(r['answer_path']) if r.get('answer_path') and pathlib.Path(r['answer_path']).is_file() else None
   if ans is not None:
    item['answer']=ans
    claimed=ans.get('evidence',[]);oks=[x for _,x in led if x['status']=='ok']
    item['all_evidence_7_fields_grounded']=bool(claimed) and all(any(all(c.get(k)==x.get(k) for k in KEYS) for x in oks) for c in claimed)
    text=json.dumps(msgs,ensure_ascii=False)
    item['evidence_ids_and_hashes_visible']=all(c.get('call_id','__MISSING__') in text and c.get('response_sha256','__MISSING__') in text for c in claimed)
    gold=ROOT/'tasks/pilot'/r['task']/'solution/gold.json';grader=gold.parent.parent/'tests/grader.py';target=pathlib.Path(tmp)/(label+'-'+r['trial_id']+'.json')
    subprocess.run([sys.executable,str(grader),r['answer_path'],'-g',str(gold),'-o',str(target)],check=True,capture_output=True,text=True)
    g=read(target);oldg=read(r['grade_path']);item['failed_checks']=[x for x in g.get('checks',[]) if not x['pass']]
    regrade.append({'pass':label,'trial_id':r['trial_id'],'grade_success':g['success'],'matches_persisted':g['success']==oldg['success'] and g['checks']==oldg['checks'],'evidence_grounded':item['all_evidence_7_fields_grounded'],'evidence_visible':item['evidence_ids_and_hashes_visible']})
   allrows.append(item);actual.append(item)
  by_pass[label]={'directory':rel(d),'settings':m['plan']['settings'],'counts':count(actual),'per_arm':{a:count([r for r in actual if r['arm']==a]) for a in ARMS},'schedule_count':len(m['plan']['schedule']),'watchdog_native_events':sum(r['native_watchdog_event'] for r in actual),'watchdog_primary_notes':sum(r['watchdog_in_primary_notes'] for r in actual),'watchdog_with_provider_error':sum(r['native_watchdog_event'] and bool(r['provider_errors']) for r in actual)}
  integrity[label]=check
# Reproduce published comparator exactly: prefer B status=ok, fallback A status=ok.
indices={p:{ident(r):r for r in allrows if r['pass']==p} for p in DIRS}
keys=set(indices['A']);selected=[];latest=[]
for k in sorted(keys):
 candidates=[indices[p][k] for p in ['B','A'] if k in indices[p]]
 selected.append(next((r for r in candidates if r['status']=='ok'),candidates[0]))
 latest.append(next(indices[p][k] for p in ['C2','C1','B','A'] if k in indices[p]))
small={ident(r):r for _,r in rows(ROOT/'results/financial-prompt-v3-pilot-20261105/trials.jsonl')}
paired={}
for arm in ARMS:
 complete=[r for r in selected if r['arm']==arm and r['status']=='ok'];paired[arm]={'matched_completed_cells':len(complete),'small_primary_on_these_cells':sum(small[ident(r)]['success'] for r in complete),'diagnostic_primary_on_these_cells':sum(r['success'] for r in complete)}
coverage=[]
for t in sorted({r['task'] for r in selected}):
 for a in ARMS:
  rr=[r for r in selected if r['task']==t and r['arm']==a]
  coverage.append({'task':t,'arm':a,'completed':sum(r['status']=='ok' for r in rr),'primary':sum(r['success'] for r in rr),'missing_runs':[r['run'] for r in rr if r['status']!='ok']})
# Period false-negative: evaluate the frozen implementation without altering it.
import importlib.util
spec=importlib.util.spec_from_file_location('frozen_period_grader',ROOT/'tasks/pilot/fin-l5-compare-01/tests/grader.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
pf=next(r for r in allrows if r['pass']=='A' and r['trial_id']=='fin-l5-compare-01__opentrading_finance__r1')
period=pf['answer']['period'];adjud={'period':period,'frozen_result':mod.period_hit(period,['2025']),'same_text_without_unrelated_negation':mod.period_hit(period.replace('không phải bội số hiện tại','bội số lịch sử'),['2025']),'official_result_preserved':True,'interpretation':'Credible false-negative: negation concerns current multiples, not year2025. Single observationalcase cannot establish prompt-style cause.'}
canary=ROOT/'audits/2026-11-05/nvidia-function-probe-deepseek-v41-flash.json';receipt=read(canary)
summary={'source_document':{'path':'opencode-review.md','sha256':sha(ROOT/'opencode-review.md')},'all_started':count(allrows),'all_started_per_arm':{a:count([r for r in allrows if r['arm']==a]) for a in ARMS},'by_pass':by_pass,'published_B_preferred_A_fallback':{'counts':count(selected),'per_arm':{a:count([r for r in selected if r['arm']==a]) for a in ARMS},'chosen_sources':dict(collections.Counter(r['pass'] for r in selected if r['status']=='ok')),'error_only_cells':sum(r['status']!='ok' for r in selected)},'latest_observed_attempt':{'counts':count(latest),'per_arm':{a:count([r for r in latest if r['arm']==a]) for a in ARMS}},'matched_complete_comparison':paired,'coverage':coverage,'watchdog':{'native_events':sum(r['native_watchdog_event'] for r in allrows),'primary_notes':sum(r['watchdog_in_primary_notes'] for r in allrows),'cooccurring_provider_errors':sum(r['native_watchdog_event'] and bool(r['provider_errors']) for r in allrows)},'provider_counts':[{'pass':p,'status':s,'error':e,'count':n} for (p,s,e),n in providercounts.items()],'response_models':[{'pass':p,'models':json.loads(ms),'count':n} for (p,ms),n in responsemodels.items()],'usage':[{'pass':p,'measurement':k,'value':n} for (p,k),n in usagecounts.items()],'integrity':integrity,'capture_failures':capture_fail,'regrades':regrade,'period_false_negative_candidate':adjud,'canary':{'path':rel(canary),'sha256':sha(canary),'model':receipt.get('model'),'response_model':receipt.get('response_model'),'status':receipt.get('status'),'catalog_status':receipt.get('catalog_status'),'function_call_verified':receipt.get('function_call_verified'),'tool_loop_status':receipt.get('tool_loop',{}).get('status'),'limitation':'Receipt contains summarized first response identity and tool continuation; no raw HTTP response hash/timestamp or second-response model identity stored.'},'manifest_source_equal_across_passes':all(m['plan']['code']==manifests['A']['plan']['code'] for m in manifests.values()),'manifest_OT_inventory_equals_v3':manifests['A']['plan']['harnesses']['opentrading']==read(ROOT/'results/financial-prompt-v3-pilot-20261105/manifest.json')['plan']['harnesses']['opentrading']}
(OUT/'deepseek-diagnostic-claims.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
(OUT/'deepseek-diagnostic-attempts.json').write_text(json.dumps(allrows,ensure_ascii=False,indent=2)+'\n')
(OUT/'deepseek-diagnostic-selected-cells.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:summary[k] for k in ['all_started','all_started_per_arm','published_B_preferred_A_fallback','latest_observed_attempt','watchdog','matched_complete_comparison']},ensure_ascii=False,indent=2))
print('Capturehash/model/sampling failures:',len(capture_fail),'capturefiles:',sum(x['capture_count'] for x in integrity.values()),'regrade mismatches:',sum(not x['matches_persisted'] for x in regrade),'unmatched evidence:',sum(not x['evidence_grounded'] for x in regrade))
