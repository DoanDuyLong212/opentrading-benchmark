"""Offline auditor negative/safety checks, without any study execution."""
import hashlib,importlib.util,json,pathlib,subprocess,sys,tempfile
p=pathlib.Path(__file__).with_name('audit-completed-run.py');spec=importlib.util.spec_from_file_location('prepared_audit',p);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
checks=[]
def check(name,value):
    checks.append(name)
    if not value:raise AssertionError(name)
r={k:k for k in a.FIELDS};r['status']='ok';claim={k:r[k] for k in a.FIELDS}
check('all seven actual evidence fields join',a.claim_join({'evidence':[claim]},[r]))
for field in a.FIELDS:
    check('tampered '+field+' rejected',not a.claim_join({'evidence':[{**claim,field:'forged'}]},[r]))
check('empty evidence is not grounded',not a.claim_join({'evidence':[]},[r]))
check('rejected execution cannot ground evidence',not a.claim_join({'evidence':[claim]},[{**r,'status':'rejected'}]))
check('no provider response is not no-call response',a.mechanism_receipt({'attempts':[]},[])['initial_zero_call_provider_responses']==0)
check('observed no-call provider response counted',a.mechanism_receipt({'attempts':[]},[{'status':200,'tool_call_count':0}])['initial_zero_call_provider_responses']==1)
with tempfile.TemporaryDirectory() as t:
    fixture=pathlib.Path(t)/'tools';fixture.mkdir()
    deepseek='nvidia/deepseek-ai/deepseek-v4.1-flash'
    (fixture/'bench_config_deepseek.json').write_text(json.dumps({'model':deepseek,'model_stratum':'deepseek'}))
    (fixture/'bench_config.json').write_text(json.dumps({'model':'nvidia/nvidia/nemotron-3.5-bolt-e4b','model_stratum':'bolt'}))
    check('DeepSeek selects registered DeepSeek filesystem config',a.registered_config(pathlib.Path(t),deepseek)[0]['model']==deepseek)
    (fixture/'bench_config_deepseek.json').write_text((fixture/'bench_config.json').read_text())
    try:a.registered_config(pathlib.Path(t),deepseek)
    except ValueError:rejected=True
    else:rejected=False
    check('Bolt config in DeepSeek registered path rejected',rejected)
    log=pathlib.Path(t)/'log';log.write_text(json.dumps({'ok':True,'financeIntent':{'phase':'unknown','correction_used':1}})+'\n')
    check('unknown phase cannot imply corrected execution',a.mechanism_receipt({'attempts':[{'log_path':str(log)}]},[])['same_intent_corrected_executions']==0)
    refused=subprocess.run([sys.executable,str(p),'--run',t],capture_output=True,text=True)
    check('explicit completion trigger required',refused.returncode!=0 and 'explicit final-completion trigger required' in refused.stderr)
result={'pass':True,'checks':checks,'auditor_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
pathlib.Path(__file__).with_name('auditor-helper-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':True,'checks':len(checks)}))
