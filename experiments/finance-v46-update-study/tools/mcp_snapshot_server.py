#!/usr/bin/env python3
"""Offline MCP replay with strict query matching and an append-only call ledger.

Schemas are frozen from local MCP source signatures (snapshot_tool_schemas.json).
Only recorded requests, documented defaults, and explicit reconstructed pilot
requests are available. Unknown entities/parameters never fall back to an answer.
"""
import copy
from decimal import DecimalException
import datetime as dt
import hashlib
import json
import math
import os
import re

# ECMA-262 unicode-mode SyntaxCharacters: escaping these is valid in BOTH
# Python re and JavaScript RegExp with the 'u' flag. Anything else must stay
# literal (Python re.escape() forms like '\-', '\ ', '\&' are illegal in JS
# unicode mode and made Ajv8 schema compilation fail on 6 catalog schemas).
JS_SYNTAX_CHARACTERS = set('/^$\\.+*?()[]{}|')


def _js_unicode_safe_escape(char):
    """Literal-escape a single character for regexes valid in Python AND JS 'u' mode."""
    if char in JS_SYNTAX_CHARACTERS:
        return '\\' + char
    if ord(char) < 0x20 or ord(char) == 0x7f:
        return '\\x%02x' % ord(char)
    return char
from pathlib import Path
import sys
import time
import uuid
from analytics_compute import NAME as COMPUTE_NAME, DEFINITION as COMPUTE_DEFINITION, compute, numeric_candidates
from analytics_calculate import NAME as CALCULATE_NAME, DEFINITION as CALCULATE_DEFINITION, calculate

# User decision 2026-11-11: the benchmark exposes data tools only. Calculation is each harness's own
# capability (OpenTrading native calculate/compute; other arms compute themselves), so the shared
# analytics calculators are not advertised and calls to them are unknown tools.
SHARED_CALCULATORS = False
from functools import lru_cache

import jsonschema
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

FROZEN_V3_SCHEMAS = json.loads(Path(__file__).with_name('snapshot_tool_schemas.json').read_text())
CONTRACT_V4 = json.loads(Path(__file__).with_name('tool_contracts_v4.json').read_text())
# Common C1 authoritative input contract; exact matching/default equivalence stays unchanged.
SCHEMAS = {item['name']: item['inputSchema'] for item in CONTRACT_V4['tools']}
BATCH_KEYS = {'symbols', 'tickers'}


@lru_cache(maxsize=512)
def _compiled_validator(serialized_schema):
    schema = json.loads(serialized_schema)
    jsonschema.Draft7Validator.check_schema(schema)
    return jsonschema.Draft7Validator(schema)


def validate_arguments(args, schema):
    _compiled_validator(json.dumps(schema,sort_keys=True,separators=(',',':'))).validate(args)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _norm(value):
    if isinstance(value, list):
        return sorted(_norm(v) for v in value)
    if isinstance(value, str):
        return value.strip().upper()
    return value


def _entry_matches(item, args):
    params = item.get('params') or {}
    schema = SCHEMAS[item['tool']]
    for key, value in params.items():
        if key not in args:
            prop = schema['properties'].get(key, {})
            if 'default' not in prop or _norm(value) != _norm(prop['default']):
                return False
    for key, val in args.items():
        if key in params:
            expected = params[key]
            if _norm(val) != _norm(expected):
                return False
        else:
            prop = schema['properties'].get(key, {})
            if 'default' not in prop or _norm(val) != _norm(prop['default']):
                return False
    return True


