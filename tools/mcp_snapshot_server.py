#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcp_snapshot_server.py — MCP stdio server REPLAY dữ liệu snapshot benchmark.

Nguồn dữ liệu: environment/payloads.json của 1 task (envelope MCP đã ghi lúc tạo task,
giữ nguyên data + provenance + availability). Server KHÔNG gọi mạng — mọi câu trả lời
là envelope đã ghi, bảo đảm 3 arm nhận đúng cùng dữ liệu (trục "Dữ liệu" — Phần 2.4).

Cách chạy (bởi harness qua stdio):
    python3 tools/mcp_snapshot_server.py <path-payloads.json>
    (hoặc env BENCH_PAYLOADS=<path>)

Hành vi:
- tools/list : union theo TÊN tool thật trong payloads; inputSchema sinh từ recorded
  params (mọi param optional, additionalProperties=true) — agent gọi tự nhiên.
- tools/call : chọn envelope cùng tên tool, khớp THAM SỐ nhiều nhất (đếm param khớp);
  hòa → envelope đầu theo thứ tự key (deterministic). Trả envelope JSON nguyên vẹn
  (data + provenance + availability + warnings) làm text content.
"""
import json
import os
import sys

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server


# ------------------------------------------------------------------ matching (unit-testable)
def _norm(v):
    """Chuẩn hoá 1 giá trị param để so sánh (list → sorted json, còn lại → str)."""
    if isinstance(v, (list, tuple)):
        return json.dumps(sorted(json.dumps(x, ensure_ascii=False, default=str) for x in v),
                          ensure_ascii=False)
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "None"
    return str(v)


def select_envelope(entries, tool_name, args):
    """Chọn envelope cho lời gọi (tool_name, args).

    entries : list (key, {tool, params, envelope}) — thứ tự key là thứ tự ghi.
    Raise KeyError nếu không có entry nào cùng tool name (chống agent gọi tool
    ngoài snapshot — đúng chủ đích allowlist G-E7).
    """
    cands = [(k, it) for k, it in entries if it.get("tool") == tool_name]
    if not cands:
        raise KeyError("Tool '%s' không có trong snapshot của task này" % tool_name)
    best_key, best_env, best_score = None, None, -1
    for k, it in cands:
        params = it.get("params") or {}
        score = sum(1 for pk, pv in params.items()
                    if pk in args and _norm(args[pk]) == _norm(pv))
        if score > best_score:
            best_key, best_env, best_score = k, it["envelope"], score
    return best_env


def build_tool_defs(entries):
    """Union theo tên tool → list ToolDef dict {name, description, inputSchema}."""
    by_name = {}
    for _k, it in entries:
        name = it.get("tool")
        if not name or name in by_name:
            continue
        props = {}
        for pk, pv in (it.get("params") or {}).items():
            if isinstance(pv, (list, tuple)):
                props[pk] = {"type": "array", "items": {}}
            elif isinstance(pv, bool):
                props[pk] = {"type": "boolean"}
            elif isinstance(pv, (int, float)):
                props[pk] = {"type": "number"}
            else:
                props[pk] = {"type": "string"}
        by_name[name] = {
            "name": name,
            "description": ("Snapshot replay — trả envelope dữ liệu đã ghi (đóng băng) "
                            "của tool '%s' cho task benchmark." % name),
            "inputSchema": {"type": "object", "properties": props,
                            "additionalProperties": True},
        }
    return list(by_name.values())


# ------------------------------------------------------------------ server
def load_entries(path):
    payloads = json.load(open(path, encoding="utf-8"))
    return [(k, v) for k, v in payloads["tools"].items()], payloads


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BENCH_PAYLOADS")
    if not path or not os.path.exists(path):
        print("mcp_snapshot_server: thiếu payloads (argv[1] hoặc BENCH_PAYLOADS)", file=sys.stderr)
        sys.exit(2)
    entries, payloads = load_entries(path)
    snap = payloads.get("snapshot_date", "?")
    server = Server("opentrading-snapshot",
                    instructions=("Snapshot replay của MCP opentrading — dữ liệu đóng băng %s. "
                                  "Mọi tool trả envelope đã ghi: {data, provenance, availability}." % snap))

    @server.list_tools()
    async def _list_tools():
        return [types.Tool(**d) for d in build_tool_defs(entries)]

    @server.call_tool()
    async def _call_tool(name, arguments):
        try:
            env = select_envelope(entries, name, dict(arguments or {}))
        except KeyError as e:
            return [types.TextContent(type="text", text=json.dumps(
                {"error": str(e), "availability": "not_in_snapshot"}, ensure_ascii=False))]
        return [types.TextContent(type="text", text=json.dumps(env, ensure_ascii=False))]

    async def _run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())

    import anyio
    anyio.run(_run)


if __name__ == "__main__":
    main()
