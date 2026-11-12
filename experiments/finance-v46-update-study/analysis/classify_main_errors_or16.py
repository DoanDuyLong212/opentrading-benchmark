#!/usr/bin/env python3
"""Error taxonomy for the merged or16 main (report only; never changes any verdict).

Every trial that is NOT primary-correct gets exactly one class (first match wins):
  dnf_token_cap      no final answer, output hit the 8192 max_output_tokens cap
  dnf_request_cap    no final answer, 24-request cap (Lỗi 424 upstream_attempt_cap_exceeded)
  dnf_infra          no final answer, provider/transport failure
  dnf_other          no final answer, other
  no_answer_object   final text has no answer object (e.g. raw tool-call markup)
  false_refusal_memory  value null on an answerable memory task (agent did not recall the stored criteria/portfolio)
  false_refusal_other   value null on another answerable task
  sign_convention    numeric gate fails only on sign (|answer| within tolerance of |gold|)
  rounding           numeric gate fails, every failing value within 10x its tolerance
  wrong_selection    set / symbol / winner field wrong (screen, rank, rule)
  wrong_quantity     numeric field wrong (wrong formula, field meaning, unit)
  judge_only         numeric gate passes, judge partial/incorrect (period/unit/source wording ...)
  manual_rejected    removed by the all-arm review
Writes analysis/out/or16-main-errors.json (per trial + counts per arm/class).

  python3 analysis/classify_main_errors_or16.py
"""
import collections, glob, json, subprocess, sys, tempfile
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from grade_run_llm import graded_attempt_text  # noqa: E402
from llm_judge import extract_answer_object  # noqa: E402

P = STUDY / 'results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main'
OUT = STUDY / 'analysis/out/or16-main-errors.json'


def jl(p):
    return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]


def get(obj, path):
    for k in path.split('.'):
        obj = obj.get(k) if isinstance(obj, dict) else None
    return obj


def regrade(task, obj):
    tdir = STUDY / 'tasks/main' / task
    with tempfile.TemporaryDirectory() as d:
        a, o = Path(d) / 'a.json', Path(d) / 'g.json'
        a.write_text(json.dumps(obj, ensure_ascii=False))
        subprocess.run([sys.executable, str(tdir / 'tests/grader.py'), str(a), '-g', str(tdir / 'solution/gold.json'),
                        '-o', str(o)], capture_output=True)
        return json.loads(o.read_text()) if o.is_file() else {}


def run_log(tid):
    return ''.join(Path(f).read_text(errors='replace') for f in glob.glob(str(P / 'trials' / tid / 'attempts/*/run.log')))


def classify(rec, row, text, gold):
    if rec['manual_rejected']:
        return 'manual_rejected', ''
    if rec['dnf']:
        tk = row.get('tokens') or {}
        log = run_log(rec['trial_id'])
        if 'upstream_attempt_cap_exceeded' in log or (row.get('requests') or 0) > 24:
            return 'dnf_request_cap', 'requests=%s' % row.get('requests')
        if (tk.get('output') or 0) >= 8192:
            return 'dnf_token_cap', 'output=%s requests=%s' % (tk.get('output'), row.get('requests'))
        if rec['dnf_infra'] or not tk:
            return 'dnf_infra', 'requests=%s usage=%s' % (row.get('requests'), bool(tk))
        return 'dnf_other', ''
    obj = extract_answer_object(text)
    if not isinstance(obj, dict):
        return 'no_answer_object', text.strip()[:80]
    if rec['false_refusal']:
        return ('false_refusal_memory' if rec['stratum'] == 'memory' else 'false_refusal_other'), str(obj.get('reason'))[:120]
    if gold.get('scoring') == 'refusal':
        return 'wrong_selection', 'refusal trap answered'
    g = regrade(rec['task'], obj)
    fails = [c for c in g.get('checks', []) if not c.get('pass', True)]
    exp = {('%s:%s' % (e['type'], e['path'])): e for e in gold.get('expects', [])}
    vfail = [exp[c['check']] for c in fails if c['check'] in exp and exp[c['check']]['type'] == 'value']
    sfail = [exp[c['check']] for c in fails if c['check'] in exp and exp[c['check']]['type'] in ('set', 'tokens')]
    if rec['numeric_gate'] is False or vfail:
        def tol(e):
            t = e.get('tol', {})
            return t.get('abs', abs(e['gold']) * t.get('rel', 0))
        def num(e):
            try:
                return float(get(obj, e['path']))
            except (TypeError, ValueError):
                return None
        vals = [(e, num(e)) for e in vfail]
        if vals and all(v is not None and abs(abs(v) - abs(e['gold'])) <= tol(e) for e, v in vals) and not sfail:
            return 'sign_convention', '; '.join('%s=%s gold=%s' % (e['path'], v, e['gold']) for e, v in vals)
        if vals and all(v is not None and abs(v - e['gold']) <= 10 * tol(e) for e, v in vals) and not sfail:
            return 'rounding', '; '.join('%s=%s gold=%s tol=%s' % (e['path'], v, e['gold'], e.get('tol')) for e, v in vals)
    if sfail:
        return 'wrong_selection', '; '.join('%s=%s' % (e['path'], get(obj, e['path'])) for e in sfail)
    if vfail or rec['numeric_gate'] is False:
        return 'wrong_quantity', '; '.join('%s=%s gold=%s' % (e['path'], get(obj, e['path']), e['gold']) for e in vfail)[:300]
    return 'judge_only', 'judge=%s' % rec['judge_verdict']


def main():
    rows = {r['trial_id']: r for r in jl(P / 'trials.jsonl')}
    recs = jl(P / 'judge-primary.jsonl')
    out, counts = [], collections.defaultdict(collections.Counter)
    for rec in recs:
        if rec['primary']:
            continue
        row = rows[rec['trial_id']]
        gold = json.loads((STUDY / 'tasks/main' / rec['task'] / 'solution/gold.json').read_text())
        text = graded_attempt_text(P, row)[0] or ''
        cls, detail = classify(rec, row, text, gold)
        out.append({'trial_id': rec['trial_id'], 'arm': rec['arm'], 'task': rec['task'], 'stratum': rec['stratum'],
                    'tier': rec['tier'], 'judge': rec['judge_verdict'], 'class': cls, 'detail': detail})
        counts[rec['arm']][cls] += 1
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'run': str(P), 'counts': counts, 'trials': out}, ensure_ascii=False, indent=1))
    print(json.dumps(counts, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
