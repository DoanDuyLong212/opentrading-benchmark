#!/usr/bin/env python3
"""Re-runnable finalization of the merged or16 main view (needed again whenever the merge or judge layers change,
because audit-v45.json and financial-review.json are hash-bound to the directory):

  1. analysis/build_main_final_or16.py           (rows + judge layers)
  2. analysis/audit_v45_amended.py               (tools auditor + amendment j)
  3. analysis/build_review_evidence.py           (review-evidence.jsonl)
  4. financial-review.json                       (all-arm win review; may only REMOVE; decisions below)
  5. summary.json via tools/metrics.build_summary

Review decisions are the root review of 2026-11-11 (see plans/2026-11-11-v46u-main-launch-notes.md): every automatic
win passes except REMOVE. Flagged wins not explained by the auto re-derivation and not in HAND_READ abort the run so a
new flag is never passed silently.

  python3 analysis/finalize_main_or16.py
"""
import itertools, json, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(STUDY / 'tools'), str(STUDY / 'analysis')]
P = STUDY / 'results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main'

REMOVE = {'fin-m2-port-511__dsh__r2': 'narrative claim false: note says all 3 holdings are at a loss ("3 mã đều lỗ") '
          'while its own figure shows GAS +11.43% (78/70); headline numbers correct, but the written claim contradicts '
          'the data -> narrative_claims fails, win removed',
          'fin-m3-update-520__opencode__r2': 'or16r3 back-fill win read by hand 2026-11-12: note states the filter as '
          '"P/E < 15, P/B < 1.5, ROE > 12" while the user\'s current remembered criteria are P/E < 10 and P/B < 1,2 '
          '(turns.json S1-S2); the criteria were invented (OpenCode has no memory) and the gold set {PVS, PVT} came out '
          'by coincidence -> narrative_claims fails (fabricated memory claim), win removed'}
# flagged wins read by hand (2026-11-11), see the label file for the finding
HAND_READ = set(json.loads((STUDY / 'analysis/labels/or16-review-hand-read.json').read_text())['hand_read'])


