"""Regressions for isolation, accounting and fail-closed provider parity."""
import os
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'runners'))
from provider import clean_env, normalize_model, aggregate_usage


def test_environment_drops_provider_keys_hooks_and_global_state(tmp_path, monkeypatch):
    monkeypatch.setenv('GOOGLE_API_KEY', 'must-not-copy')
    monkeypatch.setenv('NVIDIA_API_KEY', 'must-not-copy')
    monkeypatch.setenv('NODE_OPTIONS', '--require global-hook')
    monkeypatch.setenv('OPENCODE_CONFIG_CONTENT', '{"plugins":["user-plugin"]}')
    env = clean_env(tmp_path)
    assert not set(env) & {'GOOGLE_API_KEY', 'NVIDIA_API_KEY', 'NODE_OPTIONS', 'OPENCODE_CONFIG_CONTENT'}
    assert env['HOME'] == str(tmp_path)
    assert all(str(tmp_path) in env[k] for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME'))


def test_allowlist_never_silently_routes_paid_or_other_provider():
    assert normalize_model('nvidia/nvidia/nemotron-3.5-bolt-e4b') == 'nvidia/nemotron-3.5-bolt-e4b'
    for model in ('nvidia/deepseek-ai/deepseek-v4.1-flash', 'google/gemini-3.5-flash-lite', 'opencode-go/deepseek', 'nvidia/omitted-model', 'deepseek-ai/deepseek-v4.1-flash'):
        with pytest.raises(ValueError): normalize_model(model)


def test_usage_aggregates_all_requests_and_cache():
    usage = aggregate_usage([{'status':200,'usage':{'prompt_tokens':100,'completion_tokens':10,'prompt_tokens_details':{'cached_tokens':30}}},
                             {'status':200,'usage':{'prompt_tokens':200,'completion_tokens':20,'prompt_tokens_details':{'cached_tokens':0}}}])
    assert (usage['input'],usage['output'],usage['cached']) == (300,30,30)
    assert usage['complete'] is True


def test_missing_usage_never_fabricates_zero_complete_cost():
    assert aggregate_usage([{'status':200}]) is None
    usage=aggregate_usage([{'status':200,'usage':{'prompt_tokens':100,'completion_tokens':10}}, {'status':429}])
    assert usage['complete'] is False
    assert aggregate_usage([{'status':200,'usage':{'completion_tokens':10}}]) is None


def _gateway(tmp_path, monkeypatch, allowed=('opentrading_vn_quote_history',)):
    import threading
    import time
    from provider import ProviderGateway, DEFAULT_MODEL
    gate = ProviderGateway.__new__(ProviderGateway)
    gate.options = {'allowed_tool_names': list(allowed), 'snapshot_tool_definitions': [{'name':'vn_quote_history'}], 'request_interval_s': 0, 'max_requests': 1, 'max_total_tokens': 10000}
    gate.model, gate.key, gate.token = DEFAULT_MODEL, 'provider-secret-never-log', 'local-token'
    gate.rows, gate.lock, gate.request_count = [], threading.Lock(), 0
    gate.deadline = time.monotonic() + 30
    gate.ledger = tmp_path / 'provider.jsonl'
    return gate


class _Handler:
    def __init__(self, body, token='local-token', path='/v1/chat/completions'):
        import io
        import json
        self.path = path
        raw = json.dumps(body).encode()
        self.headers = {'Authorization': 'Bearer '+token, 'Content-Length': str(len(raw))}
        self.rfile, self.wfile = io.BytesIO(raw), io.BytesIO()
        self.response_status = None
    def send_response(self, status): self.response_status = status
    def send_header(self, *args): pass
    def end_headers(self): pass


def _body(tool='opentrading_vn_quote_history'):
    from provider import DEFAULT_MODEL
    return {'model': DEFAULT_MODEL, 'messages': [{'role':'user','content':'quote'}],
            'tools':[{'type':'function','function':{'name':tool,'parameters':{'type':'object'}}}], 'max_tokens':9999}


@pytest.mark.parametrize('tool', ['opentrading_web_fetch','opentrading_shell','execute','mcp__opentrading__invented'])
def test_exact_frozen_catalog_rejects_disguised_tools(tmp_path, monkeypatch, tool):
    gate = _gateway(tmp_path, monkeypatch)
    handler = _Handler(_body(tool))
    gate.handle(handler)
    assert handler.response_status == 403
    assert gate.rows[0]['error'] == 'non-snapshot tool exposed to model'
    assert 'provider-secret-never-log' not in gate.ledger.read_text()


def test_gateway_deadline_blocks_before_network(tmp_path, monkeypatch):
    gate = _gateway(tmp_path, monkeypatch)
    gate.deadline = 0
    handler = _Handler(_body())
    gate.handle(handler)
    assert handler.response_status == 403
    assert gate.rows[0]['error'] == 'trial deadline exhausted'


def test_gateway_aggregates_real_sse_and_enforces_output_cap(tmp_path, monkeypatch):
    import json
    import provider
    gate = _gateway(tmp_path, monkeypatch)
    seen=[]
    class Response:
        status=200
        headers={'Content-Type':'text/event-stream'}
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def __init__(self):
            import types
            self.fp=types.SimpleNamespace(raw=types.SimpleNamespace(_sock=types.SimpleNamespace(settimeout=lambda _:None)))
            self.done=False
        def read1(self, n):
            if self.done:return b''
            self.done=True
            return ('data: '+json.dumps({'model':gate.model,'choices':[],'usage':{'prompt_tokens':17,'completion_tokens':3}})+'\n\ndata: [DONE]\n\n').encode()
    def fetch(req, timeout):
        seen.append(json.loads(req.data)); return Response()
    monkeypatch.setattr(provider.urllib.request,'urlopen',fetch)
    body=_body();body['stream']=True
    handler=_Handler(body)
    gate.handle(handler)
    assert handler.response_status == 200
    assert seen[0]['max_tokens'] == 2048
    assert seen[0]['temperature'] == 0
    assert gate.rows[0]['usage']['prompt_tokens'] == 17
    assert aggregate_usage(gate.rows)['input'] == 17
    handler2=_Handler(body);gate.handle(handler2)
    assert handler2.response_status==403
    assert len(seen)==1


def test_missing_cache_is_unknown_not_measured_zero():
    result = aggregate_usage([{'status':200,'usage':{'prompt_tokens':10,'completion_tokens':2}}])
    assert result['complete'] is True
    assert result['cached'] is None and result['cache_complete'] is False


@pytest.mark.parametrize('invalid', [-1, True, float('nan'), float('inf')])
def test_invalid_usage_never_counts_as_measured(invalid):
    assert aggregate_usage([{'status':200,'usage':{'prompt_tokens':invalid,'completion_tokens':2}}]) is None


def test_complete_snapshot_catalog_required(tmp_path, monkeypatch):
    gate=_gateway(tmp_path,monkeypatch)
    gate.options['snapshot_tool_definitions'].append({'name':'finance_query'})
    gate.options['allowed_tool_names'].append('opentrading_finance_query')
    handler=_Handler(_body());gate.handle(handler)
    assert handler.response_status==403
    assert gate.rows[0]['error']=='snapshot tool inventory incomplete or duplicated'


def test_unknown_upstream_usage_cannot_replenish_token_budget(tmp_path, monkeypatch):
    gate=_gateway(tmp_path,monkeypatch)
    gate.rows=[{'upstream_attempted':True,'status':200}]
    handler=_Handler(_body());gate.handle(handler)
    assert handler.response_status==403
    assert gate.rows[-1]['error']=='previous upstream usage unknown; further requests denied'


def test_retry_after_limiter_failure_preserves_original_429(tmp_path, monkeypatch):
    import provider
    from email.message import Message
    gate=_gateway(tmp_path,monkeypatch)
    calls=[]
    def rate_lock(fp,deadline):
        calls.append(True)
        if len(calls)>1: raise ValueError('limiter deadline')
    def fetch(req,timeout):
        headers=Message();headers['Retry-After']='30'
        raise provider.urllib.error.HTTPError('https://integrate.api.nvidia.com',429,'rate limited',headers,None)
    monkeypatch.setattr(provider,'acquire_rate_lock',rate_lock)
    monkeypatch.setattr(provider.urllib.request,'urlopen',fetch)
    handler=_Handler(_body());gate.handle(handler)
    assert handler.response_status==429
    assert gate.rows[-1]['status']==429
    assert gate.rows[-1]['retry_after']=='30'
    assert gate.rows[-1]['limiter_update_error']


def test_native_opencode_final_text_excludes_tool_step_preface():
    import json
    from run_opencode import parse_output
    lines=[{'type':'step_start'}, {'type':'text','part':{'id':'a','text':'I will query the tool.'}},
           {'type':'tool_use','part':{'tool':'opentrading_vn_quote_history'}},
           {'type':'step_start'}, {'type':'text','part':{'id':'b','text':'{"value":21}'}},
           {'type':'text','part':{'id':'b','text':'{"value":21}'}}]
    assert parse_output('\n'.join(map(json.dumps,lines)))[0]=='{"value":21}'
    assert parse_output('\n'.join(map(json.dumps,lines[:3])))[0]==''


def test_real_http_response_content_length_closes_fp_without_losing_usage(tmp_path, monkeypatch):
    import io
    import json
    import http.client
    import provider
    gate=_gateway(tmp_path,monkeypatch)
    payload=json.dumps({'model':gate.model,'choices':[],'usage':{'prompt_tokens':12,'completion_tokens':3}}).encode()
    class Socket:
        def makefile(self,*args):
            return io.BytesIO(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '+str(len(payload)).encode()+b'\r\n\r\n'+payload)
    response=http.client.HTTPResponse(Socket());response.begin()
    monkeypatch.setattr(provider.urllib.request,'urlopen',lambda *a,**kw:response)
    handler=_Handler(_body());gate.handle(handler)
    assert handler.response_status==200
    assert gate.rows[-1]['usage']['prompt_tokens']==12
    assert response.fp is None
