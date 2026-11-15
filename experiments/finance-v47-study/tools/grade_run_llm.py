#!/usr/bin/env python3
"""Secondary LLM-judge grading for one completed run directory.

Reads trials.jsonl, picks the final text of the attempt the driver actually graded,
judges it with tools/llm_judge.py (OpenRouter Nemotron Ultra) and writes, next to
the sealed artifacts (never modifying them):

  llm-graded.jsonl           one row per trial (append-only; --resume skips done rows)
  llm-judge-cache.jsonl      sha256(model+prompt) -> verdict, reused across reruns
  llm-disagreements.jsonl    sealed grader vs judge disagreements for manual review
  llm-graded-summary.json    verdict counts per arm, grader x judge matrix, usage/cost

Rules: the judge is diagnostic. A sealed failure is never rescued; a sealed pass that
the judge rejects is only flagged. Trials without any final text are recorded as
`no_answer` without a model call.

  python3 tools/grade_run_llm.py RUN_DIR [--limit N] [--resume] [--pause 0.5]
"""
import argparse
import collections
import json
import sys
import time
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import llm_judge  # noqa: E402

SPLITS = ('devsmoke', 'pilot', 'main', 'holdout', 'smoke', 'memorydev')


def task_dir(task):
    for split in SPLITS:
        p = STUDY / 'tasks' / split / task
        if p.is_dir():
            return p
    raise FileNotFoundError('task not found in study corpus: ' + task)


def graded_attempt_text(run, row):
    """Final text of the attempt the driver graded (row['attempt']), else the driver answer file."""
    attempts = sorted((run / 'trials' / row['trial_id'] / 'attempts').glob('*/result.json'))
    wanted = row.get('attempt')
    chosen = None
    for path in attempts:
        prefix = path.parent.name.split('-', 1)[0]
        if prefix.isdigit() and wanted is not None and int(prefix) == int(wanted):
            chosen = path
    if chosen is None and attempts:
        chosen = attempts[-1]
    if chosen is not None:
        text = json.loads(chosen.read_text()).get('final_text')
        if text:
            return text, str(chosen.parent.name)
    answer = row.get('answer_path')
    if answer and Path(answer).is_file():
        return Path(answer).read_text(encoding='utf-8'), 'answer_path'
    return '', None


def load_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def grade_run(run_dir, *, limit=None, resume=False, pause=0.5, call=llm_judge.call_judge):
    run = Path(run_dir).resolve()
    rows = load_jsonl(run / 'trials.jsonl')
    out_path = run / 'llm-graded.jsonl'
    cache_path = run / 'llm-judge-cache.jsonl'
    cache = {r['cache_key']: r['result'] for r in load_jsonl(cache_path)}
    done = {r['trial_id'] for r in load_jsonl(out_path)} if resume else set()
    if not resume and out_path.exists():
        out_path.unlink()
    judged = 0
    manifest = run / 'manifest.json'
    split = (json.loads(manifest.read_text()).get('plan', {}).get('settings', {}).get('split') if manifest.is_file() else None)
    if split == 'holdout' and call is llm_judge.call_judge:
        def call(user, model=llm_judge.JUDGE_MODEL):
            return llm_judge.call_judge(user, model=model, deny_data_collection=True)
    with out_path.open('a') as out, cache_path.open('a') as cache_out:
        for i, row in enumerate(rows):
            if row['trial_id'] in done:
                continue
            if limit is not None and judged >= limit:
                break
            tdir = task_dir(row['task'])
            gold = json.loads((tdir / 'solution/gold.json').read_text(encoding='utf-8'))
            text, attempt = graded_attempt_text(run, row)
            if not text.strip():
                verdict = {'verdict': 'no_answer', 'reason': 'no final text', 'failed_fields': [],
                           'numeric_prepass': None, 'cached': False, 'usage': {}}
            else:
                before = set(cache)
                verdict = llm_judge.judge_answer(tdir, gold, text, cache=cache, call=call)
                for key in set(cache) - before:
                    cache_out.write(json.dumps({'cache_key': key, 'result': cache[key]}, ensure_ascii=False) + '\n')
                    cache_out.flush()
                if not verdict.get('cached'):
                    time.sleep(pause)
            content = row.get('grounded_financial_correctness')
            if content is None:
                content = row.get('semantic_correctness')
            rec = {'trial_id': row['trial_id'], 'arm': row['arm'], 'task': row['task'], 'run': row.get('run'),
                   'scoring': gold.get('scoring'), 'graded_attempt': attempt,
                   'sealed_success': bool(row.get('success')), 'sealed_error': row.get('error_type'),
                   'sealed_content_correct': None if content is None else bool(content),
                   'sealed_semantic_correctness': row.get('semantic_correctness'),
                   **verdict}
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            out.flush()
            judged += 1
            print('[%d/%d] %-46s sealed=%-5s judge=%s%s' % (
                i + 1, len(rows), row['trial_id'][:46], rec['sealed_success'], rec['verdict'],
                ' (cached)' if rec.get('cached') else ''), flush=True)
    return summarize(run)


