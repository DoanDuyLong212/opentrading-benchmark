"""Negative offline integrity fixtures exercise real oracle and grader protocols."""
import copy
import json
from pathlib import Path
import shutil

import pytest
import verify_offline as verifier

STUDY = Path(__file__).resolve().parents[2]


@pytest.fixture
def quote(tmp_path):
    source = STUDY/'tasks/smoke/smoke-quote-01'
    task = tmp_path/'tasks/smoke'/source.name
    shutil.copytree(source, task)
    return task


def test_complete_task_uses_local_oracle_and_real_grader(quote, monkeypatch):
    # Poison provider entry points: the local check must never dispatch/setup.
    import runners.provider as provider
    monkeypatch.setattr(provider.ProviderGateway, '__init__', lambda *a, **k: pytest.fail('provider initialized'))
    monkeypatch.setenv('OPENAI_API_KEY', 'must-not-enter-oracle-environment')
    result = verifier.verify_task(quote)
    assert result['entries'] > 0 and result['mutations_checked'] == 5
    assert result['files_sha256']['environment/payloads.json']


@pytest.mark.parametrize('missing', verifier.REQUIRED)
def test_missing_required_file_fails(quote, missing):
    (quote/missing).unlink()
    with pytest.raises(ValueError, match='missing required file'):
        verifier.verify_task(quote)


def test_payload_tamper_fails_before_oracle(quote):
    path = quote/'environment/payloads.json'
    path.write_text(path.read_text()+' ')
    with pytest.raises(ValueError, match='payload SHA256'):
        verifier.verify_task(quote)


def test_schema_invalid_recorded_request_rejected(quote):
    path = quote/'environment/payloads.json'
    data = json.loads(path.read_text())
    contracts_path = quote/'environment/request_contracts.json'
    contracts = json.loads(contracts_path.read_text())
    next(iter(contracts['requests'].values()))[0]['params'] = {'symbol': ['invalid-type']}
    contracts_path.write_text(json.dumps(contracts))
    path.write_text(json.dumps(data))
    gold_path = quote/'solution/gold.json'
    gold = json.loads(gold_path.read_text())
    gold['payload_sha256'] = verifier.digest_file(path)
    gold_path.write_text(json.dumps(gold))
    with pytest.raises(Exception) as error:
        verifier.verify_task(quote)
    assert error.type.__module__.startswith('jsonschema')


def test_source_receipt_tamper_fails(quote):
    path = quote/'solution/gold.json'
    gold = json.loads(path.read_text())
    gold['provenance_contract'][0]['response_sha256'] = '0'*64
    path.write_text(json.dumps(gold))
    with pytest.raises(ValueError, match='provenance binding'):
        verifier.verify_task(quote)


def test_wrong_gold_rejected_by_independent_oracle(quote):
    path = quote/'solution/gold.json'
    gold = json.loads(path.read_text())
    def change(value):
        for key, item in value.items():
            if isinstance(item, (float, int)) and not isinstance(item, bool):
                value[key] = item + 999999
                return True
            if isinstance(item, dict) and change(item):
                return True
        return False
    assert change(gold['solution'])
    path.write_text(json.dumps(gold))
    with pytest.raises(ValueError, match='oracle consistency'):
        verifier.verify_task(quote)


def test_broken_always_pass_grader_rejected(quote):
    (quote/'tests/grader.py').write_text('''import json,sys
from pathlib import Path
def main():
    Path(sys.argv[sys.argv.index('-o')+1]).write_text(json.dumps({'success': True}))
''')
    with pytest.raises(ValueError, match='accepted mutation'):
        verifier.verify_task(quote)


def test_symlink_task_rejected(quote):
    path = quote/'hidden'
    path.symlink_to(quote/'solution/gold.json')
    with pytest.raises(ValueError, match='symlink'):
        verifier.verify_task(quote)


@pytest.mark.parametrize('pattern', ['fin-s1-*', 'fin-s2-*', 'fin-s3-*', 'fin-m4-*', 'fin-m5-*'])
def test_safety_and_native_memory_contracts_checked(pattern):
    task = sorted(list((STUDY/'tasks/main').glob(pattern)) + list((STUDY/'tasks-retired/main').glob(pattern)))[0]  # S1 retired 24/11 f
    result = verifier.verify_task(task)
    if pattern.startswith('fin-s1'):
        assert result['mutations_checked'] >= 5
    if pattern.startswith('fin-m'):
        assert result['memory']


def test_missing_split_never_succeeds_empty(tmp_path):
    report = verifier.verify_study(tmp_path)
    assert not report['pass'] and report['tasks_checked'] == 0
    assert {r['check'] for r in report['failures']} >= set(verifier.SPLITS)


def test_required_provenance_cannot_disappear(quote):
    path = quote/'solution/gold.json'
    gold = json.loads(path.read_text())
    gold['provenance_contract'] = []
    path.write_text(json.dumps(gold))
    with pytest.raises(ValueError, match='coverage mismatch'):
        verifier.verify_task(quote)