def run(*cmd):
    print('$', ' '.join(map(str, cmd)), flush=True)
    r = subprocess.run([sys.executable, *map(str, cmd)], cwd=STUDY, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit('failed: %s' % cmd[0])
    return r.stdout


def close(a, b):
    return abs(a - b) <= max(abs(b) * 0.005, 0.011)


def auto_derived(ev):
    """A flagged narrative number is explained only by (1) +/- a payload number, (2) a Vietnamese thousand-separator
    parse artifact ("5.558.730.000.000" read as 5.558), or (3) sum/difference/product/ratio/%-change of two OTHER
    numbers the answer states (numbers equal to x itself are excluded, so x never explains itself)."""
    import re
    from build_review_evidence import numbers, payload_numbers
    ans = ev['answer_excerpt']
    text = json.dumps(ans, ensure_ascii=False)
    pool = [p for p in payload_numbers(STUDY / 'tasks/main' / ev['task']) if p is not None]
    vals = numbers(ans.get('values')) if isinstance(ans, dict) else []
    allnum = sorted(set(numbers(ans)))
    for x in ev['unsupported_numbers']:
        if any(close(x, abs(p)) or close(-x, p) for p in pool):
            continue
        if re.search(r'(?<![\d.,])%s(?:\.\d{3})+(?:,\d+)?(?![\d])' % re.escape(('%g' % abs(x))), text) or \
           re.search(r'(?<![\d.,])%s(?:,\d{3})+(?:\.\d+)?(?![\d])' % re.escape(('%g' % abs(x))), text):
            continue
        base = [a for a in allnum if not close(a, x) and not close(a, -x)]
        if vals and len(vals) > 1 and close(x, sum(vals)) and not any(close(v, x) for v in vals):
            continue
        if any(close(x, v) or close(x, v * 100) or close(-x, v) or close(-x, v * 100)
               for a, b in itertools.product(base, repeat=2)
               for v in (a + b, a - b, a * b, a / b if b else 1e99, (a / b - 1) if b else 1e99)):
            continue
        return False
    return True


def main():
    run('analysis/build_main_final_or16.py')
    out = run('analysis/audit_v45_amended.py', '--run', P)
    audit = json.loads((P / 'audit-v45.json').read_text())
    if not audit['pass'] or audit['fabricated_evidence_accepted']:
        raise SystemExit('audit not clean: %s' % audit['errors'][:5])
    run('analysis/build_review_evidence.py', P)
    from v45_review import protected_artifacts, REVIEW_CHECKS
    from run_manifest import hash_file
    rows = [json.loads(l) for l in open(P / 'trials.jsonl')]
    wins = [r for r in rows if r.get('success') or r.get('grounded_financial_correctness')]
    ev = {json.loads(l)['trial_id']: json.loads(l) for l in open(P / 'review-evidence.jsonl')}
    flagged = [t for t, e in ev.items() if e['needs_manual']]
    auto = {t for t in flagged if auto_derived(ev[t])}
    unread = sorted(set(flagged) - auto - HAND_READ)
    if unread:
        raise SystemExit('new flagged wins need a hand read: %s' % unread)
    dec = {}
    for r in wins:
        t = r['trial_id']
        if t in REMOVE:
            dec[t] = {'pass': False, 'checks': dict({k: True for k in REVIEW_CHECKS}, narrative_claims=False),
                      'evidence_notes': REMOVE[t]}
            continue
        note = ('all 7 checks pass in sealed grade; every number traced to the frozen payload' if not ev[t]['needs_manual']
                else 'flagged narrative numbers re-derived (sum/difference/product/ratio/%-change of numbers the answer '
                     'states from the payload)' + ('; read by hand' if t in HAND_READ else ''))
        dec[t] = {'pass': True, 'checks': {k: True for k in REVIEW_CHECKS}, 'evidence_notes': note}
    m = json.loads((P / 'manifest.json').read_text())
    review = {'schema': 'independent-financial-review-v45',
              'created_at': datetime.now(timezone(timedelta(hours=7))).isoformat(timespec='seconds'),
              'reviewer': 'v46u root review (merged or16 main: or16 + or16r infra replacement of 132 OT r1 slots + '
                          'or16r2 + or16r3 outage back-fill of fin-m3-update-520 OT r2 and OC r2)',
              'independent': True, 'manifest_sha256': m['fingerprint'], 'protected_artifacts_sha256': protected_artifacts(P),
              'automatic_audit_sha256': hash_file(P / 'audit-v45.json'),
              'scope': ('all automatic strict OR grounded-financial wins in every arm (%d); evidence '
                        'analysis/build_review_evidence.py -> review-evidence.jsonl. %d wins flagged (narrative_claims): '
                        '%d auto-derived (strict: payload +/-, VN number-format artifact, or arithmetic of two OTHER stated numbers), %d read by hand (analysis/labels/or16-review-hand-read.json); plus a hand-read stratified sample of 45 auto-derived flagged '
                        'wins (15/arm, seed 20261111) and a scan of every universal narrative claim ("đều/cả N/tất cả ... '
                        'lỗ/lãi/tăng/giảm/vượt/dưới") in all wins (32 read by hand, incl. every fin-m2-port-511 sibling). '
                        '%d win(s) removed. Audit: tools/audit_v45_run.py + amendment (j) (analysis/audit_v45_amended.py).'
                        % (len(wins), len(flagged), len(auto - HAND_READ), len(HAND_READ & set(flagged)), len(REMOVE))),
              'decisions': dec}
    (P / 'financial-review.json').write_text(json.dumps(review, ensure_ascii=False, indent=1))
    import metrics
    s = metrics.build_summary(str(P))
    (P / 'summary.json').write_text(json.dumps(s, ensure_ascii=False, indent=1))
    f = s['financial_v45']
    print(json.dumps({'audit_pass': audit['pass'], 'relaxed_j': len(audit.get('amendment_j_relaxed_bindings', [])),
                      'wins': len(wins), 'flagged': len(flagged), 'removed': len(REMOVE),
                      'review': {k: f['manual_financial_review'].get(k) for k in
                                 ('review_complete', 'reviewed_automatic_wins', 'rejected_automatic_wins')},
                      'strict': {a: x['strict_grounded_success'] for a, x in f['arms'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
