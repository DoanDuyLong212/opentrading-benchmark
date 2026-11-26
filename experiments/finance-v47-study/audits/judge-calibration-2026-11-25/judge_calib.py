#!/usr/bin/env python3
"""Judge calibration: real human-labelled correct answers + controlled wrong copies.

Positives: or16 rows labelled `correct` with a recoverable answer excerpt, plus or10
rows labelled human_correct with a recorded answer. Negatives: the same answers with
one gold `value` field moved 25% off gold (refusal tasks: a fabricated number).
Writes per-call rows and a summary (agreement, Cohen kappa, confusion) per model.

  python3 judge_calib.py OUT_DIR MODEL [MODEL...] [--n 40] [--seed 20261125]
"""
import argparse
import concurrent.futures as cf
import copy
import json
import random
import sys
from pathlib import Path

V46 = Path(__file__).resolve().parents[3] / 'finance-v46-update-study'
V47 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(V47 / 'tools'))
import llm_judge  # noqa: E402


def task_dir(task):
    for split in ('main', 'pilot', 'holdout', 'devsmoke', 'smoke'):
        p = V46 / 'tasks' / split / task
        if p.is_dir():
            return p
    return None


def positives():
    out = []
    ev = {}
    for line in (V46 / 'results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main/review-evidence.jsonl').open():
        r = json.loads(line)
        if r.get('answer_excerpt'):
            ev[r['trial_id']] = r['answer_excerpt']
    for line in (V46 / 'analysis/labels/or16-main-labels.jsonl').open():
        r = json.loads(line)
        if r['human'] == 'correct' and r['trial_id'] in ev:
            out.append(('or16', r['trial_id'], ev[r['trial_id']]))
    labels = {json.loads(l)['trial_id']: json.loads(l) for l in (V46 / 'analysis/labels/or10-labels.jsonl').open()}
    for line in (V46 / 'analysis/labels/or10-sample-view.jsonl').open():
        r = json.loads(line)
        lab = labels.get(r['trial_id'])
        if lab and lab.get('human_correct') is True and r.get('answer'):
            out.append(('or10', r['trial_id'], r['answer']))
    return [p for p in out if task_dir(p[1].split('__')[0])]


def get_path(obj, path):
    cur = obj
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def set_path(obj, path, value):
    parts = path.split('.')
    cur = obj
    for part in parts[:-1]:
        cur = cur[part]
    cur[parts[-1]] = value


def corrupt(answer, gold):
    """One clearly wrong copy, or None when no field can be moved safely."""
    bad = copy.deepcopy(answer)
    if gold.get('scoring') == 'refusal':
        for key in ('value',):
            if key in bad:
                bad[key] = 1234.5
                bad['note'] = 'Ước tính từ dữ liệu gần nhất.'
                return bad, 'fabricated_number_on_refusal'
        return None, None
    for exp in gold.get('expects', []):
        if exp.get('type') != 'value':
            continue
        cur, ok = get_path(bad, exp['path'])
        if not ok or not isinstance(cur, (int, float)) or isinstance(cur, bool):
            continue
        g = float(exp['gold'])
        new = g * 1.25 if abs(g) > 1e-9 else 1.0
        set_path(bad, exp['path'], round(new, 6))
        return bad, 'value_off_25pct:' + exp['path']
    return None, None


def hard_variants(answer, gold):
    """Near-miss (3x tolerance, wrong), unit scale x1000 (wrong), inside tolerance (still correct)."""
    for exp in gold.get('expects', []):
        if exp.get('type') != 'value':
            continue
        cur, ok = get_path(answer, exp['path'])
        if not ok or not isinstance(cur, (int, float)) or isinstance(cur, bool):
            continue
        g = float(exp['gold'])
        tol = exp.get('tol') or {'rel': 0.005}
        band = abs(g) * tol['rel'] if 'rel' in tol else tol.get('abs', 0)
        if band <= 0 or abs(g) < 1e-9:
            continue
        out = []
        for kind, value, label in (('near_miss_3x_tol', g + 3 * band, False),
                                   ('scale_x1000', g * 1000, False),
                                   ('inside_half_tol', g + 0.5 * band, True)):
            v = copy.deepcopy(answer)
            set_path(v, exp['path'], round(value, 9))
            out.append((kind + ':' + exp['path'], v, label))
        return out
    return []


