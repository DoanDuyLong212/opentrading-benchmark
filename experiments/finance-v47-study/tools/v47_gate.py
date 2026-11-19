"""v4.7-only fail-closed seal, run authorization and one-shot holdout receipts.

Kept separate from v45_gate/v44_gate: a v4.6 seal never authorizes v4.7 work.
A v4.7 seal registers exact runs; main and holdout additionally require flags
mirrored in the protected approval receipt.
"""
import json
from pathlib import Path

from protocol_compat import FINANCIAL_PROTOCOL
from run_manifest import digest_json, freeze_state, hash_file

STUDY_VERSION = 'v4.7'
SPLITS = ('devsmoke', 'pilot', 'main', 'holdout')
FLAGS = ('canary_authorized', 'main_authorized_by_user', 'holdout_authorized_by_user')


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_seal(path):
    seal = load(path)
    if seal.get('study_version') != STUDY_VERSION:
        raise ValueError('Wrong study identity: a v4.7 seal is required')
    if seal.get('protocol') != FINANCIAL_PROTOCOL or seal.get('engineering_approved') is not True:
        raise ValueError('v4.7 engineering seal missing')
    approval_path = seal.get('approval')
    if not approval_path or not Path(approval_path).is_file():
        raise ValueError('v4.7 seal approval receipt missing')
    approval = load(approval_path)
    for field in ('decision_id', 'approved_by'):
        if not approval.get(field):
            raise ValueError('v4.7 approval missing ' + field)
    for flag in FLAGS:
        if bool(seal.get(flag)) is not bool(approval.get(flag)):
            raise ValueError('v4.7 seal and approval disagree on ' + flag)
    for protected, sha in seal.get('protected_files', {}).items():
        if not Path(protected).is_file() or hash_file(protected) != sha:
            raise ValueError('Sealed file drift: ' + protected)
    runs = seal.get('runs') or []
    if not runs:
        raise ValueError('v4.7 seal registers no runs')
    for item in runs:
        if item.get('split') not in SPLITS:
            raise ValueError('Unknown split in v4.7 seal: ' + str(item.get('split')))
        config = item.get('config')
        if not config or not Path(config).is_file():
            raise ValueError('Sealed run config missing')
        if digest_json(freeze_state(load(config))) != item.get('state_sha256'):
            raise ValueError('v4.7 frozen state changed for ' + str(config))
        if not isinstance(item.get('settings'), dict) or not isinstance(item.get('tasks'), list):
            raise ValueError('Sealed run missing settings or tasks')
        if item['split'] == 'holdout' and not item.get('cohort_id'):
            raise ValueError('holdout run missing cohort_id')
    return seal, approval


def _main_authorized(seal, approval):
    return seal.get('main_authorized_by_user') is True and approval.get('main_authorized_by_user') is True


def _holdout_authorized(seal, approval):
    return _main_authorized(seal, approval) and seal.get('holdout_authorized_by_user') is True \
        and approval.get('holdout_authorized_by_user') is True


def authorize_run(seal_path, out, config, settings, tasks, resume):
    seal, approval = validate_seal(seal_path)
    selected = next((item for item in seal['runs']
                     if item.get('out') == str(Path(out).resolve())
                     and item.get('config') == str(Path(config).resolve())), None)
    if (not selected or not resume or settings != selected['settings']
            or sorted(Path(task).name for task in tasks) != sorted(selected['tasks'])):
        raise ValueError('Run differs from registered v4.7 manifest')
    split = selected['split']
    if split == 'main' and not _main_authorized(seal, approval):
        raise ValueError('v4.7 main inference not authorized by user')
    if split == 'holdout' and not _holdout_authorized(seal, approval):
        raise ValueError('v4.7 holdout inference not authorized by user')
    return selected


def holdout_receipt_value(seal_path, cohort_id):
    seal, approval = validate_seal(seal_path)
    if not _main_authorized(seal, approval):
        raise ValueError('holdout requires main authorization')
    if not _holdout_authorized(seal, approval):
        raise ValueError('holdout not authorized by user')
    if not cohort_id:
        raise ValueError('holdout cohort_id required')
    return {
        'schema': 1,
        'study_version': STUDY_VERSION,
        'seal_sha256': hash_file(seal_path),
        'approval_sha256': hash_file(seal['approval']),
        'decision_id': approval['decision_id'],
        'cohort_id': cohort_id,
    }


def write_holdout_receipt(seal_path, cohort_id, dest):
    value = holdout_receipt_value(seal_path, cohort_id)
    dest = Path(dest)
    if dest.exists():
        raise ValueError('Holdout already opened; only exact resume of the same cohort is allowed')
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return value


def validate_holdout_receipt(path, seal_path, cohort_id):
    receipt = load(path)
    expected = holdout_receipt_value(seal_path, cohort_id)
    for field, value in expected.items():
        if receipt.get(field) != value:
            raise ValueError('Holdout receipt mismatch: ' + field)
    return receipt
