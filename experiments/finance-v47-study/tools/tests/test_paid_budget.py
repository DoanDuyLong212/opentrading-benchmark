"""Synthetic offline evidence only; these fixtures never approve a live key/run."""
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import runpy
import sys
import urllib.error
import io

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(TOOLS), str(TOOLS/'runners')]
import paid_budget as pb
import provider
import run_benchmark as rb
HELPERS = runpy.run_path(str(TOOLS/'tests/test_provider_runner.py'))
MODEL = 'deepseek/deepseek-v4.1-flash-1017'
FREE_MODEL = 'nvidia/nemotron-3-ultra-550b-a55b:free'


def policy_fixture(tmp_path, cap='1', bound='.4', context=4000):
    now = datetime.now(timezone.utc)
    receipt = {'status': 'reviewed_provider_evidence', 'verified_at': now.isoformat(),
        'expires_at': (now+timedelta(hours=1)).isoformat(), 'model': MODEL,
        'route': 'openrouter_paid', 'endpoint': 'https://openrouter.ai/api/v1/chat/completions',
        'provider_host': 'synthetic-offline-host', 'dedicated_key': True, 'byok_disabled': True,
        'key_limit': {'limit': 2, 'limit_remaining': 2, 'usage': 0, 'limit_reset': None},
        'key_fingerprint': hashlib.sha256(b'offline-fixture-key').hexdigest(),
        'key_response_sha256': 'a'*64, 'bound_evidence_sha256': 'b'*64,
        'attempt_upper_bound_usd': bound, 'context_tokens': context, 'output_tokens': 2048,
        'bound_scope': 'all_billable_text_features_no_cache_discount',
        'bound_evidence': 'SYNTHETIC TEST ONLY - NO PROVIDER EVIDENCE',
        'allocation_path': str(tmp_path/'allocation.json')}
    receipt_path = tmp_path/'synthetic-receipt.json'
    receipt_path.write_text(json.dumps(receipt))
    options = {'provider_route': 'openrouter_paid', 'budget_usd': cap,
        'paid_budget_receipt': str(receipt_path),
        'paid_budget_receipt_sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        'failed_attempt_context_bound': context, 'max_output_tokens': 2048}
    return options, receipt


def make_budget(tmp_path, cap='1', bound='.4', context=4000):
    options, _ = policy_fixture(tmp_path, cap, bound, context)
    budget = pb.open_run_budget(tmp_path/'run', 'f'*64, MODEL, options)
    return budget, options


def _compete(path, contract, queue):
    try:
        b = pb.PaidBudget(path, contract)
        queue.put(('admitted', b.reserve({'process': os.getpid()})))
    except pb.BudgetError:
        queue.put(('blocked', None))


def _crash_reserved(path, contract):
    pb.PaidBudget(path, contract).reserve({'crash': 'after fsync before network/result'})
    os._exit(0)


def test_decimal_boundary_resume_and_idempotence(tmp_path):
    budget, options = make_budget(tmp_path, cap='.6', bound='.2')
    for n in range(3):
        identity = budget.reserve({'trial': n, 'arm': ['ot','opencode','memory'][n]})
        budget.settle(identity, Decimal('.2'), {'response': str(n)})
        budget.settle(identity, Decimal('.2'), {'response': str(n)})
    before = budget.path.read_bytes()
    resumed = pb.open_run_budget(tmp_path/'run', 'f'*64, MODEL, options, resume=True)
    assert resumed.summary()['measured_cost_usd'] == '0.6'
    with pytest.raises(pb.BudgetError, match='exhausted'):
        resumed.reserve({'trial': 4})
    assert budget.path.read_bytes() == before
    with pytest.raises(pb.BudgetError, match='conflicting'):
        budget.settle(identity, '.1', {'response': '2'})


def test_two_processes_only_one_last_reservation(tmp_path):
    budget, _ = make_budget(tmp_path, cap='.4')
    ctx = multiprocessing.get_context('fork')
    queue = ctx.Queue()
    workers = [ctx.Process(target=_compete, args=(str(budget.path), budget.contract, queue)) for _ in range(2)]
    for process in workers: process.start()
    for process in workers: process.join(10); assert process.exitcode == 0
    assert sorted(queue.get(timeout=2)[0] for _ in workers) == ['admitted', 'blocked']
    assert budget.summary()['reserved_usd'] == '0.4'


def test_crashed_process_keeps_unknown_charge_and_blocks_other_trials(tmp_path):
    budget, _ = make_budget(tmp_path)
    process = multiprocessing.get_context('fork').Process(target=_crash_reserved, args=(str(budget.path), budget.contract))
    process.start(); process.join(10); assert process.exitcode == 0
    resumed = pb.PaidBudget(budget.path, budget.contract)
    assert resumed.summary()['unknown_requests'] == 1
    with pytest.raises(pb.BudgetError, match='unresolved'):
        resumed.reserve({'trial': 'different-memory-episode'})


@pytest.mark.parametrize('damage', ['missing', 'truncated', 'suffix', 'interior', 'anchor'])
def test_corruption_and_suffix_deletion_never_reset_money(tmp_path, damage):
    budget, _ = make_budget(tmp_path)
    identity = budget.reserve({}); budget.settle(identity, '.2', {})
    if damage == 'missing': budget.path.unlink()
    elif damage == 'truncated': budget.path.write_bytes(budget.path.read_bytes()[:-1])
    elif damage == 'suffix': budget.path.write_bytes(b'\n'.join(budget.path.read_bytes().splitlines()[:-1])+b'\n')
    elif damage == 'interior': budget.path.write_bytes(budget.path.read_bytes().replace(b'0.4', b'0.3'))
    else: budget.allocation.write_text('{}')
    with pytest.raises(pb.BudgetError): pb.PaidBudget(budget.path, budget.contract, initialize=True)


def test_crash_after_checkpoint_before_append_requires_reconciliation(tmp_path, monkeypatch):
    budget, _ = make_budget(tmp_path)
    original = pb.atomic
    def fail_after_checkpoint(*args):
        original(*args)
        raise OSError('synthetic crash after checkpoint fsync')
    monkeypatch.setattr(pb, 'atomic', fail_after_checkpoint)
    with pytest.raises(OSError): budget.reserve({})
    monkeypatch.setattr(pb, 'atomic', original)
    with pytest.raises(pb.BudgetError, match='checkpoint'):
        pb.PaidBudget(budget.path, budget.contract)


def test_new_run_cannot_reuse_same_dedicated_allocation(tmp_path):
    budget, options = make_budget(tmp_path)
    with pytest.raises(pb.BudgetError): pb.open_run_budget(tmp_path/'second-run', 'e'*64, MODEL, options)
    changed = {**budget.contract, 'manifest_sha256': 'e'*64}
    with pytest.raises(pb.BudgetError): pb.PaidBudget(budget.path, changed)


def test_actual_charge_above_bound_is_durable_and_stops_cohort(tmp_path):
    budget, _ = make_budget(tmp_path)
    identity = budget.reserve({})
    with pytest.raises(pb.BudgetError, match='breached'): budget.settle(identity, '.4001', {})
    assert budget.summary()['measured_cost_usd'] == '0.4001'
    assert budget.summary()['bound_breached']
    with pytest.raises(pb.BudgetError): budget.reserve({})


@pytest.mark.parametrize('cap', [None, '0', '-1', 'NaN', 'Infinity', True])
def test_paid_bad_cap_rejected_before_receipt_or_credentials(tmp_path, cap):
    with pytest.raises(pb.BudgetError): pb.paid_policy(MODEL, {'provider_route':'openrouter_paid', 'budget_usd':cap})


@pytest.mark.parametrize('mutation', ['expired','unlimited','reset','wrong_model','hash','unreviewed','output','remaining'])
def test_invalid_receipt_rejected(tmp_path, mutation):
    options, receipt = policy_fixture(tmp_path)
    if mutation == 'expired': receipt['expires_at'] = '2000-01-01T00:00:00+00:00'
    elif mutation == 'unlimited': receipt['key_limit']['limit'] = None
    elif mutation == 'reset': receipt['key_limit']['limit_reset'] = 'daily'
    elif mutation == 'wrong_model': receipt['model'] = 'other'
    elif mutation == 'unreviewed': receipt['status'] = 'asserted'
    elif mutation == 'output': options['max_output_tokens'] = None
    elif mutation == 'remaining': receipt['key_limit']['limit_remaining'] = '.01'
    path = Path(options['paid_budget_receipt']); path.write_text(json.dumps(receipt))
    if mutation != 'hash': options['paid_budget_receipt_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    else: path.write_text(path.read_text()+' ')
    with pytest.raises(pb.BudgetError): pb.paid_policy(MODEL, options)


def paid_gateway(tmp_path, monkeypatch, cap='1', bound='.4', context=4000):
    gate = HELPERS['_gateway'](tmp_path, monkeypatch)
    gate.model = MODEL
    gate.budget, options = make_budget(tmp_path, cap, bound, context)
    gate.options.update(options, max_requests=10, max_total_tokens=100000)
    gate._or_budget_tick = lambda **_: None
    body = HELPERS['_body'](); body['model'] = MODEL
    return gate, body


class Response:
    status = 200
    headers = {'Content-Type': 'application/json', 'x-request-id': 'offline-request'}
    def __init__(self, raw): self.raw = raw
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read1(self, _): raw, self.raw = self.raw, b''; return raw


def raw_response(cost='.2', model=MODEL, finish='stop'):
    payload = {'id':'offline-generation','model':model,'choices':[{'finish_reason':finish,'message':{'content':'fixture'}}],
               'usage':{'prompt_tokens':17,'completion_tokens':3}}
    raw = json.dumps(payload).encode()
    if cost is not None and cost.startswith('.'): cost = '0' + cost
    if cost is not None: raw = raw.replace(b'"prompt_tokens": 17', b'"cost": '+cost.encode()+b', "prompt_tokens": 17')
    return raw


@pytest.mark.parametrize('stream', [False, True])
def test_reserve_fsync_before_network_and_cost_before_model_validation(tmp_path, monkeypatch, stream):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    body['stream'] = stream
    synced = []
    real_fsync = os.fsync
    def fsync(fd):
        synced.append(os.readlink('/proc/self/fd/'+str(fd))); real_fsync(fd)
    monkeypatch.setattr(pb.os, 'fsync', fsync)
    def fetch(req, **_):
        assert str(gate.budget.path) in synced
        assert gate.budget.summary()['unknown_requests'] == 1
        assert json.loads(req.data)['service_tier'] == 'default'
        assert json.loads(req.data)['provider'] == {'only':['synthetic-offline-host'], 'allow_fallbacks':False}
        raw = raw_response('.123456789012345678901', model='wrong')
        return Response(b'data: '+raw+b'\n\ndata: [DONE]\n\n' if stream else raw)
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    handler = HELPERS['_Handler'](body); gate.handle(handler)
    assert handler.response_status == 424
    assert gate.rows[-1]['error'] == 'provider_response_model_mismatch'
    assert gate.budget.summary()['measured_cost_usd'] == '0.123456789012345678901'
    assert gate.budget.summary()['unknown_requests'] == 0


@pytest.mark.parametrize('cost', [None,'null','true','-1','NaN','Infinity','".2"'])
def test_bad_or_missing_cost_blocks_transport_retry_and_next_trial(tmp_path, monkeypatch, cost):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    seen = []
    def fetch(*_, **__): seen.append(1); return Response(raw_response(cost))
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['error'] == 'paid_usage_cost_unknown'
    assert gate.budget.summary()['unknown_requests'] == 1
    body['messages'][0]['content'] = 'next trial'
    gate.handle(HELPERS['_Handler'](body))
    assert len(seen) == 1
    assert gate.budget.summary()['measured_cost_usd'] == '0'


def test_http_error_authoritative_cost_settles_before_retry(tmp_path, monkeypatch):
    gate, body = paid_gateway(tmp_path, monkeypatch, cap='.4', bound='.4')
    seen=[]
    def fetch(req, **_):
        seen.append(1)
        raise urllib.error.HTTPError(req.full_url, 502, 'fixture', {}, io.BytesIO(raw_response('.2')))
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    monkeypatch.setattr(provider, 'retry_delay', lambda *_: 0)
    gate.handle(HELPERS['_Handler'](body))
    assert len(seen) == 1  # Settled .2 + next .4 reservation cannot fit .4 cap.
    assert gate.budget.summary()['measured_cost_usd'] == '0.2'
    assert gate.budget.summary()['unknown_requests'] == 0


@pytest.mark.parametrize('failure', ['timeout','http','truncated'])
def test_transport_unknown_never_retries_paid(tmp_path, monkeypatch, failure):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    seen=[]
    def fetch(req, **_):
        seen.append(1)
        if failure == 'timeout': raise TimeoutError('fixture')
        if failure == 'http': raise urllib.error.HTTPError(req.full_url, 429, 'fixture', {}, io.BytesIO(b'{}'))
        return Response(b'data: '+raw_response()+b'\n')
    if failure == 'truncated': body['stream'] = True
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    gate.handle(HELPERS['_Handler'](body))
    assert len(seen) == 1 and gate.budget.summary()['unknown_requests'] == 1


def test_paid_missing_receipt_fails_before_credential_or_native_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(provider, 'credential', lambda: pytest.fail('credential access forbidden'))
    with pytest.raises(pb.BudgetError):
        provider.ProviderGateway(MODEL, tmp_path/'ledger', {'provider_route':'openrouter_paid','budget_usd':'1'})
    import isolated
    monkeypatch.setattr(isolated, 'clean_env', lambda *_: pytest.fail('native preparation forbidden'))
    with pytest.raises(pb.BudgetError):
        isolated.prepare(tmp_path/'ws', tmp_path/'task', MODEL, {'provider_route':'openrouter_paid','budget_usd':'1'})


def test_free_exemption_requires_exact_identity_and_detects_charge(tmp_path, monkeypatch):
    with pytest.raises(pb.BudgetError): pb.validate_free_identity(MODEL, {'provider_route':'openrouter_free'})
    gate = HELPERS['_gateway'](tmp_path, monkeypatch)
    gate.model = FREE_MODEL
    gate.options['provider_route'] = 'openrouter_free'
    gate._or_budget_tick = lambda **_: None
    body = HELPERS['_body'](); body['model'] = gate.model
    monkeypatch.setattr(provider.urllib.request, 'urlopen', lambda *_, **__: Response(raw_response('0', model=gate.model)))
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['status'] == 200 and gate.rows[-1]['measured_cost_usd'] == '0'
    gate.options['max_requests'] = 3
    body['messages'][0]['content'] = 'charged route'
    monkeypatch.setattr(provider.urllib.request, 'urlopen', lambda *_, **__: Response(raw_response('.01', model=gate.model)))
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['error'] == 'free_route_charged'
    assert gate.free_cost_breach


def test_effective_caps_come_from_actual_config_before_manifest():
    args = argparse.Namespace(effort='none',max_requests=24,max_output_tokens=2048,max_total_tokens=48000,
        provider_timeout_s=20, budget_usd=None, model=None)
    cfg = {'model':FREE_MODEL,'provider_options':{'provider_route':'openrouter_free',
        'max_requests':9,'memory_max_requests':48,'max_output_tokens':None,'max_total_tokens':99999,'provider_timeout_s':240}}
    options = rb.effective_provider_options(args, cfg)
    assert [options[k] for k in ('max_requests','memory_max_requests','max_output_tokens','max_total_tokens','provider_timeout_s')] == [9,48,None,99999,240]


def test_actual_driver_freezes_effective_caps_and_paid_completed_resume(tmp_path, monkeypatch):
    helpers = runpy.run_path(str(TOOLS/'tests/test_v45_execution.py'))
    out, calls, argv = helpers['cli_fixture'](tmp_path, monkeypatch)
    options, _ = policy_fixture(tmp_path)
    options.update(max_requests=7, memory_max_requests=11, max_total_tokens=123456, provider_timeout_s=77)
    config = Path(argv[argv.index('--config')+1])
    config.write_text(json.dumps({'model':MODEL,'provider_options':options}))
    def trial(*args, options=None, **kwargs):
        options = options or args[-1]
        calls.append(options['trial_id'])
        journal = pb.PaidBudget(options['paid_budget_journal'], options['paid_budget_contract'])
        identity = journal.reserve({'trial_id':options['trial_id']})
        journal.settle(identity, '.1', {'synthetic':True})
        return {'status':'ok','final_text':'{"value":0,"evidence":[]}', 'tokens':None, 'provider_requests':1}
    monkeypatch.setattr(rb, 'run_trial', trial)
    monkeypatch.setattr(rb, 'grade_answer', lambda *_, **__: {'success':False,'fp':0,'error_type':'fixture','raw':{}})
    argv += ['--budget-usd','1']
    monkeypatch.setattr(sys, 'argv', argv); rb.main()
    settings = json.loads((out/'manifest.json').read_text())['plan']['settings']
    assert (settings['max_requests'],settings['provider_timeout_s']) == (7,77)
    assert settings['effective_provider_options']['memory_max_requests'] == 11
    assert settings['transport_attempts_per_request'] == 3
    assert settings['trial_timeouts_s'] == {'v45-dev-01-quote':900}
    original = (out/'paid-budget.jsonl').read_bytes()
    monkeypatch.setattr(sys, 'argv', argv+['--resume']); rb.main()
    assert len(calls) == 2 and (out/'paid-budget.jsonl').read_bytes() == original
    assert json.loads((out/'summary.json').read_text())['paid_budget']['measured_cost_usd'] == '0.2'
    monkeypatch.setattr(sys, 'argv', argv[:-1]+['2','--resume'])
    with pytest.raises(ValueError, match='differs from frozen provider_options'): rb.main()
    assert len(calls) == 2 and (out/'paid-budget.jsonl').read_bytes() == original


def test_memory_episode_uses_resolved_request_cap_and_shared_journal(tmp_path, monkeypatch):
    import memory_runner
    captured = {}
    class Episode:
        def __init__(self, ws, task, model, arm, options): captured.update(options)
        def run(self, turns): return {'status':'completed','completed_turns':[]}
    monkeypatch.setattr(memory_runner, 'MemoryEpisode', Episode)
    monkeypatch.setattr(rb, 'memory_turns', lambda _: [])
    monkeypatch.delenv('BENCH_V47_DEV', raising=False)
    options={'max_requests':11,'memory_max_requests':48,'paid_budget_journal':'shared-run-journal',
             'paid_budget_contract':{'identity':'same-across-turns'}}
    rb.run_memory_trial('opencode', str(tmp_path/'ws'), str(tmp_path/'task'), MODEL, 900, str(tmp_path/'log'), options)
    assert captured['max_requests'] == 11  # A retry's remaining cap cannot reset to memory48.
    assert captured['paid_budget_journal'] == 'shared-run-journal'
    assert captured['paid_budget_contract'] == options['paid_budget_contract']


def test_text_parts_accepted_but_media_denied_before_dispatch(tmp_path, monkeypatch):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    body['messages'][0]['content'] = [{'type':'text','text':'quote'}]
    seen=[]
    def fetch(*_, **__): seen.append(1); return Response(raw_response('0.1'))
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['status'] == 200
    body['messages'][0]['content'] = [{'type':'image_url','image_url':{'url':'https://example.invalid/media'}}]
    gate.handle(HELPERS['_Handler'](body))
    assert len(seen) == 1 and gate.budget.summary()['unknown_requests'] == 0


def test_reported_provider_drift_settles_charge_then_persists_halt(tmp_path, monkeypatch):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    raw = json.loads(raw_response('0.1')); raw['provider'] = 'unapproved-host'
    seen=[]
    def fetch(*_, **__): seen.append(1); return Response(json.dumps(raw).encode())
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['error'] == 'paid_provider_host_mismatch'
    assert gate.budget.summary()['measured_cost_usd'] == '0.1'
    assert gate.budget.summary()['halted']
    with pytest.raises(pb.BudgetError): pb.PaidBudget(gate.budget.path, gate.budget.contract).reserve({'trial':'next'})
    assert len(seen) == 1


def test_expired_receipt_allows_accounting_only_but_no_new_dispatch(tmp_path, monkeypatch):
    budget, options = make_budget(tmp_path)
    identity = budget.reserve({}); budget.settle(identity, '.1', {})
    class Later(datetime):
        @classmethod
        def now(cls, tz=None): return datetime.now(timezone.utc)+timedelta(days=2)
    monkeypatch.setattr(pb, 'datetime', Later)
    before = budget.path.read_bytes()
    with pytest.raises(pb.BudgetError, match='current reviewed'):
        pb.open_run_budget(tmp_path/'run', 'f'*64, MODEL, options, resume=True)
    historical = pb.open_run_budget(tmp_path/'run', 'f'*64, MODEL, options, resume=True, accounting_only=True)
    assert historical.summary()['measured_cost_usd'] == '0.1'
    with pytest.raises(pb.BudgetError, match='accounting-only'): historical.reserve({})
    assert budget.path.read_bytes() == before


def test_free_admission_bound_and_not_arbitrary_route_flag():
    # Free dev-smoke identity (Nemotron :free); the active v4.7 config is the paid DeepSeek route below.
    free = 'nvidia/nemotron-3-ultra-550b-a55b:free'
    options = {'provider_route': 'openrouter_free', 'model_max_output_tokens': 65536}
    sha = pb.validate_free_identity(free, options)
    assert len(sha) == 64
    with pytest.raises(pb.BudgetError):
        pb.validate_free_identity(free, {**options, 'free_admission_sha256':'0'*64})
    with pytest.raises(pb.BudgetError):
        pb.validate_free_identity('arbitrary/paid:free', options)


def test_active_v47_config_is_paid_deepseek_and_fails_closed_without_receipt():
    cfg = json.loads((TOOLS/'bench_config_v47.json').read_text())
    options = cfg['provider_options']
    assert cfg['model'] == 'deepseek/deepseek-v4.1-flash-1017' and cfg['allowed_models'] == [cfg['model']]
    assert options['provider_route'] == 'openrouter_paid'
    assert pb.validate_free_identity(cfg['model'], options) is None
    with pytest.raises(pb.BudgetError):
        pb.paid_policy(cfg['model'], {**options, 'budget_usd': '1'})


@pytest.mark.parametrize('extension', [{'n':8}, {'n':True}, {'service_tier':'priority'}, {'service_tier':'auto'}, {'speed':'fast'}, {'preset':'priority-fixture'}, {'best_of':4}, {'reasoning':{'max_tokens':100000}}, {'unreviewed_extension':True}])
def test_paid_extensions_cannot_multiply_or_change_reserved_charge(tmp_path, monkeypatch, extension):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    body.update(extension)
    monkeypatch.setattr(provider.urllib.request, 'urlopen', lambda *_, **__: pytest.fail('unsupported extension dispatched'))
    before = gate.budget.path.read_bytes()
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['status'] == 424
    assert not gate.rows[-1]['upstream_attempted']
    assert gate.budget.path.read_bytes() == before


def test_paid_rejects_hidden_media_message_fields(tmp_path, monkeypatch):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    body['messages'][0]['audio'] = {'id':'unsupported-media'}
    monkeypatch.setattr(provider.urllib.request, 'urlopen', lambda *_, **__: pytest.fail('media dispatched'))
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['status'] == 424 and gate.budget.summary()['unknown_requests'] == 0


@pytest.mark.parametrize('location', ['request', 'message', 'text_part', 'tool'])
def test_paid_explicit_cache_control_requires_separately_reviewed_bound(tmp_path, monkeypatch, location):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    cache = {'type': 'ephemeral'}
    if location == 'request':
        body['cache_control'] = cache
    elif location == 'message':
        body['messages'][0]['cache_control'] = cache
    elif location == 'text_part':
        body['messages'][0]['content'] = [{'type': 'text', 'text': 'fixture', 'cache_control': cache}]
    else:
        body['tools'][0]['cache_control'] = cache
    monkeypatch.setattr(provider.urllib.request, 'urlopen', lambda *_, **__: pytest.fail('cache extension dispatched'))
    before = gate.budget.path.read_bytes()
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['status'] == 424 and not gate.rows[-1]['upstream_attempted']
    assert gate.budget.path.read_bytes() == before
    assert gate.budget.summary()['unknown_requests'] == 0


@pytest.mark.parametrize('index', [0,1,2])
def test_paid_accepts_actual_normalized_native_wire_text_shapes(tmp_path, monkeypatch, index):
    gate, _ = paid_gateway(tmp_path, monkeypatch, context=48000)
    artifact = json.loads((TOOLS/'tests/fixtures/historical-v44-native-wire.json').read_text())
    body = artifact['bodies'][index]; body['model'] = MODEL
    gate.options.update(allowed_tool_names=['mcp__opentrading__quote'],
                        snapshot_tool_definitions=[{'name':'quote'}])
    monkeypatch.setattr(provider.urllib.request, 'urlopen', lambda *_, **__: Response(b'data: '+raw_response('0.1')+b'\n\ndata: [DONE]\n\n'))
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['status'] == 200, gate.rows[-1].get('error')
    assert gate.budget.summary()['measured_cost_usd'] == '0.1'


@pytest.mark.parametrize('cap', [-1, True, float('nan'), 1.5])
def test_paid_invalid_requested_output_cap_never_dispatches(tmp_path, monkeypatch, cap):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    body['max_tokens'] = cap
    monkeypatch.setattr(provider.urllib.request, 'urlopen', lambda *_, **__: pytest.fail('invalid requested cap dispatched'))
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['status'] == 424 and not gate.rows[-1]['upstream_attempted']
    assert gate.budget.summary()['unknown_requests'] == 0


def _http_error(status, raw, retry_after='0'):
    import io, urllib.error
    return urllib.error.HTTPError('https://openrouter.ai/api/v1/chat/completions', status, 'err',
                                  {'Retry-After': retry_after}, io.BytesIO(raw))


def test_pre_generation_rate_limit_settles_zero_then_retries(tmp_path, monkeypatch):
    # Live 2026-11-24 (Tenstorrent): HTTP 429 with only an error object; no generation, nothing billed.
    gate, body = paid_gateway(tmp_path, monkeypatch)
    gate.options['failed_attempt_token_reservation'] = 5000
    monkeypatch.setattr(provider, 'retry_delay', lambda *a, **k: 0)
    limited = json.dumps({'error': {'message': 'Provider returned error', 'code': 429, 'metadata': {
        'provider_name': 'synthetic-offline-host', 'provider_error_code': 'rate_limit_exceeded'}},
        'user_id': 'u'}).encode()
    calls = []
    def fetch(*_, **__):
        calls.append(1)
        if len(calls) == 1: raise _http_error(429, limited)
        return Response(raw_response('.2'))
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    handler = HELPERS['_Handler'](body); gate.handle(handler)
    assert len(calls) == 2 and handler.response_status == 200
    summary = gate.budget.summary()
    assert summary['unknown_requests'] == 0 and summary['measured_cost_usd'] == '0.2'


@pytest.mark.parametrize('raw', [
    b'not json',
    json.dumps({'error': {'code': 502}, 'choices': []}).encode(),
    json.dumps({'id': 'gen-1', 'error': {'code': 502}}).encode(),
])
def test_http_error_with_possible_generation_stays_cost_unknown(tmp_path, monkeypatch, raw):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    def fetch(*_, **__): raise _http_error(502, raw)
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    gate.handle(HELPERS['_Handler'](body))
    assert gate.rows[-1]['error'] == 'paid_usage_cost_unknown'
    assert gate.budget.summary()['unknown_requests'] == 1


def test_http_error_carrying_cost_is_billed_not_zeroed(tmp_path, monkeypatch):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    raw = json.dumps({'error': {'code': 502}, 'usage': {'cost': 0.1}}).encode()
    def fetch(*_, **__): raise _http_error(502, raw)
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    gate.handle(HELPERS['_Handler'](body))
    assert gate.budget.summary()['measured_cost_usd'] == '0.1'


@pytest.mark.parametrize('value,ok', [('', True), ('thought', True), (None, True), ({'x': 1}, False), (['a'], False)])
def test_opencode_reasoning_content_text_only(tmp_path, monkeypatch, value, ok):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    body['messages'].append({'role': 'assistant', 'content': 'x', 'reasoning_content': value})
    body['messages'].append({'role': 'user', 'content': 'next'})
    sent = []
    def fetch(*_, **__): sent.append(1); return Response(raw_response('.2'))
    monkeypatch.setattr(provider.urllib.request, 'urlopen', fetch)
    gate.handle(HELPERS['_Handler'](body))
    assert bool(sent) is ok


def test_budget_mode_init_resume_refuse(tmp_path):
    import run_benchmark as rb
    out = tmp_path / 'run'; out.mkdir()
    assert rb.budget_resume_mode(out, False) == 'init'
    assert rb.budget_resume_mode(out, True) == 'init'          # presealed manifest, nothing run yet
    (out / 'paid-budget.jsonl').write_text('')
    assert rb.budget_resume_mode(out, True) == 'resume'
    (out / 'paid-budget.jsonl').unlink(); (out / 'trials.jsonl').write_text('')
    assert rb.budget_resume_mode(out, True) == 'refuse'        # trials but the money record is gone


def _renew_receipt(tmp_path, options, receipt, name, **change):
    receipt = {**receipt, **change}
    path = tmp_path / name; path.write_text(json.dumps(receipt))
    return {'paid_budget_receipt': str(path), 'paid_budget_receipt_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'approved_by': 'owner-test', 'decision': 'synthetic'}


def test_paid_resume_spends_and_keeps_cumulative_cap(tmp_path):
    import run_benchmark as rb
    options, receipt = policy_fixture(tmp_path, cap='1', bound='.4')
    out = tmp_path / 'run'
    budget = rb.open_budget_for_run(out, 'f'*64, MODEL, options, False)
    budget.settle(budget.reserve({'t': 1}), '.3', {})
    resumed = rb.open_budget_for_run(out, 'f'*64, MODEL, dict(options), True)
    assert not resumed.read_only
    resumed.settle(resumed.reserve({'t': 2}), '.3', {})
    resumed.settle(resumed.reserve({'t': 3}), '.3', {})        # .6 + .4 = 1.0: exactly at the cap is allowed
    again = rb.open_budget_for_run(out, 'f'*64, MODEL, dict(options), True)
    with pytest.raises(pb.BudgetError, match='exhausted'):
        again.reserve({'t': 4})                                  # .9 + .4 > 1 across resumes
    assert again.summary()['measured_cost_usd'] == '0.9'


def test_paid_resume_refuses_other_manifest_pending_halt(tmp_path):
    import run_benchmark as rb
    options, _ = policy_fixture(tmp_path, cap='2', bound='.4')
    out = tmp_path / 'run'
    budget = rb.open_budget_for_run(out, 'f'*64, MODEL, options, False)
    with pytest.raises(pb.BudgetError, match='another run'):
        rb.open_budget_for_run(out, 'e'*64, MODEL, dict(options), True)
    budget.reserve({'crash': 1})                                  # crash between reserve and settle
    with pytest.raises(pb.BudgetError, match='unresolved'):
        rb.open_budget_for_run(out, 'f'*64, MODEL, dict(options), True)
    resumed = rb.open_budget_for_run(out, 'f'*64, MODEL, dict(options), True, 'driver killed mid-request')
    money = resumed.summary()
    assert money['measured_cost_usd'] == '0.4' and money['unknown_requests'] == 0   # counted at full bound
    resumed.halt('reported_provider_host_mismatch')
    with pytest.raises(pb.BudgetError, match='halt'):
        rb.open_budget_for_run(out, 'f'*64, MODEL, dict(options), True)


def test_paid_resume_receipt_renewal(tmp_path):
    import run_benchmark as rb
    options, receipt = policy_fixture(tmp_path, cap='1', bound='.4')
    out = tmp_path / 'run'
    budget = rb.open_budget_for_run(out, 'f'*64, MODEL, options, False)
    budget.settle(budget.reserve({'t': 1}), '.3', {})
    # receipt expired: plain resume refuses, the sealed config is not edited
    old = datetime.now(timezone.utc) - timedelta(hours=30)
    stale = _renew_receipt(tmp_path, options, receipt, 'stale.json', verified_at=old.isoformat(),
                           expires_at=(old+timedelta(hours=1)).isoformat())
    expired = {**options, **{k: stale[k] for k in ('paid_budget_receipt', 'paid_budget_receipt_sha256')}}
    with pytest.raises(pb.BudgetError, match='current'):
        rb.open_budget_for_run(out, 'f'*64, MODEL, dict(expired), True)
    # owner renewal: key now has .75 left, enough for the remaining .7 of the cap; bound changes are allowed
    key = {**receipt['key_limit'], 'limit_remaining': .75, 'usage': .3}
    (out / pb.RENEWAL_FILE).write_text(json.dumps(_renew_receipt(tmp_path, options, receipt, 'r2.json',
                                                                 key_limit=key, attempt_upper_bound_usd='.35')))
    resumed = rb.open_budget_for_run(out, 'f'*64, MODEL, dict(expired), True)
    assert resumed.policy()['attempt_upper_bound_usd'] == '0.35'
    resumed.settle(resumed.reserve({'t': 2}), '.3', {})
    rows = [json.loads(line) for line in (out / 'paid-budget.jsonl').read_text().splitlines()]
    assert [r['kind'] for r in rows].count('renew') == 1
    # a renewal may not change identity (host / key / cap)
    for change in ({'provider_host': 'other-host'}, {'key_fingerprint': 'c'*64}):
        (out / pb.RENEWAL_FILE).write_text(json.dumps(_renew_receipt(tmp_path, options, receipt, 'bad.json', key_limit=key, **change)))
        with pytest.raises(pb.BudgetError):
            rb.open_budget_for_run(out, 'f'*64, MODEL, dict(expired), True)
    unapproved = _renew_receipt(tmp_path, options, receipt, 'r3.json', key_limit=key); unapproved.pop('approved_by')
    (out / pb.RENEWAL_FILE).write_text(json.dumps(unapproved))
    with pytest.raises(pb.BudgetError, match='approved_by'):
        rb.open_budget_for_run(out, 'f'*64, MODEL, dict(expired), True)


def test_reconcile_flag_needs_paid_journal(tmp_path):
    import run_benchmark as rb
    options, _ = policy_fixture(tmp_path)
    with pytest.raises(ValueError, match='reconcile'):
        rb.open_budget_for_run(tmp_path / 'run', 'f'*64, MODEL, options, False, 'x')


def test_halted_journal_still_blocks_reserve(tmp_path, monkeypatch):
    gate, body = paid_gateway(tmp_path, monkeypatch)
    gate.budget.halt('reported_provider_host_mismatch')
    with pytest.raises(pb.BudgetError):
        gate.budget.reserve({'probe': 1})
