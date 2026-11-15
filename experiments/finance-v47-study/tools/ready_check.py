#!/usr/bin/env python3
"""Read-only offline checks by default. Network discovery is opt-in.

A green offline result is not proof of runtime parity or financial-source truth.
A freeze certificate additionally requires the full regression suite and a completed
three-arm smoke run for this exact model/config/code/harness inventory.
"""
import argparse
import asyncio
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))


def c_provider(args):
    import urllib.request
    if not args.model.startswith('nvidia/'):
        return False, 'only NVIDIA provider verification is currently supported'
    key = os.environ.get('NVIDIA_API_KEY')
    if not key:
        return False, 'NVIDIA_API_KEY absent'
    request = urllib.request.Request('https://integrate.api.nvidia.com/v1/models',
                                     headers={'Authorization': 'Bearer '+key})
    with urllib.request.urlopen(request, timeout=30) as response:
        models = json.load(response)
    available = args.model.removeprefix('nvidia/') in {r['id'] for r in models.get('data', [])}
    return available, 'model listed' if available else 'model not in account catalog'


def bounded_command(command, timeout_s, cwd=ROOT):
    """A hard deadline also covers blocked SDK shutdown and descendant processes.

    Files avoid pipe-draining hangs when a grandchild inherits stdout/stderr.
    Every child in the command's session is killed on a deadline.
    """
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(command, cwd=cwd, stdout=stdout, stderr=stderr,
                                   start_new_session=True)
        try:
            code = process.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
            stdout.seek(0)
            progress = stdout.read().decode(errors='replace')[-1000:].strip()
            raise TimeoutError('Preflight exceeded %.1fs; child process group killed%s' %
                               (timeout_s, '; progress: '+progress if progress else ''))
        stdout.seek(0)
        stderr.seek(0)
        return subprocess.CompletedProcess(command, code, stdout.read().decode(errors='replace'),
                                           stderr.read().decode(errors='replace'))


def c_snapshot(_):
    result = bounded_command([sys.executable, str(Path(__file__).resolve()), '--snapshot-worker'], 30)
    return result.returncode == 0, (result.stdout+'\n'+result.stderr).strip()[-3000:]


def snapshot_worker():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    payloads = ROOT/'tasks'/'smoke'/'smoke-quote-01'/'environment'/'payloads.json'
    from mcp_snapshot_server import load_entries
    entries, _ = load_entries(payloads)
    entry = entries[0][1]
    tool, params = entry['tool'], entry['params']
    async def probe(ledger):
        print('MCP: spawning snapshot server', flush=True)
        env = dict(os.environ, BENCH_MCP_LEDGER=ledger)
        server = StdioServerParameters(command=sys.executable,
                                       args=[str(HERE/'mcp_snapshot_server.py'), str(payloads)], env=env)
        async with stdio_client(server) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                print('MCP: initialized', flush=True)
                names = [t.name for t in (await session.list_tools()).tools]
                result = await session.call_tool(tool, params)
                envelope = json.loads(result.content[0].text)
                print('MCP: tool response received; closing client', flush=True)
                return tool in names and not result.isError and bool(envelope.get('benchmark_evidence'))
    with tempfile.TemporaryDirectory(prefix='benchmark-ready-') as tmp:
        ledger = str(Path(tmp)/'mcp.jsonl')
        ok = asyncio.run(probe(ledger))
        print('MCP: client closed', flush=True)
        from run_benchmark import load_ledger
        rows = load_ledger(ledger)
    return ok and len(rows) == 1 and rows[0]['status'] == 'ok', 'strict replay and authoritative ledger roundtrip'


def c_grader(_):
    from build_main import synthesize
    from run_benchmark import grade_answer
    task = ROOT/'tasks'/'smoke'/'smoke-quote-01'
    gold = json.loads((task/'solution'/'gold.json').read_text())
    answer = synthesize(gold)
    answer['evidence'] = [dict(row, call_id='offline-fixture', payload_sha256=gold['payload_sha256'])
                          for row in gold['provenance_contract']]
    with tempfile.TemporaryDirectory(prefix='benchmark-grade-') as tmp:
        ap = Path(tmp)/'answer.json'
        ap.write_text(json.dumps(answer))
        correct = grade_answer(str(ap), str(task), tmp)
        answer['value'] = 9e99
        ap.write_text(json.dumps(answer))
        wrong = grade_answer(str(ap), str(task), tmp)
    return bool(correct['success']) and not wrong['success'], 'offline oracle fixture passes; wrong numeric answer fails'


def c_isolation(_):
    from run_benchmark import make_workspace
    with tempfile.TemporaryDirectory(prefix='benchmark-isolation-') as tmp:
        ws = make_workspace(str(Path(tmp)/'ws'), str(ROOT/'tasks'/'smoke'/'smoke-quote-01'))
        return sorted(os.listdir(ws)) == ['instruction.md'], 'fresh instruction-only workspace'


