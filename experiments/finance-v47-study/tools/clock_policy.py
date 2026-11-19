"""Conservative S3 policy until native wire evidence establishes clock parity.

Snapshot instructions are not proof that a runtime's native clock is pinned.
The audit consumes redacted observations tied to complete captured requests; an
inventory flag alone is deliberately insufficient.
"""
import hashlib
import re

CLOCK_POLICY = {
    's3_classification': 'diagnostic',
    's3_comparative_eligible': False,
    'reason': 'Common native date across arms and continuation requests is not established by wire evidence',
}
ARMS = ('opentrading', 'opencode', 'dsh')


def comparative_eligible(task, gold=None):
    tier = (gold or {}).get('subtier', (gold or {}).get('tier', ''))
    return not (str(tier).startswith('S3') or re.match(r'^fin-s3-', task))


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
