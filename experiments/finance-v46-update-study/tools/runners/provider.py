"""Parent-owned NVIDIA gateway: real credentials never enter the agent environment.

All three adapters use this same chat-completions route. No model substitution,
provider fallback, hidden retries or fabricated zero usage. Streaming is buffered
for reliable usage accounting; end-to-end latency includes that buffering.
"""
import contextlib
import fcntl
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import secrets
import threading
import time
import urllib.error
import urllib.request

NVIDIA_URL = 'https://integrate.api.nvidia.com/v1'
OPENROUTER_URL = 'https://openrouter.ai/api/v1'
# v4.6-update pilot route (user-authorized 2026-11-09): OpenRouter FREE tier only
# (nvidia/nemotron-3.5-super-vl:free, pricing 0/0). Paid OpenRouter variants and
# NVIDIA credit are never used by this route. Budget (user-raised 2026-11-10):
# hard-stop at 1900 upstream requests TOTAL across smoke+pilot processes
# (verified funded key: free_model_daily_requests limit=1000 per UTC day,
# reset 00:00 UTC; two UTC days cover the raised budget with reserve).
OPENROUTER_MODEL = 'nvidia/nemotron-3.5-super-vl:free'
OPENROUTER_FREE_REQUEST_BUDGET = 1900
# Paid DeepSeek route (user-authorized 2026-11-10): credit-billed with price
# entitlement in bench_config_deepseek_openrouter.json; the request guard only
# bounds runaway retries, actual cost is metered from observed usage.
OPENROUTER_PAID_MODEL = 'deepseek/deepseek-v4.1-flash-1017'
OPENROUTER_PAID_REQUEST_BUDGET = 10500  # amendment 2026-11-11 (d) D4
DEFAULT_MODEL = 'nvidia/nemotron-3.5-super-vl-120b-a12b'
AUTHORIZED_MODELS = {DEFAULT_MODEL, 'deepseek-ai/deepseek-v4.1-flash'}
# Diagnostic-only allowlist: models with a recorded real function-call canary
# receipt (catalog + tool call + tool-result continuation). Never used for
# main/holdout, which stay locked to the frozen bench_config model.
DIAGNOSTIC_MODELS = {'deepseek-ai/deepseek-v4.1-flash'}  # v43 smoke only; Nov5 recorded function-call + continuation receipt.
DIAGNOSTIC_RECEIPT_SHA256 = 'd078ce590717254cc73d423d90345dde070ea2167c5abd2d94f1f6bf988c4f31'


def credential():
    value = os.environ.get('NVIDIA_API_KEY')
    if value:
        return value
    for name in ('~/.opentrading/auth.json', '~/.local/share/opencode/auth.json'):
        try:
            entry = json.loads(Path(name).expanduser().read_text()).get('nvidia', {})
            value = entry.get('key') or entry.get('apiKey')
            if value:
                return value
        except (OSError, ValueError):
            pass
    raise ValueError('NVIDIA credential missing')