def equivalent_schema(value):
    """JSON Schema for the unchanged matcher's case/space normalization.

    Support order-independent unique-valued arrays using exact length and
    contains assertions, never by broadening or changing the matcher.
    Patterns use ECMA-262 unicode-mode-compatible literal escaping (v4.6):
    Python re.escape() emits \\-, '\\ ', \\&, \\~, \\# which are illegal
    identity escapes inside JavaScript RegExp with the 'u' flag (Ajv8
    unicodeRegExp:true). Escaping only the JS SyntaxCharacters keeps
    Python-re semantics identical (all backslash forms below are literal in
    Python too) while making every pattern compilable in unicode mode.
    """
    if isinstance(value, str):
        pattern = ''.join('[' + char.lower() + char.upper() + ']' if char.isalpha() and len(char.lower())==1 and len(char.upper())==1
                          else _js_unicode_safe_escape(char) for char in value.strip())
        return {'type': 'string', 'pattern': r'^\s*' + pattern + r'\s*$'}
    if isinstance(value, list):
        normalized = [_norm(v) for v in value]
        if len({digest(v) for v in normalized}) != len(value):
            raise ValueError('Duplicate-valued finite array variant requires reviewed multiset schema')
        # Draft7 contains+exact length enforce each normalized item exactly once.
        # uniqueItems alone would miss differently cased duplicates.
        items = [equivalent_schema(v) for v in value]
        return ({'type':'array','minItems':len(value),'maxItems':len(value),
                 'items':{'anyOf':items},'allOf':[{'contains':item} for item in items]}
                if items else {'type':'array','maxItems':0})
    return {'const': value}


def finite_input_schema(entries, name):
    """C2 is the public finite relation, intersected with unchanged C1 domains.

    anyOf (not oneOf) permits overlapping default-equivalent recordings. Required
    selectors remain required. No request is chosen and no actual args mutate.
    """
    schema = copy.deepcopy(SCHEMAS[name])
    branches = []
    variants = []
    for _, entry in entries:
        if entry['tool'] != name: continue
        params = entry.get('params') or {}
        variants.append(copy.deepcopy(params))
        properties, required = {}, []
        for key, prop in schema.get('properties', {}).items():
            if key in params:
                properties[key] = equivalent_schema(params[key])
                if 'default' not in prop or _norm(params[key]) != _norm(prop['default']): required.append(key)
            elif 'default' in prop:
                properties[key] = equivalent_schema(prop['default'])
        branch = {'type':'object', 'properties':properties, 'required':required, 'additionalProperties':False}
        if branch not in branches: branches.append(branch)
    schema['anyOf'] = branches
    schema['x-opentrading-schema-profile'] = 'finite-replay-c2'
    schema['x-finite-request-variants'] = variants
    schema['x-repair-fields'] = []
    return schema


def finite_error_paths(entries, name, args):
    """Public mismatch locations; contains no answer data or selected fallback."""
    if not isinstance(args, dict): return ['/']
    variants = []
    for _, entry in entries:
        if entry['tool'] != name: continue
        params = entry.get('params') or {}
        paths = set()
        for key in set(params) | set(args):
            default = SCHEMAS[name].get('properties', {}).get(key, {}).get('default', object())
            if _norm(args.get(key, default)) != _norm(params.get(key, default)): paths.add('/'+key)
        variants.append(paths)
    if not variants:return ['/']
    nearest = min(len(paths) for paths in variants)
    # Diagnostic locations only: no query is substituted or selected for execution.
    return sorted(set().union(*(paths for paths in variants if len(paths)==nearest)))



def select_entry(entries, tool_name, args):
    cands = [(k, v) for k, v in entries if v.get('tool') == tool_name]
    if not cands or tool_name not in SCHEMAS:
        raise KeyError("Tool '%s' is not in this snapshot" % tool_name)
    if not isinstance(args, dict):
        raise ValueError('arguments must be a JSON object')
    try:
        json.dumps(args, allow_nan=False)
        validate_arguments(args, SCHEMAS[tool_name])
    except (ValueError, jsonschema.ValidationError) as exc:
        raise ValueError('invalid request arguments: %s' % str(exc).splitlines()[0]) from exc
    # Authoritative C2 finite-support validation, independent of answer payloads.
    try:
        validate_arguments(args, finite_input_schema(entries, tool_name))
    except jsonschema.ValidationError as exc:
        raise ValueError('unsupported finite-snapshot query; inspect allowed_public_variants') from exc
    matches = [(k, v) for k, v in cands if _entry_matches(v, args)]
    if not matches:
        raise ValueError('request is not recorded in this snapshot; inspect the tool snapshot_requests')
    # An omitted optional argument must not silently choose among different requests.
    distinct = {digest(v['params']) for _, v in matches}
    if len(distinct) > 1:
        raise ValueError('ambiguous request: supply parameters that distinguish snapshot_requests')
    return matches[0]