def _record(row, gold, attempt, verdict):
    content = row.get('grounded_financial_correctness')
    if content is None:
        content = row.get('semantic_correctness')
    return {'trial_id': row['trial_id'], 'arm': row['arm'], 'task': row['task'], 'run': row.get('run'),
            'scoring': gold.get('scoring'), 'graded_attempt': attempt,
            'sealed_success': bool(row.get('success')), 'sealed_error': row.get('error_type'),
            'sealed_content_correct': None if content is None else bool(content),
            'sealed_semantic_correctness': row.get('semantic_correctness'), **verdict}


def scheduled_count(run):
    manifest = run / 'manifest.json'
    return len(json.loads(manifest.read_text())['plan']['schedule']) if manifest.is_file() else None


def grade_run_batched(run_dir, *, batch=5, follow=False, out_name='llm-graded.jsonl', only=None, poll=120,
                      call=llm_judge.call_judge):
    """User 2026-11-11: several trials per judge request; --follow grades a running cohort as trials land
    (waits for full batches, flushes the remainder when the schedule is complete). Resumable by trial id."""
    run = Path(run_dir).resolve()
    out_path = run / out_name
    cache_path = run / 'llm-judge-cache.jsonl'
    cache = {r['cache_key']: r['result'] for r in load_jsonl(cache_path)}
    split = (json.loads((run / 'manifest.json').read_text()).get('plan', {}).get('settings', {}).get('split')
             if (run / 'manifest.json').is_file() else None)
    if split == 'holdout':
        base = call
        def call(user, **kw):
            return base(user, deny_data_collection=True, **kw)
    while True:
        rows = load_jsonl(run / 'trials.jsonl')
        if only is not None:
            rows = [r for r in rows if r['trial_id'] in only]
        done = {r['trial_id'] for r in load_jsonl(out_path)}
        pending = [r for r in rows if r['trial_id'] not in done]
        total = len(only) if only is not None else scheduled_count(run)
        complete = (not follow) or (total is not None and len(rows) >= total)
        if not pending and complete:
            break
        if len(pending) < batch and not complete:
            time.sleep(poll)
            continue
        group = pending[:batch]
        items, meta = [], {}
        with out_path.open('a') as out:
            for row in group:
                tdir = task_dir(row['task'])
                gold = json.loads((tdir / 'solution/gold.json').read_text(encoding='utf-8'))
                text, attempt = graded_attempt_text(run, row)
                meta[row['trial_id']] = (row, gold, attempt, text)
                if not text.strip():
                    rec = _record(row, gold, attempt, {'verdict': 'no_answer', 'reason': 'no final text', 'failed_fields': [],
                                                        'numeric_prepass': None, 'cached': False, 'usage': {}})
                    out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                else:
                    items.append((row['trial_id'], tdir, gold, text))
            if items:
                before = set(cache)
                results = llm_judge.judge_batch(items, cache=cache, call=call)
                with cache_path.open('a') as cache_out:
                    for key in set(cache) - before:
                        cache_out.write(json.dumps({'cache_key': key, 'result': cache[key]}, ensure_ascii=False) + '\n')
                for iid, *_ in items:
                    row, gold, attempt, _t = meta[iid]
                    rec = _record(row, gold, attempt, results[iid])
                    out.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    print('%-48s sealed=%-5s judge=%s (%s)' % (iid[:48], rec['sealed_success'], rec['verdict'], rec.get('mode', 'cached' if rec.get('cached') else '')), flush=True)
            out.flush()
    return None


def content_label(r):
    """Content-level sealed label (grounded financial correctness, else semantic, else strict)."""
    value = r.get('sealed_content_correct')
    return r['sealed_success'] if value is None else value


