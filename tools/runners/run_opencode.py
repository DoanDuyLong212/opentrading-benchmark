# -*- coding: utf-8 -*-
"""Runner arm OpenCode — headless `opencode run` với isolation XDG per-trial.

Isolation (không đụng cấu hình user thật):
- XDG_CONFIG_HOME = <trial>/runner/xdg-config  → chỉ có opencode.json chứa MCP snapshot
  (loại bỏ MCP github/playwright/canva + plugins của user khỏi trial)
- XDG_DATA_HOME  = <trial>/runner/xdg-data   → auth.json copy (key NVIDIA) + sessions riêng
- cwd = workspace (chỉ instruction.md); agent tự viết answer.json trong workspace.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import popen_run

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SNAPSHOT = os.path.join(TOOLS, "mcp_snapshot_server.py")
OPENCODE_BIN = os.path.expanduser("~/.opencode/bin/opencode")


def run(ws, instruction, task_dir, model, timeout_s, log_path):
    tdir = os.path.dirname(ws)
    rdir = os.path.join(tdir, "runner")
    xdg_cfg = os.path.join(rdir, "xdg-config")
    xdg_data = os.path.join(rdir, "xdg-data")
    os.makedirs(os.path.join(xdg_cfg, "opencode"), exist_ok=True)
    os.makedirs(os.path.join(xdg_data, "opencode"), exist_ok=True)

    payloads = os.path.join(task_dir, "environment", "payloads.json")
    cfg = {"$schema": "https://opencode.ai/config.json",
           "mcp": {"opentrading": {"type": "local",
                                   "command": [sys.executable, SNAPSHOT, payloads],
                                   "enabled": True}}}
    with open(os.path.join(xdg_cfg, "opencode", "opencode.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)

    src_auth = os.path.expanduser("~/.local/share/opencode/auth.json")
    if os.path.exists(src_auth):
        shutil.copy(src_auth, os.path.join(xdg_data, "opencode", "auth.json"))

    env = {**os.environ, "XDG_CONFIG_HOME": xdg_cfg, "XDG_DATA_HOME": xdg_data}
    cmd = [OPENCODE_BIN, "run", "--standalone", "--format", "json", "--auto",
           "-m", model, instruction]
    rc, out, err, timed_out = popen_run(cmd, cwd=ws, env=env, timeout_s=timeout_s, log_path=log_path)

    final_parts, session_id, tokens = [], None, None
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("sessionID"):
            session_id = ev["sessionID"]
        part = ev.get("part") or {}
        if ev.get("type") == "text" and part.get("text"):
            final_parts.append(part["text"])
        # usage (nếu có): part.tokens hoặc ev.tokens
        tk = (part.get("tokens") if isinstance(part, dict) else None) or ev.get("tokens")
        if isinstance(tk, dict):
            tokens = tk
    answer_path = os.path.join(ws, "answer.json")
    return {"status": "timeout" if timed_out else ("ok" if rc == 0 else "error"),
            "answer_path": answer_path if os.path.exists(answer_path) else None,
            "final_text": "\n".join(final_parts),
            "session_id": session_id, "tokens": tokens,
            "notes": "" if rc == 0 else "exit=%s" % rc}
