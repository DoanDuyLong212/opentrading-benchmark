"""Public-only endpoint fixtures; no financial answers or hidden schemas."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from public_response_contract import append_public_contract, public_success_example, validate_public_response_contract


@pytest.fixture
def instruction():
    return append_public_contract('''Return exactly one JSON object:
```json
{"value":0,"unit":"%","period":"two reporting periods","source":"vn_quote_history","note":"optional"}
```
source is the exact tool name in the catalog.
''')


def answer(**updates):
    return dict(value=1.25, unit='%', period='synthetic reporting period', source='vn_quote_history', evidence=[], **updates)


def check(instruction, value):
    return validate_public_response_contract(instruction, json.dumps(value))


def test_valid_number_and_optional_note(instruction):
    assert check(instruction, answer())['valid']
    assert check(instruction, answer(note='explanation'))['valid']


@pytest.mark.parametrize('missing', ['period', 'source'])
def test_numeric_answer_does_not_excuse_missing_public_fields(instruction, missing):
    value = answer()
    del value[missing]
    result = check(instruction, value)
    assert not result['valid']
    assert 'Missing requested field: '+missing in result['errors']


# v4.6-update: the SOLE fenced JSON render moved to the accepted class
# (test_sole_fenced_json_accepted_bare_equivalent) per the contract change;
# prose-prefix and doubled objects remain rejected.
@pytest.mark.parametrize('render', [lambda s:'Answer: '+s, lambda s:s+' '+s])
def test_transport_requires_literal_single_json_object(instruction, render):
    assert not validate_public_response_contract(instruction, render(json.dumps(answer())))['valid']


@pytest.mark.parametrize('value', [[], 1, 'text', None])
def test_nonobjects_rejected(instruction, value):
    assert not check(instruction, value)['valid']


def test_source_is_tool_namespace_not_provider(instruction):
    value = answer()
    value['source'] = 'Synthetic provider'
    assert not check(instruction, value)['valid']


def test_global_catalog_tool_absent_from_task_is_rejected(instruction):
    value = answer()
    value['source'] = 'symbol_resolve'
    # This canonical name is globally valid, but not registered for this task.
    assert check(instruction, value)['valid']
    result = validate_public_response_contract(instruction, json.dumps(value), ['vn_quote_history'])
    assert not result['valid']
    assert any('exact registered tool names' in error for error in result['errors'])


@pytest.mark.parametrize('field,value', [('value',True), ('period',2026), ('evidence',{})])
def test_required_json_types(instruction, field, value):
    response = answer()
    response[field] = value
    assert not check(instruction, response)['valid']


def test_uniform_refusal_also_applies_to_aggregation():
    instruction = append_public_contract('```json\n{"values":{},"ranking":[],"period":"reporting periods","source":"vn_quote_history"}\n```')
    refusal = {'value':None, 'reason':'No supported response establishes this assertion.', 'evidence':[]}
    assert check(instruction, refusal) == {'valid':True, 'errors':[], 'branch':'refusal'}
    for update in ({'values':{'synthetic':1}}, {'reason':''}, {'reason':4}, {'evidence':{}}, {'value':'null'}):
        assert not check(instruction, dict(refusal, **update))['valid']


def test_explicit_public_nullable_field(instruction):
    value = answer()
    value['source'] = None
    assert check(instruction+'\nsource: null is allowed.', value)['valid']
    assert not check(instruction, value)['valid']


def test_unsupported_public_shape_fails_transparently():
    for text in ('No public JSON example', '```json\n[]\n```', '```json\n{}\n```\n```json\n{}\n```'):
        result = validate_public_response_contract(text, '{}')
        assert not result['valid'] and result['errors'][0].startswith('unsupported_public_contract:')


def test_all_282_development_main_holdout_instructions_have_supported_single_example():
    # Batch-3 memory corpus (user-authorized 2026-11-10): +18 main fin-mem + 10 holdout fin-mem.
    instructions = list((ROOT/'tasks').glob('*/*/instruction.md'))
    # Main amendment 2026-11-10: +50 migrated financial holdout tasks (60-task holdout).
    # Amendment 2026-11-11 (d): 114 tasks retired to tasks-retired (not matched by this glob); +88 compute/memory
    # tasks (main 60, holdout 14, pilot 14) -> 306.
    assert len(instructions) == 306
    for path in instructions:
        assert isinstance(public_success_example(path.read_text()), dict), path


@pytest.mark.parametrize('arm', ['opentrading', 'opentrading_baseline', 'opencode', 'dsh'])
def test_common_endpoint_preserves_semantic_and_frozen_results(tmp_path, monkeypatch, instruction, arm):
    import run_benchmark as rb
    task = tmp_path/'task'
    (task/'environment').mkdir(parents=True)
    (task/'solution').mkdir()
    (task/'solution/gold.json').write_text(json.dumps({'scoring':'value','expects':[]}))
    (task/'instruction.md').write_text(instruction)
    (task/'environment/payloads.json').write_text('{"snapshot_date":"2026-11-01","tools":{}}')
    response = answer()
    del response['period']
    monkeypatch.setattr(rb, 'run_trial', lambda *a, **k: {'status':'ok', 'final_text':json.dumps(response), 'workspace':a[1], 'tokens':{'input':1,'output':1}, 'provider_requests':1})
    monkeypatch.setattr(rb, 'grade_answer', lambda *a, **k: {'success':True,'fp':0,'error_type':None,'raw':{'semantic_correctness':True}})
    monkeypatch.setattr(rb, 'grounded_answer', lambda *a: True)
    monkeypatch.setattr(rb, 'read_task_meta', lambda *a: {})
    monkeypatch.setattr(rb, 'load_ledger', lambda *a: [])
    result = rb.execute_trial({'task':'synthetic','arm':arm,'run':1,'trial_id':'synthetic'}, str(task), str(tmp_path/'out'), 'offline', 240)
    assert result['semantic_correctness'] and result['frozen_v41_success'] and result['frozen_v3_success']
    assert not result['success'] and not result['contract_correctness'] and not result['public_contract_valid']
    assert result['error_type'] == 'public_contract_invalid'

def test_sole_fenced_json_accepted_bare_equivalent():
 # v4.6-update: a SOLE fenced JSON with whitespace outside is equivalent to the
 # bare object (grounded metric fence acceptance; fix for fence-style models).
 import json as _json
 instruction = append_public_contract('Giá KDH?\n```json\n{"value":0,"unit":"u","period":"p","source":"vn_quote_history"}\n```')
 ev = [{"tool":"vn_quote_history","source":"s","as_of":"2026-11-02","call_id":"c","payload_sha256":"a","response_sha256":"b"}]
 obj = {"value":21,"unit":"nghìn đồng","period":"2026-10-29","source":"vn_quote_history","evidence":ev}
 fenced = '```json\n' + _json.dumps(obj, ensure_ascii=False) + '\n```'
 assert validate_public_response_contract(instruction, fenced)['valid'] is True
 assert validate_public_response_contract(instruction, _json.dumps(obj, ensure_ascii=False))['valid'] is True
 assert validate_public_response_contract(instruction, fenced + '\nprose')['valid'] is False
 two = fenced + '\n```json\n{"value":22}\n```'
 assert validate_public_response_contract(instruction, two)['valid'] is False