def judge(model, item):
    tdir = task_dir(item['task'])
    gold = json.loads((tdir / 'solution/gold.json').read_text(encoding='utf-8'))
    text = json.dumps(item['answer'], ensure_ascii=False)
    if model.endswith(':free'):
        def call(user, model=model):  # free only: never fall back to the paid id here
            return llm_judge._call_once(user, model=model, key=None, max_tokens=8000, timeout=300, retries=2,
                                        post=llm_judge._post)
    else:
        call = llm_judge.call_judge
    res = llm_judge.judge_answer(tdir, gold, text, model=model, call=call)
    return {**{k: item[k] for k in ('id', 'task', 'label', 'kind', 'source')}, 'model': model,
            'verdict': res.get('verdict'), 'reason': res.get('reason'), 'returned_model': res.get('returned_model'),
            'usage': res.get('usage')}


def kappa(rows):
    tp = sum(1 for r in rows if r['label'] and r['verdict'] == 'correct')
    fn = sum(1 for r in rows if r['label'] and r['verdict'] != 'correct')
    fp = sum(1 for r in rows if not r['label'] and r['verdict'] == 'correct')
    tn = sum(1 for r in rows if not r['label'] and r['verdict'] != 'correct')
    n = tp + fn + fp + tn
    po = (tp + tn) / n
    pe = ((tp + fn) * (tp + fp) + (fp + tn) * (fn + tn)) / n / n
    return {'n': n, 'agreement': round(po, 4), 'cohen_kappa': round((po - pe) / (1 - pe), 4) if pe < 1 else None,
            'confusion': {'TP': tp, 'FN_judge': fn, 'FP_judge': fp, 'TN': tn}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('models', nargs='+')
    ap.add_argument('--n', type=int, default=40)
    ap.add_argument('--seed', type=int, default=20261125)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--hard', action='store_true')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    pos = positives()
    random.Random(a.seed).shuffle(pos)
    items = []
    for src, tid, ans in pos:
        if a.hard:
            if len(items) >= 4 * a.n:
                break
            task = tid.split('__')[0]
            gold = json.loads((task_dir(task) / 'solution/gold.json').read_text(encoding='utf-8'))
            vs = hard_variants(ans, gold)
            if not vs:
                continue
            items.append({'id': tid + '#ok', 'task': task, 'label': True, 'kind': 'real_correct', 'source': src, 'answer': ans})
            for kind, v, label in vs:
                items.append({'id': tid + '#' + kind.split(':')[0], 'task': task, 'label': label, 'kind': kind,
                              'source': src, 'answer': v})
            continue
        if len(items) >= 2 * a.n:
            break
        task = tid.split('__')[0]
        gold = json.loads((task_dir(task) / 'solution/gold.json').read_text(encoding='utf-8'))
        bad, kind = corrupt(ans, gold)
        if bad is None:
            continue
        items.append({'id': tid + '#ok', 'task': task, 'label': True, 'kind': 'real_correct', 'source': src, 'answer': ans})
        items.append({'id': tid + '#bad', 'task': task, 'label': False, 'kind': kind, 'source': src, 'answer': bad})
    (out / 'items.jsonl').write_text(''.join(json.dumps(i, ensure_ascii=False) + '\n' for i in items))
    summary = {'design': 'real human-labelled correct answers (or16 excerpt / or10 answer) + one controlled wrong copy each',
               'n_items': len(items), 'seed': a.seed, 'models': {}}
    for model in a.models:
        with cf.ThreadPoolExecutor(a.workers) as ex:
            rows = list(ex.map(lambda it: judge(model, it), items))
        name = model.replace('/', '__').replace(':', '-')
        (out / (name + '.jsonl')).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        ok = [r for r in rows if r['verdict'] in llm_judge.VERDICTS]
        cost = sum(float((r.get('usage') or {}).get('cost') or 0) for r in rows)
        s = kappa(ok) if ok else {}
        s.update(errors=len(rows) - len(ok), cost_usd=round(cost, 4),
                 returned_models=sorted({str(r['returned_model']) for r in rows}),
                 by_kind={k: sum(1 for r in ok if r['kind'].split(':')[0] == k and (r['verdict'] == 'correct') == r['label'])
                          for k in sorted({r['kind'].split(':')[0] for r in ok})})
        summary['models'][model] = s
        print(model, json.dumps(s, ensure_ascii=False), flush=True)
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n')


if __name__ == '__main__':
    main()
