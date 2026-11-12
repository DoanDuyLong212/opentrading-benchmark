"""OpenTrading native agent, with only frozen snapshot MCP tools."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import popen_run
from isolated import prepare, finish, SNAPSHOT, TOOLS

BUN = os.path.expanduser('~/.bun/bin/bun')


def run(ws, instruction, task_dir, model, timeout_s, log_path, options=None):
    options = {**(options or {}), 'timeout_s': timeout_s}
    root, env, gateway, mcp_env = prepare(ws, task_dir, model, options)
    from experiment_conditions import RUNTIME_ROOT, prompt_directory
    if not options.get('opentrading_runtime_root') or Path(options['opentrading_runtime_root']).resolve() != RUNTIME_ROOT.resolve():
        raise ValueError('Explicit trusted OpenTrading runtime root required')
    variant = options.get('prompt_variant') or 'finance'
    prompts = prompt_directory(variant)
    env.update(BENCH_OT_RUNTIME=str(RUNTIME_ROOT.resolve()), BENCH_PROMPT_DIR=str(prompts),
               BENCH_AS_OF=gateway.options['snapshot_as_of'])
    home = root / 'ot-home'
    (home / 'cache').mkdir(parents=True, exist_ok=True)
    cfg = {'provider': 'nvidia', 'model': gateway.model, 'toolSearch': 'off', 'memory': {'provider': 'none'},
           'benchmark_prompt_variant': variant, 'benchmark_runtime_root': str(RUNTIME_ROOT.resolve())}
    (home / 'config.json').write_text(json.dumps(cfg))
    (home / 'auth.json').write_text(json.dumps({'nvidia': {'type': 'api', 'key': gateway.token}}))
    catalog = {'nvidia': {'id': 'nvidia', 'name': 'NVIDIA controlled gateway', 'env': ['NVIDIA_API_KEY'],
               'npm': '@ai-sdk/openai-compatible', 'api': gateway.url,
               'models': {gateway.model: {'id': gateway.model, 'name': gateway.model, 'reasoning': False,
                                          'tool_call': True, 'limit': {'context': 32000, 'output': 2048}}}}}
    (home / 'cache/models.json').write_text(json.dumps(catalog))
    mcp = {'mcpServers': {'opentrading': {'type': 'stdio', 'command': sys.executable,
            'args': [str(SNAPSHOT)], 'env': mcp_env, 'startupTimeoutMs': 30000,
            'toolTimeoutMs': 30000, 'alwaysLoad': True}}}
    (home / 'mcp.json').write_text(json.dumps(mcp))
    env.update(OPENTRADING_HOME=str(home), NVIDIA_API_KEY=gateway.token)
    env['BENCH_INVENTORY'] = str(root / 'native-inventory.json')
    with gateway:
        rc, out, err, timed_out = popen_run([BUN, str(TOOLS / 'runners/ot_headless.ts'), instruction],
            cwd=ws, env=env, timeout_s=timeout_s, log_path=log_path)
    session = None
    errors = []
    for line in err.splitlines():
        try: event = json.loads(line)
        except ValueError: continue
        if event.get('type') == 'error': errors.append(event.get('message', 'agent error'))
        session = event.get('sessionId') or event.get('session') or session
    return finish(root, gateway, {'status': 'timeout' if timed_out else 'ok' if rc == 0 and not errors else 'error',
        'final_text': out, 'session_id': session, 'notes': '; '.join(errors)[:180]}, 'opentrading', cfg)
