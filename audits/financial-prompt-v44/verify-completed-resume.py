#!/usr/bin/env python3
"""Guarded actual completed-driver resume. Review before execution; no inference permitted."""
import hashlib, importlib.util, json, os, pathlib, subprocess, sys, traceback
sys.dont_write_bytecode = True
BASE = pathlib.Path('/home/doanlong/extra/benchmark')
AUDIT = BASE/'audits/financial-prompt-v44'
SEAL = AUDIT/'preinference-seal-startupfix1.json'
SUPERVISOR = AUDIT/'supervisor-startupfix1/state.json'
EXPECTED_STATE = '5e4add17dab9d6eb5891c29afa5e34c1a257dc53aaf4f9be2353602e7fbc7f1a'
OUTPUT = pathlib.Path('/tmp/v44-final-report/completed-resume-proof.json')
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def validate_complete(item):
    out=pathlib.Path(item['out']); m=read(out/'manifest.json')
    assert item['split']=='smoke' and item['trials']==24
    assert m['fingerprint']==item['manifest_sha256']
    assert digest(m['plan'])==item['manifest_sha256']
    wanted={f'{task}__{arm}__r{r}' for task in ['smoke-agg-01','smoke-quote-01','smoke-trap-01'] for arm in ['opentrading_baseline','opentrading_finance','opencode','dsh'] for r in [1,2]}
    schedule=m['plan']['schedule']; ids=[x['trial_id'] for x in schedule]
    rows=[json.loads(s) for s in (out/'trials.jsonl').read_text().splitlines() if s.strip()]
    assert len(schedule)==len(rows)==24 and len(set(ids))==24 and set(ids)==wanted
    assert len({x['trial_id'] for x in rows})==24 and {x['trial_id'] for x in rows}==wanted
    states=list((out/'trials').glob('*/state.json'))
    assert len(states)==24 and {read(p)['trial_id'] for p in states}==wanted
    assert {p.parent.name for p in states}==wanted
    assert all(read(p).get('started_at') and read(p).get('started_epoch') for p in states)
    return {'n_scheduled':24,'n_completed':24,'n_started':24,'trial_ids':sorted(wanted),'manifest_fingerprint':m['fingerprint'],'trials_sha256':sha(out/'trials.jsonl'),'requests_from_rows':sum(r.get('requests',0) for r in rows)}
def snapshot(items):
    files={}; excluded={}
    for item in items:
        out=pathlib.Path(item['out'])
        for p in sorted(out.rglob('*')):
            rel=p.relative_to(out).as_posix(); key=item['key']+'/'+rel
            if rel in ('summary.json','.driver.lock') and item['split']=='smoke':
                if p.is_file(): excluded[key]={'sha256':sha(p),'mtime_ns':p.stat().st_mtime_ns}
                continue
            st=p.lstat()
            if p.is_symlink():files[key]={'symlink':os.readlink(p),'mtime_ns':st.st_mtime_ns,'target_sha256':sha(p) if p.is_file() else None}
            elif p.is_file():files[key]={'sha256':sha(p),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns}
    return {'protected':files,'excluded_regenerable_summary_and_driver_lock_only':excluded}
class ForbiddenTrial(BaseException): pass
def child(command):
    sys.path.insert(0,str(pathlib.Path(command[1]).parent))
    spec=importlib.util.spec_from_file_location('run_benchmark',command[1]); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=module.execute_trial; original_argv=sys.argv[:]
    def forbidden(*a,**kw):raise ForbiddenTrial('FATAL: completed resume attempted execute_trial; provider execution prohibited')
    module.execute_trial=forbidden;sys.argv=command[1:]
    try:module.main()
    finally:module.execute_trial=original;sys.argv=original_argv

def main():
    if len(sys.argv)>1 and sys.argv[1]=='--child':child(json.loads(sys.argv[2]));return
    seal=read(SEAL); supervisor=read(SUPERVISOR)
    assert seal['state_sha256']==EXPECTED_STATE and digest(seal['states'])==EXPECTED_STATE
    assert supervisor['seal']==str(SEAL) and supervisor['status']=='blocked'
    assert sha(pathlib.Path(seal['audit_script']['path']))==seal['audit_script']['sha256']
    # Frozen driver's real main() additionally invokes v44_gate.validate_seal, checking all sealed source/runtime/task/config hashes.
    smokes=[r for r in seal['runs'] if r['split']=='smoke']
    assert {r['key'] for r in smokes}=={'smoke-bolt','smoke-deepseek'}
    checks={r['key']:validate_complete(r) for r in smokes}
    commands=[]
    for item in smokes:
        cmd=supervisor['runs'][item['key']]['command']
        assert cmd[0]=='/usr/bin/python3' and cmd[1]==str(BASE/'experiments/finance-v44-study/tools/run_benchmark.py')
        assert cmd.count('--resume')==1 and cmd[cmd.index('--split')+1]=='smoke'
        for flag,value in [('--out',item['out']),('--config',item['config']),('--v44-seal',str(SEAL))]:assert cmd[cmd.index(flag)+1]==value
        commands.append((item,cmd))
    before=snapshot(seal['runs']); seal_sha=sha(SEAL); supervisor_sha=sha(SUPERVISOR)
    result={'kind':'v44-guarded-completed-resume','state_sha256':EXPECTED_STATE,'seal_file_sha256':seal_sha,'supervisor_file_sha256':supervisor_sha,'prechecks':checks,'before':before,'runs':[],'pass':False,'guard':'execute_trial replaced with fatal BaseException in external wrapper only; actual unmodified driver main parses exact supervisor CLI'}
    OUTPUT.write_text(json.dumps(result,indent=2))
    try:
        for item,cmd in commands:
            log=OUTPUT.parent/(item['key']+'-completed-resume.log')
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
            with log.open('w') as h:
                proc=subprocess.run(['/usr/bin/python3',str(pathlib.Path(__file__).resolve()),'--child',json.dumps(cmd)],stdout=h,stderr=subprocess.STDOUT,env=env,cwd=BASE,timeout=180)
            result['runs'].append({'key':item['key'],'actual_driver_argv':cmd,'exit_code':proc.returncode,'log':str(log),'execute_trial_calls':0 if proc.returncode==0 else 'unproven'})
            if proc.returncode:raise RuntimeError('guarded real driver resume failed: '+item['key'])
        assert sha(SEAL)==seal_sha and sha(SUPERVISOR)==supervisor_sha
        after=snapshot(seal['runs']); result['after']=after
        result['protected_bytes_sizes_and_mtime_ns_identical']=before['protected']==after['protected']
        result['postchecks']={r['key']:validate_complete(r) for r in smokes}
        assert result['postchecks']==checks
        assert result['protected_bytes_sizes_and_mtime_ns_identical']
        result['pass']=True;result['new_model_calls']=0
    except BaseException as exc:
        result['after']=snapshot(seal['runs']); result['error']=repr(exc);result['traceback']=traceback.format_exc();raise
    finally:OUTPUT.write_text(json.dumps(result,indent=2))
    print(json.dumps({'pass':result['pass'],'proof':str(OUTPUT),'protected_files':len(before['protected']),'new_model_calls':0}))
if __name__=='__main__':main()
