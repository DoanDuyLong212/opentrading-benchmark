#!/usr/bin/env python3
"""Batched judge over the NVIDIA API (integrate.api.nvidia.com) with the same judge model, prompts, parser and cache
as tools/grade_run_llm.py (user 2026-11-11: "sử dụng chấm thay thế bằng key nvidia ... model nemotron-3-ultra-550b-a55b").

Why: the OpenRouter free Ultra endpoint started returning empty 1-token completions (HTTP 200) and its daily free
quota (1000) is nearly used; paid fallback would draw on the key reserved for the holdout.
Only the transport changes (URL + key + model id without ':free'); tools/ stays untouched (frozen by the or16 seal).
The key is read from opencode's auth.json and never printed. Holdout is refused: holdout gold goes only through the
registered OpenRouter paid route with data_collection=deny.

Usage: same flags as tools/grade_run_llm.py batched mode (--batch N [--follow] [--out F] [--only FILE]).
"""
import json, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import llm_judge  # noqa: E402
import grade_run_llm  # noqa: E402

NIM_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
NIM_MODEL = 'nvidia/nemotron-3-ultra-550b-a55b'
RETRIES = 11
AUTH = Path.home() / '.local/share/opencode/auth.json'


def nim_key():
    return json.loads(AUTH.read_text())['nvidia']['key']


def or_deny_call(user, model=None, **kw):
    """Holdout route (registered): OpenRouter paid Ultra id, provider data_collection=deny, same retry budget."""
    kw.setdefault('retries', RETRIES)
    kw['deny_data_collection'] = True
    return llm_judge.call_judge(user, model=llm_judge.JUDGE_MODEL_PAID, **kw)


FREE_RESERVE = 5          # keep this many OpenRouter free requests unused
FREE_RETRIES = 3


def free_remaining():
    import urllib.request
    req = urllib.request.Request('https://openrouter.ai/api/v1/key',
                                 headers={'Authorization': 'Bearer ' + llm_judge.openrouter_key()})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())['data']
    return (data.get('free_model_daily_requests') or {}).get('remaining', 0)


def or_free_call(user, model=None, **kw):
    """Main only: OpenRouter ':free' Ultra with NO paid fallback (the paid key budget is reserved for the holdout).
    Stops the worker before the daily free quota drops below FREE_RESERVE."""
    if kw.get('deny_data_collection'):
        raise SystemExit('holdout must use the OpenRouter paid deny route')
    retries = min(kw.get('retries', FREE_RETRIES), FREE_RETRIES)
    if free_remaining() < retries + 1 + FREE_RESERVE:
        raise SystemExit('OpenRouter free quota nearly used; stopping free worker')
    res = llm_judge._call_once(user, model=llm_judge.JUDGE_MODEL_PAID + ':free', key=None, max_tokens=8000,
                               timeout=kw.get('timeout', 120), retries=retries, post=llm_judge._post,
                               system=kw.get('system'), parser=kw.get('parser'))
    res['judge_route'] = 'openrouter-free'
    return res


def nim_call(user, model=None, **kw):
    if kw.get('deny_data_collection'):
        raise SystemExit('holdout must use the OpenRouter paid deny route')
    # The Ultra backend (same one behind OpenRouter's free route) returns an empty 1-11 token completion in ~50% of
    # calls, independent of prompt (measured 2026-11-11); empty replies come back in ~1 s, so retry more.
    kw.setdefault('retries', RETRIES)
    kw.setdefault('timeout', 120)   # NIM occasionally hangs a request; 300 s x 12 tries stalled the queue
    import time
    for wait in (120, 300, 600):     # NVIDIA rate limit: outer back-off beyond _call_once's own retries
        res = llm_judge.call_judge(user, model=NIM_MODEL, **kw)
        if not (res.get('verdict') == 'judge_error' and res.get('reason') == 'http_429'):
            break
        print('nim http_429: waiting %ds' % wait, flush=True)
        time.sleep(wait)
    res['provider'] = 'nvidia-nim'
    res['judge_route'] = 'nvidia-nim'
    return res


_judge_batch = llm_judge.judge_batch


