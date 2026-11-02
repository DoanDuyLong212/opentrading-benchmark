#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ready_check.py — preflight benchmark: kiểm tra mọi điều kiện trước khi chạy.

Chạy: python3 tools/ready_check.py [--model nvidia/z-ai/glm-5.3-flash]
Exit 0 = sẵn sàng; exit 1 = có hạng mục FAIL (in bảng chi tiết).

Bao phủ (đối ứng gates G-E1..E7 phần smoke):
  1. Python deps (mcp SDK)                 5. Snapshot server handshake (tools/list + call)
  2. Key NVIDIA + model khả dụng            6. Workspace isolation (chỉ instruction.md)
  3. 3 harness binary + version/commit      7. Grader roundtrip (ok/mut trên 1 task)
  4. Driver + runner + config tồn tại       8. Banned-tools không nằm trong snapshot
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

CHECKS = []


def check(name, fn):
    CHECKS.append((name, fn))


def sh(cmd, timeout=30):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


# 1 ---------------------------------------------------------------- deps
def c_deps(_):
    import mcp  # noqa
    return True, "mcp SDK OK"


# 2 ---------------------------------------------------------------- NVIDIA
def c_nvidia(args):
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        return False, "NVIDIA_API_KEY chưa set"
    rc, out, err = sh('curl -s --max-time 20 https://integrate.api.nvidia.com/v1/models '
                      '-H "Authorization: Bearer $NVIDIA_API_KEY"')
    if rc != 0 or not out:
        return False, "không gọi được /v1/models (%s)" % err[:80]
    try:
        ids = [m["id"] for m in json.loads(out)["data"]]
    except Exception as e:
        return False, "phản hồi lạ: %s" % e
    model = args.model.split("/", 1)[1] if "/" in args.model else args.model
    ok = model in ids
    return ok, "model %s %s (account có %d model trong list)" % (
        model, "khả dụng" if ok else "KHÔNG trong list", len(ids))


# 3 ---------------------------------------------------------------- harnesses
def c_harnesses(_):
    lines = []
    ok = True
    rc, out, _ = sh("opencode --version")
    lines.append("opencode: %s" % (out or "THIẾU"))
    ok = ok and rc == 0
    rc, out, _ = sh(os.path.expanduser("~/.local/bin/dsh") + " --version")
    lines.append("dsh: %s" % (out or "THIẾU"))
    ok = ok and rc == 0
    rc, out, _ = sh(os.path.expanduser("~/.bun/bin/bun") + " --version")
    lines.append("bun: %s" % (out or "THIẾU"))
    ok = ok and rc == 0
    rc, out, _ = sh("git -C %s rev-parse --short HEAD 2>/dev/null" % os.path.expanduser("~/OpenTrading"))
    lines.append("OpenTrading commit: %s" % (out or "THIẾU repo"))
    ok = ok and rc == 0
    return ok, " · ".join(lines)


# 4 ---------------------------------------------------------------- files
def c_files(_):
    need = ["run_benchmark.py", "mcp_snapshot_server.py", "bench_config.json",
            "runners/run_opencode.py", "runners/run_dsh.py", "runners/run_opentrading.py",
            "runners/ot_headless.ts", "runners/common.py"]
    missing = [f for f in need if not os.path.exists(os.path.join(HERE, f))]
    if missing:
        return False, "thiếu: %s" % ", ".join(missing)
    cfg = json.load(open(os.path.join(HERE, "bench_config.json"), encoding="utf-8"))
    return True, "đủ 8 file · model mặc định=%s" % cfg.get("model")


# 5 ---------------------------------------------------------------- snapshot handshake
def c_snapshot(_):
    payloads = os.path.join(ROOT, "tasks", "main", "fin-l1-quote-vn-101", "environment", "payloads.json")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def probe():
        params = StdioServerParameters(
            command=sys.executable, args=[os.path.join(HERE, "mcp_snapshot_server.py"), payloads],
            env={**os.environ})
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                res = await s.call_tool("vn_quote_history", {"symbol": "EIB"})
                return [t.name for t in tools.tools], json.loads(res.content[0].text)

    names, env = asyncio.run(probe())
    ok = "vn_quote_history" in names and env.get("data", {}).get("last") is not None
    return ok, "tools=%s · envelope last=%s as_of=%s" % (
        names, env.get("data", {}).get("last"), (env.get("provenance") or {}).get("as_of", "?")[:19])


