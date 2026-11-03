# -*- coding: utf-8 -*-
"""Runner arm OpenTrading — wrapper headless qua core harness (bun + ot_headless.ts).

Isolation per-trial bằng OPENTRADING_HOME riêng:
- config.json : provider/model (NVIDIA)
- auth.json   : copy từ ~/.opentrading/auth.json (key NVIDIA)
- mcp.json    : MCP snapshot server (stdio) — thay server thật

LƯU Ý (R14): OpenTrading KHÔNG có tool ghi file builtin → agent không tự ghi được
answer.json; runner trả final_text (chỉ text-delta) và driver trích JSON thành
answer.json (extract_answer_json) — chuẩn hoá ngang với "parse JSON output" arm khác.
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import popen_run

TOOLS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SNAPSHOT = os.path.join(TOOLS, "mcp_snapshot_server.py")
WRAPPER = os.path.join(TOOLS, "runners", "ot_headless.ts")
BUN = os.path.expanduser("~/.bun/bin/bun")


def run(ws, instruction, task_dir, model, timeout_s, log_path):
    tdir = os.path.abspath(os.path.dirname(ws))  # bất biến: mọi path con tuyệt đối
    home = os.path.join(tdir, "ot-home")
    os.makedirs(home, exist_ok=True)
    payloads = os.path.join(task_dir, "environment", "payloads.json")
    if "/" in model:
        provider, model_id = model.split("/", 1)
    else:
        provider, model_id = "nvidia", model
    with open(os.path.join(home, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"provider": provider, "model": model_id, "toolSearch": "off",
                   "memory": {"provider": "none"}}, f, ensure_ascii=False, indent=1)
    src_auth = os.path.expanduser("~/.opentrading/auth.json")
    if os.path.exists(src_auth):
        shutil.copy(src_auth, os.path.join(home, "auth.json"))
    mcp = {"mcpServers": {"opentrading": {"type": "stdio",
                                          "command": sys.executable,
                                          "args": [SNAPSHOT],
                                          "env": {"BENCH_PAYLOADS": payloads},
                                          "startupTimeoutMs": 30000,
                                          "toolTimeoutMs": 120000,
                                          "alwaysLoad": True}}}
    with open(os.path.join(home, "mcp.json"), "w", encoding="utf-8") as f:
        json.dump(mcp, f, ensure_ascii=False, indent=1)

    env = {**os.environ, "OPENTRADING_HOME": home}
    # Chuẩn hoá môi trường (R14): OpenTrading không có tool ghi file — nhắc arm này
    # in kết quả cuối dạng khối ```json``` để runner trích thành answer.json.
    # Chuỗi HẰNG SỐ áp cho MỌI trial OT (công bằng nội bộ arm, không đụng gold).
    ENV_NOTE = ("\n\n## Lưu ý môi trường chạy\n"
                "- Phiên này KHÔNG có tool ghi file. Sau khi tính xong, in kết quả cuối "
                "cùng dưới dạng MỘT khối ```json``` đúng schema ở trên ngay trong câu "
                "trả lời của bạn (không ghi file).")
    cmd = [BUN, WRAPPER, instruction + ENV_NOTE]
    rc, out, err, timed_out = popen_run(cmd, cwd=ws, env=env, timeout_s=timeout_s, log_path=log_path)

    # stderr = JSONL events → tìm usage/session nếu có
    tokens, session_id = None, None
    for line in (err or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(ev.get("usage"), dict):
            tokens = ev["usage"]
        for key in ("sessionID", "sessionId", "session_id", "session"):
            if isinstance(ev.get(key), str) and ev[key]:
                session_id = ev[key]
    return {"status": "timeout" if timed_out else ("ok" if rc == 0 else "error"),
            "answer_path": None,  # driver trích từ final_text (R14)
            "final_text": out or "",
            "session_id": session_id, "tokens": tokens,
            "notes": "" if rc == 0 else "exit=%s" % rc}
