#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_benchmark.py — DRIVER benchmark harness tài chính (1 lệnh chạy pilot/main/holdout).

Ví dụ:
    python3 tools/run_benchmark.py --split pilot                      # 3 arm × 24 task × 3 runs? (mặc định runs=1)
    python3 tools/run_benchmark.py --split pilot --sample 5 --seed 20261102 --runs 1
    python3 tools/run_benchmark.py --split main --runs 3
    python3 tools/run_benchmark.py --split holdout --confirm-holdout  # GUARD quy chế 7.4

Mỗi trial:
  1. workspace = runs/<runid>/trials/<task>__<arm>__r<run>/ — CHỈ chứa instruction.md
     (gold/payloads nằm ngoài workspace — runner contract, PRE-REGISTER 02/11).
  2. Gọi runner của arm (tools/runners/run_<arm>.py) với timeout = time_limit_min.
  3. Chấm bằng tests/grader.py THẬT của task (-g gold ngoài workspace).
  4. Ghi 1 dòng trials.jsonl (schema Phần 2.5 benchmark-plan) + log thô.

Điều kiện chung 3 arm (8 trục rút gọn): cùng model/key NVIDIA · cùng instruction ·
cùng workspace · cùng MCP snapshot (mcp_snapshot_server.py phục vụ đúng envelope) ·
cùng grader · cùng timeout · session mới mỗi trial.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

ARMS = ("opencode", "dsh", "opentrading")
SPLITS = ("pilot", "smoke", "main", "holdout")
ANSWER_KEYS = ("value", "values", "verdict", "ranking", "reason")


# ------------------------------------------------------------------ config
def load_config():
    path = os.path.join(HERE, "bench_config.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ chọn task
def select_tasks(split, sample=None, seed=None, tasks_filter=None, confirm_holdout=False):
    """Trả list đường dẫn task dir, thứ tự sorted (deterministic)."""
    if split not in SPLITS:
        raise SystemExit("split phải là 1 trong: %s" % ", ".join(SPLITS))
    if split == "holdout" and not confirm_holdout:
        # Quy chế holdout 7.4: không chạy trước freeze; mở đúng 1 lần có chủ đích.
        print("TỪ CHỐI: holdout niêm phong — chỉ chạy với --confirm-holdout sau khi freeze.")
        raise SystemExit(2)
    root = os.path.join(ROOT, "tasks", split)
    ids = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    if tasks_filter:
        unknown = [t for t in tasks_filter if t not in ids]
        if unknown:
            raise ValueError("Task không tồn tại trong split %s: %s" % (split, unknown))
        ids = [t for t in ids if t in set(tasks_filter)]
    if sample is not None:
        import random
        rng = random.Random(seed or 0)
        ids = sorted(rng.sample(ids, min(sample, len(ids))))
    return [os.path.join(root, i) for i in ids]


def count_mcp_calls(log_path, task_dir):
    """Đếm tín hiệu lời gọi tool MCP trong log thô của trial (best-effort).

    Hợp lệ hoá runner contract: agent phải dùng MCP snapshot, không đọc payloads
    trực tiếp. Quét: '"tool":"<name>"' (opencode NDJSON) · tool-start labels
    (opentrading) · mcp__opentrading__<name> (dsh)."""
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            log = f.read()
    except OSError:
        return 0
    try:
        with open(os.path.join(task_dir, "environment", "payloads.json"), encoding="utf-8") as f:
            raw = json.load(f)["tools"].values()
        # 2 cấu trúc payloads (main: {tool, params, envelope} · pilot: envelope-trực-tiếp)
        tools = {(v.get("tool") if ("tool" in v and "envelope" in v) else k)
                 for k, v in zip(json.load(open(os.path.join(task_dir, "environment", "payloads.json"),
                                                encoding="utf-8"))["tools"].keys(), raw)}
    except (OSError, KeyError):
        return 0
    n = 0
    for t in tools:
        if not t:
            continue
        esc = re.escape(t)
        n += len(re.findall(r'"tool"\s*:\s*"[^"]*%s' % esc, log))
        n += len(re.findall(r"mcp__opentrading__%s\b" % esc, log))
        n += len(re.findall(r"tool-start[^\n]*%s" % esc, log))
        n += len(re.findall(r"opentrading\.%s\b" % esc, log))  # code mode: tools.opentrading.<tool>
    return n


def read_task_meta(task_dir):
    """Đọc task.toml dạng phẳng (time_limit_min, level, snapshot_date...)."""
    meta = {}
    with open(os.path.join(task_dir, "task.toml"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r'^(\w+)\s*=\s*"?([^"#\n]+)"?', line)
            if m:
                key, val = m.group(1).strip(), m.group(2).strip().strip('"')
                if key not in meta:
                    meta[key] = val
    return meta


# ------------------------------------------------------------------ workspace
def make_workspace(out_base, task_dir):
    """Workspace per-trial: CHỈ instruction.md — không gold, không payloads."""
    os.makedirs(out_base, exist_ok=True)
    ws = out_base
    with open(os.path.join(task_dir, "instruction.md"), encoding="utf-8") as f:
        instr = f.read()
    with open(os.path.join(ws, "instruction.md"), "w", encoding="utf-8") as f:
        f.write(instr)
    return ws


# ------------------------------------------------------------------ extract answer (opentrading)
def _balanced_objects(text):
    """Trích mọi object JSON cân bằng ({} ngoài string) từ text — theo thứ tự xuất hiện."""
    out = []
    depth = 0
    start = None
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    out.append(text[start:i + 1])
                    start = None
    return out


def extract_answer_json(text):
    """Opentrading không có tool ghi file → runner chuẩn hoá: rút answer.json từ output.

    Ưu tiên: fenced ```json``` → object chứa key answer-schema → object JSON đầu tiên.
    Trả None nếu không có JSON hợp lệ.
    """
    if not text:
        return None
    # 1) fenced blocks
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S):
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 2) object chứa key answer-schema (ưu tiên object có key nhiều nhất rồi cuối cùng)
    cands = []
    for raw in _balanced_objects(text):
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            hits = sum(1 for k in ANSWER_KEYS if k in obj)
            if hits:
                cands.append((hits, obj))
    if cands:
        cands.sort(key=lambda x: x[0])
        return cands[-1][1]
    return None


