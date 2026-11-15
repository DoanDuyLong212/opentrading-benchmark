"""Main amendment 2026-11-10: B0 judge-primary gate and conditional main authorization."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from b0_gate import b0_gate  # noqa: E402
from run_manifest import hash_file  # noqa: E402
from v45_gate import validate_seal  # noqa: E402


def _seal(tmp_path, approval_obj, **kw):
    approval = tmp_path / 'approval.json'
    approval.write_text(json.dumps(approval_obj))
    seal = {'protocol': 'financial_product_v45', 'study_version': 'v4.6-update', 'engineering_approved': True,
            'approval': str(approval), 'main_authorized_by_user': False, 'diagnostic_pilot_authorized': False,
            'protected_files': {str(approval): hash_file(approval)}, 'runs': []}
    seal.update(kw)
    p = tmp_path / 'seal.json'
    p.write_text(json.dumps(seal))
    return p


def test_main_requires_b0_gate_and_user_authorization_in_both_seal_and_approval(tmp_path):
    main = [{'split': 'main', 'config': '/nonexistent'}]
    # seal claims main but approval does not authorize it
    with pytest.raises(ValueError, match='unauthorized main'):
        validate_seal(_seal(tmp_path, {'approved': True}, main_authorized_by_user=True, gate='b0_judge_primary', runs=main))
    # approval authorizes but the seal is not a b0 seal
    with pytest.raises(ValueError, match='unauthorized main'):
        validate_seal(_seal(tmp_path, {'approved': True, 'main_authorized_by_user': True}, main_authorized_by_user=True, runs=main))
    # unauthorized seal listing a main run is still rejected
    with pytest.raises(ValueError, match='smoke/pilot only'):
        validate_seal(_seal(tmp_path, {'approved': True}, runs=[{'split': 'main'}]))


def _pilot(tmp_path, *, audit_pass=True, review=True, primary=True, trials=6):
    out = tmp_path / 'pilot'
    out.mkdir(exist_ok=True)
    summary = {'financial_v45': {'complete': True, 'arms': {'a': {'scheduled': 3}, 'b': {'scheduled': 3}},
                                 'manual_financial_review': {'review_complete': review, 'accepted_financial_fabrications': 0}}}
    (out / 'summary.json').write_text(json.dumps(summary))
    (out / 'audit-v45.json').write_text(json.dumps({'pass': audit_pass, 'fabricated_evidence_accepted': 0}))
    if primary:
        (out / 'judge-primary-summary.json').write_text(json.dumps({'trials': trials, 'manual_review_applied': True,
                                                                    'arms': {'a': {'primary_financial_correctness': 2}}}))
    return out


def test_b0_gate_is_admission_only(tmp_path):
    k = tmp_path / 'k.json'
    k.write_text(json.dumps({'cohen_kappa': 0.8}))
    assert b0_gate(_pilot(tmp_path), k)['pass']
    assert not b0_gate(_pilot(tmp_path, audit_pass=False), k)['pass']
    assert not b0_gate(_pilot(tmp_path, review=False), k)['pass']
    assert not b0_gate(_pilot(tmp_path, trials=5), k)['pass']
    k.write_text(json.dumps({'cohen_kappa': 0.5}))
    assert not b0_gate(_pilot(tmp_path), k)['pass']


def test_auditor_formula_constants_match_opentrading():
    from v45_math_audit import formula_constant
    assert all(formula_constant(v) for v in (5, 31, 1000, 1000000, 0.001, 100, 365))
    assert not any(formula_constant(v) for v in (12345, 1741.62, 0.59, 32.5))