def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    po = sum(a == b for a, b in pairs) / n
    pa, pb = sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return None if pe == 1 else round((po - pe) / (1 - pe), 4)


def summarize(run):
    recs = load_jsonl(run / 'llm-graded.jsonl')
    matrix = collections.Counter((content_label(r), r['verdict']) for r in recs)
    strict = collections.Counter((r['sealed_success'], r['verdict']) for r in recs)
    per_arm = collections.defaultdict(collections.Counter)
    for r in recs:
        per_arm[r['arm']][r['verdict']] += 1
    judged = [r for r in recs if r['verdict'] in llm_judge.VERDICTS]
    pairs = [(bool(content_label(r)), r['verdict'] == 'correct') for r in judged]
    disagreements = [dict(r, disagreement='content_pass_judge_not_correct' if content_label(r)
                          else 'content_fail_judge_correct')
                     for r in judged if bool(content_label(r)) != (r['verdict'] == 'correct')]
    (run / 'llm-disagreements.jsonl').write_text(
        ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in disagreements))
    usage = collections.Counter()
    cost = 0.0
    for r in recs:
        if r.get('cached'):
            continue
        u = r.get('usage') or {}
        if not u and r.get('usage_batch') and r.get('batch_size'):
            # batched judging: each item carries the whole request's usage; attribute an equal share
            u = {k: v / r['batch_size'] for k, v in r['usage_batch'].items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
            usage[k] += u.get(k) or 0
        cost += u['cost'] if isinstance(u.get('cost'), (int, float)) else llm_judge.usage_cost(u)
    models = collections.Counter(r.get('returned_model') for r in recs if r.get('returned_model'))
    summary = {
        'run': str(run), 'trials': len(recs), 'judge_model_requested': llm_judge.JUDGE_MODEL,
        'judge_models_returned': dict(models), 'role': 'secondary diagnostic; never rescues sealed failures',
        'verdicts': dict(collections.Counter(r['verdict'] for r in recs)),
        'per_arm': {a: dict(c) for a, c in sorted(per_arm.items())},
        'comparison_label': 'sealed grounded_financial_correctness (else semantic_correctness, else strict success)',
        'sealed_content_x_judge': {'%s|%s' % ('pass' if k[0] else 'fail', k[1]): v for k, v in sorted(matrix.items(), key=str)},
        'sealed_strict_x_judge': {'%s|%s' % ('pass' if k[0] else 'fail', k[1]): v for k, v in sorted(strict.items(), key=str)},
        'judged_trials': len(judged),
        'agreement_rate_content': round(sum(a == b for a, b in pairs) / len(pairs), 4) if pairs else None,
        'cohen_kappa_content': kappa(pairs),
        'disagreements': {'content_pass_judge_not_correct': sum(1 for r in disagreements if content_label(r)),
                          'content_fail_judge_correct': sum(1 for r in disagreements if not content_label(r)),
                          'by_sealed_error_type': dict(collections.Counter(r.get('sealed_error') for r in disagreements)),
                          'file': 'llm-disagreements.jsonl (manual review required; triage only)'},
        'numeric_prepass_vs_judge': dict(collections.Counter(
            '%s|%s' % (r['numeric_prepass']['all_ok'], r['verdict']) for r in recs
            if isinstance(r.get('numeric_prepass'), dict))),
        'judge_usage_uncached': dict(usage),
        'judge_cost_usd_estimate': round(cost, 4),
        'price_per_1m': llm_judge.PRICE_PER_1M,
    }
    (run / 'llm-graded-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_dir')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--pause', type=float, default=0.5)
    ap.add_argument('--batch', type=int, help='trials per judge request (batched mode)')
    ap.add_argument('--follow', action='store_true', help='batched: keep grading a running cohort until complete')
    ap.add_argument('--out', default='llm-graded.jsonl', help='batched: output file name inside the run dir')
    ap.add_argument('--only', help='batched: file with one trial_id per line to grade')
    a = ap.parse_args()
    if a.batch:
        only = set(Path(a.only).read_text().split()) if a.only else None
        grade_run_batched(a.run_dir, batch=a.batch, follow=a.follow, out_name=a.out, only=only)
    else:
        grade_run(a.run_dir, limit=a.limit, resume=a.resume, pause=a.pause)


if __name__ == '__main__':
    main()