def c_harnesses(args):
    from run_manifest import harness_inventory
    config_path = getattr(args, 'config', str(ROOT/'tools/bench_config.json'))
    inventory = harness_inventory(json.loads(Path(config_path).read_text()))
    ok = all(inventory.get(arm, {}).get('version') for arm in ('opencode','dsh','bun')) and bool(inventory.get('opentrading', {}).get('source_sha256'))
    return ok, json.dumps({k: v.get('version', v.get('source_sha256')) for k,v in inventory.items()})


def c_tests(_):
    result = bounded_command([sys.executable, '-m', 'pytest', 'tools/tests', '-q'], 300)
    output = (result.stdout+'\n'+result.stderr).strip()
    return result.returncode == 0, output[-3000:]


def verify_mcp_attempt(task, attempt, allow_empty=False):
    """Replay ledger arguments offline; only explicit contract rejections are healthy.

    This validates execution evidence, independently of whether the model selected
    useful arguments. Never turn a rejected request into a successful tool result.
    """
    from mcp_snapshot_server import load_entries, select_entry, select_envelope, digest
    from run_benchmark import load_ledger
    from run_manifest import hash_file
    ledger = attempt.get('ledger_path')
    if not ledger or not Path(ledger).is_file():
        if allow_empty:
            return []  # Caller must prove provider emitted zero tool calls.
        raise ValueError('Missing authoritative MCP ledger')
    rows = load_ledger(ledger)
    if not rows:
        if allow_empty:
            return []
        raise ValueError('Missing observed MCP attempt')
    payload = task/'environment'/'payloads.json'
    entries, _ = load_entries(payload)
    sources={}
    calculation_refs={}
    for row in rows:
        arguments = row.get('arguments')
        if (row.get('schema_version') != 2 or not isinstance(arguments, dict)
                or row.get('arguments_sha256') != digest(arguments)
                or row.get('payload_sha256') != hash_file(payload)):
            raise ValueError('Invalid or unbound MCP ledger record')
        if row.get('tool') in ('analytics_compute','analytics_calculate'):
            from analytics_compute import compute
            try:
                if row['tool']=='analytics_compute':derived=compute(arguments,sources)
                else:
                    from analytics_calculate import calculate
                    derived=calculate(arguments,sources,calculation_refs)
                    derived['derived_ref']='calc:'+row['call_id']
            except (ValueError,KeyError,IndexError,TypeError,OverflowError,__import__('decimal').DecimalException,__import__('jsonschema').ValidationError) as exc:
                if row.get('status')!='rejected' or row.get('error_code')!='invalid_derivation' or row.get('error')!=str(exc):
                    raise ValueError('Invalid derivation rejection differs from actual dependency validation')
            else:
                if row.get('status')!='ok' or row.get('response_sha256')!=digest(derived) or row.get('derivation')!=derived['derived_result'] or row.get('source_evidence')!=derived['source_evidence']:
                    raise ValueError('Derived result differs from exact prior source arithmetic')
                if row['tool']=='analytics_calculate':
                    if row.get('derived_ref')!=derived['derived_ref']:raise ValueError('Derived reference differs from ledger namespace')
                    calculation_refs[derived['derived_ref']]=derived
            if row.get('record_kind')!='deterministic_derivation' or any(row.get(k) is not None for k in ('matched_entry_id','source','as_of')):
                raise ValueError('Derived call masquerades as upstream financial evidence')
            continue
        try:
            key, _ = select_entry(entries, row.get('tool'), arguments)
            envelope = select_envelope(entries, row.get('tool'), arguments)
        except (KeyError, ValueError) as exc:
            expected_error = type(exc).__name__ + ': request not replayable; inspect snapshot_requests'
            if (row.get('status') != 'rejected' or row.get('error') != expected_error
                    or any(row.get(k) is not None for k in ('matched_entry_id', 'source', 'as_of', 'response_sha256'))):
                raise ValueError('MCP failure is not an explicit snapshot contract rejection')
        else:
            provenance = envelope.get('provenance') or {}
            if (row.get('status') != 'ok' or row.get('matched_entry_id') != key
                    or row.get('response_sha256') != digest(envelope)
                    or row.get('source') != provenance.get('source') or row.get('as_of') != provenance.get('as_of')):
                raise ValueError('Successful MCP ledger record disagrees with frozen replay')
            envelope['benchmark_evidence']={k:row[k] for k in ('call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of')}
            sources[row['call_id']]={**envelope,'_benchmark_request':{'tool':row['tool'],'arguments':arguments}}
    return rows