def judge_batch_confirmed(items, *, cache=None, model=llm_judge.JUDGE_MODEL, call=llm_judge.call_judge):
    """Amendment (i) 2026-11-11: a batched reply can attach one item's verdict to another id (or16r: XYZA answers
    judged with a QWER9 reason). Every batch verdict other than 'correct' is re-judged alone with the single-item
    prompt and the single verdict is final; the batch verdict is kept for audit. Same rule for every arm."""
    out = _judge_batch(items, cache=cache, model=model, call=call)
    for iid, tdir, gold, text in items:
        r = out[iid]
        if r.get('mode') == 'batch' and r.get('verdict') != 'correct':
            single = llm_judge.judge_answer(tdir, gold, text, cache=cache, model=model,
                                            call=lambda u, model=model: call(u, model=model))
            if single.get('verdict') not in llm_judge.VERDICTS:
                out[iid] = dict(r, confirm_failed=single.get('reason'))   # no usable single verdict: batch stands
                continue
            out[iid] = dict(single, mode='single_confirm', batch_verdict=r.get('verdict'),
                            batch_reason=r.get('reason'), batch_failed_fields=r.get('failed_fields'))
    return out


def confirm_existing(run, graded_name, call=None):
    call = call or nim_call
    src = run / graded_name
    out_path = run / (Path(graded_name).stem + '-confirm.jsonl')
    done = {r['trial_id'] for r in grade_run_llm.load_jsonl(out_path)}
    cache_path = run / 'llm-judge-cache.jsonl'
    cache = {r['cache_key']: r['result'] for r in grade_run_llm.load_jsonl(cache_path)}
    rows = {r['trial_id']: r for r in grade_run_llm.load_jsonl(run / 'trials.jsonl')}
    todo = [g for g in grade_run_llm.load_jsonl(src)
            if g.get('mode') == 'batch' and g.get('verdict') != 'correct' and g['trial_id'] not in done]
    for g in todo:
        row = rows[g['trial_id']]
        tdir = grade_run_llm.task_dir(row['task'])
        gold = json.loads((tdir / 'solution/gold.json').read_text(encoding='utf-8'))
        text, attempt = grade_run_llm.graded_attempt_text(run, row)
        before = set(cache)
        single = llm_judge.judge_answer(tdir, gold, text, cache=cache, call=call)
        if single.get('verdict') not in llm_judge.VERDICTS:   # no usable single verdict: batch stands, retry later
            print('%-48s batch=%s single=%s (kept batch)' % (g['trial_id'][:48], g['verdict'], single.get('verdict')))
            continue
        with cache_path.open('a') as c:
            for key in set(cache) - before:
                c.write(json.dumps({'cache_key': key, 'result': cache[key]}, ensure_ascii=False) + '\n')
        rec = grade_run_llm._record(row, gold, attempt, dict(single, mode='single_confirm', batch_verdict=g['verdict'],
                                                               batch_reason=g.get('reason'),
                                                               batch_failed_fields=g.get('failed_fields')))
        with out_path.open('a') as o:
            o.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print('%-48s batch=%s single=%s' % (g['trial_id'][:48], g['verdict'], rec['verdict']), flush=True)


def main():
    ap = grade_run_llm.argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--batch', type=int, default=5)
    ap.add_argument('--follow', action='store_true')
    ap.add_argument('--out', default='llm-graded.jsonl')
    ap.add_argument('--only')
    ap.add_argument('--route', choices=('nim', 'openrouter-deny', 'openrouter-free'), default='nim',
                    help='nim: NVIDIA API (main only); openrouter-deny: OpenRouter paid id with data_collection=deny '
                         '(the only route allowed for holdout)')
    ap.add_argument('--confirm-existing', metavar='GRADED',
                    help='amendment (i) post-pass: re-judge alone every non-correct batch verdict already in GRADED '
                         '(file name in the run dir); writes <GRADED stem>-confirm.jsonl')
    a = ap.parse_args()
    run = Path(a.run_dir).resolve()
    split = json.loads((run / 'manifest.json').read_text())['plan']['settings']['split']
    if split == 'holdout' and a.route != 'openrouter-deny':
        raise SystemExit('refused: holdout is judged only via the OpenRouter paid deny route (--route openrouter-deny)')
    llm_judge.judge_batch = judge_batch_confirmed      # amendment (i), every route
    if a.route == 'openrouter-free':
        if split != 'main':
            raise SystemExit('openrouter-free is for main only')
        call = or_free_call
    elif a.route == 'nim':
        llm_judge.OPENROUTER_URL = NIM_URL          # _post reads the module global at call time
        llm_judge.openrouter_key = nim_key
        call = nim_call
    else:
        call = or_deny_call
    if a.confirm_existing:
        return confirm_existing(run, a.confirm_existing, call=call)
    only = set(Path(a.only).read_text().split()) if a.only else None
    grade_run_llm.grade_run_batched(run, batch=a.batch, follow=a.follow, out_name=a.out, only=only, call=call)


if __name__ == '__main__':
    main()
