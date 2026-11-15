#!/usr/bin/env python3
"""Durable sequential, fixed-schedule v44 smoke supervisor. No tuning or fallback."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
from datetime import datetime,timezone
from v44_gate import ROOT, validate_seal, diagnostic_quality, require_pilot_authorization
from run_manifest import hash_file


def atomic_state(path,value):
    path=Path(path);tmp=path.with_suffix('.tmp')
    with tmp.open('w') as fp:
        json.dump(value,fp,indent=2);fp.write('\n');fp.flush();os.fsync(fp.fileno())
    os.replace(tmp,path)


def command(item,seal):
    config=json.loads(Path(item['config']).read_text())
    return [sys.executable,str(ROOT/'tools/run_benchmark.py'),'--split',item['split'],
            '--arms','opentrading_baseline,opentrading_finance,opencode,dsh','--runs','2',
            '--seed','20261105','--config',item['config'],'--out',item['out'],
            '--timeout',str(config['trial_timeout_s']),'--provider-timeout-s',str(config['provider_timeout_s']),
            '--retry','0','--retry-backoff','4','--pause','2','--effort','none','--max-requests','24',
            '--max-output-tokens','2048','--max-total-tokens','48000','--v44-seal',str(seal),'--resume']


def pid_alive(pid):
    if not isinstance(pid,int) or pid<=0:return False
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False


def run_child(command,log,state,state_path,stage):
    state.update(stage=stage,child_pid=None,supervisor_pid=os.getpid())
    atomic_state(state_path,state)
    child=None
    try:
        with Path(log).open('a') as fp:
            child=subprocess.Popen(command,cwd=ROOT,stdout=fp,stderr=subprocess.STDOUT,start_new_session=True)
            state['child_pid']=child.pid
            atomic_state(state_path,state)
            while True:
                try:
                    code=child.wait(timeout=5)
                    state.update(child_pid=None,heartbeat_at=datetime.now(timezone.utc).isoformat())
                    atomic_state(state_path,state)
                    return code
                except subprocess.TimeoutExpired:
                    state['heartbeat_at']=datetime.now(timezone.utc).isoformat()
                    atomic_state(state_path,state)
    finally:
        if child is not None and child.poll() is None:
            # SIGINT lets the Python driver unwind gateway/native-session finally blocks.
            # Native SDK/MCP children use separate sessions and cannot be killed by the driver's group alone.
            cleanup={'child_pid':child.pid,'signals':['SIGINT']}
            os.killpg(child.pid,signal.SIGINT)
            try:child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                cleanup['signals'].append('SIGTERM');os.killpg(child.pid,signal.SIGTERM)
                try:child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    cleanup['signals'].append('SIGKILL');os.killpg(child.pid,signal.SIGKILL);child.wait()
            cleanup['returncode']=child.returncode
            state['last_child_cleanup']=cleanup
        state['child_pid']=None
        atomic_state(state_path,state)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seal',required=True);ap.add_argument('--state',required=True)
    ap.add_argument('--audit-script',required=True);ap.add_argument('--audit-output',required=True)
    a=ap.parse_args();seal=Path(a.seal).resolve();state_path=Path(a.state).resolve()
    state_path.parent.mkdir(parents=True,exist_ok=True)
    with state_path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        state=json.loads(state_path.read_text()) if state_path.exists() else {'kind':'v44-sequential-smoke','runs':{}}
        if state.get('seal') not in (None,str(seal)):
            raise ValueError('Supervisor belongs to another seal')
        if pid_alive(state.get('child_pid')):
            state.update(status='blocked',reason='Prior driver/auditor child is still alive; refusing duplicate or orphan execution')
            atomic_state(state_path,state);return 1
        state.update(seal=str(seal),supervisor_pid=os.getpid(),child_pid=None)
        try:
            receipt=validate_seal(seal)
            if str(Path(a.audit_script).resolve())!=receipt['audit_script']['path']:
                raise ValueError('Supervisor audit script differs from engineering-approved sealed auditor')
            for item in receipt['runs']:
                validate_seal(seal)
                stratum=item['key'];prior=state['runs'].get(stratum,{})
                if prior.get('status') in ('completed','skipped_quality_gate'):continue
                if item['split']=='pilot':
                    try:require_pilot_authorization(receipt,item)
                    except (ValueError,FileNotFoundError) as exc:
                        state['runs'][stratum]={'status':'skipped_quality_gate','reason':str(exc),'out':item['out']}
                        atomic_state(state_path,state);continue
                state.update(status='running',updated_at=datetime.now(timezone.utc).isoformat())
                state['runs'][stratum]={'status':'running','out':item['out'],'command':command(item,seal)}
                atomic_state(state_path,state)
                code=run_child(command(item,seal),state_path.parent/(stratum+'-driver.log'),state,state_path,stratum+'-driver')
                if code:
                    state['runs'][stratum].update(status='blocked',exit_code=code)
                    raise RuntimeError('Driver infrastructure/identity failure; no new stratum launched')
                validate_seal(seal)
                audit_cmd=[sys.executable,str(Path(a.audit_script).resolve()),'--execute','--run',item['out'],
                           '--output',str(Path(a.audit_output).resolve())]
                code=run_child(audit_cmd,state_path.parent/(stratum+'-audit.log'),state,state_path,stratum+'-audit')
                if code:
                    state['runs'][stratum].update(status='blocked',audit_exit_code=code)
                    raise RuntimeError('Independent audit controls failed; model quality failure alone does not block')
                report=json.loads(Path(a.audit_output).read_text())
                model=json.loads(Path(item['config']).read_text())['model']
                audited=report['completed_runs'][item['split']+'-'+model]
                if audited.get('audit_controls_pass') is not True or audited.get('errors'):
                    raise ValueError('Audit exit0 lacks explicit model-keyed control pass')
                if item['split']=='smoke':
                    atomic_state(Path(item['out'])/'v44-audit-controls.json',{
                        'manifest_sha256':item['manifest_sha256'],'trials_sha256':hash_file(Path(item['out'])/'trials.jsonl'),
                        'audit_controls_pass':True,'zero_accepted_fabrication':audited.get('zero_accepted_fabrication') is True,
                        'auditor_sha256':receipt['audit_script']['sha256'],'smoke_financial_canary_pass':audited.get('smoke_financial_canary_pass') is True})
                diagnostic=diagnostic_quality(item['out']) if item['split']=='smoke' else {'quality_pass':None,'note':'pilot descriptive results; no auto-promotion'}
                if item['split']=='smoke':
                    diagnostic['smoke_financial_canary_pass']=audited.get('smoke_financial_canary_pass') is True
                    diagnostic['quality_pass']=diagnostic['quality_pass'] and diagnostic['smoke_financial_canary_pass']
                diagnostic_path=state_path.parent/(stratum+'-diagnostic.json')
                atomic_state(diagnostic_path,diagnostic)
                state['runs'][stratum].update(status='completed',audit_controls_pass=True,
                                              quality_pass=diagnostic['quality_pass'],diagnostic=str(diagnostic_path))
                state.update(status='running',updated_at=datetime.now(timezone.utc).isoformat())
                atomic_state(state_path,state)
            state.update(status='completed',stage='completed',updated_at=datetime.now(timezone.utc).isoformat(),
                         note='Both registered smokes and eligible per-model pilots completed; quality-gated skips retained. No promotion or production install.')
            atomic_state(state_path,state);return 0
        except (Exception,KeyboardInterrupt) as exc:
            state.update(status='blocked',reason=str(exc) or type(exc).__name__,child_pid=None,
                         updated_at=datetime.now(timezone.utc).isoformat())
            atomic_state(state_path,state);return 1

def terminate_supervisor(*_):
    raise KeyboardInterrupt('Supervisor terminated')


if __name__=='__main__':
    signal.signal(signal.SIGTERM,terminate_supervisor)
    sys.exit(main())
