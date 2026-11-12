#!/usr/bin/env python3
"""Offline MCP replay with strict query matching and an append-only call ledger.

Schemas are frozen from local MCP source signatures (snapshot_tool_schemas.json).
Only recorded requests, documented defaults, and explicit reconstructed pilot
requests are available. Unknown entities/parameters never fall back to an answer.
"""
import copy
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

import jsonschema
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

FROZEN_V3_SCHEMAS = json.loads(Path(__file__).with_name('snapshot_tool_schemas.json').read_text())
CONTRACT_V4 = json.loads(Path(__file__).with_name('tool_contracts_v4.json').read_text())
# Common C1 authoritative input contract; exact matching/default equivalence stays unchanged.
SCHEMAS = {item['name']: item['inputSchema'] for item in CONTRACT_V4['tools']}
BATCH_KEYS = {'symbols', 'tickers'}


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


def select_entry(entries, tool_name, args):
    cands = [(k, v) for k, v in entries if v.get('tool') == tool_name]
    if not cands or tool_name not in SCHEMAS:
        raise KeyError("Tool '%s' is not in this snapshot" % tool_name)
    if not isinstance(args, dict):
        raise ValueError('arguments must be a JSON object')
    try:
        json.dumps(args, allow_nan=False)
        jsonschema.validate(args, SCHEMAS[tool_name])
    except (ValueError, jsonschema.ValidationError) as exc:
        raise ValueError('invalid request arguments: %s' % str(exc).splitlines()[0]) from exc
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
        # Preserve source descriptions and actual MCP output/annotation metadata.
        # Replay constraints describe this offline environment, not production API behavior.
        definition['description'] += ("\n\nFrozen replay restriction: only snapshot_requests below are replayable. "
            "Supply all recorded non-default parameters; omitted parameters retain the real schema defaults. "
            "Read source/as_of from provenance and cite benchmark_evidence. snapshot_requests=" +
            json.dumps([v['params'] for _, v in entries if v['tool'] == name], ensure_ascii=False))
        definitions.append(definition)
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
        jsonschema.validate(entry.get('params') or {}, SCHEMAS[entry['tool']])
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
                'invalid_request' if str(exc).startswith(('invalid request', 'arguments')) else 'not_recorded')
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
                         'guidance': 'Correct the request using the schema and snapshot_requests. A rejected request does not establish missing financial data.'},
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


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('BENCH_PAYLOADS')
    if not path:
        raise SystemExit('mcp_snapshot_server: missing payload path')
    entries, payloads = load_entries(path)
    payload_sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
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
        env = replay_call(entries, name, arguments or {}, payload_sha, os.environ.get('BENCH_MCP_LEDGER'))
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