def verify_request_capture(request, expected_temperature=0, expected_top_p=1):
    from run_manifest import hash_file, digest_json
    import hashlib
    native_body = None
    for stage in ('native', 'effective'):
        capture = request.get(stage+'_request_capture')
        if not isinstance(capture, dict) or not capture.get('path'):
            raise ValueError('Provider wire request capture missing')
        path = Path(capture['path'])
        if not path.is_file() or hash_file(path) != capture.get('raw_sha256'):
            raise ValueError('Provider wire raw capture hash mismatch')
        body = json.loads(path.read_bytes())
        if digest_json(body) != capture.get('canonical_sha256'):
            raise ValueError('Provider wire canonical capture hash mismatch')
        if body.get('model') != request.get('request_model'):
            raise ValueError('Provider wire captured model differs from ledger')
        if [t.get('function', {}).get('name') for t in body.get('tools', [])] != request.get('tool_names'):
            raise ValueError('Provider wire captured tools differ from ledger')
        def paths(value, prefix='$'):
            found = [prefix]
            if isinstance(value, dict):
                for key, item in value.items(): found.extend(paths(item, prefix+'.'+key))
            elif isinstance(value, list):
                for index, item in enumerate(value): found.extend(paths(item, prefix+'[%d]' % index))
            return found
        if capture.get('field_paths') != paths(body):
            raise ValueError('Provider wire field paths mismatch')
        if stage == 'native' and (hashlib.sha256(json.dumps(body.get('messages'), sort_keys=True).encode()).hexdigest() != request.get('message_sha256')
                or hashlib.sha256(json.dumps(body.get('tools', []), sort_keys=True, ensure_ascii=False).encode()).hexdigest() != request.get('tool_schema_sha256')):
            raise ValueError('Provider wire messages/schema binding mismatch')
        if stage == 'effective' and (body.get('temperature') != expected_temperature or body.get('top_p') != expected_top_p):
            raise ValueError('Provider effective sampling policy mismatch')
        if stage == 'native':
            native_body = body
        else:
            permitted = {'temperature', 'top_p', 'max_tokens', 'max_completion_tokens', 'stream_options'}
            if {k:v for k,v in body.items() if k not in permitted} != {k:v for k,v in native_body.items() if k not in permitted}:
                raise ValueError('Provider effective body changed outside declared sampling/cap rewrites')
            if body.get('max_tokens') != request.get('effective_max_tokens'):
                raise ValueError('Provider effective output cap differs from ledger')


