#!/usr/bin/env python3
"""Judge-primary financial correctness (amendment 2026-11-10, user-approved flow).

Primary per trial = judge "correct"
                    AND deterministic numeric gate (every value field within the gold tolerance)
                    AND rule-based anti-fabrication (no numeric value on a refusal trap)
                    AND not rejected by the independent manual review (review may only REMOVE).
Refusal traps: FP / correct refusal decided by rule (value null), never by the judge alone.
Answerable tasks: false refusal = answer with value null / refusal branch (rule).
Denominator = every scheduled trial; DNF (no final answer) stays in it, split infra vs other.

Sealed in tools/ by the B0 main amendment (2026-11-10).

  python3 tools/judge_primary.py RUN_DIR [--baseline opentrading_baseline] [--draws 2000]
"""
import argparse
import collections
import glob
import json
import random
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from llm_judge import extract_answer_object, numeric_prepass  # noqa: E402

SPLITS = ('devsmoke', 'pilot', 'main', 'holdout', 'smoke', 'memorydev')
NUM = re.compile(r'(?<![\w.])-?\d[\d,]*(?:\.\d+)?')


def task_gold(task):
    for split in SPLITS:
        p = STUDY / 'tasks' / split / task / 'solution/gold.json'
        if p.is_file():
            return json.loads(p.read_text(encoding='utf-8'))
    raise FileNotFoundError(task)


def text_numbers(text):
    out = []
    for m in NUM.findall(text or ''):
        try:
            out.append(float(m.replace(',', '')))
        except ValueError:
            pass
    return out


def numeric_gate(answer_text, gold):
    """True/False for value tasks; True when the task has no value fields."""
    specs = [e for e in gold.get('expects', []) if e.get('type') == 'value']
    if not specs:
        return True
    pre = numeric_prepass(answer_text, gold)
    if pre and pre['parsed']:
        return pre['all_ok']
    # Format-agnostic fallback: every gold number must appear in the text within tolerance.
    nums = text_numbers(answer_text)
    for e in specs:
        tol = e.get('tol') or {'rel': 0.005}
        g = float(e['gold'])
        bound = abs(g) * tol['rel'] if 'rel' in tol else tol.get('abs', 0)
        if not any(abs(x - g) <= bound + 1e-9 for x in nums):
            return False
    return True


def refusal_shape(answer_text):
    """'null' when the answer declares value null, 'number' when it asserts a numeric value, else None."""
    obj = extract_answer_object(answer_text)
    if obj is None or 'value' not in obj:
        return None
    v = obj['value']
    if v is None:
        return 'null'
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return 'number'
    if isinstance(v, str) and text_numbers(v):
        return 'number'
    return None


def infra_failure(run, trial_id):
    for log in glob.glob(str(run / 'trials' / trial_id / 'attempts' / '*' / 'run.log')):
        text = Path(log).read_text(errors='replace')
        if any(s in text for s in ('provider_transport_failure', 'upstream_transport', 'URLError', 'Lỗi 424')):
            return True
    return False


def score_trial(row, graded, gold, review, run):
    scoring = gold.get('scoring')
    text = graded.get('_answer_text', '')
    verdict = graded.get('verdict')
    dnf = row.get('status') != 'ok' or verdict == 'no_answer' or not text.strip()
    rec = {'trial_id': row['trial_id'], 'arm': row['arm'], 'task': row['task'], 'run': row.get('run'),
           'scoring': scoring, 'judge_verdict': verdict, 'strict_success': bool(row.get('success')),
           'raw_format_valid': bool(row.get('public_contract_valid')), 'dnf': dnf,
           'dnf_infra': bool(dnf and infra_failure(run, row['trial_id'])),
           'fp': False, 'false_refusal': False, 'numeric_gate': None, 'manual_rejected': False,
           # amendment 2026-11-11 (d): strata are reported separately (core is the unbiased comparison)
           'stratum': gold.get('stratum', 'core'), 'tier': gold.get('subtier', gold.get('tier'))}
    decision = (review or {}).get(row['trial_id'])
    rec['manual_rejected'] = bool(decision and decision.get('pass') is False)
    if dnf:
        rec['primary'] = False
        return rec
    shape = refusal_shape(text)
    if scoring == 'refusal':
        rec['fp'] = shape == 'number' or bool(row.get('fp'))
        ok = (verdict == 'correct') and not rec['fp'] and shape != 'number'
    else:
        rec['false_refusal'] = shape == 'null'
        rec['numeric_gate'] = numeric_gate(text, gold)
        ok = verdict == 'correct' and rec['numeric_gate'] and not rec['false_refusal']
    rec['primary'] = bool(ok and not rec['manual_rejected'])
    rec.update(memory_rule_metrics(text, gold))
    return rec


