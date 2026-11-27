"""Conservative S3 policy until native wire evidence establishes clock parity.

Snapshot instructions are not proof that a runtime's native clock is pinned.
The audit consumes redacted observations tied to complete captured requests; an
inventory flag alone is deliberately insufficient.
"""
import hashlib
import json
import re
import tomllib
from functools import lru_cache
from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parents[1]
SPLITS = ('main', 'holdout', 'devsmoke', 'pilot', 'smoke')

CLOCK_POLICY = {
    'safety_classification': 'diagnostic',
    'safety_comparative_eligible': False,
    'methodology_decision_status': 'pending_FinDaHuman',
    's3_classification': 'robustness (pooled)',
    's3_comparative_eligible': True,
    'reason': 'Amendment 2026-11-25 (e/f): every harness main process runs on the snapshot clock (LD_PRELOAD shim); '
              'S1/S2-buy retired; S2 data-instruction and S3 stale-data tasks are pooled as stratum robustness',
}
ARMS = ('opentrading', 'opencode', 'dsh')


@lru_cache(maxsize=None)
def _task_metadata(task, root, _seen=()):
    """Stratum/tier từ task.toml + gold.json; dev-copy thiếu cả hai thì theo development-lineage."""
    for split in SPLITS:
        task_dir = Path(root)/'tasks'/split/task
        if not task_dir.is_dir():
            continue
        toml_meta, gold_meta = {}, {}
        if (task_dir/'task.toml').is_file():
            data = tomllib.loads((task_dir/'task.toml').read_text(encoding='utf-8'))
            toml_meta = {'stratum': data.get('stratum'), 'tier': data.get('subtier') or data.get('tier')}
        gold_path = task_dir/'solution'/'gold.json'
        if gold_path.is_file():
            gold = json.loads(gold_path.read_text(encoding='utf-8'))
            gold_meta = {'stratum': gold.get('stratum'), 'tier': gold.get('subtier') or gold.get('tier')}
        meta = {'stratum': toml_meta.get('stratum') or gold_meta.get('stratum'),
                'tier': toml_meta.get('tier') or gold_meta.get('tier')}
        if not any(meta.values()):
            lineage = task_dir/'development-lineage.json'
            if lineage.is_file():
                origin = json.loads(lineage.read_text(encoding='utf-8')).get('origin_task_id')
                if origin and origin not in _seen and origin != task:
                    meta = _task_metadata(origin, root, _seen + (task,))
        return meta
    return {}


def comparative_eligible(task, gold=None):
    """Only stratum `safety` stays out of the primary analysis.

    Amendment 2026-11-25 (f): S1/S2-buy were retired; the kept S2 times10/zero and S3 tasks are stratum `robustness`
    and pooled (S3's earlier exclusion was the unpinned native clock; every harness now runs on the snapshot clock,
    amendment 2026-11-25 e). Task metadata is canonical, the record only supplements it.
    """
    meta, record = _task_metadata(task, STUDY_ROOT), gold or {}
    if 'safety' in {str(s) for s in (meta.get('stratum'), record.get('stratum'))}:
        return False
    # Retired advice-forcing families stay out even for a copy without metadata.
    return not re.match(r'^(dev-)?fin-(s1|s2-buy)-', task)


def audit_clock_observations(observations, expected_date):
    """Audit explicit native-date observations from first and continuation wire requests.

    Each observation supplies arm, stage, native_date, snapshot_date and complete
    redacted request text. A caller must extract native_date from runtime context,
    not from the task instruction. This does not change the diagnostic policy.
    """
    seen, evidence, errors = set(), [], []
    for row in observations:
        key = (row.get('arm'), row.get('stage'))
        request = row.get('redacted_request')
        if key in seen:
            errors.append('duplicate arm/stage observation: %s/%s' % key)
        seen.add(key)
        if not isinstance(request, str) or not request.strip():
            errors.append('complete redacted request required: %s/%s' % key)
        if row.get('native_date') != expected_date or row.get('snapshot_date') != expected_date:
            errors.append('date mismatch or missing native date: %s/%s' % key)
        evidence.append({'arm': key[0], 'stage': key[1], 'native_date': row.get('native_date'),
                         'snapshot_date': row.get('snapshot_date'),
                         'request_sha256': hashlib.sha256((request or '').encode()).hexdigest()})
    for key in {(a, s) for a in ARMS for s in ('first', 'continuation')} - seen:
        errors.append('missing wire observation: %s/%s' % key)
    return {'parity_verified': not errors, 'errors': sorted(errors), 'evidence': evidence,
            'policy': dict(CLOCK_POLICY)}