def verify_local_rejections(attempt, provider, definitions, enabled, return_records=False):
    """Join local SDK validation failures to generated IDs and next model context.

    A locally rejected argument never reaches MCP. It is counted only with an
    actual native event, schema-invalid input and the same error result in a
    hash-bound model request. This exception cannot hide lost executed calls.
    """
    import jsonschema
    path = attempt.get('log_path')
    if not path or not Path(path).is_file():
        return []
    events, all_events = [], []
    for line in Path(path).read_text(errors='replace').splitlines():
        try: event = json.loads(line)
        except ValueError: continue
        if isinstance(event, dict): all_events.append(event)
        if isinstance(event, dict) and event.get('localRejection'):
            events.append(event)
    # v45 current agent emits immutable finance notices after tool events.
    # Join them back by original SDK ID; never infer a rejection from prose.
    ends=[]
    for event in all_events:
        if event.get('type')=='tool-end':ends.append(event)
        if event.get('type')!='notice':continue
        try:notice=json.loads(event.get('text',''))
        except(ValueError,TypeError):continue
        matches=[end for end in ends if end.get('callId')==notice.get('sdk_call_id')]
        origin=notice.get('origin_provider_request_index')
        if origin is not None:
            matches=[end for end in matches if end.get('origin_provider_request_index',end.get('provider_request_index'))==origin]
            for field in ('memory_session','memory_turn','native_session_id'):
                wanted=notice.get('origin_'+field)
                if wanted is not None and any(end.get('origin_'+field,end.get(field)) is not None for end in matches):
                    # v4.6-update fix: disambiguate only when a candidate actually
                    # carries the field — the tool-end events predate origin
                    # stamping for some fields, and filtering on a field no
                    # candidate has killed every unique match.
                    matches=[end for end in matches if end.get('origin_'+field,end.get(field))==wanted]
        # Legacy unstamped histories are admissible only when genuinely unique.
        # A replay must never attach to the latest unrelated reuse of an SDK ID.
        if len(matches)!=1:
            if notice.get('event') in ('financial_call_audit','financial_local_rejection'):raise ValueError('Financial notice lacks unique immutable origin tool-end')
            continue
        target=matches[0]
        if notice.get('event')=='financial_call_audit':target['financeIntent']=notice
        if notice.get('event')=='financial_local_rejection':
            target['localRejection']={k:v for k,v in notice.items()if k not in('event','sdk_call_id')}
            if not any(target is old for old in events):events.append(target)
    if not events:
        # v4.6-update fix #9 (2026-11-10): MCP-level schema rejections on the
        # native CLI path surface as tool-end ok:false WITHOUT the finance
        # notice wrapper (the notice hook only fires for client-side
        # InvalidToolInputError before dispatch). Bind them here with the same
        # strictness as notice-joined rejections: exact callId join to a
        # tool-start, the finance rejection policy markers in the output, and
        # the canonical tool name parsed from the runtime error itself.
        starts={e.get('callId'):e for e in all_events if e.get('type')=='tool-start'}
        bound_ids={e.get('callId') for e in events if e.get('localRejection')}
        import re as _re
        for end in all_events:
            if end.get('type')!='tool-end' or end.get('ok') is not False:continue
            if end.get('callId') in bound_ids:continue
            output=str(end.get('output') or '')
            if 'invalid_argument' not in output or 'Type validation failed' not in output or 'Tham số không hợp lệ' not in output:continue
            start=starts.get(end.get('callId'))
            if not start or not start.get('name'):continue
            m=_re.search(r'cho\s+([A-Za-z0-9_]+):',output)
            tool_name=m.group(1) if m else start.get('name')
            end['localRejection']={'code':'invalid_tool_input','tool':tool_name,'rawInput':start.get('input'),'reason':output[:600],'origin_provider_request_index':end.get('origin_provider_request_index',end.get('provider_request_index')),'origin_sdk_call_id':end.get('callId')}
            events.append(end)
    if not events:
        return []
    if not enabled and any(event.get('localRejection',{}).get('code')=='policy_guard_rejected' for event in events):
        raise ValueError('Unexpected finance policy guard outside candidate policy')
    schemas = {prefix+d['name']: d['inputSchema'] for d in definitions
               for prefix in ('opentrading_', 'mcp__opentrading__', 'mcp_opentrading_')}
    read_only = {prefix+d['name'] for d in definitions if d.get('annotations',{}).get('readOnlyHint') is True
                 for prefix in ('opentrading_', 'mcp__opentrading__', 'mcp_opentrading_')}
    for d in definitions:
        if d.get('native_utility'):
            schemas[d['name']]={**d['inputSchema'],'x-opentrading-schema-profile':'finite-replay-c2'}
            read_only.add(d['name'])
    generated = {call for request in provider for call in request.get('response_tool_call_ids', [])}
    from collections import Counter
    generated_counts=Counter(call for request in provider for call in request.get('response_tool_call_ids',[]))
    seen=Counter();proof_records=[]
    for event in events:
        local, call_id = event['localRejection'], event.get('callId')
        name, raw = local.get('tool'), local.get('rawInput')
        if (local.get('code') not in ('invalid_tool_input', 'policy_guard_rejected') or event.get('ok') is not False
                or seen[call_id]>=generated_counts[call_id] or call_id not in generated or name not in schemas):
            raise ValueError('Local rejection lacks unique generated call/schema binding')
        seen[call_id]+=1
        arguments = raw
        # v4.6: distinct tool-failure classes. A schema-valid rejection is only
        # reconcilable with (a) an authenticated public finite-replay error or
        # (b) an infrastructure validator-compile failure; both keep the failed
        # call and its cost, neither becomes financial evidence. Anything else
        # fails closed.
        reason_text = str(local.get('reason') or '')
        event_output = str((event or {}).get('output') or '')
        compile_failure = any(marker in reason_text + ' ' + event_output for marker in
                              ('invalid escaped character for Unicode pattern', 'Invalid regular expression'))
        public_finite = any(marker in reason_text + ' ' + event_output for marker in
                            ('unsupported_snapshot_query', 'request not replayable', 'invalid_derivation'))
        classification = None
        if compile_failure:
            # v4.6: the JS/Ajv schema compile crash precedes argument validation.
            # Every call to that tool fails identically; this is an infrastructure
            # admission failure regardless of argument validity.
            classification = 'validator_compilation_failure'
        if local['code'] == 'invalid_tool_input' and classification is None:
            try:
                arguments = json.loads(raw) if isinstance(raw, str) else raw
                jsonschema.validate(arguments, schemas[name])
                schema_valid = True
            except (ValueError, jsonschema.ValidationError):
                schema_valid = False
                arguments = json.loads(raw) if isinstance(raw, str) else raw
            if schema_valid and public_finite:
                classification = 'schema_valid_unsupported_captured_query'
            elif not schema_valid:
                classification = 'schema_invalid_arguments'
            else:
                raise ValueError('Claimed local rejection has schema-valid arguments and an unauthenticated public reason')
        else:
            arguments = json.loads(raw) if isinstance(raw, str) else raw
            if schemas[name].get('x-opentrading-schema-profile') in ('finite-replay-c2','deterministic-derivation-v44','deterministic-derivation-v45','grounded-calculation-v45'):
                from intent_audit import verify_v42_local_intent
                verify_v42_local_intent(event,all_events,provider,schemas)
            else:
                reason = local.get('reason')
                bounded_reason = 'Bounded finance correction allows one execution of each originally failed read-only tool only.'
                if reason == bounded_reason:
                    allowed = local.get('allowedTools')
                    if (local.get('phase') != 'bounded_finance_correction' or not isinstance(allowed,list)
                            or len(allowed) != len(set(allowed)) or any(tool not in read_only for tool in allowed)):
                        raise ValueError('Bounded correction lacks actual registered allowed-tool phase')
                    phase_proven = False
                    for request in provider:
                        if call_id not in request.get('response_tool_call_ids',[]): continue
                        capture = request.get('native_request_capture') or {}
                        if not capture.get('path'): continue
                        messages = json.loads(Path(capture['path']).read_text()).get('messages',[])
                        phases = [i for i,m in enumerate(messages) if m.get('role') == 'user' and 'One bounded correction.' in str(m.get('content',''))]
                        if not phases: continue
                        original_ids = {c.get('id') for m in messages[:phases[-1]] for c in m.get('tool_calls',[])}
                        starts, failed_names = {}, set()
                        for prior in all_events:
                            if prior is event: break
                            prior_id = prior.get('callId')
                            if prior_id not in original_ids: continue
                            if prior.get('type') == 'tool-start': starts[prior_id] = prior
                            if prior.get('type') == 'tool-end':
                                tool = starts.get(prior_id,{}).get('name')
                                if prior.get('ok'): failed_names.discard(tool)
                                else: failed_names.add(tool)
                        if not set(allowed) <= failed_names:
                            raise ValueError('Bounded correction allowed tools lack prior failed native calls')
                        # A disallowed tool or a second execution of an allowed tool
                        # must be rejected before touching MCP.
                        called = {c.get('function',{}).get('name') for m in messages[phases[-1]+1:] for c in m.get('tool_calls',[])}
                        if name not in allowed or name in called: phase_proven = True
                        elif name in allowed:
                            # Parallel duplicate calls may be rejected in one SDK batch,
                            # before a subsequent request contains the first call result.
                            # Prove the other actual batch call reached MCP, rather than
                            # treating arbitrary generated-but-lost calls as executions.
                            batch_ids = set(request.get('response_tool_call_ids',[]))
                            starts_before = {}
                            for prior in all_events:
                                if prior is event: break
                                if prior.get('type') == 'tool-start': starts_before[prior.get('callId')] = prior
                            ledger = attempt.get('ledger_path')
                            rows = ([json.loads(line) for line in Path(ledger).read_text().splitlines() if line.strip()]
                                    if ledger and Path(ledger).is_file() else [])
                            canonical = next(d['name'] for d in definitions if any(name == prefix+d['name'] for prefix in ('opentrading_', 'mcp__opentrading__', 'mcp_opentrading_')))
                            for later in provider:
                                later_capture = later.get('native_request_capture') or {}
                                if not later_capture.get('path'): continue
                                later_messages = json.loads(Path(later_capture['path']).read_text()).get('messages',[])
                                batches = [m.get('tool_calls',[]) for m in later_messages
                                           if any(c.get('id')==call_id for c in m.get('tool_calls',[]))]
                                for batch in batches:
                                    for other in batch:
                                        other_id, function = other.get('id'), other.get('function',{})
                                        if other_id==call_id or other_id not in batch_ids or function.get('name')!=name: continue
                                        start = starts_before.get(other_id,{})
                                        try: other_args = json.loads(function.get('arguments','null'))
                                        except ValueError: continue
                                        if start.get('name')!=name or start.get('input')!=other_args: continue
                                        if any(row.get('tool')==canonical and row.get('arguments')==other_args and row.get('status') in ('ok','rejected') for row in rows):
                                            phase_proven = True

                    if not phase_proven:
                        raise ValueError('Bounded correction guard lacks native phase/repetition wire proof')
                else:
                    if reason not in ('Tool correction changed the original entity/currency scope; rejected without execution.',
                                      'Tool correction changed the original temporal/financial scope; rejected without execution.',
                                      'Tool correction exhausted or repeated rejected arguments; do not replay this request.'):
                        raise ValueError('Unrecognized policy guard rejection')
                    starts, failures = {}, []
                    for prior in all_events:
                        if prior is event: break
                        if prior.get('type') == 'tool-start': starts[prior.get('callId')] = prior
                        if prior.get('type') == 'tool-end' and starts.get(prior.get('callId'), {}).get('name') == name:
                            if prior.get('ok'): failures = []
                            else: failures.append(prior)
                    if not failures:
                        raise ValueError('Policy guard has no preceding failed same-tool intent')
                    prior_inputs = [starts[f.get('callId')].get('input') for f in failures]
                    def entities(value):
                        return {str(x).strip().upper() for x in (value if isinstance(value,list) else [value]) if isinstance(x,str)}
                    if 'temporal/financial scope' in reason:
                        original = prior_inputs[0]
                        props = schemas[name].get('properties', {})
                        def valid_scope_field(key, value):
                            if not __import__('re').fullmatch(r'year|quarter|month|date|startDate|endDate|fromDate|toDate|period|start|end|from|to|scope|consolidated',key,__import__('re').I):
                                return False
                            schema = props.get(key, {})
                            return key in props and ('enum' not in schema or value in schema['enum'])
                        changed = isinstance(original,dict) and isinstance(arguments,dict) and any(
                            valid_scope_field(key,value) and str(value).strip().upper()!=str(arguments.get(key,'[UNDEFINED]')).strip().upper()
                            for key,value in original.items())
                        if not changed:
                            raise ValueError('Temporal guard does not actually change original financial scope')
                    elif 'changed the original' in reason:
                        original = prior_inputs[0]
                        changed = isinstance(original, dict) and isinstance(arguments, dict) and any(
                            __import__('re').search('symbol|ticker|currency|entity|peers', key, __import__('re').I)
                            and not entities(value) <= entities(arguments.get(key)) for key,value in original.items())
                        if not changed:
                            raise ValueError('Scope guard does not actually change original entity/currency')
                    else:
                        repeated = any(json.dumps(value,sort_keys=True)==json.dumps(arguments,sort_keys=True) for value in prior_inputs)
                        denied = any(__import__('re').search(r'auth|permission|unauthorized|forbidden|no.data|not.found|unavailable', str(f.get('output','')), __import__('re').I) for f in failures)
                        if not repeated and len(failures)<2 and not denied:
                            raise ValueError('Correction guard is not repeated, exhausted or denied')
        consumed = False
        from v45_call_binding import context_results
        for context in context_results(provider):
            if context['id']!=call_id or context['tool']!=__import__('v45_call_binding').canonical(name):continue
            expected_args=__import__('v45_call_binding').arguments(raw)
            if context['arguments']!=expected_args:continue
            content=str(context['content'])
            if local['code']=='policy_guard_rejected':
                error_matches=local.get('reason')in content
            elif classification=='validator_compilation_failure':
                error_matches=any(word in content for word in('Invalid input','invalid_tool_input','invalid_argument','InvalidToolInputError','invalid escaped character','Invalid regular expression'))
            elif classification=='schema_valid_unsupported_captured_query':
                error_matches=any(word in content for word in('Invalid input','invalid_tool_input','invalid_argument','InvalidToolInputError','unsupported_snapshot_query','invalid_derivation','request not replayable'))
            else:
                # v4.6-update fix: the OT runtime emits rejection output in
                # Vietnamese for Vietnamese-market users; add those markers plus
                # the structured rejection code so a genuine local rejection is
                # recognized regardless of the message language.
                error_matches=any(word in content for word in('Invalid input','invalid_tool_input','invalid_argument','InvalidToolInputError','Invalid input for tool','Tham số không hợp lệ','Sửa tham số',str(local.get('code') or '')))
            if error_matches:
                if 'benchmark_evidence'in content:raise ValueError('Local rejection illegally carries financial evidence')
                consumed=True
        if not consumed:
            raise ValueError('Local rejection was not consumed as actual model-visible tool error')
        proof_records.append({'sdk_call_id':call_id,'tool':name,'arguments':__import__('v45_call_binding').arguments(raw),'code':local['code'],'reason':local.get('reason'),'classification':classification,'infrastructure':classification=='validator_compilation_failure','provider_request_index':event.get('provider_request_index'),'memory_session':event.get('memory_session'),'memory_turn':event.get('memory_turn'),**{key:local.get(key,event.get(key)) for key in ('origin_provider_request_index','origin_sdk_call_id','origin_memory_session','origin_memory_turn','origin_native_session_id','replay_of')}})
    return proof_records if return_records else sorted(sdk for sdk,count in seen.items()for _ in range(count))