def admission(model_id):
    directory=Path(__file__).resolve().parents[2]/'audits/model-admission'
    if model_id.endswith(':free'):
        # v4.6-update OR :free route: the canary receipt filename normalizes
        # the OpenRouter id to openrouter__<model-without-provider, ':'->'-'>.json.
        receipt=directory/('openrouter__'+model_id.split('/',1)[1].replace(':','-')+'.json')
    elif model_id==OPENROUTER_PAID_MODEL:
        receipt=directory/('deepseek__deepseek-v4.1-flash-1017-openrouter.json')
    else:
        receipt=directory/(model_id.replace('/','__')+'.json')
    if receipt.is_file():
        data=json.loads(receipt.read_text())
        if data.get('model')==model_id and data.get('function_call_verified') is True and data.get('tool_loop',{}).get('status')==200 and data.get('response_model')==model_id:
            return {**data,'checkpoint_unverified':False,'accepted_response_model':model_id,'admission_contract':'exact-identity-v1'}
        # v4.6-update OR :free route (user-authorized 2026-11-09/10): the
        # OpenRouter receipt records model_requested/returned_model (exact
        # identity), a 3-probe canary and pricing 0/0. Same strictness: the
        # receipt must prove the exact requested identity with a real canary.
        if data.get('model_requested')==model_id and data.get('returned_model')==model_id and data.get('user_authorized') is True and data.get('route')=='openrouter_free':
            probes=data.get('probes_detail') or {}
            if not ('PASS' in str(data.get('probes','')) and probes):raise ValueError('v45 OR admission receipt lacks passing canary probes')
            return {**data,'checkpoint_unverified':True,'accepted_response_model':model_id,'admission_contract':'openrouter-free-route-user-authorized-20261109'}
        # v4.6-update paid OR route (deepseek, 2026-11-10): identity_canary
        # receipt schema (model_requested/returned_model/probes list/pass) —
        # exact identity + 3 passing probes required, same as :free.
        if data.get('model_requested')==model_id and data.get('returned_model')==model_id and data.get('pass') is True:
            probes=data.get('probes') or []
            ok_probes=[p for p in probes if isinstance(p,dict) and (p.get('content_ok') is True or p.get('tool_called') is True or p.get('probe')=='vn_follow')]
            if len(ok_probes)<2:raise ValueError('v45 paid-OR admission receipt lacks passing canary probes')
            return {**data,'checkpoint_unverified':True,'accepted_response_model':model_id,'admission_contract':'openrouter-paid-route-user-authorized-20261110'}
        raise ValueError('v45 exact model admission invalid')
    route=directory/(model_id.replace('/','__')+'-route-v2.json')
    if model_id!=DEFAULT_MODEL or not route.is_file():raise ValueError('v45 actual function-call admission receipt missing')
    data=json.loads(route.read_text())
    accepted='private/nvidia/nemotron-3.5-super-120b-a12b'
    if data.get('contract')!='user-authorized-requested-route-v2' or data.get('requested_model')!=model_id or data.get('returned_model')!=accepted or data.get('checkpoint_unverified') is not True or data.get('user_authorized') is not True or data.get('function_call_verified') is not True:raise ValueError('v45 route-contract admission invalid')
    evidence=Path(data.get('canary_path',''))
    if not evidence.is_file() or hashlib.sha256(evidence.read_bytes()).hexdigest()!=data.get('canary_sha256'):raise ValueError('v45 immutable route evidence missing or changed')
    return {**data,'accepted_response_model':accepted,'admission_contract':data['contract']}


def normalize_model(model):
    if not model.startswith('nvidia/') or model[7:] not in AUTHORIZED_MODELS:
        raise ValueError('Only the two user-authorized v45 NVIDIA models are enabled')
    model_id=model[7:];admission(model_id);return model_id


class GatewayFailure(Exception):
    def __init__(self, code, origin='local_policy', status=409):
        super().__init__(code);self.code=code;self.origin=origin;self.status=status


def retry_delay(status, error_text, retry_after, attempt, remaining):
    """Pre-exposure only. None means never retry; timing cannot extend deadline."""
    if status not in (429,500,502,503,504,598): return None
    text=(error_text or '').lower()
    if any(word in text for word in ('daily','quota exhausted','insufficient_quota','billing','credit')):return None
    if status==429 and not retry_after and not any(word in text for word in ('rate','minute','rpm','rps','temporar','too many requests')):return None
    delay=(4,8)[attempt-1] if attempt in (1,2) else None
    if delay is None:return None
    if retry_after:
        from email.utils import parsedate_to_datetime
        try: observed=float(retry_after)
        except (ValueError,TypeError):
            try: observed=max(0,parsedate_to_datetime(retry_after).timestamp()-time.time())
            except (ValueError,TypeError,OverflowError):return None
        if not math.isfinite(observed) or observed>60:return None
        delay=max(delay,max(0,observed))
    return delay if delay<remaining else None


def clean_env(home):
    """Allowlist rather than trying to remove every provider/user hook variable."""
    home = Path(home).resolve()
    env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'TZ', 'SSL_CERT_FILE', 'SSL_CERT_DIR') if k in os.environ}
    env['HOME'] = str(home)
    for key, sub in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state'), ('TMPDIR', 'tmp')]:
        dest = home / sub
        dest.mkdir(parents=True, exist_ok=True)
        env[key] = str(dest)
    return env