def select_envelope(entries, tool_name, args):
    _, item = select_entry(entries, tool_name, args)
    envelope = copy.deepcopy(item['envelope'])
    return envelope


def build_tool_defs(entries):
    catalog = json.loads(Path(__file__).with_name('tool_contracts_v4.json').read_text())
    contracts = {item['name']: item for item in catalog['tools']}
    names = list(dict.fromkeys(item['tool'] for _, item in entries))
    definitions = []
    for name in names:
        definition = copy.deepcopy(contracts[name])
        definition['inputSchema'] = finite_input_schema(entries, name)
        # Common finite support takes priority over the preserved production metadata.
        # No argument transformation occurs here or in select_entry/replay_call.
        variants = json.dumps([v['params'] for _, v in entries if v['tool'] == name], ensure_ascii=False)
        definition['description'] = (
            "FINITE SNAPSHOT SUPPORT: use a recorded public variant below and only default-equivalent optional arguments "
            "allowed by inputSchema. Production optional windows/projections are NOT generally supported here. "
            "snapshot_requests=" + variants + "\n"
            "If unsupported_snapshot_query: inspect argument_paths and allowed_public_variants; choose a supported "
            "same-intent request only if entity, period, metric and scope remain unchanged. "
            "retryable_with_corrected_arguments permits a bounded correction; rejection does not mean financial data is absent. "
            "Read provenance and copy benchmark_evidence only from actual successful responses.\n\n"
            "PRODUCTION API METADATA (capabilities below do not expand this finite snapshot):\n" + definition['description'])
        definitions.append(definition)
    if SHARED_CALCULATORS:
        definitions.append(copy.deepcopy(COMPUTE_DEFINITION))
        definitions.append(copy.deepcopy(CALCULATE_DEFINITION))
    return definitions


def load_entries(path):
    payloads = json.loads(Path(path).read_text(encoding='utf-8'))
    contracts_path = Path(path).with_name('request_contracts.json')
    contracts = json.loads(contracts_path.read_text()) if contracts_path.exists() else {}
    entries = []
    for key, value in payloads['tools'].items():
        if isinstance(value, dict) and 'tool' in value and 'envelope' in value:
            item = copy.deepcopy(value)
            if key in contracts.get('parameter_corrections', {}):
                item['params'] = contracts['parameter_corrections'][key]['params']
            entries.append((key, item))
            continue
        requests = contracts.get('requests', {}).get(key)
        if not requests:
            raise ValueError('legacy snapshot requires explicit request_contracts.json: %s' % key)
        for idx, request in enumerate(requests):
            env = copy.deepcopy(value)
            if 'select_row' in request:
                field, symbol = request['select_row']
                row = next(row for row in env['data'][field] if row['symbol'] == symbol)
                env['data'] = row if field == 'banks' else {**row, 'interval': env['data'].get('interval', '1D')}
            entries.append(('%s:%d' % (key, idx), {'tool': key, 'params': request['params'], 'envelope': env}))
    for _, entry in entries:
        validate_arguments(entry.get('params') or {}, SCHEMAS[entry['tool']])
    return entries, payloads


