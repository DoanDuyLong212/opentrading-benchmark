# -*- coding: utf-8 -*-
"""Test cho tools/mcp_snapshot_server.py — replay envelope MCP từ payloads.json.

Chạy: python3 -m pytest tools/tests/test_snapshot_server.py -q
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # benchmark/
sys.path.insert(0, os.path.join(ROOT, "tools"))

from mcp_snapshot_server import build_tool_defs, select_envelope  # noqa: E402

REPO_TASK = os.path.join(ROOT, "tasks", "main", "fin-l1-quote-vn-101", "environment", "payloads.json")


# ---------------------------------------------------------------- fixtures
def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _entries(payloads):
    return [(k, v) for k, v in payloads["tools"].items()]


@pytest.fixture
def two_same_tool():
    """2 envelope CÙNG tool name (vn_quote_history) khác symbol — buộc match theo params."""
    return [
        ("vnq:EIB", {"tool": "vn_quote_history", "params": {"symbol": "EIB", "days": 5},
                     "envelope": {"data": {"symbol": "EIB", "last": 16.1}, "provenance": {"as_of": "A"}}}),
        ("vnq:ACB", {"tool": "vn_quote_history", "params": {"symbol": "ACB", "days": 5},
                     "envelope": {"data": {"symbol": "ACB", "last": 24.5}, "provenance": {"as_of": "B"}}}),
        ("vnq10:ANV", {"tool": "vn_quote_history", "params": {"symbol": "ANV", "days": 10},
                       "envelope": {"data": {"symbol": "ANV", "last": 17.8}, "provenance": {"as_of": "C"}}}),
    ]


# ---------------------------------------------------------------- unit: matcher
def test_select_exact_param_match(two_same_tool):
    env = select_envelope(two_same_tool, "vn_quote_history", {"symbol": "ACB", "days": 5})
    assert env["data"]["symbol"] == "ACB"


def test_select_scores_more_matching_params(two_same_tool):
    """days=10 khớp 2/2 params của ANV thay vì 1/2 của EIB/ACB."""
    env = select_envelope(two_same_tool, "vn_quote_history", {"symbol": "ANV", "days": 10})
    assert env["data"]["symbol"] == "ANV"


def test_select_missing_identity_rejected(two_same_tool):
    """Không có args nào khớp → hòa 0-0 → giữ envelope đầu theo thứ tự key."""
    with pytest.raises(ValueError):
        select_envelope(two_same_tool, "vn_quote_history", {})


def test_select_unknown_tool_raises(two_same_tool):
    with pytest.raises(KeyError):
        select_envelope(two_same_tool, "web_search", {})


def test_select_list_param_match():
    """Param dạng list (symbols batch) khớp theo so sánh list."""
    entries = [("batch:banks1", {"tool": "vn_equity_quote_batch",
                                 "params": {"symbols": ["ACB", "STB", "VPB", "HDB", "TPB"]},
                                 "envelope": {"data": {"quotes": []}}}),
               ("batch:tech1", {"tool": "vn_equity_quote_batch",
                                "params": {"symbols": ["CMG", "ELC", "VGI", "CTR", "FOX"]},
                                "envelope": {"data": {"quotes": [{"symbol": "CMG", "last": 1}]}}})]
    env = select_envelope(entries, "vn_equity_quote_batch", {"symbols": ["CMG", "ELC", "VGI", "CTR", "FOX"]})
    assert env["data"]["quotes"] == [{"symbol": "CMG", "last": 1}]


# ---------------------------------------------------------------- unit: tools/list
def test_legacy_requires_explicit_request_contract(tmp_path):
    from mcp_snapshot_server import load_entries
    payload = tmp_path / "payloads.json"
    payload.write_text(json.dumps({"tools": {"vs_indicator_data": {"data": {"rows": []}}}}))
    with pytest.raises(ValueError, match="request_contracts"):
        load_entries(payload)


def test_build_tool_defs_union_and_schema():
    payloads = _load(REPO_TASK)
    entries = _entries(payloads)
    defs = build_tool_defs(entries)
    names = [d["name"] for d in defs]
    # User 2026-11-11: no shared calculators; calculation is each harness's own capability.
    assert names == ["vn_quote_history"]
    from mcp_snapshot_server import SHARED_CALCULATORS, replay_call
    assert SHARED_CALCULATORS is False
    rejected = replay_call(entries, "analytics_calculate", {}, "p" * 64, None)
    assert rejected["request_rejected"] is True and rejected["error"]["code"] == "unknown_tool"
    schema = defs[0]["inputSchema"]
    assert schema["type"] == "object"
    assert "symbol" in schema["properties"]
    assert schema["required"] == ["symbol"]
    assert schema["additionalProperties"] is False


def test_build_tool_defs_mark_readonly_hint():
    """OpenTrading chỉ auto-allow MCP tool khi annotations.readOnlyHint=true —
    snapshot replay là read-only nên BẮT BUỘC khai báo (headless mode)."""
    payloads = _load(REPO_TASK)
    defs = build_tool_defs(_entries(payloads))
    ann = defs[0].get("annotations") or {}
    assert ann.get("readOnlyHint") is True


# ---------------------------------------------------------------- integration: stdio handshake
@pytest.mark.asyncio
async def test_stdio_server_roundtrip(tmp_path):
    """Khởi động server qua stdio thật + gọi tools/list và tools/call qua MCP client."""
    payloads = _load(REPO_TASK)
    pfile = tmp_path / "payloads.json"
    pfile.write_text(json.dumps(payloads, ensure_ascii=False), encoding="utf-8")

    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(ROOT, "tools", "mcp_snapshot_server.py"), str(pfile)],
        env={**os.environ, "BENCH_PAYLOADS": str(pfile)},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert "vn_quote_history" in [t.name for t in tools.tools]
            bad = await session.call_tool('vn_quote_history', {'symbol': 'EIB', 'days': 1})
            assert bad.isError is True
            diagnostic = json.loads(bad.content[0].text)
            assert diagnostic['error']['code'] == 'unsupported_snapshot_query'
            assert diagnostic['error']['snapshot_requests']
            assert 'benchmark_evidence' not in diagnostic and 'data' not in diagnostic
            res = await session.call_tool("vn_quote_history", {"symbol": "EIB"})
            assert res.isError is False
            text = res.content[0].text
            data = json.loads(text)
            assert data["data"]["last"] == pytest.approx(16.1)
            assert data["provenance"]["as_of"]  # provenance giữ nguyên

@pytest.mark.parametrize('arguments', [
    {'symbol': 'INVENTED'}, {'symbol': 'EIB', 'days': 10},
    {'symbol': 'EIB', 'days': True}, {'symbol': 'EIB', 'unknown': 'x'},
    {'symbol': ['EIB']}, {'symbol': 'EIB', 'interval': '1W'},
])
def test_contradictory_and_malformed_requests_rejected(two_same_tool, arguments):
    with pytest.raises(ValueError):
        select_envelope(two_same_tool, 'vn_quote_history', arguments)


def test_optional_parameter_ambiguity_rejected():
    entries=[('a',{'tool':'vn_quote_history','params':{'symbol':'EIB','days':5},'envelope':{'data':1}}),
             ('b',{'tool':'vn_quote_history','params':{'symbol':'EIB','days':10},'envelope':{'data':2}})]
    with pytest.raises(ValueError):
        select_envelope(entries,'vn_quote_history',{'symbol':'EIB'})


def test_ledger_success_and_rejection_are_bound_to_response(tmp_path, two_same_tool):
    from mcp_snapshot_server import replay_call, digest
    path=tmp_path/'calls.jsonl'
    env=replay_call(two_same_tool,'vn_quote_history',{'symbol':'EIB','days':5},'a'*64,str(path))
    rejected=replay_call(two_same_tool,'vn_quote_history',{'symbol':'NOPE'},'a'*64,str(path))
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    assert [r['status'] for r in rows]==['ok','rejected']
    assert len({r['call_id'] for r in rows})==2
    assert rows[0]['response_sha256']==digest({k:v for k,v in env.items() if k!='benchmark_evidence'})
    assert env['benchmark_evidence']['call_id']==rows[0]['call_id']
    assert rows[0]['as_of']=='A'
    assert rejected['request_rejected'] is True
    assert rejected['error']['code'] == 'unsupported_snapshot_query'
    assert 'benchmark_evidence' not in rejected
    assert rejected['error']['snapshot_requests']
    assert 'data' not in rejected


def test_pilot_merged_capture_requires_individual_symbols():
    from mcp_snapshot_server import load_entries
    entries,_=load_entries(os.path.join(ROOT,'tasks/pilot/fin-l3-agg-01/environment/payloads.json'))
    assert len(entries)==5
    assert select_envelope(entries,'vn_quote_history',{'symbol':'VCB'})['data']['last']==56.3
    with pytest.raises(ValueError):select_envelope(entries,'vn_quote_history',{'symbol':'FAKE'})


def test_batch_subsets_do_not_reuse_full_batch_summary():
    entries=[('batch',{'tool':'crypto_spot','params':{'symbols':['BTCUSDT','ETHUSDT']},
                      'envelope':{'data':{'tickers':[],'summary':'full batch'}}})]
    with pytest.raises(ValueError):
        select_envelope(entries,'crypto_spot',{'symbols':['BTCUSDT']})


def test_omitted_nondefault_parameters_do_not_mutate_request(two_same_tool):
    with pytest.raises(ValueError):
        select_envelope(two_same_tool,'vn_quote_history',{'symbol':'EIB'})


def test_nonfinite_rejection_is_also_recorded(tmp_path,two_same_tool):
    from mcp_snapshot_server import replay_call
    path=tmp_path/'ledger.jsonl'
    env=replay_call(two_same_tool,'vn_quote_history',{'symbol':'EIB','days':float('nan')},'a'*64,str(path))
    assert env['request_rejected'] is True
    assert env['error']['code'] == 'invalid_request'
    assert 'benchmark_evidence' not in env
    row=json.loads(path.read_text());assert row['status']=='rejected'
    assert row['arguments']['days']=='[NONFINITE]'