def recompute_primary_fields(task, final_text, final_calls, status, timely):
    """Bind persisted endpoints to raw completion, current contract and receipts."""
    from public_response_contract import validate_public_response_contract, append_public_contract
    from mcp_snapshot_server import load_entries, build_tool_defs
    from run_benchmark import grounded_answer, extract_answer_json, grade_answer
    task = Path(task)
    names = [d['name'] for d in build_tool_defs(load_entries(task/'environment/payloads.json')[0])]
    snapshot_date = json.loads((task/'environment/payloads.json').read_text())['snapshot_date']
    instruction = ('Benchmark time context: answer relative to the frozen data snapshot as of '+snapshot_date+
                   '. Execution wall-clock does not advance the financial reporting period. Use response provenance.as_of for evidence.\n\n'+(task/'instruction.md').read_text())
    public = validate_public_response_contract(append_public_contract(instruction), final_text, names)
    answer = extract_answer_json(final_text)
    grounded = grounded_answer(answer, final_calls)
    with tempfile.TemporaryDirectory(prefix='benchmark-canary-') as tmp:
        answer_path = Path(tmp)/'answer.json'
        if answer is not None:
            answer_path.write_text(json.dumps(answer))
        grade = grade_answer(str(answer_path), str(task), tmp) if answer is not None else {'success': False}
    contract = bool(grade['success'] and public['valid'])
    return {'public_contract_valid': public['valid'], 'public_contract_errors': public['errors'],
            'public_contract_branch': public['branch'], 'contract_correctness': contract,
            'evidence_grounded': grounded, 'grounded_correctness': contract and grounded,
            'success': bool(contract and grounded and status == 'ok' and timely)}


