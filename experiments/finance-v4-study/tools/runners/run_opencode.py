"""OpenCode native standalone run, isolated HOME/XDG with snapshot-only tools."""
import json
import os
from pathlib import Path
import sys
import subprocess
import signal
import socket
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import popen_run
from isolated import prepare, finish, SNAPSHOT
OPENCODE_BIN = os.path.expanduser('~/.opencode/bin/opencode')


def run(ws, instruction, task_dir, model, timeout_s, log_path, options=None):
    options = {**(options or {}), 'timeout_s': timeout_s}
    root, env, gateway, mcp_env = prepare(ws, task_dir, model, options)
    cfg = {'$schema': 'https://opencode.ai/config.json',
        'plugins': ['-*', 'opencode.agent', 'opencode.config.agent', 'opencode.config.mcp', 'opencode.config.provider', 'opencode.provider.dynamic', 'opencode.provider.nvidia', 'opencode.tools'],
        'agents': {'title': {'disabled': True}, 'summary': {'disabled': True}, 'compaction': {'disabled': True}},
        'providers': {'nvidia': {'package': '@ai-sdk/openai-compatible', 'name': 'NVIDIA controlled gateway',
            'settings': {'apiKey': gateway.token, 'baseURL': gateway.url},
            'models': {gateway.model: {'name': gateway.model, 'capabilities': {'tools': True, 'input': ['text'], 'output': ['text'], 'reasoning': {'supported': False}},
                'limit': {'context': 32000, 'output': 2048}}}}},
        'permissions': [{'action': action, 'resource': '*', 'effect': 'deny'} for action in ('execute','subagent','browser','shell','external_directory','webfetch','websearch','read','write','edit','glob','grep','skill','question','task','todowrite','todoread')],
        'mcp': {'servers': {'opentrading': {'type': 'local', 'command': [sys.executable, str(SNAPSHOT)],
                  'environment': mcp_env, 'codemode': False}}}}
    config_path = Path(env['XDG_CONFIG_HOME']) / 'opencode/opencode.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(cfg, indent=2))
    env.update(OPENCODE_CONFIG=str(config_path), OPENCODE_DISABLE_EXTERNAL_SKILLS='1',
        OPENCODE_DISABLE_PROJECT_CONFIG='1', OPENCODE_DISABLE_AUTOUPDATE='1', OPENCODE_DISABLE_MODELS_FETCH='1',
        OPENCODE_DISABLE_AUTOCOMPACT='1')
    # Start a dedicated native server, wait for its MCP catalog, then attach the
    # native CLI run. run --standalone can race slow Python MCP startup.
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    server_url = 'http://127.0.0.1:%d' % port
    env['PWD'] = str(Path(ws).resolve())
    env['OPENCODE_SERVER_PASSWORD'] = gateway.token
    started = time.monotonic()
    rc, out, err, timed_out = 1, '', '', False
    startup_error = ''
    server = None
    with gateway, open(root / 'opencode-server.log', 'w', encoding='utf-8') as server_log:
        try:
            server = subprocess.Popen([OPENCODE_BIN, 'serve', '--hostname', '127.0.0.1', '--port', str(port)],
                cwd=ws, env=env, stdin=subprocess.DEVNULL, stdout=server_log, stderr=server_log,
                text=True, start_new_session=True)
            catalog = None
            while time.monotonic() - started < min(45, timeout_s):
                if server.poll() is not None:
                    raise RuntimeError('native OpenCode server exited during startup')
                remaining = timeout_s - (time.monotonic() - started)
                try:
                    check = subprocess.run([OPENCODE_BIN, 'api', '--server', server_url, 'mcp.list'],
                        cwd=ws, env=env, capture_output=True, text=True, timeout=max(0.1, min(8, remaining)))
                except subprocess.TimeoutExpired:
                    continue
                try: catalog = json.loads(check.stdout)
                except ValueError: catalog = None
                (root / 'mcp-check.log').write_text((check.stdout + '\n' + check.stderr).replace(gateway.token, '[local-token]'))
                (root / 'mcp-catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2))
                if catalog and any(item.get('name', item.get('id')) == 'opentrading' and
                    (item.get('status') == 'connected' or (isinstance(item.get('status'), dict) and item['status'].get('status') == 'connected'))
                    for item in catalog.get('data', [])):
                    break
                time.sleep(min(0.5, max(0, timeout_s - (time.monotonic() - started))))
            else:
                raise TimeoutError('native OpenCode MCP catalog did not become ready')
            remaining = timeout_s - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError('trial deadline exhausted during MCP startup')
            rc, out, err, timed_out = popen_run([OPENCODE_BIN, 'run', '--server', server_url, '--format', 'json',
                '--auto', '--title', 'benchmark trial', '-m', model, instruction],
                cwd=ws, env=env, timeout_s=remaining, log_path=log_path)
        except Exception as exc:
            startup_error = str(exc) if isinstance(exc, (RuntimeError, TimeoutError)) else type(exc).__name__
            timed_out = isinstance(exc, (TimeoutError, subprocess.TimeoutExpired))
            Path(log_path).write_text('native OpenCode startup/run failed: ' + startup_error + '\n')
        finally:
            if server is not None:
                try: os.killpg(server.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: server.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    try: os.killpg(server.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    server.wait(timeout=1)
                try: os.killpg(server.pid, signal.SIGKILL)
                except ProcessLookupError: pass
    final_text, session, native_error = parse_output(out)
    return finish(root, gateway, {'status': 'timeout' if timed_out else 'ok' if rc == 0 and not native_error else 'error',
        'final_text': final_text, 'session_id': session, 'notes': startup_error or ('' if rc == 0 and not native_error else 'native runner error (exit=%s)' % rc)}, 'opencode', cfg)


def parse_output(output):
    """Use only the final assistant step, preserving unmodified text contents."""
    texts, session, native_error = {}, None, False
    for line in output.splitlines():
        try: event = json.loads(line)
        except ValueError: continue
        session = event.get('sessionID') or session
        native_error = native_error or event.get('type') == 'error'
        part = event.get('part') or {}
        if event.get('type') in ('step_start', 'tool_use'):
            texts.clear()
        if event.get('type') == 'text' and isinstance(part.get('text'), str):
            texts[part.get('id', len(texts))] = part['text']
    return '\n'.join(texts.values()), session, native_error