def replay_call(entries, tool, arguments, payload_sha256, ledger_path=None):
    """One authoritative call record, including rejected requests. No credentials."""
    start = time.monotonic()
    stamp = lambda: dt.datetime.now(dt.timezone.utc).isoformat()
    def safe(value):
        if isinstance(value, dict):
            return {k: ('[REDACTED]' if any(part in k.lower() for part in ('key', 'secret', 'token', 'password')) else safe(v)) for k,v in value.items()}
        if isinstance(value, list): return [safe(v) for v in value]
        if isinstance(value, float) and not math.isfinite(value): return '[NONFINITE]'
        return value
    recorded_args = safe(arguments)
    record = {'schema_version': 2, 'call_id': str(uuid.uuid4()), 'tool': tool,
              'arguments': recorded_args, 'arguments_sha256': digest(recorded_args),
              'payload_sha256': payload_sha256, 'started_at': stamp()}
    try:
        key, _ = select_entry(entries, tool, arguments)
        env = select_envelope(entries, tool, arguments)
        provenance = env.get('provenance') or {}
        record.update(status='ok', matched_entry_id=key,
                      source=provenance.get('source'), as_of=provenance.get('as_of'),
                      availability=env.get('availability'), response_sha256=digest(env))
        env['benchmark_evidence'] = {k: record[k] for k in
            ('call_id', 'tool', 'matched_entry_id', 'payload_sha256', 'response_sha256', 'source', 'as_of')}
    except (KeyError, ValueError) as exc:
        record.update(status='rejected', error=type(exc).__name__ + ': request not replayable; inspect snapshot_requests', matched_entry_id=None,
                      source=None, as_of=None, response_sha256=None)
        code = ('unknown_tool' if isinstance(exc, KeyError) else
                'invalid_request' if str(exc).startswith(('invalid request', 'arguments')) else 'unsupported_snapshot_query')
        record['error_code'] = code
        if code == 'invalid_request' and tool in FROZEN_V3_SCHEMAS:
            try:
                jsonschema.validate(arguments, FROZEN_V3_SCHEMAS[tool])
            except (jsonschema.ValidationError, ValueError, TypeError):
                record['schema_failure_class'] = 'frozen_v3_type_or_shape'
            else:
                record['schema_failure_class'] = 'v4_domain_constraint'
        env = {'error': {'code': code, 'message': str(exc),
                         'retryable_with_corrected_arguments': code != 'unknown_tool',
                         'snapshot_requests': [v['params'] for _, v in entries if v['tool'] == tool],
                         'allowed_public_variants': [v['params'] for _, v in entries if v['tool'] == tool],
                         'argument_paths': finite_error_paths(entries, tool, arguments) if tool in SCHEMAS else ['/'],
                         'failure_class': ('type_or_domain' if code == 'invalid_request' else 'finite_snapshot_support'),
                         'guidance': 'Inspect argument_paths, compare allowed_public_variants with your arguments, and make at most one supported same-intent correction when retryable_with_corrected_arguments is true. Preserve entity, period, metric and scope; do not repeat rejected arguments. A rejected snapshot query is not evidence that financial data is missing.'},
               'request_rejected': True}
    record.update(ended_at=stamp(), duration_ms=round((time.monotonic()-start)*1000, 3))
    if ledger_path:
        # One O_APPEND write per record; fail the tool call if its ledger cannot be persisted.
        line = (json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n').encode()
        fd = os.open(ledger_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            written = os.write(fd, line)
            if written != len(line):
                raise OSError('partial ledger append; trial must be treated as incomplete')
            os.fsync(fd)
        finally:
            os.close(fd)
    return env


def replay_compute(arguments, sources, payload_sha256, ledger_path=None):
    """Derived ledger namespace; never masquerade as recorded upstream receipt."""
    start=time.monotonic();stamp=lambda:dt.datetime.now(dt.timezone.utc).isoformat()
    record={'schema_version':2,'call_id':str(uuid.uuid4()),'tool':COMPUTE_NAME,
            'arguments':arguments,'arguments_sha256':digest(arguments),'payload_sha256':payload_sha256,
            'started_at':stamp(),'matched_entry_id':None,'source':None,'as_of':None,'response_sha256':None,
            'record_kind':'deterministic_derivation'}
    try:
        env=compute(arguments,sources)
        record.update(status='ok',response_sha256=digest(env),derivation=copy.deepcopy(env['derived_result']),
                      source_evidence=copy.deepcopy(env['source_evidence']))
    except (ValueError,KeyError,IndexError,TypeError,OverflowError,DecimalException,jsonschema.ValidationError) as exc:
        record.update(status='rejected',error_code='invalid_derivation',error=str(exc))
        env={'request_rejected':True,'error':{'code':'invalid_derivation','message':str(exc),
             'retryable_with_corrected_arguments':True,'numeric_candidates':numeric_candidates(arguments,sources),'repair_fields':['operands[].path'],'guidance':'Keep original call_id/operation/entity/period/metric; correct selector only using visible retrieved data. Use only numeric leaves from successful source calls in this session, exact explicit source units and supported operation. JSON pointers escape ~ as ~0 and / inside a key as ~1.'}}
    record.update(ended_at=stamp(),duration_ms=round((time.monotonic()-start)*1000,3))
    if ledger_path:
        line=(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n').encode()
        fd=os.open(ledger_path,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
        try:
            if os.write(fd,line)!=len(line):raise OSError('partial derived ledger append')
            os.fsync(fd)
        finally:os.close(fd)
    return env


def replay_calculate(arguments,sources,derived,payload_sha256,ledger_path=None):
    start=time.monotonic();stamp=lambda:dt.datetime.now(dt.timezone.utc).isoformat()
    record={'schema_version':2,'call_id':str(uuid.uuid4()),'tool':CALCULATE_NAME,'arguments':arguments,'arguments_sha256':digest(arguments),'payload_sha256':payload_sha256,'started_at':stamp(),'matched_entry_id':None,'source':None,'as_of':None,'response_sha256':None,'record_kind':'deterministic_derivation'}
    try:
        env=calculate(arguments,sources,derived)
        env['derived_ref']='calc:'+record['call_id']
        record.update(status='ok',response_sha256=digest(env),derivation=copy.deepcopy(env['derived_result']),source_evidence=copy.deepcopy(env['source_evidence']),derived_ref=env['derived_ref'])
        derived[env['derived_ref']]=copy.deepcopy(env)
    except (ValueError,KeyError,IndexError,TypeError,OverflowError,DecimalException,jsonschema.ValidationError) as exc:
        record.update(status='rejected',error_code='invalid_derivation',error=str(exc))
        env={'request_rejected':True,'error':{'code':'invalid_derivation','message':str(exc),'retryable_with_corrected_arguments':True,'repair_fields':['variables[].path'],'guidance':'Preserve original source call_id or derived_id, entity/period/metric, alignment and formula intent; correct only actual numeric leaf selectors. Unit mismatch needs an explicitly compatible dimension.'}}
    record.update(ended_at=stamp(),duration_ms=round((time.monotonic()-start)*1000,3))
    if ledger_path:
        line=(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n').encode();fd=os.open(ledger_path,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
        try:
            if os.write(fd,line)!=len(line):raise OSError('partial calculation ledger append')
            os.fsync(fd)
        finally:os.close(fd)
    return env


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('BENCH_PAYLOADS')
    if not path:
        raise SystemExit('mcp_snapshot_server: missing payload path')
    entries, payloads = load_entries(path)
    payload_sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    session_sources = {}
    session_derived = {}
    server = Server('opentrading-snapshot', instructions=
                    'Offline frozen MCP snapshot %s. Cite tool, provenance.source, provenance.as_of, '
                    'benchmark_evidence.call_id and payload_sha256 in answer evidence.' % payloads.get('snapshot_date'))

    @server.list_tools()
    async def _list_tools():
        return [types.Tool(**item) for item in build_tool_defs(entries)]

    # Validate inside replay_call so schema-invalid calls are still represented
    # in the authoritative ledger instead of disappearing in the MCP SDK.
    @server.call_tool(validate_input=False)
    async def _call_tool(name, arguments):
        if SHARED_CALCULATORS and name == CALCULATE_NAME:
            env = replay_calculate(arguments or {}, session_sources, session_derived, payload_sha, os.environ.get('BENCH_MCP_LEDGER'))
        elif SHARED_CALCULATORS and name == COMPUTE_NAME:
            env = replay_compute(arguments or {}, session_sources, payload_sha, os.environ.get('BENCH_MCP_LEDGER'))
        else:
            env = replay_call(entries, name, arguments or {}, payload_sha, os.environ.get('BENCH_MCP_LEDGER'))
            if env.get('benchmark_evidence'):
                session_sources[env['benchmark_evidence']['call_id']] = {**copy.deepcopy(env),'_benchmark_request':{'tool':name,'arguments':copy.deepcopy(arguments or {})}}
        return types.CallToolResult(
            content=[types.TextContent(type='text', text=json.dumps(env, ensure_ascii=False, allow_nan=False))],
            structuredContent=env,
            isError=env.get('request_rejected') is True)

    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    import anyio
    anyio.run(_run)


if __name__ == '__main__':
    main()
