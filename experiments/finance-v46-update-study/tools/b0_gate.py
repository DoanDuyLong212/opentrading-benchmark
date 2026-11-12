"""B0-only admission gate (main amendment 2026-11-10, user-approved judge-primary flow).

Replaces the retired B1 superiority gate (v45_gate.quality_gate) for studies sealed with
gate == 'b0_judge_primary'. It is an admission/integrity gate, never a superiority claim:

  * complete schedule; independent instrumentation audit PASS with 0 accepted fabricated evidence;
  * independent all-arm manual review complete with 0 accepted financial fabrications;
  * judge-primary scoring present for every scheduled trial (tools/judge_primary.py);
  * judge calibration on hand-labelled trials with Cohen kappa >= 0.6 (analysis/labels/*-kappa.json
    registered in the seal).
"""
import json
from pathlib import Path

GATE_NAME = 'b0_judge_primary'
KAPPA_MIN = 0.6


def b0_gate(out, kappa_file=None):
    out = Path(out)
    why = []
    def load(name):
        p = out / name
        return json.loads(p.read_text()) if p.is_file() else None
    summary, audit, primary = load('summary.json'), load('audit-v45.json'), load('judge-primary-summary.json')
    data = (summary or {}).get('financial_v45', {})
    if not data.get('complete'):
        why.append('incomplete schedule')
    if not audit or not audit.get('pass') or audit.get('fabricated_evidence_accepted') != 0:
        why.append('instrumentation audit not PASS or fabrication unknown')
    review = data.get('manual_financial_review', {})
    if not review.get('review_complete') or review.get('accepted_financial_fabrications') != 0:
        why.append('manual all-arm review pending or fabrication accepted')
    scheduled = sum(m.get('scheduled', 0) for m in data.get('arms', {}).values())
    if not primary or primary.get('trials') != scheduled or not primary.get('manual_review_applied'):
        why.append('judge-primary scoring missing/stale for the reviewed schedule')
    if kappa_file is not None:
        try:
            k = json.loads(Path(kappa_file).read_text()).get('cohen_kappa')
        except (OSError, ValueError):
            k = None
        if not isinstance(k, (int, float)) or k < KAPPA_MIN:
            why.append('judge calibration kappa below %.1f or missing' % KAPPA_MIN)
    return {'pass': not why, 'reasons': why, 'gate': GATE_NAME, 'scheduled': scheduled,
            'arms_primary': {a: m.get('primary_financial_correctness') for a, m in (primary or {}).get('arms', {}).items()}}
