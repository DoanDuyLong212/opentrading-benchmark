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
    env = select_envelope(two_same_tool, "vn_quote_history", {"symbol": "ACB"})
    assert env["data"]["symbol"] == "ACB"


def test_select_scores_more_matching_params(two_same_tool):
    """days=10 khớp 2/2 params của ANV thay vì 1/2 của EIB/ACB."""
    env = select_envelope(two_same_tool, "vn_quote_history", {"symbol": "ANV", "days": 10})
    assert env["data"]["symbol"] == "ANV"


def test_select_tie_keeps_first_by_key_order(two_same_tool):
    """Không có args nào khớp → hòa 0-0 → giữ envelope đầu theo thứ tự key."""
    env = select_envelope(two_same_tool, "vn_quote_history", {})
    assert env["data"]["symbol"] == "EIB"


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
                                "envelope": {"data": {"quotes": ["x"]}}})]
    env = select_envelope(entries, "vn_equity_quote_batch", {"symbols": ["CMG", "ELC", "VGI", "CTR", "FOX"]})
    assert env["data"]["quotes"] == ["x"]


# ---------------------------------------------------------------- unit: tools/list
def test_build_tool_defs_union_and_schema():
    payloads = _load(REPO_TASK)
    entries = _entries(payloads)
    defs = build_tool_defs(entries)
    names = [d["name"] for d in defs]
    assert names == ["vn_quote_history"]
    schema = defs[0]["inputSchema"]
    assert schema["type"] == "object"
    assert "symbol" in schema["properties"]
    assert schema.get("required") in (None, [])


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
            res = await session.call_tool("vn_quote_history", {"symbol": "EIB"})
            text = res.content[0].text
            data = json.loads(text)
            assert data["data"]["last"] == pytest.approx(16.1)
            assert data["provenance"]["as_of"]  # provenance giữ nguyên
