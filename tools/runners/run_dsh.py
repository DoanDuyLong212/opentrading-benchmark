# -*- coding: utf-8 -*-
"""Runner arm DSH — `dsh --profile headless --json --patch <per-trial patch>`.

Patch per-trial (sinh vào <trial>/runner/): model mặc định + MCP snapshot server
(dsh-mcp-client, tool name dạng mcp__opentrading__<tool> — grader chấm `source`
theo substring nên vẫn khớp). stdin nhận instruction (`-`), cwd = workspace.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import popen_run

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SNAPSHOT = os.path.join(TOOLS, "mcp_snapshot_server.py")
DSH_BIN = os.path.expanduser("~/.local/bin/dsh")


def _patch_yml(snapshot, payloads, provider, model):
    return ("- id: agent-default-model\n"
            "  config:\n"
            "    provider: %s\n"
            "    model: %s\n"
            "- id: mcp-opentrading\n"
            "  name: '@deepseek-ai/dsh-mcp-client'\n"
            "  config:\n"
            "    serverName: opentrading\n"
            "    transport: stdio\n"
            "    command: %s\n"
            "    args: ['%s']\n"
            "    env:\n"
            "      BENCH_PAYLOADS: '%s'\n"
            % (provider, model, sys.executable, snapshot, payloads))


def run(ws, instruction, task_dir, model, timeout_s, log_path):
    tdir = os.path.dirname(ws)
    rdir = os.path.join(tdir, "runner")
    os.makedirs(rdir, exist_ok=True)
    payloads = os.path.join(task_dir, "environment", "payloads.json")
    if "/" in model:
        provider, model_id = model.split("/", 1)
    else:
        provider, model_id = "nvidia", model
    patch = os.path.join(rdir, "bench.dsh.patch.yml")
    with open(patch, "w", encoding="utf-8") as f:
        f.write(_patch_yml(SNAPSHOT, payloads, provider, model_id))

    cmd = [DSH_BIN, "--profile", "headless", "--patch", patch, "--json", "-"]
    rc, out, err, timed_out = popen_run(cmd, cwd=ws, env=dict(os.environ), timeout_s=timeout_s,
                                        log_path=log_path, stdin_text=instruction)

    texts, session_id, tokens = [], None, None
    for line in (out or "").splitlines() + (err or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            texts.append(line)  # dòng thường (nếu dsh in final message không --json)
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(ev.get("text"), str) and ev["text"]:
            texts.append(ev["text"])
        for key in ("sessionID", "sessionId", "session_id"):
            if ev.get(key):
                session_id = ev[key]
        if isinstance(ev.get("usage"), dict):
            tokens = ev["usage"]
    answer_path = os.path.join(ws, "answer.json")
    return {"status": "timeout" if timed_out else ("ok" if rc == 0 else "error"),
            "answer_path": answer_path if os.path.exists(answer_path) else None,
            "final_text": "\n".join(texts),
            "session_id": session_id, "tokens": tokens,
            "notes": "" if rc == 0 else "exit=%s" % rc}
