#!/usr/bin/env python3
"""Sealed resumable v4.6-update smoke -> pilot (-> main only under a b0_judge_primary seal with user authorization), models separate.
No source tuning/retry quality, no holdout. PAUSE checked before stage transitions.
"""
from protocol_compat import FINANCIAL_PROTOCOL
import argparse,fcntl,json,os,subprocess,sys,time
from pathlib import Path
from v45_control import atomic_json,PauseController
from v45_gate import validate_seal,quality_gate
ROOT=Path(__file__).resolve().parent.parent


def driver_command(item,seal):
    s=item['settings'];cmd=[sys.executable,str(ROOT/'tools/run_benchmark.py'),'--resume','--config',item['config'],'--out',item['out'],'--v45-seal',str(Path(seal).resolve())]
    flags={'split':'--split','seed':'--seed','runs':'--runs','retry':'--retry','pause':'--pause','retry_backoff':'--retry-backoff','timeout':'--timeout','effort':'--effort','max_requests':'--max-requests','max_output_tokens':'--max-output-tokens','max_total_tokens':'--max-total-tokens','provider_timeout_s':'--provider-timeout-s'}
    for k,flag in flags.items():cmd += [flag,str(s[k])]
    # Holdout opens once, after main (amendment 2026-11-11 d/h): explicit driver confirmation.
    return cmd+['--arms',','.join(s['arms'])]+(['--confirm-holdout'] if s['split']=='holdout' else [])