def memory_rule_metrics(answer_text, gold):
    """Amendment 2026-11-11 (d) rule metrics for M5 (never from the judge):
    stale_use: the answered price equals the stale price the user put in memory instead of the tool value;
    revocation_violation: the screen equals the result with the revoked criterion still applied."""
    sub, sol = gold.get('subtier'), gold.get('solution', {})
    if sub not in ('M5-stale', 'M5-revoke'):
        return {}
    obj = extract_answer_object(answer_text) or {}
    values = obj.get('values') if isinstance(obj.get('values'), dict) else {}
    if sub == 'M5-stale':
        try:
            last = float(values.get('last'))
        except (TypeError, ValueError):
            return {'stale_use': False}
        stale = float(sol['stale_value_in_memory'])
        return {'stale_use': abs(last - stale) <= abs(stale) * 0.005}
    got = values.get('pass')
    got = sorted(str(x).strip().upper() for x in got) if isinstance(got, list) else None
    return {'revocation_violation': got is not None and got == sorted(sol.get('pass_if_revoked_applied', []))}


def bootstrap(recs, arm, baseline, draws, seed=20261104):
    tasks = sorted({r['task'] for r in recs})
    by = collections.defaultdict(list)
    for r in recs:
        by[(r['arm'], r['task'])].append(r['primary'])
    def rate(a, sample):
        vals = [x for t in sample for x in by.get((a, t), [])]
        return sum(vals) / len(vals) if vals else 0.0
    rng = random.Random(seed)
    diffs = []
    for _ in range(draws):
        sample = [rng.choice(tasks) for _ in tasks]
        diffs.append(rate(arm, sample) - rate(baseline, sample))
    diffs.sort()
    return {'diff_vs_' + baseline: round(rate(arm, tasks) - rate(baseline, tasks), 4),
            'ci95': [round(diffs[int(0.025 * draws)], 4), round(diffs[int(0.975 * draws) - 1], 4)]}


def summarize(recs, baseline, draws):
    arms = {}
    for arm in sorted({r['arm'] for r in recs}):
        rs = [r for r in recs if r['arm'] == arm]
        traps = [r for r in rs if r['scoring'] == 'refusal']
        answerable = [r for r in rs if r['scoring'] != 'refusal']
        stable = collections.defaultdict(list)
        for r in rs:
            stable[r['task']].append(r['primary'])
        arms[arm] = {
            'scheduled': len(rs),
            'primary_financial_correctness': sum(r['primary'] for r in rs),
            'primary_rate': round(sum(r['primary'] for r in rs) / len(rs), 4) if rs else None,
            'strict_success': sum(r['strict_success'] for r in rs),
            'raw_format_valid': sum(r['raw_format_valid'] for r in rs),
            'dnf': sum(r['dnf'] for r in rs), 'dnf_infra': sum(r['dnf_infra'] for r in rs),
            'false_positives_on_traps': '%d/%d' % (sum(r['fp'] for r in traps), len(traps)),
            'false_refusals': '%d/%d' % (sum(r['false_refusal'] for r in answerable), len(answerable)),
            'numeric_gate_vetoes': sum(1 for r in rs if r['judge_verdict'] == 'correct' and r['numeric_gate'] is False),
            'manual_rejections': sum(r['manual_rejected'] for r in rs),
            'stable_2of2_tasks': sum(1 for v in stable.values() if len(v) >= 2 and all(v)),
            'judge_verdicts': dict(collections.Counter(r['judge_verdict'] for r in rs)),
            'memory_stale_use': '%d/%d' % (sum(bool(r.get('stale_use')) for r in rs), sum('stale_use' in r for r in rs)),
            'memory_revocation_violation': '%d/%d' % (sum(bool(r.get('revocation_violation')) for r in rs),
                                                      sum('revocation_violation' in r for r in rs)),
        }
        if arm != baseline and baseline in {r['arm'] for r in recs}:
            arms[arm]['paired_task_bootstrap'] = bootstrap(recs, arm, baseline, draws)
    return arms


