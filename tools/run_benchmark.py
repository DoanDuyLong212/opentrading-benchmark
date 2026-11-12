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
def load_config(path=None):
    path = path or os.path.join(HERE, "bench_config.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ chọn task
def select_tasks(split, sample=None, seed=None, tasks_filter=None, confirm_holdout=False, include_quarantined=False):
    """Trả list đường dẫn task dir, thứ tự sorted (deterministic)."""
    if split not in SPLITS:
        raise SystemExit("split phải là 1 trong: %s" % ", ".join(SPLITS))
    if split == "holdout" and not confirm_holdout:
        # Quy chế holdout 7.4: không chạy trước freeze; mở đúng 1 lần có chủ đích.
        print("TỪ CHỐI: holdout niêm phong — chỉ chạy với --confirm-holdout sau khi freeze.")
        raise SystemExit(2)
    root = os.path.join(ROOT, "tasks", split)
    ids = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    from run_manifest import task_eligibility
    eligibility = {tid: task_eligibility(os.path.join(root, tid)) for tid in ids}
    excluded = {tid: meta['exclusion_reason'] for tid, meta in eligibility.items() if not meta['confirmatory_eligible']}
    memory_ids={tid for tid,meta in eligibility.items() if meta.get('memory_multiturn')}
    if tasks_filter and memory_ids & set(tasks_filter):raise ValueError('Memory tasks require the separate versioned multi-turn driver')
    ids=[tid for tid in ids if tid not in memory_ids]
    if include_quarantined and split not in ('smoke', 'pilot'):
        raise ValueError('Quarantined tasks are available only for explicit smoke/pilot diagnostics')
    if tasks_filter:
        unknown = [t for t in tasks_filter if t not in ids]
        if unknown:
            raise ValueError("Task không tồn tại trong split %s: %s" % (split, unknown))
        ids = [t for t in ids if t in set(tasks_filter)]
        if not include_quarantined and set(ids) & set(excluded):
            raise ValueError('Explicit selection includes quarantined tasks: '+str({t: excluded[t] for t in ids if t in excluded}))
    if excluded and not include_quarantined:
        print('Excluded %d quarantined tasks: %s' % (len(excluded), json.dumps(excluded, ensure_ascii=False)), file=sys.stderr)
        ids = [tid for tid in ids if tid not in excluded]
    if sample is not None:
        import random
        rng = random.Random(seed or 0)
        ids = sorted(rng.sample(ids, min(sample, len(ids))))
    return [os.path.join(root, i) for i in ids]


def load_ledger(path):
    """Authoritative MCP server records only; never infer calls from harness prose."""
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict) or not row.get("call_id"):
                    raise ValueError("Invalid MCP ledger record")
                rows.append(row)
    if len({r["call_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate MCP call IDs")
    return rows


def grounded_answer(answer, ledger):
    """Every claimed item must have actually been returned in this attempt."""
    evidence = answer.get("evidence") if isinstance(answer, dict) else None
    if not isinstance(evidence, list) or not evidence:
        return False
    successful = [r for r in ledger if r.get("status") == "ok"]
    for claim in evidence:
        if not isinstance(claim, dict):
            return False
        def matches(row):
            provenance = row.get("provenance") or {}
            return (claim.get("tool") == row.get("tool")
                    and claim.get("source") == row.get("source", provenance.get("source"))
                    and claim.get("as_of") == row.get("as_of", provenance.get("as_of"))
                    and bool(claim.get("source")) and bool(claim.get("as_of"))
                    and bool(claim.get("call_id")) and claim["call_id"] == row.get("call_id")
                    and bool(claim.get("payload_sha256")) and claim["payload_sha256"] == row.get("payload_sha256")
                    and bool(claim.get("matched_entry_id")) and claim["matched_entry_id"] == row.get("matched_entry_id")
                    and bool(claim.get("response_sha256")) and claim["response_sha256"] == row.get("response_sha256"))
        if not any(matches(row) for row in successful):
            return False
    return True


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
    if os.listdir(out_base):
        raise ValueError("Workspace must be empty; answer/session reuse is forbidden")
    ws = out_base
    with open(os.path.join(task_dir, "instruction.md"), encoding="utf-8") as f:
        instr = f.read()
    with open(os.path.join(ws, "instruction.md"), "w", encoding="utf-8") as f:
        f.write(instr)
    return ws


# ------------------------------------------------------------------ extract answer (opentrading)
def extract_answer_json(text):
    """Exactly one final JSON object, optionally wrapped in a sole JSON fence.

    Duplicate keys, nonfinite values, prose, extra objects and malformed fences
    are invalid transport. Never salvage a nested object from a malformed answer.
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    if text.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.S)
        if not match:
            return None
        text = match.group(1).strip()
    def unique_object(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('Duplicate JSON key')
            out[key] = value
        return out
    def reject_constant(value):
        raise ValueError('Nonfinite JSON constant: '+value)
    def finite_float(value):
        import math
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Nonfinite JSON number')
        return number
    try:
        obj = json.loads(text, object_pairs_hook=unique_object, parse_constant=reject_constant, parse_float=finite_float)
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
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
def run_trial(arm, ws, instruction, task_dir, model, timeout_s, log_path, options=None):
    """Gọi runner của arm; trả dict(status, answer_path, session_id, tokens, wall_ms, notes)."""
    from experiment_conditions import condition
    selected = condition(arm)
    options = dict(options or {}, condition=arm, **selected)
    mod = __import__("runners.run_%s" % selected['native_arm'], fromlist=["run"])
    t0 = time.monotonic()
    try:
        res = mod.run(ws=ws, instruction=instruction, task_dir=task_dir,
                      model=model, timeout_s=timeout_s, log_path=log_path, options=options)
    except Exception as e:
        res = {"status": "runner_error", "answer_path": None, "session_id": None,
               "tokens": None, "wall_ms": int((time.monotonic() - t0) * 1000),
               "notes": "%s: %s" % (type(e).__name__, e)}
    res.setdefault("wall_ms", int((time.monotonic() - t0) * 1000))
    return res


# ------------------------------------------------------------------ bounded trial execution

def transient_failure(result, log_text):
    # Format/semantic errors, credentials, provider incompatibility and budget caps
    # are deterministic failures. Retry only a provider's identifiable transient error.
    if result.get("final_text") and extract_answer_json(result["final_text"]) is not None:
        return False
    if result.get("provider_ledger") and os.path.exists(result["provider_ledger"]):
        try:
            rows = [json.loads(line) for line in open(result["provider_ledger"], encoding="utf-8") if line.strip()]
            return bool(rows) and rows[-1].get("status") in (429, 500, 502, 503, 504)
        except (OSError, ValueError):
            return False
    text = (str(result.get("notes", "")) + " " + log_text).lower()
    if re.search(r"\b(?:400|401|403|404)\b|unsupported|invalid.api.key|budget.exceeded|cap.exceeded", text):
        return False
    return bool(re.search(r"\b(?:429|500|502|503|504)\b|too many requests|rate.?limit|service unavailable|connection reset|temporarily unavailable", text))


def sum_attempt_tokens(attempts):
    from metrics import norm_tokens
    normalized = [norm_tokens(a.get("tokens")) for a in attempts]
    if not normalized or any(n is None or a.get("tokens", {}).get("complete") is False for n, a in zip(normalized, attempts)):
        return None
    out = {}
    for field in ("input", "output", "reasoning", "cache_read"):
        values = [n.get(field) for n in normalized]
        out[field] = sum(values) if all(isinstance(v, (int, float)) for v in values) else None
    out["complete"] = all(a.get("tokens", {}).get("complete", True) for a in attempts)
    return out


def execute_trial(item, task_dir, out_dir, model, timeout_s, retries=0, backoff_s=0, options=None):
    tid, arm, run = item["task"], item["arm"], item["run"]
    tdir = os.path.join(out_dir, "trials", item["trial_id"])
    from pathlib import Path
    from run_manifest import write_exclusive
    state_path = Path(tdir)/'state.json'
    recovering = (Path(tdir)/'attempts').exists()
    os.makedirs(tdir, exist_ok=True)
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state['timeout_s'] != timeout_s or state['trial_id'] != item['trial_id']:
            raise ValueError('Interrupted trial state disagrees with frozen schedule')
    else:
        state = {'trial_id': item['trial_id'], 'timeout_s': timeout_s,
                 'started_at': datetime.now(timezone.utc).isoformat(), 'started_epoch': time.time()}
        write_exclusive(state_path, state)
    instr = open(os.path.join(task_dir, "instruction.md"), encoding="utf-8").read()
    payload_clock = json.load(open(os.path.join(task_dir, 'environment', 'payloads.json'), encoding='utf-8'))['snapshot_date']
    instr = ('Benchmark time context: answer relative to the frozen data snapshot as of '+payload_clock+
             '. Execution wall-clock does not advance the financial reporting period. Use response provenance.as_of for evidence.\n\n'+instr)
    started_at = state['started_at']
    started = time.monotonic()
    attempts, all_calls = [], []
    answer, answer_path, grade = None, None, None
    if recovering:
        for directory in sorted((Path(tdir)/'attempts').iterdir()):
            if not directory.is_dir():
                continue
            result_file = directory/'result.json'
            if result_file.exists():
                result = json.loads(result_file.read_text())
                result['recovered'] = True
            else:
                # A crash mid-request cannot be assumed free or successful. Preserve
                # every artifact; unknown usage stays N/A and no new call is issued.
                result = {'status': 'interrupted', 'tokens': None, 'provider_requests': None,
                          'workspace': str(directory/'ws'), 'ledger_path': str(directory/'mcp.jsonl'),
                          'log_path': str(directory/'run.log'), 'attempt': len(attempts)+1,
                          'recovered': True, 'notes': 'Process stopped before durable attempt result'}
            attempts.append(result)
            try:
                all_calls.extend(load_ledger(result['ledger_path']))
            except (ValueError, json.JSONDecodeError):
                result['ledger_error'] = 'Interrupted or malformed MCP ledger'
                result['status'] = 'interrupted'
    for number in ([] if recovering else range(1, retries + 2)):
        remaining = timeout_s - (time.monotonic() - started)
        if remaining <= 0:
            break
        # If an interrupted invocation left a directory, do not reuse its contents.
        import uuid
        attempt_dir = os.path.join(tdir, "attempts", "%02d-%s" % (number, uuid.uuid4().hex[:12]))
        ws = make_workspace(os.path.join(attempt_dir, "ws"), task_dir)
        log_path = os.path.join(attempt_dir, "run.log")
        ledger_path = os.path.join(attempt_dir, "mcp.jsonl")
        opts = dict(options or {}, timeout_s=remaining, mcp_ledger=ledger_path,
                    provider_ledger=os.path.join(attempt_dir, "provider.jsonl"))
        if attempts:
            spent_requests = sum(a.get("provider_requests", a.get("requests", 0)) or 0 for a in attempts)
            spent_tokens = sum_attempt_tokens(attempts)
            if spent_tokens is None or any(spent_tokens.get(k) is None for k in ('input', 'output')):
                break  # Unknown billing cannot justify replenishing a retry budget.
            opts['max_requests'] = opts.get('max_requests', 24) - spent_requests
            opts['max_total_tokens'] = opts.get('max_total_tokens', 48000) - spent_tokens['input'] - spent_tokens['output']
            if min(opts['max_requests'], opts['max_total_tokens']) <= 0:
                break
        res = run_trial(arm, ws, instr, task_dir, model, remaining, log_path, opts)
        try:
            ledger = load_ledger(ledger_path)
        except (OSError, ValueError):
            ledger = []
            res.update(status='telemetry_error', ledger_error='Malformed MCP ledger', notes='Authoritative ledger could not be verified')
        all_calls.extend(ledger)
        res.update({"attempt": number, "workspace": ws, "log_path": log_path,
                    "ledger_path": ledger_path, "mcp_calls": len(ledger),
                    "driver_elapsed_ms": int((time.monotonic()-started)*1000)})
        attempts.append(res)
        from run_manifest import write_exclusive
        write_exclusive(os.path.join(attempt_dir, 'result.json'), res)
        log = open(log_path, encoding="utf-8", errors="replace").read() if os.path.exists(log_path) else ""
        remaining = timeout_s - (time.monotonic() - started)
        if number <= retries and transient_failure(res, log) and remaining > backoff_s:
            time.sleep(backoff_s)
            continue
        break
    res = attempts[-1] if attempts else {"status": "timeout"}
    ws = res.get("workspace")
    if ws and res.get("final_text"):
        answer = extract_answer_json(res["final_text"])
        if answer is not None:
            answer_path = os.path.join(ws, "answer.json")
            if os.path.exists(answer_path):
                if not recovering or json.load(open(answer_path, encoding='utf-8')) != answer:
                    raise ValueError('Existing answer conflicts with persisted final output')
            else:
                with open(answer_path, "x", encoding="utf-8") as handle:
                    json.dump(answer, handle, ensure_ascii=False, indent=2)
    # All arms share final JSON transport. Files/write-tool inputs are not rescued.
    if answer_path:
        grade = grade_answer(answer_path, task_dir, tdir)
    else:
        grade = {"success": False, "fp": 0, "error_type": "invalid_json" if res.get("final_text") else "khong_tra_loi", "raw": {}}
    wall_ms = (max((a.get('driver_elapsed_ms', 0) for a in attempts), default=0) if recovering
               else int((time.monotonic() - started) * 1000))
    if recovering and any(a.get('status') == 'interrupted' for a in attempts):
        wall_ms = max(wall_ms, int((time.time()-state['started_epoch'])*1000))
    timely = wall_ms <= timeout_s * 1000
    final_calls = ([r for r in all_calls if r in load_ledger(res["ledger_path"])]
                   if res.get("ledger_path") and not res.get("ledger_error") else [])
    grounded = grounded_answer(answer, final_calls)
    semantic = bool(grade.get("raw", {}).get("semantic_correctness", grade["success"]))
    contract_correct = bool(grade["success"])
    status = res.get("status", "unknown")
    success = contract_correct and grounded and status == "ok" and timely
    meta = read_task_meta(task_dir)
    requests = [a.get("provider_requests", a.get("requests")) for a in attempts]
    trial = dict(item, schema_version=3, model=model, level=meta.get("level", "?"),
                 status=status, success=success, semantic_correctness=semantic,
                 grounded_correctness=contract_correct and grounded, evidence_grounded=grounded,
                 contract_correctness=contract_correct, schema_valid=grade.get("raw", {}).get("schema_valid"),
                 timely=timely, answer_source="final_json" if answer_path else "missing",
                 fp=grade["fp"], error_type=(grade["error_type"] or ("ungrounded" if semantic and not grounded else None)),
                 execution_error=None if status == "ok" and timely else status if timely else "timeout",
                 wall_ms=wall_ms, timeout_s=timeout_s, tokens=sum_attempt_tokens(attempts),
                 requests=sum(requests) if all(isinstance(r, int) for r in requests) else None,
                 session_id=res.get("session_id"), attempt=len(attempts), attempts=attempts,
                 mcp_calls=len(all_calls), mcp_successful_calls=sum(r.get("status") == "ok" for r in all_calls),
                 workspace=ws, answer_path=answer_path, grade_path=grade.get("grade_path"),
                 snapshot_date=meta.get("snapshot_date"), started_at=started_at,
                 ended_at=datetime.now(timezone.utc).isoformat(), recovered=recovering)
    return trial


# ------------------------------------------------------------------ main

def repair_interrupted_append(path):
    """Under the run lock: quarantine only an unterminated trailing JSON fragment."""
    from pathlib import Path
    from run_manifest import write_exclusive
    path = Path(path)
    if not path.exists():
        return
    raw = path.read_bytes()
    if not raw or raw.endswith(b'\n'):
        return
    boundary = raw.rfind(b'\n') + 1
    trailing = raw[boundary:]
    try:
        json.loads(trailing)
    except (ValueError, UnicodeDecodeError):
        import uuid
        quarantine = path.with_name('trials.truncated-'+uuid.uuid4().hex+'.bin')
        with quarantine.open('xb') as handle:
            handle.write(trailing)
            handle.flush()
            os.fsync(handle.fileno())
        with path.open('r+b') as handle:
            handle.truncate(boundary)
            handle.flush()
            os.fsync(handle.fileno())
    else:
        with path.open('ab') as handle:
            handle.write(b'\n')
            handle.flush()
            os.fsync(handle.fileno())


def main():
    import fcntl
    from pathlib import Path
    from run_manifest import prepare_manifest, validate_freeze, open_holdout, validate_trial_rows
    ap = argparse.ArgumentParser(description="Frozen, resumable benchmark v2; NVIDIA small models for verification")
    ap.add_argument("--split", default="smoke", choices=SPLITS)
    ap.add_argument("--arms", default="all")
    ap.add_argument("--sample", type=int)
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--tasks")
    ap.add_argument("--model")
    ap.add_argument("--config", default=os.path.join(HERE, "bench_config.json"))
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--out")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--confirm-holdout", action="store_true")
    ap.add_argument("--include-quarantined", action="store_true", help="explicit smoke/pilot diagnostics only; never confirmatory")
    ap.add_argument("--freeze-receipt")
    ap.add_argument("--retry", type=int, default=1)
    ap.add_argument("--pause", type=float, default=2)
    ap.add_argument("--retry-backoff", type=float, default=4)
    ap.add_argument("--timeout", type=float, help="whole trial budget in seconds; retries share it")
    ap.add_argument("--effort", default="none", choices=("none", "low", "medium", "high"))
    ap.add_argument("--max-requests", type=int, default=24)
    ap.add_argument("--max-output-tokens", type=int, default=2048)
    ap.add_argument("--max-total-tokens", type=int, default=48000)
    ap.add_argument("--provider-timeout-s", type=float, default=None,
                    help="override per-request provider timeout (gateway default 45s); pilot/smoke diagnostics only")
    ap.add_argument("--list-only", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    model = args.model or cfg.get("model")
    arms = list(ARMS) if args.arms == "all" else args.arms.split(",")
    from experiment_conditions import CONDITIONS
    if not model or not arms or len(set(arms)) != len(arms) or any(a not in CONDITIONS for a in arms):
        ap.error("invalid model or arms")
    if args.split in ('main', 'holdout') and any(a not in ARMS for a in arms):
        ap.error('experimental condition aliases are pilot/smoke diagnostics only')
    if args.runs < 1 or args.retry < 0 or args.pause < 0 or args.retry_backoff < 0 or (args.timeout is not None and args.timeout <= 0):
        ap.error("runs/budgets must be positive and retry/pause nonnegative")
    if not model.startswith("nvidia/") or args.effort != "none":
        ap.error("only verified NVIDIA effort=none is supported; future Go/medium remains unverified")
    if min(args.max_requests, args.max_output_tokens, args.max_total_tokens) < 1:
        ap.error("request/token caps must be positive")
    if args.provider_timeout_s is not None and args.provider_timeout_s <= 0:
        ap.error("provider timeout must be positive")
    if args.provider_timeout_s is not None and args.split in ("main", "holdout"):
        ap.error("provider-timeout override is pilot/smoke diagnostics only")
    tasks = select_tasks(args.split, args.sample, args.seed,
                         args.tasks.split(",") if args.tasks else None, args.confirm_holdout, args.include_quarantined)
    if not tasks:
        ap.error("empty task selection")
    if args.list_only:
        print("\n".join(os.path.basename(t) for t in tasks))
        return
    freeze = None
    if args.split in ("main", "holdout") and not args.freeze_receipt:
        ap.error("main/holdout requires a validated --freeze-receipt")
    if args.freeze_receipt:
        if model != cfg.get("model"):
            ap.error("--model differs from the frozen configuration; create a new verified configuration")
        freeze = validate_freeze(args.freeze_receipt, cfg)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out_dir = os.path.abspath(args.out or os.path.join(ROOT, "results", "%s_%s" % (ts, args.split)))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, ".driver.lock"), "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Another driver owns this output directory")
        settings = {k: getattr(args, k) for k in ("split", "seed", "runs", "retry", "pause", "retry_backoff", "timeout", "effort", "max_requests", "max_output_tokens", "max_total_tokens")}
        settings.update(model=model, arms=arms, freeze_sha256=freeze)
        if args.provider_timeout_s is not None:
            settings['provider_timeout_s'] = args.provider_timeout_s
        settings['conditions'] = {name: CONDITIONS[name] for name in arms}
        settings['clock_policy'] = 'snapshot_as_of; OpenTrading native now pinned; other native clocks observed in wire capture'
        from run_manifest import task_eligibility
        split_root = Path(ROOT)/'tasks'/args.split
        settings['quarantined_tasks'] = {p.name: task_eligibility(p)['exclusion_reason']
                                        for p in sorted(split_root.iterdir()) if p.is_dir()
                                        and not task_eligibility(p)['confirmatory_eligible']}
        settings['include_quarantined'] = args.include_quarantined
        manifest = prepare_manifest(out_dir, settings, tasks, cfg, args.resume)
        if args.split == "holdout":
            open_holdout(out_dir, freeze, args.resume)
        trials_path = Path(out_dir)/"trials.jsonl"
        import metrics
        if args.resume:
            repair_interrupted_append(trials_path)
        rows = metrics.load_trials(out_dir)
        validate_trial_rows(rows, manifest)
        completed = {t["trial_id"] for t in rows}
        expected_ids = {t["trial_id"] for t in manifest["plan"]["schedule"]}
        if not completed <= expected_ids:
            raise ValueError("Existing trial IDs are outside frozen schedule")
        by_task = {os.path.basename(t): t for t in tasks}
        options = {k: getattr(args, k) for k in ("effort", "max_requests", "max_output_tokens", "max_total_tokens")}
        if args.provider_timeout_s is not None:
            options['provider_timeout_s'] = args.provider_timeout_s
        options['opentrading_runtime_root'] = cfg.get('opentrading_runtime_root')
        with trials_path.open("a", encoding="utf-8") as handle:
            for item in manifest["plan"]["schedule"]:
                if item["trial_id"] in completed:
                    continue
                task = by_task[item["task"]]
                timeout = args.timeout or int(read_task_meta(task).get("time_limit_min", "15")) * 60
                row = execute_trial(item, task, out_dir, model, timeout, args.retry, args.retry_backoff, options)
                row["manifest_sha256"] = manifest["fingerprint"]
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
                completed.add(item["trial_id"])
                print("[%d/%d] %s status=%s semantic=%s grounded=%s success=%s wall=%sms" %
                      (len(completed), len(expected_ids), item["trial_id"], row["status"], row["semantic_correctness"], row["evidence_grounded"], row["success"], row["wall_ms"]), flush=True)
                if args.pause:
                    time.sleep(args.pause)
        summary = metrics.build_summary(out_dir)
        (Path(out_dir)/"summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
        metrics.print_summary(summary)
        print("Results:", out_dir)


if __name__ == "__main__":
    main()
