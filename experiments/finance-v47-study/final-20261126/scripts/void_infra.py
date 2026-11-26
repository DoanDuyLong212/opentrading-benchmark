"""Final-sweep voiding for one run dir (pre-registered rules, outcome-blind):
  transport : terminal provider row error_origin == upstream_transport
  infra-cap : terminal upstream_attempt_cap_exceeded and (attempts - failed transport) < cap
  infra-tok : terminal local_token_budget_exhausted, had failed transport, and usage + 1 reservation <= 4.6M tokens
Voided rows -> trials-voided-sweep.jsonl, dirs -> trials-voided-sweep/<id>; receipt VOID-SWEEP-<n>.json.
Usage: python3 void_infra.py RUN_DIR [--apply]   (prints count)
"""
import ast
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


def rows_of(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def usage_tokens(rows):
    t = 0
    for x in rows:
        u = x.get('usage')
        if isinstance(u, str):
            try:
                u = ast.literal_eval(u)
            except Exception:
                u = None
        if isinstance(u, dict):
            t += u.get('total_tokens') or 0
    return t


def reason(run, row):
    atts = sorted((run / 'trials' / row['trial_id'] / 'attempts').glob('*'))
    if not atts:
        return None
    led = rows_of(atts[-1] / 'provider.jsonl')
    if not led:
        return None
    last = led[-1]
    tf = [x for x in led if x.get('error_origin') == 'upstream_transport']
    if last.get('error_origin') == 'upstream_transport':
        return 'transport'
    if last.get('error') == 'upstream_attempt_cap_exceeded' and tf:
        cap = 48 if row['task'].startswith(('fin-m', 'fin-i5')) else 24
        if sum(1 for x in led if str(x.get('upstream_attempted')) == 'True') - len(tf) < cap:
            return 'infra-cap'
    if last.get('error') == 'local_token_budget_exhausted' and tf and usage_tokens(led) + 1441792 <= 4600000:
        return 'infra-tok'
    return None


def main(run, apply):
    run = Path(run).resolve()
    tpath = run / 'trials.jsonl'
    raw = tpath.read_bytes()
    lines = [l for l in raw.decode().splitlines() if l.strip()]
    keep, void = [], []
    for l in lines:
        r = json.loads(l)
        why = reason(run, r) if r.get('status') != 'ok' else None
        (void if why else keep).append((l, r, why))
    print(len(void))
    if not apply or not void:
        return
    n = 1
    while (run / f'VOID-SWEEP-{n}.json').exists():
        n += 1
    with open(run / 'trials-voided-sweep.jsonl', 'a') as fh:
        fh.write(''.join(l + '\n' for l, _, _ in void))
    dest = run / 'trials-voided-sweep'
    dest.mkdir(exist_ok=True)
    for _, r, _ in void:
        src = run / 'trials' / r['trial_id']
        target = dest / f"{r['trial_id']}.{n}"
        if src.exists():
            shutil.move(str(src), str(target))
    tmp = run / 'trials.jsonl.tmp-sweep'
    tmp.write_text(''.join(l + '\n' for l, _, _ in keep))
    os.replace(tmp, tpath)
    (run / f'VOID-SWEEP-{n}.json').write_text(json.dumps({
        'trials_jsonl_sha256_before': hashlib.sha256(raw).hexdigest(),
        'trials_jsonl_sha256_after': hashlib.sha256(tpath.read_bytes()).hexdigest(),
        'voided': [{'trial_id': r['trial_id'], 'reason': why} for _, r, why in void]}, indent=1))


if __name__ == '__main__':
    main(sys.argv[1], '--apply' in sys.argv[2:])
