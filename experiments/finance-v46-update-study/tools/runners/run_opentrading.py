"""OpenTrading native agent, with only frozen snapshot MCP tools."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import popen_run
from isolated import prepare, finish, SNAPSHOT, TOOLS

BUN = os.path.expanduser('~/.bun/bin/bun')


def native_result_status(rc, stderr, timed_out):
    """Use the current native completion event, retaining partial text separately."""
    session, errors, completion = None, [], None
    contract_invalid = None
    for line in stderr.splitlines():
        try: event = json.loads(line)
        except ValueError: continue
        if not isinstance(event,dict): continue
        if event.get('type') == 'error': errors.append(event.get('message','agent error'))
        if event.get('type') == 'notice':
            try: notice=json.loads(event.get('text',''))
            except (ValueError,TypeError): notice={}
            if notice.get('event')=='financial_contract_invalid':contract_invalid=notice

        session = event.get('sessionId') or event.get('session') or session
        if event.get('type') == 'done':
            completion = {'outcome':event.get('outcome'), 'unanswered':event.get('unanswered',False),
                          'recoveries':event.get('recoveries',[])}
    outcome = (completion or {}).get('outcome')
    status = ('timeout' if timed_out else 'error' if rc != 0 or errors else
              'native_contract_invalid' if contract_invalid is not None else 'ok' if outcome == 'completed' else 'aborted' if outcome == 'aborted' else 'error')
    note = '; '.join(str(error) for error in errors)
    if not note and status != 'ok': note = 'Native completion outcome: '+str(outcome)
    return {'status':status, 'session_id':session, 'notes':note[:180], 'native_completion':completion, 'native_contract_invalid':contract_invalid}


def run(ws, instruction, task_dir, model, timeout_s, log_path, options=None):
    options = {**(options or {}), 'timeout_s': timeout_s}
    root, env, gateway, mcp_env = prepare(ws, task_dir, model, options)
    from experiment_conditions import RUNTIME_ROOT, prompt_directory
    if not options.get('opentrading_runtime_root') or Path(options['opentrading_runtime_root']).resolve() != RUNTIME_ROOT.resolve():
        raise ValueError('Explicit trusted OpenTrading runtime root required')
    variant = options.get('prompt_variant') or 'finance'
    prompts = prompt_directory(variant)
    env.update(BENCH_OT_RUNTIME=str(RUNTIME_ROOT.resolve()), BENCH_PROMPT_DIR=str(prompts),
               BENCH_AS_OF=gateway.options['snapshot_as_of'],
               BENCH_FINANCE_POLICY='on' if options.get('finance_policy') else 'off',
               BENCH_NATIVE_LEDGER=str(root/'native-derived.jsonl'), BENCH_PROVIDER_LEDGER=str(gateway.ledger), BENCH_NATIVE_RETRY_MAX='0')
    home = root / 'ot-home'
    (home / 'cache').mkdir(parents=True, exist_ok=True)
    cfg = {'provider': 'nvidia', 'model': gateway.model, 'toolSearch': 'off', 'memory': {'provider': 'notebook' if options.get('memory_profile')=='controlled-memory-v1' and options.get('condition')=='ot_memory_on' else 'none'},
           'benchmark_prompt_variant': variant, 'benchmark_runtime_root': str(RUNTIME_ROOT.resolve())}
    (home / 'config.json').write_text(json.dumps(cfg))
    (home / 'auth.json').write_text(json.dumps({'nvidia': {'type': 'api', 'key': gateway.token}}))
    catalog = {'nvidia': {'id': 'nvidia', 'name': 'NVIDIA controlled gateway', 'env': ['NVIDIA_API_KEY'],
               'npm': '@ai-sdk/openai-compatible', 'api': gateway.url,
               'models': {gateway.model: {'id': gateway.model, 'name': gateway.model, 'reasoning': bool(options.get('native_reasoning_capability',True)),
                                          'tool_call': True, 'limit': {'context': int(options.get('context_window',32768)), 'output': int(options.get('max_output_tokens',2048))}}}}}
    (home / 'cache/models.json').write_text(json.dumps(catalog))
    mcp = {'mcpServers': {'opentrading': {'type': 'stdio', 'command': sys.executable,
            'args': [str(SNAPSHOT)], 'env': mcp_env, 'startupTimeoutMs': 30000,
            'toolTimeoutMs': 30000, 'alwaysLoad': True}}}
    (home / 'mcp.json').write_text(json.dumps(mcp))
    env.update(OPENTRADING_HOME=str(home), NVIDIA_API_KEY=gateway.token)
    env['BENCH_INVENTORY'] = str(root / 'native-inventory.json')
    with gateway:
        rc, out, err, timed_out = popen_run([options.get('native_bun_binary') or BUN, str(TOOLS / 'runners/ot_headless.ts'), instruction],
            cwd=ws, env=env, timeout_s=timeout_s, log_path=log_path)
    native = native_result_status(rc, err, timed_out)
    return finish(root, gateway, {**native, 'final_text': out}, 'opentrading', cfg)
