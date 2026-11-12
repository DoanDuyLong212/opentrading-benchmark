#!/usr/bin/env python3
"""Evidence for the independent all-arm manual financial review (review may only REMOVE wins).

For every automatic win (strict success OR grounded financial correctness) it records, per the 7
preregistered checks, the evidence from the sealed grade plus an independent narrative check:
every number written in the answer (note/reason/values) must be traceable to the frozen task payload
(within 0.5% or after unit scaling) or equal to a value the answer itself reports. Anything not
mechanically supported is flagged for manual reading; the reviewer's final decisions are applied with
--decide.

  python3 analysis/build_review_evidence.py RUN_DIR            # writes review-evidence.jsonl
"""
import json
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from grade_run_llm import graded_attempt_text  # noqa: E402
from llm_judge import extract_answer_object  # noqa: E402

NUM = re.compile(r'(?<![\w.])-?\d[\d,]*(?:\.\d+)?')
SCALES = (1, 1e3, 1e6, 1e9, 1e-3, 1e-6, 1e-9, 100, 0.01)


def numbers(obj):
    out = []
    if isinstance(obj, bool) or obj is None:
        return out
    if isinstance(obj, (int, float)):
        return [float(obj)]
    if isinstance(obj, str):
        for m in NUM.findall(obj):
            try:
                out.append(float(m.replace(',', '')))
            except ValueError:
                pass
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ('evidence', 'source_evidence', 'memory_evidence'):
                continue
            out += numbers(v)
    if isinstance(obj, list):
        for v in obj:
            out += numbers(v)
    return out


def payload_numbers(task_dir):
    data = json.loads((task_dir / 'environment/payloads.json').read_text())
    vals = numbers(data)
    return vals


def supported(x, pool):
    if abs(x) < 1e-12 or float(x).is_integer() and abs(x) <= 31:  # dates/day counts/small ordinals
        return True
    for p in pool:
        for s in SCALES:
            q = p * s
            if q and abs(x - q) <= abs(q) * 0.005 + 0.006:
                return True
    return False


def main(run):
    run = Path(run).resolve()
    rows = [json.loads(l) for l in (run / 'trials.jsonl').read_text().splitlines() if l.strip()]
    wins = [r for r in rows if r.get('success') or r.get('grounded_financial_correctness')]
    out = []
    for r in wins:
        task_dir = next(p for p in (STUDY / 'tasks').glob('*/' + r['task']) if p.is_dir())
        grade = json.loads((run / 'trials' / r['trial_id'] / 'grade.json').read_text())
        checks = {c['check']: c.get('pass') for c in grade['checks']}
        text = graded_attempt_text(run, r)[0]
        ans = extract_answer_object(text) or {}
        pool = payload_numbers(task_dir) + numbers({k: v for k, v in ans.items() if k == 'values' or k == 'value'})
        unsupported = sorted({x for x in numbers({k: v for k, v in ans.items() if k not in ('evidence',)})
                              if not supported(x, pool)})
        def all_pass(prefixes):
            sel = [v for k, v in checks.items() if k.split(':')[0] in prefixes]
            return all(sel) if sel else True
        auto = {
            'source': all_pass(('str', 'str_all')) and checks.get('provenance', True) is not False,
            'entity': all_pass(('tokens', 'set', 'list_order', 'verdict')),
            'period': all_pass(('period',)),
            'unit': all_pass(('unit',)),
            'scope': checks.get('no_unrequested_numeric_claims', True) is not False,
            'arithmetic': all_pass(('value',)),
            'narrative_claims': not unsupported,
        }
        out.append({'trial_id': r['trial_id'], 'task': r['task'], 'scoring': grade.get('task_id') and r.get('error_type'),
                    'auto_checks': auto, 'needs_manual': not all(auto.values()), 'unsupported_numbers': unsupported[:20],
                    'answer_excerpt': {k: v for k, v in ans.items() if k not in ('evidence',)}})
    (run / 'review-evidence.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in out))
    flagged = [x for x in out if x['needs_manual']]
    print('wins', len(out), 'flagged for manual reading', len(flagged))
    for x in flagged:
        print(x['trial_id'], {k: v for k, v in x['auto_checks'].items() if not v}, x['unsupported_numbers'][:8])


if __name__ == '__main__':
    main(sys.argv[1])
