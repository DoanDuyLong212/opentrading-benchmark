"""v4.7 seal, authorization and one-shot holdout receipt contracts."""
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import v47_gate
from run_manifest import digest_json


@pytest.fixture(autouse=True)
def stub_freeze_state(monkeypatch):
    """Gate tests exercise seal matching, not the heavy toolchain inventory."""
    monkeypatch.setattr(v47_gate, 'freeze_state', lambda config: {'config': config})


def seal_fixture(tmp_path, **overrides):
    config = tmp_path / 'config.json'
    config.write_text(json.dumps({'protocol': 'financial_product_v45', 'study_version': 'v4.7'}))
    protected = tmp_path / 'protected.py'
    protected.write_text('value = 1\n')
    approval = tmp_path / 'approval.json'
    approval.write_text(json.dumps({'decision_id': 'DEC-1', 'approved_by': 'FinDaHuman'}))
    seal = {
        'study_version': 'v4.7',
        'protocol': 'financial_product_v45',
        'engineering_approved': True,
        'approval': str(approval),
        'protected_files': {str(protected): v47_gate.hash_file(protected)},
        'runs': [{
            'out': str((tmp_path / 'out').resolve()),
            'config': str(config.resolve()),
            'split': 'devsmoke',
            'settings': {'split': 'devsmoke'},
            'tasks': ['task-a'],
            'state_sha256': digest_json({'config': json.loads(config.read_text())}),
        }],
    }
    seal.update(overrides)
    path = tmp_path / 'seal.json'
    path.write_text(json.dumps(seal))
    return path, seal, approval


def authorize(seal_path, task='task-a', resume=True):
    seal = json.loads(Path(seal_path).read_text())
    run = seal['runs'][0]
    return v47_gate.authorize_run(seal_path, run['out'], run['config'], run['settings'], [Path(task)], resume)


def test_rejects_other_study_version(tmp_path):
    path, seal, _ = seal_fixture(tmp_path, study_version='v4.6-update')
    with pytest.raises(ValueError, match='v4.7'):
        v47_gate.validate_seal(path)


def test_rejects_tampered_protected_file(tmp_path):
    path, seal, _ = seal_fixture(tmp_path)
    Path(next(iter(seal['protected_files']))).write_text('value = 2\n')
    with pytest.raises(ValueError, match='drift'):
        v47_gate.validate_seal(path)


def test_rejects_seal_approval_flag_disagreement(tmp_path):
    path, seal, approval = seal_fixture(tmp_path)
    data = json.loads(approval.read_text())
    data['main_authorized_by_user'] = True
    approval.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='disagree'):
        v47_gate.validate_seal(path)


def test_authorizes_registered_devsmoke_resume_only(tmp_path):
    path, seal, _ = seal_fixture(tmp_path)
    assert authorize(path)['split'] == 'devsmoke'
    with pytest.raises(ValueError, match='differs'):
        authorize(path, resume=False)
    with pytest.raises(ValueError, match='differs'):
        authorize(path, task='task-b')


def test_main_and_holdout_require_user_authorization(tmp_path):
    path, seal, approval = seal_fixture(tmp_path)
    data = json.loads(Path(path).read_text())
    data['runs'][0]['split'] = 'main'
    Path(path).write_text(json.dumps(data))
    with pytest.raises(ValueError, match='main inference not authorized'):
        authorize(path)
    data['main_authorized_by_user'] = True
    Path(path).write_text(json.dumps(data))
    approval_data = json.loads(approval.read_text())
    approval_data['main_authorized_by_user'] = True
    approval.write_text(json.dumps(approval_data))
    assert authorize(path)['split'] == 'main'


def test_holdout_receipt_opens_once_and_binds_decision(tmp_path):
    path, seal, approval = seal_fixture(tmp_path)
    data = json.loads(Path(path).read_text())
    data['runs'][0]['split'] = 'holdout'
    data['runs'][0]['cohort_id'] = 'holdout-v47-a'
    data['main_authorized_by_user'] = True
    data['holdout_authorized_by_user'] = True
    Path(path).write_text(json.dumps(data))
    approval_data = json.loads(approval.read_text())
    approval_data.update(main_authorized_by_user=True, holdout_authorized_by_user=True)
    approval.write_text(json.dumps(approval_data))
    with pytest.raises(ValueError, match='holdout run missing cohort_id'):
        bad = json.loads(Path(path).read_text())
        bad['runs'][0].pop('cohort_id')
        Path(path).write_text(json.dumps(bad))
        v47_gate.validate_seal(path)
    Path(path).write_text(json.dumps(data))
    receipt = tmp_path / 'holdout-receipt.json'
    written = v47_gate.write_holdout_receipt(path, 'holdout-v47-a', receipt)
    assert written['decision_id'] == 'DEC-1'
    assert v47_gate.validate_holdout_receipt(receipt, path, 'holdout-v47-a')['cohort_id'] == 'holdout-v47-a'
    with pytest.raises(ValueError, match='already opened'):
        v47_gate.write_holdout_receipt(path, 'holdout-v47-a', receipt)
    with pytest.raises(ValueError, match='mismatch'):
        v47_gate.validate_holdout_receipt(receipt, path, 'other-cohort')
