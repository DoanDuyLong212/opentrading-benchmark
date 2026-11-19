"""Common isolated per-attempt runner setup and auditable provider accounting."""
from protocol_compat import FINANCIAL_PROTOCOL
import json
import os
import site
import hashlib
import sys
from pathlib import Path
from provider import ProviderGateway, aggregate_usage, clean_env

TOOLS = Path(__file__).resolve().parents[1]
SNAPSHOT = TOOLS / 'mcp_snapshot_server.py'


def prepare(ws, task_dir, model, options):
    options = dict(options or {})
    from paid_budget import paid_policy, validate_free_identity
    paid_policy(model, options)
    validate_free_identity(model, options)
    from trusted_bun import trusted_bun
    from trusted_toolchain import trusted_runtime
    options['native_bun_binary'] = str(trusted_bun())
    options['opentrading_runtime_root'] = str(trusted_runtime(options))
    root = Path(ws).resolve().parent / 'runner'
    root.mkdir(parents=True, exist_ok=True)
    env = clean_env(root / 'home')
    ledger = options.get('provider_ledger') or str(root / 'provider.jsonl')
    sys.path.insert(0, str(TOOLS))
    from mcp_snapshot_server import load_entries, build_tool_defs
    entries, payloads = load_entries(Path(task_dir).resolve() / 'environment/payloads.json')
    as_of = payloads.get('snapshot_date')
    if not isinstance(as_of, str) or not as_of:
        raise ValueError('Frozen snapshot_date required for common clock context')
    options['snapshot_as_of'] = as_of
    definitions = build_tool_defs(entries)
    options['allowed_tool_names'] = sorted({prefix + item['name'] for item in definitions for prefix in ('opentrading_', 'mcp__opentrading__', 'mcp_opentrading_')})
    options['snapshot_tool_definitions'] = definitions
    # Every arm gets its own native shell tool; commands execute unfiltered
    # inside the shared no-network Docker sandbox (mathshell/ is the launcher). OpenTrading keeps read_result for its spilled tool output.
    if options.get('native_arm') in ('opencode', 'dsh') and options.get('protocol') == FINANCIAL_PROTOCOL:
        shell_def = json.loads((TOOLS / 'runners/native_shell_tools.json').read_text())[options['native_arm']]
        options['allowed_tool_names'] += [shell_def['name']]
        options['native_tool_definitions'] = [{'name': shell_def['name'], 'inputSchema': shell_def['inputSchema']}]
    if options.get('native_arm') == 'opentrading' and options.get('protocol') == FINANCIAL_PROTOCOL:
        options['allowed_tool_names'] += ['shell','read_result']
        import subprocess
        sourceenv=dict(env,BENCH_OT_RUNTIME=str(options['opentrading_runtime_root']))
        got=subprocess.run([options['native_bun_binary'],str(TOOLS/'runners/native_schema.ts')],env=sourceenv,capture_output=True,text=True,timeout=30,check=True)
        options['native_tool_definitions']=json.loads(got.stdout)
    gateway = ProviderGateway(model, ledger, options)
    bun_path=options['native_bun_binary']
    bun_sha=hashlib.sha256(Path(bun_path).read_bytes()).hexdigest()
    mcp_env = {'BENCH_BUN_BIN':bun_path,'BENCH_BUN_SHA256':bun_sha,'PYTHONPATH': site.getusersitepackages(), 'BENCH_PAYLOADS': str(Path(task_dir).resolve() / 'environment/payloads.json')}
    # Shared shell sandbox (sandbox/run.ts, decision 2026-11-16 6b): mathshell/bin first in PATH and
    # $SHELL for every arm; each command runs unfiltered in a no-network container that sees only this
    # trial's workspace and its own temp folder.
    if options.get('protocol') == FINANCIAL_PROTOCOL:
        mathshell = TOOLS / 'runners/mathshell'
        image = options.get('sandbox_image')
        if not image:
            raise ValueError('v4.7 shell sandbox image (provider_options.sandbox_image) required')
        env['PATH'] = str(mathshell / 'bin') + os.pathsep + env.get('PATH', '/usr/bin:/bin')
        env['SHELL'] = str(mathshell / 'bin/bash')
        env['BENCH_BUN_BIN'] = bun_path
        env['BENCH_SHELL_SANDBOX'] = str(TOOLS / 'runners/sandbox/run.ts')
        env['BENCH_SANDBOX_IMAGE'] = str(image)
        env['BENCH_SANDBOX_WORKSPACE'] = str(Path(ws).resolve())
        env['BENCH_SANDBOX_TMP'] = str(root / 'sandbox-tmp')
        env['BENCH_OT_RUNTIME'] = str(options['opentrading_runtime_root'])
        env['BENCH_SHELL_LEDGER'] = str(root / 'shell.jsonl')
        env['BENCH_SHELL_ARM'] = str(options.get('native_arm') or '')
    evidence = options.get('mcp_ledger') or os.environ.get('BENCH_MCP_LEDGER')
    if evidence:
        mcp_env['BENCH_MCP_LEDGER'] = str(Path(evidence).resolve())
    return root, env, gateway, mcp_env