def validate_live_run(out_dir, config, model):
    from metrics import load_trials
    from run_manifest import code_fingerprint, harness_inventory, task_fingerprint, digest_json, validate_trial_rows, protocol_fingerprint
    from runners.provider import aggregate_usage, valid_count
    path = Path(out_dir)
    manifest = json.loads((path/'manifest.json').read_text())
    plan = manifest['plan']
    settings = plan['settings']
    expected_tasks = {p.name for p in (ROOT/'tasks'/'smoke').iterdir() if p.is_dir()}
    if (plan.get('schema_version') != 3 or manifest.get('fingerprint') != digest_json(plan) or settings['model'] != model
            or settings['effort'] != 'none' or settings['runs'] < 2
            or set(settings['arms']) != {'opencode','dsh','opentrading'}
            or set(plan['tasks']) != expected_tasks or plan['config'] != config
            or plan['code'] != code_fingerprint() or plan['harnesses'] != harness_inventory(config)
            or plan.get('protocol') != protocol_fingerprint(config)
            or settings['split'] != 'smoke' or settings.get('include_quarantined', False)):
        raise ValueError('Certificate requires complete repeated smoke (all 3 tasks x 3 arms, >=2 runs) for exact current state')
    for tid in expected_tasks:
        if plan['tasks'][tid] != task_fingerprint(ROOT/'tasks'/'smoke'/tid):
            raise ValueError('Live smoke task fingerprint changed')
    rows = load_trials(path)
    if not validate_trial_rows(rows, manifest):
        raise ValueError('Live smoke run is incomplete')
    primary_arms = set()
    numeric_retrieval_arms = set()
    rejection_count = 0
    for row in rows:
        if (row.get('manifest_sha256') != manifest['fingerprint'] or row['status'] != 'ok'
                or not row.get('timely') or not isinstance(row.get('tokens'), dict)
                or row['tokens'].get('complete') is not True or row.get('requests', 0) < 1):
            raise ValueError('Live smoke contains execution, budget, usage or tool-path failures')
        attempts = row.get('attempts')
        if not isinstance(attempts, list) or not attempts:
            raise ValueError('Missing actual runtime attempts')
        task = ROOT/'tasks'/'smoke'/row['task']
        from mcp_snapshot_server import load_entries, build_tool_defs
        definitions = build_tool_defs(load_entries(task/'environment'/'payloads.json')[0])
        complete_sets = [{prefix+d['name'] for d in definitions}
                         for prefix in ('opentrading_', 'mcp__opentrading__', 'mcp_opentrading_')]
        calls, final_calls, provider_rows = [], [], []
        for attempt in attempts:
            final_calls = verify_mcp_attempt(task, attempt, allow_empty=True)
            calls.extend(final_calls)
            inv_path = attempt.get('inventory_path')
            provider_path = attempt.get('provider_ledger')
            if not inv_path or not provider_path:
                raise ValueError('Missing actual runtime inventory or provider ledger')
            inventory = json.loads(Path(inv_path).read_text())
            from experiment_conditions import condition, prompt_directory
            expected_condition = condition(row['arm'])
            if (inventory.get('condition') != row['arm'] or inventory.get('native_arm') != expected_condition['native_arm']
                    or inventory.get('prompt_variant') != expected_condition['prompt_variant']
                    or inventory.get('finance_policy', False) != expected_condition['finance_policy']):
                raise ValueError('Runtime condition/variant binding failed')
            expected_as_of = json.loads((task/'environment/payloads.json').read_text())['snapshot_date']
            clock = inventory.get('clock_policy') or {}
            if clock.get('answer_as_of') != expected_as_of or clock.get('native_now_pinned') is not (row['arm'] == 'opentrading'):
                raise ValueError('Runtime snapshot clock policy binding failed')
            if row['arm'] == 'opentrading':
                from run_manifest import hash_file
                directory = prompt_directory('finance')
                if (inventory.get('prompt_directory') != str(directory) or inventory.get('prompt_files') !=
                        {p.name: hash_file(p) for p in sorted(directory.glob('*.md'))}):
                    raise ValueError('Runtime prompt files binding failed')
            provider = [json.loads(line) for line in Path(provider_path).read_text().splitlines() if line.strip()]
            provider_rows.extend(provider)
            if (inventory.get('arm') != row['arm'] or inventory.get('model') != model.removeprefix('nvidia/')
                    or inventory.get('skills') != [] or inventory.get('external_plugins') != []
                    or inventory.get('effort') != 'none' or inventory.get('provider') != 'nvidia'
                    or not inventory.get('usage_complete') or not provider
                    or inventory.get('observed_tool_sets') != [r.get('tool_names', []) for r in provider]):
                raise ValueError('Runtime parity inventory failed for '+row['arm'])
            for request in provider:
                verify_request_capture(request)
                from wire_contracts import verify_c2_wire_contracts
                verify_c2_wire_contracts(json.loads(Path(request['native_request_capture']['path']).read_text()),definitions)
                names = request.get('tool_names')
                if (request.get('status') != 200 or not isinstance(request.get('usage'), dict)
                        or not all(valid_count(request['usage'].get(key)) for key in ('prompt_tokens', 'completion_tokens'))
                        or request.get('request_model') != model.removeprefix('nvidia/')
                        or request.get('response_models') != [model.removeprefix('nvidia/')]
                        or request.get('effort') not in (None, 'none', 'off')
                        or not isinstance(names, list) or len(names) != len(set(names)) or set(names) not in complete_sets
                        or type(request.get('tool_call_count')) is not int or request['tool_call_count'] < 0):
                    raise ValueError('Provider wire inventory/usage/model/tool parity failed')
            local_rejections = verify_local_rejections(attempt, provider, definitions, expected_condition['finance_policy'])
            if sum(r['tool_call_count'] for r in provider) != len(final_calls) + len(local_rejections):
                raise ValueError('Provider tool calls lack matching authoritative MCP ledger records')
        observed_usage = aggregate_usage(provider_rows)
        if (not observed_usage or not observed_usage['complete']
                or row.get('requests') != len(provider_rows)
                or any(not valid_count(row['tokens'].get(key))
                       or row['tokens'][key] != observed_usage[key] for key in ('input', 'output'))):
            raise ValueError('Trial usage totals disagree with authoritative provider ledger')
        if row.get('mcp_calls') != len(calls) or row.get('mcp_successful_calls') != sum(c['status'] == 'ok' for c in calls):
            raise ValueError('Trial MCP counts disagree with authoritative ledger')
        rejection_count += sum(c['status'] == 'rejected' for c in calls)
        recomputed = recompute_primary_fields(task, attempts[-1].get('final_text'), final_calls, row['status'], row['timely'])
        if any(type(row.get(key)) is not type(value) or row.get(key) != value for key, value in recomputed.items()):
            raise ValueError('Persisted primary/public contract fields disagree with raw final response and authoritative receipts')
        if recomputed['success']:
            primary_arms.add(row['arm'])
            # Sealed rule: at least one primary-correct quote/aggregation answer
            # with an actual successful vn_quote_history execution PER arm.
            if (row['task'] in {'smoke-quote-01','smoke-agg-01'}
                    and any(call.get('status') == 'ok' and call.get('tool') == 'vn_quote_history' for call in final_calls)):
                numeric_retrieval_arms.add(row['arm'])
    if primary_arms != {'opencode','dsh','opentrading'}:
        raise ValueError('Each arm needs at least one complete primary-correct smoke canary')
    if numeric_retrieval_arms != {'opencode','dsh','opentrading'}:
        raise ValueError('Each arm needs primary-correct numeric financial retrieval canary, not only refusal')
    return {'numeric_canary_arms':sorted(numeric_retrieval_arms), 'manifest_sha256': manifest['fingerprint'], 'out_dir': str(path.resolve()), 'n_trials': len(rows),
            'stability_runs': settings['runs'], 'protocol': 'operational_parity_v42',
            'snapshot_rejections': rejection_count, 'model_quality_failures': sum(not r.get('success') for r in rows)}


