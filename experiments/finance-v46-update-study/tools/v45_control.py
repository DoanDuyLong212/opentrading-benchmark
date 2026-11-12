"""Cooperative user stop; never delete or re-run a recorded attempt.
SIGINT/SIGTERM request graceful pause; second signal is OS force termination.
Crash recovery is handled by driver execute_trial as terminal interrupted.
"""
import argparse, json, os, signal, tempfile, time
from pathlib import Path


def atomic_json(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


class PauseController:
    def __init__(self,out):self.out=Path(out);self.flag=self.out/'PAUSE';self.requested=False;self.signals=0
    def install(self):
        def handler(sig,frame):
            self.signals+=1
            if self.signals>1:raise KeyboardInterrupt('Forced interruption; active attempt will be retained terminal on resume')
            self.requested=True
        signal.signal(signal.SIGINT,handler);signal.signal(signal.SIGTERM,handler)
    def paused(self):return self.requested or self.flag.exists()
    def checkpoint(self,stage,completed,total,active=None):
        atomic_json(self.out/'control-state.json',{'stage':stage,'completed':completed,'scheduled':total,'active_trial':active,'pause_requested':self.paused(),'pid':os.getpid(),'pid_start_ticks':Path('/proc/self/stat').read_text().split()[21],'updated_epoch':time.time()})


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=['pause','hard-stop','continue','status']);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out).resolve()
    if not (out/'manifest.json').exists() and not (out/'state.json').exists():raise SystemExit('Refusing unknown output without manifest/state')
    if a.action=='pause':atomic_json(out/'PAUSE',{'requested_epoch':time.time(),'mode':'finish current trial then stop'})
    elif a.action=='hard-stop':
        state=json.loads((out/'control-state.json').read_text());pid=state['pid']
        stat=Path('/proc')/str(pid)/'stat';cmdline=Path('/proc')/str(pid)/'cmdline'
        if not stat.exists() or stat.read_text().split()[21]!=state.get('pid_start_ticks'):raise SystemExit('PID context missing or recycled; no signal sent')
        cmd=cmdline.read_bytes().replace(b'\0',b' ').decode(errors='replace')
        if not any(name in cmd for name in ('run_benchmark.py','v45_supervisor.py')) or str(out) not in cmd:raise SystemExit('Refusing unrelated process')
        atomic_json(out/'PAUSE',{'requested_epoch':time.time(),'mode':'hard-stop','reason':'user interruption; active attempt retained terminal interrupted'})
        parents={}
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():continue
            try:parents[int(entry.name)]=int((entry/'stat').read_text().split()[3])
            except (OSError,ValueError,IndexError):continue
        descendants={pid};changed=True
        while changed:
            old=len(descendants);descendants.update(p for p,parent in parents.items() if parent in descendants);changed=len(descendants)>old
        for child in sorted(descendants-{pid},reverse=True):
            try:os.kill(child,signal.SIGKILL)
            except ProcessLookupError:pass
        try:os.kill(pid,signal.SIGKILL)
        except ProcessLookupError:pass
    elif a.action=='continue':
        (out/'PAUSE').unlink(missing_ok=True)
        # Remove only flags provably propagated by this supervisor, not user flags.
        state=json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {}
        active=state.get('active_out')
        if active:
            flag=Path(active)/'PAUSE'
            if flag.exists():
                detail=json.loads(flag.read_text())
                if detail.get('origin')=='pipeline':flag.unlink()
    value=json.loads((out/'control-state.json').read_text()) if (out/'control-state.json').exists() else {'state':'not started or supervisor boundary'}
    value['pause_flag']=(out/'PAUSE').exists();print(json.dumps(value,indent=2))
if __name__=='__main__':main()