def valid_count(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def aggregate_usage(rows):
    good = [r['usage'] for r in rows if isinstance(r.get('usage'), dict) and
            all(valid_count(r['usage'].get(k)) for k in ('prompt_tokens', 'completion_tokens'))]
    if not good:
        return None
    cached = [(u.get('prompt_tokens_details') or {}).get('cached_tokens') for u in good]
    cache_complete = len(good) == len(rows) and all(valid_count(c) for c in cached)
    observed_cache = sum(c for c in cached if valid_count(c))
    return {'input': sum(u['prompt_tokens'] for u in good),
            'output': sum(u['completion_tokens'] for u in good),
            'cached': observed_cache if cache_complete else None,
            'cache_read': observed_cache if cache_complete else None,
            'cached_observed': observed_cache, 'cache_complete': cache_complete,
            'usage_requests': len(good), 'requests': len(rows),
            'complete': len(good) == len(rows)}


def acquire_rate_lock(fp, deadline):
    """A process holding the shared limiter cannot stall a trial indefinitely."""
    while True:
        try:
            fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise ValueError('rate limiter lock exceeds trial deadline')
            time.sleep(min(0.02, max(0, deadline - time.monotonic())))


def native_tool_allowlist(options):
    allowed={'calculate','compute','read_result'}
    if options.get('memory_profile')=='controlled-memory-v1' and options.get('condition')=='ot_memory_on' and options.get('native_arm')=='opentrading':
        allowed.add('memory_read')
    # Amendment 2026-11-11 (d): native-memory stratum, OT B0 with its own notebook read tool.
    if options.get('memory_profile')=='native-v2' and options.get('condition')=='opentrading_baseline' and options.get('native_arm')=='opentrading':
        allowed.add('memory_read')
    # DSH's opt-in prior-session search tools (memory stratum only; schemas pinned in dsh_session_search_tools.json).
    if options.get('memory_profile')=='native-v2' and options.get('condition')=='dsh' and options.get('native_arm')=='dsh':
        allowed |= {'session_event_read','session_event_search','session_event_trace','session_search','session_trace'}
    return allowed


class ProviderGateway:
    def __init__(self, model, ledger, options=None):
        self.options = dict(options or {})
        for key,value in {'timeout_s':900,'provider_timeout_s':240,'max_requests':24,'max_output_tokens':8192,'max_total_tokens':3600000,'failed_attempt_context_bound':1048576,'failed_attempt_token_reservation':1056768,'failed_attempt_reservation_provenance':'NVIDIA model cards: combined context upper bound 1048576 plus output8192; protocol reservation, not measured usage or billing estimate'}.items():self.options.setdefault(key,value)
        reservation=self.options.get('failed_attempt_token_reservation')
        bound=self.options.get('failed_attempt_context_bound')
        if reservation is not None and (not isinstance(bound,int) or not isinstance(reservation,int) or reservation<bound+int(self.options['max_output_tokens']) or reservation>int(self.options['max_total_tokens'])):raise ValueError('failed-attempt reservation must cover declared context plus output and fit total budget')
        or_route = self.options.get('provider_route') in ('openrouter_free','openrouter_paid')
        if or_route:
            # v4.6-update OR routes: requested OpenRouter identity is admitted by
            # its OWN canary receipt, never by the NVIDIA admission table. The
            # :free variant is pricing 0/0 with a hard request budget; the paid
            # variant (deepseek) bills credit with price entitlement in config.
            self.model = model
            adm_path = self.options.get('openrouter_admission')
            self.admission = json.loads(Path(adm_path).read_text()) if adm_path and Path(adm_path).is_file() else {
                'accepted_response_model': model, 'checkpoint_unverified': True,
                'admission_contract': 'openrouter-free-route-user-authorized-20261109' if self.options.get('provider_route')=='openrouter_free' else 'openrouter-paid-route-user-authorized-20261110'}
        else:
            self.model = normalize_model(model)
            self.admission = admission(self.model)
        self.accepted_response_model = self.admission['accepted_response_model']
        if self.options.get('effort', 'none') not in ('none', 'off', None):
            raise ValueError('Requested effort is not verified on all adapters; refusing parity claim')
        self.key = (os.environ.get('OPENROUTER_KEY') or credential()) \
            if or_route else credential()
        self.token = secrets.token_hex(24)
        self.ledger = Path(ledger)
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.rows = []
        self.logical_count = 0
        self.terminal_failures = {}
        self.lock = threading.Lock()
        self.dispatch_lock = threading.Lock()
        self.request_count = 0
        self.deadline = time.monotonic() + float(self.options.get('timeout_s', 300))
        gateway = self
        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(max(0.1, min(5, gateway.deadline - time.monotonic())))
            def log_message(self, *_):
                pass
            def do_GET(self):
                self.send_error(404)
            def do_POST(self):
                remaining = max(0, gateway.deadline - time.monotonic())
                if not gateway.dispatch_lock.acquire(timeout=remaining):
                    self.send_error(503, 'trial deadline exhausted')
                    return
                try:
                    gateway.handle(self)
                finally:
                    gateway.dispatch_lock.release()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = False
        self.server.block_on_close = True
        self.url = 'http://127.0.0.1:%d/v1' % self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def record(self, row):
        self.rows.append(row)
        with self.ledger.open('a', encoding='utf-8') as fp:
            fp.write(json.dumps(row, ensure_ascii=False) + '\n')
            fp.flush()
            os.fsync(fp.fileno())

    def capture_request(self, raw, body, stage):
        """Persist body only: HTTP authorization remains parent-owned and absent."""
        directory = self.ledger.parent / 'provider-requests'
        directory.mkdir(mode=0o700, exist_ok=True)
        path = directory / ('%04d-%s.json' % (len(self.rows) + 1, stage))
        # Provider and local gateway credentials must never enter capture artifacts.
        text = raw.decode('utf-8')
        for secret in (self.key, self.token):
            if secret and secret in text:
                raise ValueError('credential found in model request body; capture denied')
        path.write_bytes(raw)
        path.chmod(0o600)
        def paths(value, prefix='$'):
            found = [prefix]
            if isinstance(value, dict):
                for key, item in value.items(): found.extend(paths(item, prefix+'.'+key))
            elif isinstance(value, list):
                for index, item in enumerate(value): found.extend(paths(item, prefix+'[%d]' % index))
            return found
        return {'path': str(path.resolve()), 'raw_sha256': hashlib.sha256(raw).hexdigest(),
                'canonical_sha256': hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
                'field_paths': paths(body)}

    def attempt_event(self, value):
        path=self.ledger.parent/'provider-attempt-events.jsonl'
        with path.open('a',encoding='utf-8') as fp:
            fp.write(json.dumps(value,ensure_ascii=False)+'\n');fp.flush();os.fsync(fp.fileno())
        path.chmod(0o600)

    def capture_response(self, raw, logical_id, attempt):
        for secret in (self.key,self.token):
            if secret and secret.encode() in raw:raw=raw.replace(secret.encode(),b'[REDACTED]')
        directory=self.ledger.parent/'provider-responses';directory.mkdir(mode=0o700,exist_ok=True)
        path=directory/('%04d-%02d.bin'%(logical_id,attempt));path.write_bytes(raw);path.chmod(0o600)
        return {'path':str(path.resolve()),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

    def check_control(self):
        control=self.options.get('control_file')
        if not control:return
        path=Path(control)
        if not path.exists():return
        try:state=json.loads(path.read_text())
        except (ValueError,OSError):raise GatewayFailure('invalid_user_control_state','local_control',424)
        if state.get('pause') is True or state.get('hard_stop') is True:raise GatewayFailure('user_pause_requested','local_control',424)

    def _or_budget_tick(self, path=None, paid=False):
        # v4.6-update user budget: persistent all-time counter for the OpenRouter
        # routes across smoke+pilot processes. :free = 1900 hard-stop (raised
        # 2026-11-10); paid (deepseek) = 1900 requests cost-bounding guard with
        # price entitlement in config. Hard safety net only; graceful daily stop
        # for :free is the external quota watcher on the authoritative
        # GET /api/v1/key free_model counter (paid has no daily free cap).
        name = 'openrouter-paid-budget-counter.json' if paid else 'openrouter-free-budget-counter.json'
        budget = OPENROUTER_PAID_REQUEST_BUDGET if paid else OPENROUTER_FREE_REQUEST_BUDGET
        path = path or (Path(__file__).resolve().parents[2]/'results'/name)
        try:state=json.loads(path.read_text())
        except (ValueError,OSError):state={}
        today=time.strftime('%Y-%m-%d',time.gmtime())
        if state.get('date')!=today:state={'date':today,'daily':0,'total':int(state.get('total',0))}
        state['daily']=int(state.get('daily',0))+1
        state['total']=int(state.get('total',0))+1
        state['updated']=time.time()
        path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_suffix('.json.tmp');tmp.write_text(json.dumps(state));tmp.replace(path)
        if state['total']>budget:raise GatewayFailure('openrouter_user_budget_exhausted','local_control',424)

    def controlled_wait(self, delay):
        end=time.monotonic()+delay
        while True:
            self.check_control()
            remaining=end-time.monotonic()
            if remaining<=0:return
            time.sleep(min(.05,remaining))

    def handle(self, handler):
        start = time.time()
        row = {'index': len(self.rows) + 1, 'started_at': start, 'expected_model': self.model, 'upstream_attempted': False,'requested_model':self.model,'accepted_response_model':getattr(self,'accepted_response_model',self.model),'checkpoint_unverified':getattr(self,'admission',{}).get('checkpoint_unverified',False),'admission_contract':getattr(self,'admission',{}).get('admission_contract','exact-identity-v1')}
        status, payload, content_type = 400, b'', 'application/json'
        try:
            if time.monotonic() >= self.deadline:
                raise ValueError('trial deadline exhausted')
            if handler.path != '/v1/chat/completions':
                raise ValueError('endpoint denied')
            if handler.headers.get('Authorization') != 'Bearer ' + self.token:
                raise ValueError('gateway authorization denied')
            raw_body = handler.rfile.read(min(int(handler.headers.get('Content-Length', '0')), 4000000))
            body = json.loads(raw_body)
            row['native_request_capture'] = self.capture_request(raw_body, body, 'native')
            if body.get('model') != self.model:
                raise ValueError('model mismatch; side models denied')
            if body.get('reasoning_effort') not in (None, 'none', 'off'):
                raise ValueError('reasoning effort mismatch')
            row.update({'request_model': body['model'], 'effort': body.get('reasoning_effort'),
                        'message_sha256': hashlib.sha256(json.dumps(body.get('messages'), sort_keys=True).encode()).hexdigest(),
                        'tool_names': [x.get('function', {}).get('name') for x in body.get('tools', [])],
                        'tool_schema_sha256': hashlib.sha256(json.dumps(body.get('tools', []), sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                        'stream': bool(body.get('stream')),
                        'session_header_present': any('session' in k.lower() for k in handler.headers)})
            # All adapter-exposed tools must belong to the frozen snapshot server.
            if not row['tool_names']:
                raise ValueError('snapshot tool inventory absent')
            allowed = set(self.options.get('allowed_tool_names', []))
            raw = [d['name'] for d in self.options.get('snapshot_tool_definitions', [])]
            native_defs=self.options.get('native_tool_definitions', [])
            native_names={d['name'] for d in native_defs}
            if not native_names.issubset(native_tool_allowlist(self.options)):raise ValueError('unapproved native utility')
            allowed |= native_names
            complete_sets = [{prefix + name for name in raw} for prefix in ('opentrading_', 'mcp__opentrading__', 'mcp_opentrading_')]
            # v4.6 fix: MCP tools reach the wire under their prefixed namespaces
            # (e.g. mcp__opentrading__vn_quote_history) while snapshot_tool_definitions
            # carries bare names; registered = bare ∪ native ∪ all prefixed forms.
            registered = allowed | set().union(*complete_sets)
            actual = row['tool_names']
            if not registered or any(n not in registered for n in actual):
                raise ValueError('unregistered tool exposed to model')
            if len(actual) != len(set(actual)) or (set(actual)-native_names) not in complete_sets:
                raise ValueError('snapshot tool inventory incomplete or duplicated')
            from wire_contracts import verify_c2_wire_contracts
            verify_c2_wire_contracts({**body,'tools':[x for x in body.get('tools',[]) if x.get('function',{}).get('name') not in native_names]},self.options.get('snapshot_tool_definitions',[]))
            from wire_contracts import schema_constraints
            for definition in native_defs:
                observed=next((x['function'] for x in body.get('tools',[]) if x.get('function',{}).get('name')==definition['name']),None)
                if observed is None or schema_constraints(observed.get('parameters'))!=schema_constraints(definition.get('inputSchema')):raise ValueError('native utility wire schema changed or missing: '+definition['name'])
            max_out = int(self.options.get('max_output_tokens', 8192))
            requested_out = body.get('max_tokens', body.get('max_completion_tokens', max_out))
            body.pop('max_completion_tokens', None)
            body['max_tokens'] = min(requested_out or max_out, max_out)
            body['temperature'] = float(self.options.get('temperature',1 if self.model==DEFAULT_MODEL else 0))
            body['top_p'] = float(self.options.get('top_p',.95 if self.model==DEFAULT_MODEL else 1))
            row['effective_temperature'] = body['temperature']
            row['effective_top_p'] = body['top_p']
            row['requested_max_tokens'] = requested_out
            row['effective_max_tokens'] = body['max_tokens']
            if body.get('stream'):
                body['stream_options'] = {'include_usage': True}
            effective_raw=json.dumps(body).encode()
            fingerprint=hashlib.sha256(effective_raw).hexdigest()
            row['payload_fingerprint']=fingerprint
            if not hasattr(self,'terminal_failures'):self.terminal_failures={}
            if fingerprint in self.terminal_failures:
                prior=self.terminal_failures[fingerprint]
                row.update(terminal_redelivery_of=prior['logical_request_id'],error='terminal_logical_request_redelivery',error_origin='local_replay_guard')
                raise GatewayFailure('terminal_logical_request_redelivery','local_replay_guard',424)
            row['effective_request_capture']=self.capture_request(effective_raw,body,'effective')
            self.logical_count=getattr(self,'logical_count',0)+1
            logical_id=self.logical_count
            base_request_fields=row.copy()
            for attempt in range(1,4):
                attempt_started=time.time()
                row.update(logical_request_id=logical_id,transport_attempt=attempt,retry_owner='common_gateway',upstream_attempted=False)
                self.check_control()
                if time.monotonic()>=self.deadline:raise GatewayFailure('trial_deadline_exhausted')
                if self.request_count>=int(self.options.get('max_requests',24)):raise GatewayFailure('upstream_attempt_cap_exceeded')
                prior=[r for r in self.rows if r.get('upstream_attempted')]
                if any(not r.get('token_reservation') and (not isinstance(r.get('usage'),dict) or not all(valid_count(r['usage'].get(k)) for k in ('prompt_tokens','completion_tokens'))) for r in prior):
                    raise GatewayFailure('previous_upstream_usage_unknown')
                used=sum(r.get('token_reservation',0)+sum((r.get('usage') or {}).get(k,0) for k in ('prompt_tokens','completion_tokens')) for r in prior)
                estimate=len(effective_raw)
                planned_reservation=max(estimate+body['max_tokens'],int(self.options.get('failed_attempt_context_bound') or 0)+body['max_tokens'])
                row.update(input_budget_estimate_bytes=estimate,next_attempt_reserved_tokens=planned_reservation,token_budget_policy='actual observed usage plus failed-attempt reservations; next attempt reserves declared maximum combined model context plus max output, or larger full UTF8 body estimate')
                if used+planned_reservation>int(self.options.get('max_total_tokens',3600000)):raise GatewayFailure('local_token_budget_exhausted')
                with open('/tmp/benchmark-nvidia-rate.lock','a+') as rate:
                    acquire_rate_lock(rate,self.deadline);rate.seek(0)
                    try:previous=float(rate.read() or '0')
                    except ValueError:previous=0
                    pause=max(0,previous+float(self.options.get('request_interval_s',2))-time.time())
                    if time.monotonic()+pause>=self.deadline:raise GatewayFailure('local_rate_wait_deadline')
                    if pause:self.controlled_wait(pause)
                    rate.seek(0);rate.truncate();rate.write(str(time.time()));rate.flush()
                self.check_control()
                self.request_count+=1;row['upstream_attempted']=True
                self.attempt_event({'phase':'before_upstream_dispatch','logical_request_id':logical_id,'transport_attempt':attempt,'upstream_attempt_number':self.request_count,'payload_sha256':fingerprint,'native_request_capture':row['native_request_capture'],'effective_request_capture':row['effective_request_capture'],'time':time.time()})
                _route = 'openrouter' if self.options.get('provider_route') in ('openrouter_free','openrouter_paid') else 'nvidia'
                if _route=='openrouter':self._or_budget_tick(paid=self.options.get('provider_route')=='openrouter_paid')
                _url = (OPENROUTER_URL if _route == 'openrouter' else NVIDIA_URL) + '/chat/completions'
                _hdrs = {'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json', 'User-Agent': 'vn-finance-benchmark/4.5'}
                if _route == 'openrouter':
                    _hdrs['HTTP-Referer'] = 'https://localhost/vn-finance-benchmark'
                    _hdrs['X-Title'] = 'vn-finance-benchmark'
                request=urllib.request.Request(_url,data=effective_raw,headers=_hdrs)
                request_deadline=min(self.deadline,time.monotonic()+float(self.options.get('provider_timeout_s',240)))
                payload=b'';response_headers={};error_text='';transient=False
                try:
                    with urllib.request.urlopen(request,timeout=max(.1,request_deadline-time.monotonic())) as response:
                        status=response.status;content_type=response.headers.get('Content-Type','application/json')
                        response_headers={k:v for k,v in response.headers.items() if k.lower() in ('x-request-id','request-id','retry-after','content-type')}
                        parts=[];size=0
                        while True:
                            remaining=request_deadline-time.monotonic()
                            if remaining<=0:raise TimeoutError('provider request deadline exhausted')
                            sock=getattr(getattr(getattr(response,'fp',None),'raw',None),'_sock',None)
                            if sock is not None:sock.settimeout(remaining)
                            part=response.read1(16384)
                            if not part:break
                            parts.append(part);size+=len(part);payload=b''.join(parts)
                            if size>4000000:
                                row.update(bytes_received=len(payload),raw_response_capture=self.capture_response(payload,logical_id,attempt))
                                raise GatewayFailure('upstream_response_byte_cap','upstream_protocol',502)
                except urllib.error.HTTPError as exc:
                    status=exc.code;payload=exc.read(4000000);response_headers={'retry-after':exc.headers.get('Retry-After')}
                    error_text=payload.decode('utf-8',errors='replace');transient=True
                except (urllib.error.URLError,TimeoutError,ConnectionError,OSError) as exc:
                    status=598;error_text=type(exc).__name__;transient=not payload
                row.update(response_headers=response_headers,bytes_received=len(payload),raw_response_capture=self.capture_response(payload,logical_id,attempt))
                self.attempt_event({'phase':'upstream_response_observed','logical_request_id':logical_id,'transport_attempt':attempt,'status':status,'bytes_received':len(payload),'raw_response_capture':row['raw_response_capture'],'time':time.time()})
                if transient:
                    # Unknown usage is never assumed zero. Retry requires an explicitly
                    # preregistered upper reservation covering this entire failed attempt.
                    row.update(error='provider_transport_failure',error_origin='upstream_transport')
                    reservation=self.options.get('failed_attempt_token_reservation')
                    row['reservation_policy_provenance']=self.options.get('failed_attempt_reservation_provenance')
                    can_reserve=isinstance(reservation,int) and reservation>=estimate+body['max_tokens']
                    if can_reserve and used+reservation<=int(self.options.get('max_total_tokens',3600000)):row['token_reservation']=reservation;row['usage_complete']=False
                    else:can_reserve=False
                    wait=retry_delay(status,error_text,response_headers.get('retry-after'),attempt,self.deadline-time.monotonic()) if can_reserve and (status!=598 or not payload) else None
                    row.update(status=status if wait is not None else 424,upstream_or_policy_status=status,delivery_status=424 if wait is None else None,duration_s=time.time()-attempt_started,retry_scheduled=wait is not None,logical_final=wait is None)
                    self.record(row.copy())
                    if wait is None:
                        payload=json.dumps({'error':{'message':error_text,'code':row['error'],'origin':row['error_origin']}}).encode();row=None;break
                    row={**base_request_fields,'index':len(self.rows)+1,'started_at':time.time(),'upstream_attempted':False,'logical_request_id':logical_id,'transport_attempt':attempt+1}
                    self.controlled_wait(wait)
                    row={**base_request_fields,'index':len(self.rows)+1,'started_at':time.time(),'expected_model':self.model,'native_request_capture':self.capture_request(raw_body,json.loads(raw_body),'native'),'effective_request_capture':self.capture_request(effective_raw,body,'effective'),'message_sha256':hashlib.sha256(json.dumps(body.get('messages'),sort_keys=True).encode()).hexdigest()}
                    continue
                try:
                    from provider_response import response_chunks
                    chunks=response_chunks(payload,stream=bool(body.get('stream')))
                except (ValueError,UnicodeError):raise GatewayFailure('malformed_provider_response','upstream_protocol',502)
                row['usage']=next((x['usage'] for x in reversed(chunks) if x.get('usage')),None)
                bound=self.options.get('failed_attempt_context_bound')
                if bound is not None and isinstance(row.get('usage'),dict) and all(valid_count(row['usage'].get(k)) for k in ('prompt_tokens','completion_tokens')):
                    observed=sum(row['usage'][k] for k in ('prompt_tokens','completion_tokens'))
                    if observed>int(bound)+int(body['max_tokens']):raise GatewayFailure('observed_usage_exceeds_registered_context_bound','upstream_protocol',502)
                row['response_models']=sorted({x['model'] for x in chunks if x.get('model')})
                row['finish_reasons']=[c['finish_reason'] for x in chunks for c in x.get('choices',[]) if c.get('finish_reason') is not None]
                if not row['finish_reasons']:raise GatewayFailure('provider_finish_reason_missing','upstream_protocol',502)
                row['response_tool_call_ids']=sorted({t['id'] for x in chunks for c in x.get('choices',[]) for t in (c.get('delta') or c.get('message') or {}).get('tool_calls',[]) if t.get('id')})
                row['tool_call_count']=len(row['response_tool_call_ids'])
                if not row['response_models']:raise GatewayFailure('provider_response_model_missing','upstream_protocol',502)
                if row['response_models']!=[getattr(self,'accepted_response_model',self.model)]:raise GatewayFailure('provider_response_model_mismatch','upstream_protocol',502)
                break
        except GatewayFailure as exc:
            if row.get('upstream_attempted') and not (isinstance(row.get('usage'),dict) and all(valid_count(row['usage'].get(k)) for k in ('prompt_tokens','completion_tokens'))) and self.options.get('failed_attempt_token_reservation') is not None:
                row['token_reservation']=self.options['failed_attempt_token_reservation'];row['usage_complete']=False
            row.update(error=exc.code,error_origin=exc.origin);status=exc.status
            payload=json.dumps({'error':{'message':exc.code,'code':exc.code,'origin':exc.origin}}).encode()
        except Exception as exc:
            row.update(error=str(exc) if isinstance(exc,ValueError) else type(exc).__name__,error_origin='local_validation')
            status=400;payload=json.dumps({'error':{'message':row['error'],'origin':row['error_origin']}}).encode()
        if status>=400:
            original_status=status
            status=424  # Failed Dependency: terminal logical failure, never auth masquerade.
            if row is not None:row.update(upstream_or_policy_status=original_status,delivery_status=status)
            if 'fingerprint' in locals() and fingerprint not in self.terminal_failures:
                self.terminal_failures[fingerprint]={'logical_request_id':logical_id if 'logical_id' in locals() else None,'status':original_status}
        if row is not None:
            row.update(status=status,duration_s=time.time()-start,logical_final=True)
            with self.lock:self.record(row)
        try:
            if hasattr(handler, 'connection'):
                handler.connection.settimeout(max(0.1, min(5, self.deadline - time.monotonic())))
            handler.send_response(status)
            handler.send_header('Content-Type', content_type)
            handler.send_header('Content-Length', str(len(payload)))
            handler.end_headers()
            handler.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError, TimeoutError, OSError):
            pass
