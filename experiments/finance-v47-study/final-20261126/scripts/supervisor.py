"""Detached supervisor for the 300-task completion runs (one stream at a time, in order).
Self-heals: 4 MB byte-cap Cohort STOP (reconcile at upper bound with actual cost noted), agent-written answer.json
conflict (one recovery resume per trial), one crash-recovery relaunch per run, one final infra-void sweep per run.
Anything else -> writes SUPERVISOR.ALERT and stops. Writes SUPERVISOR.DONE when all runs are complete.
Log: supervisor.log
"""
import json
import re
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path

B = Path('/home/doanlong/extra/bench-v47-pin/runs/deepinfra-20261125')
ORDER = ['a-ot', 'a-dsh', 'a-oc', 'a-dsh2', 'a-all', 'b-ot', 'b2-ot']
LOG = B / 'supervisor.log'
PROXY = 'http://127.0.0.1:25360'
TRIAL = re.compile(r'^\[(\d+)/(\d+)\] (\S+) status=(\S+)')


def log(msg):
    with LOG.open('a') as f:
        f.write(datetime.now().isoformat(timespec='seconds') + ' ' + msg + '\n')


def alive_any():
    return subprocess.run(['pgrep', '-f', '^python3 tools/run_benchmark.py --config ' + str(B)], capture_output=True).returncode == 0


def alive(name):
    return subprocess.run(['pgrep', '-f', f'^python3 tools/run_benchmark.py --config {B}/{name}/'], capture_output=True).returncode == 0


def done_count(name):
    p = B / name / 'run/trials.jsonl'
    return sum(1 for l in p.read_text().splitlines() if l.strip()) if p.exists() else 0


def sched_count(name):
    return len(json.loads((B / name / 'run/manifest.json').read_text())['plan']['schedule'])


def launch(name, *extra):
    if alive_any():
        log(f'not launching {name}: a runner is alive')
        return
    with open(B / name / 'run.log', 'a') as f:
        f.write(f'=== supervisor {" ".join(extra)[:60] or "resume"} {datetime.now().isoformat(timespec="seconds")} ===\n')
    import shlex
    cmd = ' '.join(shlex.quote(x) for x in [str(B / name / 'run.sh'), *extra])
    subprocess.run(['bash', '-c', f'setsid nohup {cmd} >/dev/null 2>&1 < /dev/null & disown'])
    log(f'launched {name} {" ".join(extra)[:80]}')
    time.sleep(20)


def gen_cost(gen):
    try:
        env = dict(l.strip().split('=', 1) for l in open('/home/doanlong/extra/benchmark/.env') if '=' in l and not l.startswith('#'))
        key = env['OPENROUTER_KEY_2'].strip().strip('"').strip("'")
        op = urllib.request.build_opener(urllib.request.ProxyHandler({'https': PROXY}))
        d = json.load(op.open(urllib.request.Request('https://openrouter.ai/api/v1/generation?id=' + gen, headers={'Authorization': 'Bearer ' + key}), timeout=30))['data']
        return f"{d.get('total_cost')} / {d.get('tokens_completion')} completion tokens"
    except Exception as e:
        return 'lookup failed ' + type(e).__name__


def alert(msg):
    log('ALERT ' + msg)
    (B / 'SUPERVISOR.ALERT').write_text(datetime.now().isoformat() + ' ' + msg + '\n')
    raise SystemExit(1)


def last_activity(name):
    ts = [p.stat().st_mtime for p in (B / name / 'run/trials').glob('*/attempts/*/provider.jsonl')]
    return max(ts) if ts else 0


log('supervisor start')
for name in ORDER:
    reconciles, conflicts, crash_relaunch, swept = 0, set(), 0, False
    started_wait = time.time()
    while True:
        if alive(name):
            if time.time() - max(last_activity(name), started_wait) > 2400:
                alert(f'{name}: no provider activity for 40 min')
            time.sleep(30)
            continue
        if alive_any():           # some other runner (e.g. old chain) still running; wait for it
            time.sleep(30)
            continue
        done, sched = done_count(name), sched_count(name)
        if done == sched:
            if not swept:
                swept = True
                n = int(subprocess.run(['python3', str(B / 'void_infra.py'), str(B / name / 'run'), '--apply'], capture_output=True, text=True).stdout.strip() or 0)
                if n:
                    log(f'{name}: final sweep voided {n} infra-failed trial(s); re-running them')
                    launch(name)
                    started_wait = time.time()
                    continue
            blocked = []
            for tl in (B / name / 'run/trials.jsonl').read_text().splitlines():
                r = json.loads(tl)
                if r.get('status') != 'ok':
                    atts = sorted((B / name / 'run/trials' / r['trial_id'] / 'attempts').glob('*'))
                    if atts and 'paid USD budget exhausted' in (atts[-1] / 'provider.jsonl').read_text():
                        blocked.append(r['trial_id'])
            if blocked and name != 'a-dsh':
                alert(f'{name}: trials blocked by the run cap (need a new run): {blocked}')
            log(f'{name}: complete {done}/{sched}')
            break
        rl = B / name / 'run.log'
        lines = rl.read_text(errors='replace').splitlines() if rl.exists() else []
        tail = '\n'.join(lines[-4:])
        cs = B / name / 'run/control-state.json'
        st = json.loads(cs.read_text()) if cs.exists() else {}
        if st.get('stage') is None or (done == 0 and 'Traceback' not in tail and not any(TRIAL.match(l) for l in lines)):
            if crash_relaunch < 2:          # never started (e.g. waiting) or killed before first trial
                crash_relaunch += 1
                launch(name)
                started_wait = time.time()
                continue
        if 'Cohort STOP: paid charge unresolved' in tail and reconciles < 15:
            trials = [m for m in map(TRIAL.match, lines) if m]
            tid = trials[-1].group(3) if trials else None
            atts = sorted((B / name / 'run/trials' / tid / 'attempts').glob('*')) if tid else []
            led = [json.loads(l) for l in (atts[-1] / 'provider.jsonl').read_text().splitlines() if l.strip()] if atts else []
            if led and led[-1].get('error') == 'upstream_response_byte_cap':
                resp = sorted((atts[-1] / 'provider-responses').glob('*'))[-1].read_bytes()[:4000].decode('utf-8', 'replace')
                g = (re.search(r'"id":"(gen-[^"]+)"', resp) or [None, '?'])[1]
                reconciles += 1
                launch(name, '--reconcile-paid-pending', f'{tid} last request aborted by gateway upstream_response_byte_cap (4MB, degenerate repetition); OpenRouter generation {g}: {gen_cost(g)}; settled at reserved upper bound per protocol (supervisor)')
                started_wait = time.time()
                continue
            alert(f'{name}: paid budget stop not caused by byte cap:\n{tail}')
        if 'Existing answer conflicts with persisted final output' in tail and st.get('active_trial') not in conflicts:
            conflicts.add(st.get('active_trial'))
            launch(name)
            started_wait = time.time()
            continue
        if crash_relaunch < 2 and 'Traceback' not in tail:
            crash_relaunch += 1
            log(f'{name}: runner gone without traceback ({done}/{sched}); relaunch #{crash_relaunch}')
            launch(name)
            started_wait = time.time()
            continue
        alert(f'{name}: runner exited {done}/{sched}:\n{tail[-800:]}')
(B / 'SUPERVISOR.DONE').write_text(datetime.now().isoformat() + '\n')
log('ALL RUNS COMPLETE')
