"""Operational certification separates measured model mistakes from broken paths."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ready_check as RC
import run_manifest as RM
from mcp_snapshot_server import load_entries, replay_call, build_tool_defs
from build_main import synthesize


@pytest.fixture
def smoke(tmp_path, monkeypatch):
    monkeypatch.setattr(RM, 'code_fingerprint', lambda: {'test-code': 'frozen'})
    monkeypatch.setattr(RM, 'harness_inventory', lambda *args: {'test-harness': 'frozen'})
    model = 'nvidia/nvidia/nemotron-3.5-bolt-e4b'
    config = {'model': model}
    tasks = sorted((RC.ROOT/'tasks'/'smoke').iterdir())
    settings = {'model': model, 'effort': 'none', 'runs': 2, 'arms': ['opencode','dsh','opentrading'],
                'split': 'smoke', 'seed': 42}
    manifest = RM.prepare_manifest(tmp_path, settings, tasks, config)
    rows = []
    for index, item in enumerate(manifest['plan']['schedule']):
        task = RC.ROOT/'tasks'/'smoke'/item['task']
        directory = tmp_path/str(index)
        directory.mkdir()
        payload = task/'environment'/'payloads.json'
        entries, _ = load_entries(payload)
        entry = entries[0][1]
        ledger = directory/'mcp.jsonl'
        primary = item['task'] == 'smoke-quote-01'
        arguments = entry['params'] if primary else {'__invalid_snapshot_request__': True}
        envelope = replay_call(entries, entry['tool'], arguments, RM.hash_file(payload), str(ledger))
        answer = synthesize(json.loads((task/'solution'/'gold.json').read_text())) if primary else None
        if primary:
            answer['evidence'] = [envelope['benchmark_evidence']]
        names = ['opentrading_'+d['name'] for d in build_tool_defs(entries)]
        provider = [{'status': 200, 'request_model': model.removeprefix('nvidia/'),
                     'response_models': [model.removeprefix('nvidia/')], 'effort': None,
                     'tool_names': names, 'tool_call_count': 1,
                     'usage': {'prompt_tokens': 12, 'completion_tokens': 3}}]
        # Synthetic fixture only: body capture is exercised; no model call is made.
        from runners.provider import ProviderGateway
        gate = ProviderGateway.__new__(ProviderGateway)
        gate.ledger, gate.rows, gate.key, gate.token = directory/'provider.jsonl', [], 'fixture-secret', 'fixture-token'
        body = {'model': model.removeprefix('nvidia/'), 'messages': [{'role': 'user', 'content': 'fixture'}],
                'tools': [{'function': {'name': name}} for name in names], 'temperature': 0, 'top_p': 1, 'max_tokens': 2048}
        provider[0]['effective_max_tokens'] = 2048
        import hashlib
        provider[0]['message_sha256'] = hashlib.sha256(json.dumps(body['messages'], sort_keys=True).encode()).hexdigest()
        provider[0]['tool_schema_sha256'] = hashlib.sha256(json.dumps(body['tools'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        for stage in ('native', 'effective'):
            provider[0][stage+'_request_capture'] = gate.capture_request(json.dumps(body).encode(), body, stage)
        provider_path = directory/'provider.jsonl'
        provider_path.write_text(json.dumps(provider[0])+'\n')
        inventory = {'arm': item['arm'], 'model': model.removeprefix('nvidia/'), 'provider': 'nvidia',
                     'effort': 'none', 'skills': [], 'external_plugins': [], 'usage_complete': True,
                     'observed_tool_sets': [names]}
        from experiment_conditions import condition, prompt_directory
        inventory.update(condition=item['arm'], **condition(item['arm']))
        inventory['clock_policy'] = {'answer_as_of': '2026-11-01', 'native_now_pinned': item['arm'] == 'opentrading'}
        if item['arm'] == 'opentrading':
            prompt_dir = prompt_directory('finance')
            inventory.update(prompt_directory=str(prompt_dir), prompt_files={p.name: RM.hash_file(p) for p in sorted(prompt_dir.glob('*.md'))})
        inv_path = directory/'inventory.json'
        inv_path.write_text(json.dumps(inventory))
        attempt = {'ledger_path': str(ledger), 'provider_ledger': str(provider_path),
                   'inventory_path': str(inv_path), 'final_text': json.dumps(answer) if answer else 'bad model answer'}
        rows.append(dict(item, manifest_sha256=manifest['fingerprint'], model=model, status='ok', timely=True,
                         tokens={'input': 12, 'output': 3, 'complete': True}, requests=1, attempts=[attempt],
                         success=primary, mcp_calls=1, mcp_successful_calls=int(primary)))
    def write():
        (tmp_path/'trials.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    write()
    return tmp_path, config, model, rows, write


def test_operational_certificate_allows_explicit_rejections_as_quality_failures(smoke):
    path, config, model, _, _ = smoke
    proof = RC.validate_live_run(path, config, model)
    assert proof['n_trials'] == 18
    assert proof['snapshot_rejections'] == 12
    assert proof['model_quality_failures'] == 12


def test_zero_tool_model_response_needs_proven_zero_calls_and_complete_catalog(smoke):
    path, config, model, rows, write = smoke
    row = next(r for r in rows if not r['success'])
    Path(row['attempts'][0]['ledger_path']).unlink()
    row.update(mcp_calls=0, mcp_successful_calls=0)
    provider_path = Path(row['attempts'][0]['provider_ledger'])
    provider = json.loads(provider_path.read_text())
    provider['tool_call_count'] = 0
    provider_path.write_text(json.dumps(provider)+'\n')
    write()
    assert RC.validate_live_run(path, config, model)['n_trials'] == 18
    provider['tool_call_count'] = 1
    provider_path.write_text(json.dumps(provider)+'\n')
    with pytest.raises(ValueError, match='lack matching'):
        RC.validate_live_run(path, config, model)


@pytest.mark.parametrize('usage', [{}, {'prompt_tokens': -1, 'completion_tokens': 3},
                                  {'prompt_tokens': True, 'completion_tokens': 3},
                                  {'prompt_tokens': 12, 'completion_tokens': float('inf')},
                                  {'prompt_tokens': 12, 'completion_tokens': float('nan')}])
def test_certificate_requires_finite_nonnegative_authoritative_usage(smoke, usage):
    path, config, model, rows, _ = smoke
    provider_path = Path(rows[0]['attempts'][0]['provider_ledger'])
    provider = json.loads(provider_path.read_text())
    provider['usage'] = usage
    provider_path.write_text(json.dumps(provider)+'\n')
    with pytest.raises(ValueError, match='Provider wire'):
        RC.validate_live_run(path, config, model)


@pytest.mark.parametrize('field,value', [('requests', 2), ('input', 999), ('output', True)])
def test_certificate_recomputes_trial_usage_from_provider_ledger(smoke, field, value):
    path, config, model, rows, write = smoke
    if field == 'requests':
        rows[0][field] = value
    else:
        rows[0]['tokens'][field] = value
    write()
    with pytest.raises(ValueError, match='usage totals'):
        RC.validate_live_run(path, config, model)


@pytest.mark.parametrize('failure', ['all_rejected', 'invented_evidence', 'malformed_ledger',
                                    'server_error', 'unknown_usage', 'missing_tool', 'timeout'])
def test_operational_certificate_rejects_broken_paths_and_fake_canaries(smoke, failure):
    path, config, model, rows, write = smoke
    row = next(r for r in rows if r['success'])
    attempt = row['attempts'][0]
    if failure == 'all_rejected':
        for r in rows:
            r['success'] = False
    elif failure == 'invented_evidence':
        answer = json.loads(attempt['final_text'])
        answer['evidence'][0]['call_id'] = 'invented'
        attempt['final_text'] = json.dumps(answer)
    elif failure == 'malformed_ledger':
        Path(attempt['ledger_path']).write_text('{truncated')
    elif failure == 'server_error':
        record = json.loads(Path(attempt['ledger_path']).read_text())
        record.update(status='rejected', error='Server crashed')
        Path(attempt['ledger_path']).write_text(json.dumps(record)+'\n')
    elif failure == 'unknown_usage':
        row['tokens']['complete'] = False
    elif failure == 'missing_tool':
        provider = json.loads(Path(attempt['provider_ledger']).read_text())
        provider['tool_names'] = []
        Path(attempt['provider_ledger']).write_text(json.dumps(provider)+'\n')
        inventory = json.loads(Path(attempt['inventory_path']).read_text())
        inventory['observed_tool_sets'] = [[]]
        Path(attempt['inventory_path']).write_text(json.dumps(inventory))
    elif failure == 'timeout':
        row['status'] = 'timeout'
    write()
    with pytest.raises((ValueError, json.JSONDecodeError)):
        RC.validate_live_run(path, config, model)


def test_certificate_rejects_modified_raw_provider_capture(smoke):
    path, config, model, rows, _ = smoke
    provider_path = Path(rows[0]['attempts'][0]['provider_ledger'])
    request = json.loads(provider_path.read_text())
    target = Path(request['effective_request_capture']['path'])
    target.write_text(target.read_text()+' ')
    with pytest.raises(ValueError, match='raw capture hash'):
        RC.validate_live_run(path, config, model)


def test_certificate_rejects_wrong_prompt_variant_inventory(smoke):
    path, config, model, rows, _ = smoke
    row = next(r for r in rows if r['arm'] == 'opentrading')
    target = Path(row['attempts'][0]['inventory_path'])
    data = json.loads(target.read_text())
    data['prompt_variant'] = 'baseline'
    target.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='condition/variant'):
        RC.validate_live_run(path, config, model)


def test_certificate_rejects_effective_message_rewrite_even_with_rehashed_capture(smoke):
    path, config, model, rows, _ = smoke
    provider_path = Path(rows[0]['attempts'][0]['provider_ledger'])
    request = json.loads(provider_path.read_text())
    from runners.provider import ProviderGateway
    gate = ProviderGateway.__new__(ProviderGateway)
    gate.ledger, gate.rows, gate.key, gate.token = provider_path, [], 'fixture-secret', 'fixture-token'
    effective = json.loads(Path(request['effective_request_capture']['path']).read_text())
    effective['messages'][0]['content'] = 'Different prompt'
    request['effective_request_capture'] = gate.capture_request(json.dumps(effective).encode(), effective, 'effective')
    provider_path.write_text(json.dumps(request)+'\n')
    with pytest.raises(ValueError, match='outside declared'):
        RC.validate_live_run(path, config, model)