# 6 ---------------------------------------------------------------- isolation
def c_isolation(_):
    from run_benchmark import make_workspace
    import tempfile
    task = os.path.join(ROOT, "tasks", "pilot", "fin-l1-macro-01")
    with tempfile.TemporaryDirectory(prefix="rc-iso-") as td:
        ws = make_workspace(os.path.join(td, "ws"), task)
        entries = sorted(os.listdir(ws))
        return entries == ["instruction.md"], "workspace=%s" % entries


# 7 ---------------------------------------------------------------- grader roundtrip
def c_grader(_):
    from build_main import synthesize
    from run_benchmark import grade_answer
    import tempfile
    task = os.path.join(ROOT, "tasks", "pilot", "fin-l1-quote-01")
    gold = json.load(open(os.path.join(task, "solution", "gold.json")))
    with tempfile.TemporaryDirectory(prefix="rc-grade-") as td:
        ap = os.path.join(td, "answer.json")
        json.dump(synthesize(gold), open(ap, "w", encoding="utf-8"), ensure_ascii=False)
        g1 = grade_answer(ap, task, td)
        json.dump(synthesize(gold, mutate=True), open(ap, "w", encoding="utf-8"), ensure_ascii=False)
        g2 = grade_answer(ap, task, td)
    ok = g1["success"] is True and g2["success"] is False
    return ok, "đúng→pass · đột biến→fail %s" % ("OK" if ok else "LỖI")


# 8 ---------------------------------------------------------------- banned tools
def c_banned(_):
    banned = {"web_search", "web_fetch", "sentiment_score"}
    bad = []
    for split in ("pilot", "smoke"):
        root = os.path.join(ROOT, "tasks", split)
        for tid in sorted(os.listdir(root)):
            p = os.path.join(root, tid, "environment", "payloads.json")
            if not os.path.exists(p):
                continue
            tools = {v.get("tool") for v in json.load(open(p, encoding="utf-8"))["tools"].values()}
            hit = tools & banned
            if hit:
                bad.append("%s/%s: %s" % (split, tid, hit))
    return not bad, ("0 task chứa banned tool trong snapshot" if not bad else "; ".join(bad[:3]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None)
    args = ap.parse_args()
    if not args.model:
        cfg = json.load(open(os.path.join(HERE, "bench_config.json"), encoding="utf-8"))
        args.model = cfg["model"]

    check("1 deps python-mcp", c_deps)
    check("2 key NVIDIA + model", c_nvidia)
    check("3 harness binaries", c_harnesses)
    check("4 driver/runner/config", c_files)
    check("5 MCP snapshot handshake", c_snapshot)
    check("6 workspace isolation", c_isolation)
    check("7 grader roundtrip", c_grader)
    check("8 banned-tools trong snapshot", c_banned)

    n_fail = 0
    print("READY CHECK — model: %s" % args.model)
    print("=" * 72)
    for name, fn in CHECKS:
        try:
            ok, msg = fn(args)
        except Exception as e:
            ok, msg = False, "%s: %s" % (type(e).__name__, e)
        n_fail += 0 if ok else 1
        print("[%s] %-28s %s" % ("PASS" if ok else "FAIL", name, msg))
    print("=" * 72)
    print("KẾT QUẢ: %d/%d PASS — %s" % (len(CHECKS) - n_fail, len(CHECKS),
                                        "SẴN SÀNG chạy benchmark" if n_fail == 0 else "CHƯA SẴN SÀNG"))
    sys.exit(0 if n_fail == 0 else 1)


if __name__ == "__main__":
    main()