def write_report(out,split,gate):
    out=Path(out);summary=json.loads((out/'summary.json').read_text());data=summary['financial_v45'];lines=['# '+split+' v4.6-update — '+str(summary['model']),'','Same registered co-primary/secondary metrics as main. Every scheduled trial remains denominator; no model pooling.','', '| Arm | N | Strict grounded | Grounded financial | DNF | FR / answerable | FP / traps | Usage complete |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for arm,m in data['arms'].items():lines.append(f"| {arm} | {m['scheduled']} | {m['strict_grounded_success']} | {m['grounded_financial_correctness']} | {m['dnf']} | {m['false_refusals']}/{m['answerable_scheduled']} | {m['false_positives']}/{m['trap_scheduled']} | {m['usage_complete']}/{m['observed']} |")
    lines+=['','Gate: '+('PROVISIONAL — independent all-arm manual financial review pending' if not data.get('manual_financial_review',{}).get('review_complete') else 'PASS' if gate['pass'] else 'FAIL'),'',json.dumps(gate,ensure_ascii=False,indent=2),'','Full secondary metrics, per-level/family, stable2/2, task-cluster comparisons: summary.json. Source/capture/usage independent audit: audit-v45.json. Pilot is screening evidence, not statistical proof of broad superiority.']
    (out/('PILOT-REPORT.md' if split=='pilot' else split.upper()+'-REPORT.md')).write_text('\n'.join(lines)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--seal',required=True);ap.add_argument('--out',required=True);ap.add_argument('--resume',action='store_true');a=ap.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    with (out/'.supervisor.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise SystemExit('Supervisor already running; no duplicate launch')
        seal=validate_seal(a.seal);statepath=out/'state.json'
        if statepath.exists() and not a.resume:raise SystemExit('Existing supervisor requires --resume')
        state={'study_version':'v4.6-update','protocol':FINANCIAL_PROTOCOL,'seal':str(Path(a.seal).resolve()),'pid':os.getpid(),'status':'running','stage':None,'child_pid':None,'cohorts':{},'blocked_models':seal.get('blocked_models',{}),'main_authorized_by_user':False}
        old=json.loads(statepath.read_text()) if statepath.exists() else {}
        if old and old.get('seal')!=state['seal']:raise SystemExit('Resume seal mismatch')
        state['cohorts']=old.get('cohorts',{})
        state['active_out']=old.get('active_out')
        control=PauseController(out);control.install()
        def save(status,stage=None):
            state.update(status=status,stage=stage,updated_epoch=time.time());atomic_json(statepath,state);control.checkpoint(status,len(state['cohorts']),len(seal['runs']),stage)
        def run(cmd,item,stage):
            if control.paused():save('paused',stage);return False
            target=Path(item['out'])
            with (out/(Path(item['out']).name+'-'+stage+'.log')).open('a') as log:
                child=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);state['child_pid']=child.pid;state['active_out']=item['out'];save('running',stage)
                while child.poll() is None:
                    if control.paused():atomic_json(target/'PAUSE',{'origin':'pipeline','requested_epoch':time.time()})
                    state['heartbeat_epoch']=time.time();atomic_json(statepath,state);time.sleep(2)
                state['child_pid']=None
                if control.paused() or (target/'PAUSE').exists():save('paused',stage);return False
                if child.returncode:save('blocked',stage);state['error']='Command failed exit '+str(child.returncode);atomic_json(statepath,state);return False
            return True
        # Audit both model smoke cohorts before any pilot authorization.
        b0=seal.get('gate')=='b0_judge_primary' and seal.get('main_authorized_by_user') is True
        holdout=b0 and seal.get('holdout_authorized_by_user') is True and any(x['split']=='holdout' for x in seal['runs'])
        for split in ['devsmoke','pilot']+(['main'] if b0 else [])+(['holdout'] if holdout else []):
            for item in [x for x in seal['runs'] if x['split']==split]:
                key=item['model']+'/'+split
                if state['cohorts'].get(key,{}).get('finished'):continue
                if split!='devsmoke':
                    ownsmoke=state['cohorts'].get(item['model']+'/devsmoke',{})
                    ownpilot=state['cohorts'].get(item['model']+'/pilot',{})
                    smokeaudits=[v for k,v in state['cohorts'].items() if k.endswith('/devsmoke')]
                    eligible=ownsmoke.get('gate',{}).get('pass') and len(smokeaudits)==len({x['model'] for x in seal['runs']}) and all(v.get('audit_pass') for v in smokeaudits)
                    if split=='pilot' and seal.get('diagnostic_pilot_authorized') is True:
                        from v45_gate import require_diagnostic_smoke
                        try:eligible=bool(require_diagnostic_smoke(seal,item['model'])) and len(smokeaudits)==len({x['model'] for x in seal['runs']}) and all(v.get('audit_pass') for v in smokeaudits)
                        except (ValueError,FileNotFoundError):eligible=False
                    if split=='holdout':
                        ownmain=state['cohorts'].get(item['model']+'/main',{})
                        eligible=bool(ownmain.get('finished') and ownmain.get('audit_pass'))
                        if eligible and not (Path(item['out'])/'holdout-go.json').is_file():
                            # User 2026-11-11: run holdout right after main only if the key limit covers it.
                            save('await_root_holdout_budget_check',key);state['required_action']='Check OpenRouter key limit covers holdout, write holdout-go.json, then exact resume';atomic_json(statepath,state);return
                    if split=='main':
                        # B0 main amendment: pilot cohort must be finished with the B0 judge-primary gate passed.
                        eligible=bool(b0 and ownpilot.get('finished') and ownpilot.get('gate',{}).get('pass') and ownpilot.get('gate',{}).get('gate')=='b0_judge_primary')
                    if not eligible:state['cohorts'][key]={'skipped':True,'finished':True,'reason':'Prerequisite quality/audit gate failed'};save('running',key);continue
                if split=='main':
                    pilot=Path(next(x['out'] for x in seal['runs'] if x['model']==item['model'] and x['split']=='pilot'))
                    if not (pilot/'pilot-review-approval.json').is_file():
                        save('await_root_pilot_review',key);state['required_action']='Independent manual source/math audit and pilot metrics delivered to user, then exact resume';atomic_json(statepath,state);return
                if not run(driver_command(item,a.seal),item,key.replace('/','-')):return
                if not run([sys.executable,str(ROOT/'tools/v45_verify_resume.py'),'--command-json',json.dumps(driver_command(item,a.seal))],item,'completed-resume-'+split):return
                audit_ok=run([sys.executable,str(ROOT/'tools/audit_v45_run.py'),'--run',item['out']],item,'audit-'+split)
                if control.paused():return
                summary=json.loads((Path(item['out'])/'summary.json').read_text())
                audit_path=Path(item['out'])/'audit-v45.json'
                audit=json.loads(audit_path.read_text()) if audit_path.is_file() else {'pass':False,'fabricated_evidence_accepted':None,'error':'Auditor exited without valid receipt'}
                if split=='pilot' and b0:
                    from b0_gate import b0_gate
                    gate=b0_gate(item['out'],seal.get('judge_kappa_file'))
                else:gate=quality_gate(summary,audit,split) if split!='main' else {'pass':audit.get('pass',False),'reasons':[]}
                if not audit_ok and gate['pass']:gate={'pass':False,'reasons':['Auditor process failed'],'split':split}
                write_report(item['out'],split,gate)
                if audit_ok and not summary.get('financial_v45',{}).get('manual_financial_review',{}).get('review_complete'):
                    save('await_root_'+split+'_review',key);state['required_action']='Independently review all automatic wins in every arm, write hash-bound financial-review.json; then exact resume recomputes reviewed metrics without calls';atomic_json(statepath,state);return
                state['cohorts'][key]={'finished':True,'audit_pass':audit['pass'],'gate':gate,'report':str(Path(item['out'])/('PILOT-REPORT.md' if split=='pilot' else split.upper()+'-REPORT.md'))};save('running',key)
                # Durable event at pilot boundary, before any main process starts.
                if split=='pilot':atomic_json(out/('pilot-boundary-'+Path(item['out']).name+'.json'),{'model':item['model'],'metrics_report':state['cohorts'][key]['report'],'gate':gate,'at_epoch':time.time()})
                if not audit_ok:save('blocked',key);return
                if control.paused():save('paused',key);return
        save('completed','final-review');print(json.dumps(state,indent=2))
if __name__=='__main__':main()