# ------------------------------------------------------------------ grading
def grade_answer(answer_path, task_dir, out_dir):
    """Chấm qua grader THẬT của task. Trả {success, fp, error_type, grade_path, raw}."""
    gold = os.path.join(task_dir, "solution", "gold.json")
    grader = os.path.join(task_dir, "tests", "grader.py")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "grade.json")
    if not os.path.exists(answer_path):
        return {"success": False, "fp": 0, "error_type": "khong_tra_loi",
                "grade_path": out_path, "raw": {"detail": "không có answer.json"}}
    try:
        subprocess.run([sys.executable, grader, answer_path, "-g", gold, "-o", out_path],
                       capture_output=True, text=True, cwd=out_dir, timeout=60)
        with open(out_path, encoding="utf-8") as f:
            g = json.load(f)
    except Exception as e:  # grader crash → thất bại trial, không chết driver
        return {"success": False, "fp": 0, "error_type": "grader_error",
                "grade_path": out_path, "raw": {"detail": str(e)[:200]}}
    return {"success": bool(g.get("success")), "fp": int(g.get("fp") or 0),
            "error_type": g.get("error_type"), "grade_path": out_path, "raw": g}


# ------------------------------------------------------------------ runner dispatch
def run_trial(arm, ws, instruction, task_dir, model, timeout_s, log_path):
    """Gọi runner của arm; trả dict(status, answer_path, session_id, tokens, wall_ms, notes)."""
    mod = __import__("runners.run_%s" % arm, fromlist=["run"])
    t0 = time.monotonic()
    try:
        res = mod.run(ws=ws, instruction=instruction, task_dir=task_dir,
                      model=model, timeout_s=timeout_s, log_path=log_path)
    except Exception as e:
        res = {"status": "runner_error", "answer_path": None, "session_id": None,
               "tokens": None, "wall_ms": int((time.monotonic() - t0) * 1000),
               "notes": "%s: %s" % (type(e).__name__, e)}
    res.setdefault("wall_ms", int((time.monotonic() - t0) * 1000))
    return res


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description="Driver benchmark harness tài chính")
    ap.add_argument("--split", default="pilot", choices=SPLITS)
    ap.add_argument("--arms", default="all", help="'all' hoặc 'opencode,dsh,opentrading'")
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=20261102)
    ap.add_argument("--tasks", default=None, help="danh sách id, phân cách phẩy")
    ap.add_argument("--model", default=None, help="mặc định lấy từ tools/bench_config.json")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--out", default=None, help="mặc định results/<ts>_<split>")
    ap.add_argument("--confirm-holdout", action="store_true")
    ap.add_argument("--retry", type=int, default=2, help="số lần thử lại trial lỗi hạ tầng (429/timeout)")
    ap.add_argument("--pause", type=float, default=5.0, help="giây nghỉ giữa các trial (tránh 429)")
    ap.add_argument("--list-only", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    model = args.model or cfg.get("model")
    if not model:
        raise SystemExit("Chưa có model — truyền --model hoặc đặt trong tools/bench_config.json")
    arms = list(ARMS) if args.arms == "all" else [a.strip() for a in args.arms.split(",") if a.strip()]
    for a in arms:
        if a not in ARMS:
            raise SystemExit("arm không hợp lệ: %s (chọn trong %s)" % (a, ARMS))

    tasks_filter = [t.strip() for t in args.tasks.split(",")] if args.tasks else None
    tasks = select_tasks(args.split, args.sample, args.seed, tasks_filter, args.confirm_holdout)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.abspath(args.out or os.path.join(ROOT, "results", "%s_%s" % (ts, args.split)))
    os.makedirs(out_dir, exist_ok=True)
    print("DRIVER: split=%s arms=%s model=%s runs=%d → %s" % (args.split, ",".join(arms), model, args.runs, out_dir))

    if args.list_only:
        for t in tasks:
            print(" -", os.path.basename(t))
        return

    trials_path = os.path.join(out_dir, "trials.jsonl")
    stats = {a: {"n": 0, "ok": 0, "fp": 0, "wall": []} for a in arms}
    n_total = len(tasks) * args.runs * len(arms)
    n_done = 0
    with open(trials_path, "a", encoding="utf-8") as trials:
        for task_dir in tasks:
            tid = os.path.basename(task_dir)
            meta = read_task_meta(task_dir)
            level = meta.get("level", "?")
            timeout_s = int(meta.get("time_limit_min", "15")) * 60
            instr = open(os.path.join(task_dir, "instruction.md"), encoding="utf-8").read()
            for run in range(1, args.runs + 1):
                for arm in arms:
                    n_done += 1
                    tdir = os.path.join(out_dir, "trials", "%s__%s__r%d" % (tid, arm, run))
                    ws = make_workspace(os.path.join(tdir, "ws"), task_dir)
                    log_path = os.path.join(tdir, "run.log")
                    attempt = 0
                    while True:
                        attempt += 1
                        res = run_trial(arm, ws, instr, task_dir, model, timeout_s, log_path)
                        status = res.get("status", "unknown")
                        # chỉ thử lại khi lỗi HẠ TẦNG: runner lỗi rõ
                        # + lỗi 429/quota trong log (harness tự retry nội bộ có thể đã hút cạn)
                        got_answer = bool(res.get("answer_path")) or bool(res.get("final_text"))
                        log_low = ""
                        try:
                            log_low = open(log_path, encoding="utf-8", errors="replace").read().lower()
                        except OSError:
                            pass
                        rate_limited = (not got_answer) and bool(
                            re.search(r"429|too many requests|rate.?limit|hết quota", log_low))
                        infr = status in ("error", "runner_error") or rate_limited
                        if infr and attempt <= args.retry:
                            print("   ↻ retry %s %s (attempt %d, status=%s) sau %.0fs" % (
                                tid, arm, attempt, status, args.pause * 2))
                            time.sleep(args.pause * 2)
                            continue
                        break
                    if args.pause:
                        time.sleep(args.pause)
                    answer_path = res.get("answer_path")
                    answer_src = "file" if answer_path and os.path.exists(answer_path) else None
                    if answer_src is None and res.get("answer_candidates"):
                        ans = res["answer_candidates"][-1]
                        answer_path = os.path.join(ws, "answer.json")
                        with open(answer_path, "w", encoding="utf-8") as f:
                            json.dump(ans, f, ensure_ascii=False, indent=1)
                        answer_src = "extracted_input"
                    if answer_src is None and res.get("final_text"):
                        ans = extract_answer_json(res["final_text"])
                        if ans is not None:
                            answer_path = os.path.join(ws, "answer.json")
                            with open(answer_path, "w", encoding="utf-8") as f:
                                json.dump(ans, f, ensure_ascii=False, indent=1)
                            answer_src = "extracted"
                    g = grade_answer(answer_path, task_dir, tdir) if answer_path else \
                        {"success": False, "fp": 0, "error_type": "khong_tra_loi",
                         "grade_path": None, "raw": {}}
                    trial = {
                        "trial_id": "%s__%s__r%d" % (tid, arm, run),
                        "arm": arm, "model": model, "level": level, "task": tid, "run": run,
                        "status": status,
                        "answer_source": answer_src or "missing",
                        "success": g["success"], "fp": g["fp"], "error_type": g["error_type"],
                        "wall_ms": res.get("wall_ms"),
                        "tokens": res.get("tokens"),
                        "requests": res.get("requests"),
                        "session_id": res.get("session_id"),
                        "attempt": attempt,
                        "mcp_calls": count_mcp_calls(log_path, task_dir),
                        "workspace": os.path.relpath(ws, ROOT),
                        "snapshot_date": meta.get("snapshot_date"),
                        "started_at": int(time.time()),
                    }
                    trials.write(json.dumps(trial, ensure_ascii=False) + "\n")
                    trials.flush()
                    st = stats[arm]
                    st["n"] += 1
                    st["ok"] += 1 if g["success"] else 0
                    st["fp"] += g["fp"]
                    if trial["wall_ms"]:
                        st["wall"].append(trial["wall_ms"])
                    print("[%d/%d] %-22s %-11s %-8s success=%s fp=%d mcp=%d %sms" % (
                        n_done, n_total, tid, arm, status, g["success"], g["fp"],
                        trial["mcp_calls"], trial["wall_ms"] or "-"))

    print("=" * 78)
    print("TÓM TẮT (model=%s, split=%s):" % (model, args.split))
    for arm in arms:
        st = stats[arm]
        mean_wall = sum(st["wall"]) / len(st["wall"]) if st["wall"] else 0
        print("  %-11s trials=%-3d success=%-3d fp=%-3d wall_ms_mean=%d" % (
            arm, st["n"], st["ok"], st["fp"], mean_wall))
    print("Kết quả: %s | Log thô: results/<runid>/trials/" % trials_path)


if __name__ == "__main__":
    main()
