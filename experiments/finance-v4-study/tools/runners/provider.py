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
DEFAULT_MODEL = 'nvidia/nemotron-3.5-bolt-e4b'
# Diagnostic-only allowlist: models with a recorded real function-call canary
# receipt (catalog + tool call + tool-result continuation). Never used for
# main/holdout, which stay locked to the frozen bench_config model.
DIAGNOSTIC_MODELS = set()  # This isolated study admits Bolt only, including direct Gateway construction.


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


def normalize_model(model):
    if not model.startswith('nvidia/'):
        raise ValueError('Only explicitly authorized NVIDIA inference is enabled')
    model_id = model[len('nvidia/'):]
    if model_id != DEFAULT_MODEL and model_id not in DIAGNOSTIC_MODELS:
        raise ValueError('Model lacks a recorded function-call canary receipt; only verified NVIDIA smoke/diagnostic models are enabled')
    return model_id


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


class ProviderGateway:
    def __init__(self, model, ledger, options=None):
        self.options = options or {}
        self.model = normalize_model(model)
        if self.options.get('effort', 'none') not in ('none', 'off', None):
            raise ValueError('Requested effort is not verified on all adapters; refusing parity claim')
        self.key = credential()
        self.token = secrets.token_hex(24)
        self.ledger = Path(ledger)
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.rows = []
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

    def handle(self, handler):
        start = time.time()
        row = {'index': len(self.rows) + 1, 'started_at': start, 'expected_model': self.model, 'upstream_attempted': False}
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
            complete_sets = [{prefix + name for name in raw} for prefix in ('opentrading_', 'mcp__opentrading__', 'mcp_opentrading_')]
            actual = row['tool_names']
            if not allowed or any(n not in allowed for n in actual):
                raise ValueError('non-snapshot tool exposed to model')
            if len(actual) != len(set(actual)) or set(actual) not in complete_sets:
                raise ValueError('snapshot tool inventory incomplete or duplicated')
            max_out = int(self.options.get('max_output_tokens', 2048))
            requested_out = body.get('max_tokens', body.get('max_completion_tokens', max_out))
            body.pop('max_completion_tokens', None)
            body['max_tokens'] = min(requested_out or max_out, max_out)
            body['temperature'] = 0
            body['top_p'] = 1
            row['effective_temperature'] = 0
            row['effective_top_p'] = 1
            row['requested_max_tokens'] = requested_out
            row['effective_max_tokens'] = body['max_tokens']
            if body.get('stream'):
                body['stream_options'] = {'include_usage': True}
            with self.lock:
                if self.request_count >= int(self.options.get('max_requests', 24)):
                    raise ValueError('request cap exceeded')
                self.request_count += 1
                if any(r.get('upstream_attempted') and not (isinstance(r.get('usage'), dict) and all(valid_count(r['usage'].get(k)) for k in ('prompt_tokens','completion_tokens'))) for r in self.rows):
                    raise ValueError('previous upstream usage unknown; further requests denied')
                used = sum(sum((r.get('usage') or {}).get(k, 0) for k in ('prompt_tokens', 'completion_tokens')) for r in self.rows)
                cap = int(self.options.get('max_total_tokens', 48000))
                # Reserve worst-case output + conservative input estimate before request.
                estimate = len(json.dumps(body.get('messages', []), ensure_ascii=False).encode()) + len(json.dumps(body.get('tools', []), ensure_ascii=False).encode())
                row['input_budget_estimate_bytes'] = estimate
                row['token_budget_policy'] = 'actual usage plus conservative UTF8-byte estimate for next input and max output'
                if used + estimate + body['max_tokens'] > cap:
                    raise ValueError('token budget exhausted before request')
                with open('/tmp/benchmark-nvidia-rate.lock', 'a+') as rate:
                    acquire_rate_lock(rate, self.deadline)
                    rate.seek(0)
                    try: previous = float(rate.read() or '0')
                    except ValueError: previous = 0
                    pause = max(0, previous + float(self.options.get('request_interval_s', 2)) - time.time())
                    if time.monotonic() + pause >= self.deadline:
                        raise ValueError('rate-limit wait exceeds trial deadline')
                    if pause: time.sleep(pause)
                    rate.seek(0); rate.truncate(); rate.write(str(time.time())); rate.flush()
                effective_raw = json.dumps(body).encode()
                row['effective_request_capture'] = self.capture_request(effective_raw, body, 'effective')
                request = urllib.request.Request(NVIDIA_URL + '/chat/completions',
                    data=effective_raw, headers={'Authorization': 'Bearer ' + self.key,
                    'Content-Type': 'application/json', 'User-Agent': 'vn-finance-benchmark/2'})
                request_deadline = min(self.deadline, time.monotonic() + float(self.options.get('provider_timeout_s', 45)))
                row['upstream_attempted'] = True
                with urllib.request.urlopen(request, timeout=max(0.1, request_deadline - time.monotonic())) as response:
                    status = response.status
                    content_type = response.headers.get('Content-Type', 'application/json')
                    parts, size = [], 0
                    while True:
                        remaining = request_deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError('provider request deadline exhausted')
                        # Recompute per-read timeout to enforce a hard request deadline.
                        raw = getattr(getattr(response, 'fp', None), 'raw', None)
                        sock = getattr(raw, '_sock', None)
                        if sock is not None:
                            sock.settimeout(remaining)
                        part = response.read1(16384)
                        if not part:
                            break
                        parts.append(part)
                        size += len(part)
                        if size > 4000000:
                            raise ValueError('provider response exceeds byte cap')
                    payload = b''.join(parts)
                chunks = []
                if body.get('stream'):
                    for line in payload.decode().splitlines():
                        if line.startswith('data: ') and line[6:] != '[DONE]':
                            with contextlib.suppress(ValueError): chunks.append(json.loads(line[6:]))
                else:
                    chunks = [json.loads(payload)]
                row['usage'] = next((x['usage'] for x in reversed(chunks) if x.get('usage')), None)
                row['response_models'] = sorted({x['model'] for x in chunks if x.get('model')})
                if row['response_models'] != [self.model]:
                    raise ValueError('provider response model mismatch')
                row['response_tool_call_ids'] = sorted({t['id'] for x in chunks for c in x.get('choices', []) for t in (c.get('delta') or c.get('message') or {}).get('tool_calls', []) if t.get('id')})
                row['tool_call_count'] = len(row['response_tool_call_ids'])
        except urllib.error.HTTPError as exc:
            status = exc.code
            row['error'] = 'provider_http_error'
            row['retry_after'] = exc.headers.get('Retry-After')
            if status == 429 and row['retry_after'] and time.monotonic() < self.deadline:
                from email.utils import parsedate_to_datetime
                try:
                    delay = float(row['retry_after'])
                except ValueError:
                    try: delay = max(0, parsedate_to_datetime(row['retry_after']).timestamp() - time.time())
                    except (ValueError, TypeError): delay = 0
                try:
                    with open('/tmp/benchmark-nvidia-rate.lock', 'a+') as rate:
                        acquire_rate_lock(rate, self.deadline)
                        rate.seek(0); rate.truncate(); rate.write(str(time.time() + delay)); rate.flush()
                except (ValueError, OSError):
                    row['limiter_update_error'] = 'retry-after could not be persisted before deadline'
            payload = json.dumps({'error': {'message': 'NVIDIA HTTP %d' % status, 'type': 'provider_error'}}).encode()
        except Exception as exc:
            row['error'] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
            status = 403 if isinstance(exc, ValueError) else 502
            payload = json.dumps({'error': {'message': row['error'], 'type': 'benchmark_gateway'}}).encode()
        row.update(status=status, duration_s=time.time() - start)
        with self.lock:
            self.record(row)
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