def main():
    from run_manifest import freeze_state, digest_json, write_exclusive
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', default=str(HERE/'bench_config.json'))
    ap.add_argument('--model')
    ap.add_argument('--provider-probe', action='store_true', help='explicit NVIDIA catalog request')
    ap.add_argument('--run-tests', action='store_true')
    ap.add_argument('--live-run', help='completed current three-arm smoke directory')
    ap.add_argument('--certificate', help='write a freeze certificate; implies --run-tests and requires --live-run')
    args = ap.parse_args()
    config = json.loads(Path(args.config).read_text())
    args.model = args.model or config['model']
    checks = [('harness versions (isolated HOME)', c_harnesses), ('MCP replay+ledger', c_snapshot),
              ('workspace isolation', c_isolation), ('grader roundtrip', c_grader)]
    if args.provider_probe:
        checks.append(('explicit provider catalog probe', c_provider))
    if args.run_tests or args.certificate:
        checks.append(('full regression suite', c_tests))
    results = []
    for name, fn in checks:
        try:
            ok, detail = fn(args)
        except Exception as exc:
            ok, detail = False, type(exc).__name__+': '+str(exc)
        results.append(ok)
        print('[%s] %s: %s' % ('PASS' if ok else 'FAIL', name, detail), flush=True)
    live = None
    if args.live_run:
        try:
            live = validate_live_run(args.live_run, config, args.model)
            print('[PASS] live parity artifact verified')
        except Exception as exc:
            results.append(False)
            print('[FAIL] live parity:', str(exc))
    if args.certificate:
        if not all(results) or live is None or args.model != config.get('model'):
            raise SystemExit('Certificate refused: need passing regressions, exact-model three-arm live smoke, and current config')
        state = freeze_state(config)
        write_exclusive(args.certificate, {'schema_version': 3, 'state_sha256': digest_json(state),
                        'model': args.model, 'offline_passed': True, 'live_parity_passed': True, 'live_run': live,
                        'scope': config.get('evaluation_scope', 'snapshot_grounded_financial_qa'),
                        'source_truth_limit': 'Numerical truth is relative to frozen tool payload; independent filings accuracy is not certified.'})
        print('Certificate:', str(Path(args.certificate).resolve()))
    print('Offline checks completed. Main readiness additionally requires a current freeze certificate; financial-source truth is outside these checks.')
    raise SystemExit(0 if all(results) else 1)


if __name__ == '__main__':
    if sys.argv[1:] == ['--snapshot-worker']:
        ok, detail = snapshot_worker()
        print(detail, flush=True)
        raise SystemExit(0 if ok else 1)
    main()
