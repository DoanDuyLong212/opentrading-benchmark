#!/usr/bin/env python3
"""Actual completed driver CLI under an unconditional inference interceptor.
Protects every trial/manifest byte+mtime; zero execute_trial invocations required.
"""
import argparse,json,sys
from pathlib import Path
from run_manifest import hash_file
from v45_control import atomic_json

def snapshot(out):
    out=Path(out);paths=[out/'manifest.json',out/'trials.jsonl']+[p for p in (out/'trials').rglob('*') if p.is_file() and not p.is_symlink()]
    return {str(p.relative_to(out)):{'sha256':hash_file(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in sorted(paths) if p.is_file()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--command-json',required=True);a=p.parse_args();command=json.loads(a.command_json)
    if not isinstance(command,list) or len(command)<3 or Path(command[1]).name!='run_benchmark.py' or '--resume' not in command:raise ValueError('Expected exact saved completed-resume driver command')
    out=Path(command[command.index('--out')+1]).resolve()
    from metrics import load_trials
    from run_manifest import validate_trial_rows
    manifest=json.loads((out/'manifest.json').read_text())
    if not validate_trial_rows(load_trials(out),manifest):raise ValueError('Resume proof requires exact completed schedule')
    before=snapshot(out);calls=[]
    import run_benchmark as rb
    class UnexpectedInference(BaseException):pass
    def forbidden(*args,**kwargs):calls.append(str(args[:1]));raise UnexpectedInference('Completed resume attempted an inference; blocked before provider construction')
    rb.execute_trial=forbidden;argv=sys.argv;sys.argv=[command[1],*command[2:]]
    try:rb.main()
    finally:sys.argv=argv
    after=snapshot(out);proof={'schema':'completed-resume-v45','pass':not calls and before==after,'new_execute_trial_calls':len(calls),'new_model_calls':0,'protected_files':len(before),'before':before,'after':after,'manifest_sha256':manifest['fingerprint'],'method':'actual saved driver CLI, execute_trial BaseException interceptor, per-file SHA256/size/mtime'}
    atomic_json(out/'completed-resume-proof.json',proof)
    if not proof['pass']:raise ValueError('Completed resume mutated protected artifacts or attempted execution')
    print(json.dumps({k:v for k,v in proof.items() if k not in ('before','after')},indent=2))
if __name__=='__main__':main()