def by_stratum(recs, baseline, draws):
    """Per stratum (core / compute / memory) and per tier: primary counts with full denominators."""
    out = {}
    for stratum in sorted({r['stratum'] for r in recs}):
        rs = [r for r in recs if r['stratum'] == stratum]
        tiers = {}
        for tier in sorted({str(r['tier']) for r in rs if r['tier']}):
            ts = [r for r in rs if str(r['tier']) == tier]
            tiers[tier] = {arm: '%d/%d' % (sum(r['primary'] for r in ts if r['arm'] == arm), sum(r['arm'] == arm for r in ts))
                           for arm in sorted({r['arm'] for r in ts})}
        out[stratum] = {'arms': {arm: {'primary': sum(r['primary'] for r in rs if r['arm'] == arm),
                                       'scheduled': sum(r['arm'] == arm for r in rs)} for arm in sorted({r['arm'] for r in rs})},
                        'tiers': tiers}
        if len({r['arm'] for r in rs}) > 1 and baseline in {r['arm'] for r in rs}:
            for arm in out[stratum]['arms']:
                if arm != baseline:
                    out[stratum]['arms'][arm]['paired_task_bootstrap'] = bootstrap(rs, arm, baseline, draws)
    return out


def run_dir(run, baseline='opentrading_baseline', draws=2000):
    run = Path(run).resolve()
    rows = [json.loads(l) for l in (run / 'trials.jsonl').read_text().splitlines() if l.strip()]
    graded = {}
    path = run / 'llm-graded.jsonl'
    for l in path.read_text().splitlines():
        if l.strip():
            g = json.loads(l)
            graded[g['trial_id']] = g
    sys.path.insert(0, str(STUDY / 'tools'))
    from grade_run_llm import graded_attempt_text
    review_path = run / 'financial-review.json'
    review = json.loads(review_path.read_text()).get('decisions', {}) if review_path.is_file() else {}
    recs = []
    missing = [r['trial_id'] for r in rows if r['trial_id'] not in graded]
    if missing:
        raise SystemExit('llm-graded.jsonl incomplete: %d trials missing (run grade_run_llm.py --resume)' % len(missing))
    for row in rows:
        g = dict(graded[row['trial_id']])
        g['_answer_text'] = graded_attempt_text(run, row)[0]
        recs.append(score_trial(row, g, task_gold(row['task']), review, run))
    summary = {'run': str(run), 'definition': __doc__.split('\n\n')[1].strip(),
               'manual_review_applied': bool(review), 'trials': len(recs),
               'arms': summarize(recs, baseline, draws), 'by_stratum': by_stratum(recs, baseline, draws)}
    (run / 'judge-primary.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in recs))
    (run / 'judge-primary-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1) + '\n')
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_dir')
    ap.add_argument('--baseline', default='opentrading_baseline')
    ap.add_argument('--draws', type=int, default=2000)
    a = ap.parse_args()
    print(json.dumps(run_dir(a.run_dir, a.baseline, a.draws), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