def finish(root, gateway, result, arm, config):
    inventory = {'arm': arm, 'model': gateway.model, 'provider': 'openrouter' if gateway.options.get('provider_route') in ('openrouter_free','openrouter_paid') else 'nvidia',
                 'provider_route': gateway.options.get('provider_route', 'nvidia'),
                 'effort': gateway.options.get('effort', 'none'),
                 'effective_caps': {k:gateway.options.get(k) for k in ('max_requests','max_output_tokens','model_max_output_tokens','max_total_tokens','timeout_s','provider_timeout_s')},
                 'condition': gateway.options.get('condition', arm),
                 'native_arm': gateway.options.get('native_arm', arm),
                 'prompt_variant': gateway.options.get('prompt_variant'),
                 'finance_policy': gateway.options.get('finance_policy', False),
                 'clock_policy': {'answer_as_of': gateway.options.get('snapshot_as_of'),
                                  'native_now_pinned': arm == 'opentrading',
                                  'cross_arm_native_date_parity_verified': False,
                                  's3_comparative_eligible': False,
                                  'effective_native_date': None,
                                  'effective_native_date_evidence': 'not audited from complete captured requests',
                                  'native_stall_ms': 300000 if arm == 'opentrading' else None,
                                  'native_clock_limitation': None if arm == 'opentrading' else 'native runtime clock not controlled; captured request exposes effective context'},
                 'snapshot_tool_definitions': gateway.options.get('snapshot_tool_definitions', []),
                 'allowed_tool_names': gateway.options.get('allowed_tool_names', []),
                 'native_system_prompt': True, 'skills': [], 'external_plugins': [],
                 'tool_policy': {'snapshot_mcp': True, 'shell': 'native commands unfiltered in shared no-network Docker sandbox',
                                 'native_tools': [d.get('name') for d in gateway.options.get('native_tool_definitions', [])],
                                 'memory_profile': gateway.options.get('memory_profile', 'none'),
                                 'external_web_subagents': False},
                 'isolation': {'native_harness': 'host process with isolated HOME/XDG/environment',
                               'shell_commands': 'Docker: no network, read-only root, trial workspace/tmp mounts only',
                               'sandbox_image': gateway.options.get('sandbox_image')},
                 'config': config, 'observed_tool_sets': [r.get('tool_names', []) for r in gateway.rows],
                 'provider_requests': len(gateway.rows),
                 'provider_upstream_requests': sum(bool(r.get('upstream_attempted')) for r in gateway.rows),
                 'usage_complete': bool(gateway.rows) and bool((aggregate_usage(gateway.rows) or {}).get('complete'))}
    native = root / 'native-inventory.json'
    if native.exists():
        inventory['native_inventory'] = json.loads(native.read_text())
    catalog = root / 'mcp-catalog.json'
    if catalog.exists():
        inventory['native_mcp_catalog'] = json.loads(catalog.read_text())
    if arm == 'opentrading':
        from experiment_conditions import prompt_directory
        directory = prompt_directory(gateway.options.get('prompt_variant') or 'finance')
        inventory['prompt_directory'] = str(directory)
        inventory['prompt_files'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob('*.md'))}
    # Local gateway bearer is ephemeral and not a provider credential; redact nevertheless.
    clean = json.loads(json.dumps(inventory).replace(gateway.token, '[local-gateway-token]'))
    path = root / 'inventory.json'
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + '\n')
    result.update(tokens=aggregate_usage(gateway.rows), provider_requests=len(gateway.rows),
                  provider_usage=aggregate_usage(gateway.rows), inventory_path=str(path),
                  provider_ledger=str(gateway.ledger), answer_path=None, answer_candidates=[])
    if not gateway.rows and result.get('status') == 'ok':
        result['status'] = 'error'
        result['notes'] = 'native harness produced no provider request'
    logical={}
    for row in gateway.rows:logical.setdefault(row.get('logical_request_id',('single',row.get('index'))),[]).append(row)
    final_failures=[group for group in logical.values() if group[-1].get('status') != 200]
    result['transport_recovered']=any(len(group)>1 and group[-1].get('status')==200 for group in logical.values())
    result['first_attempt_completed']=bool(gateway.rows) and not final_failures and result.get('status')=='ok' and bool(result.get('final_text')) and all(len(group)==1 for group in logical.values())
    result['token_reservations_not_observed_usage']=sum(r.get('token_reservation',0) for r in gateway.rows)
    result['native_derived_ledger']=str(root/'native-derived.jsonl') if (root/'native-derived.jsonl').exists() else None
    if final_failures:
        result['status'] = 'error' if result['status'] != 'timeout' else 'timeout'
        result['notes'] = 'provider request failed; inspect redacted provider ledger'
    return normalize_native_completion(result)


def normalize_native_completion(result):
    """Native termination is independent from raw public JSON validity."""
    completion=result.get('native_completion')
    if isinstance(completion,dict):
        completion['accepted']=bool(result.get('status')=='ok' and completion.get('outcome')=='completed' and result.get('final_text'))
    result['native_completed']=bool(isinstance(completion,dict) and completion.get('accepted'))
    return result
