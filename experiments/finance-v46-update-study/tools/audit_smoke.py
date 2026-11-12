#!/usr/bin/env python3
"""Bounded Gemini smoke using existing runners; no main/holdout, no retry.

Only the three existing smoke tasks; stop an arm after provider/infrastructure failure.
Credentials are normalized in this process only, never printed or saved in the audit.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import run_benchmark as rb


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--out", default="results/audit-gemini-20261104")
    args = ap.parse_args()
    if not 10 <= args.timeout <= 120:
        raise SystemExit("timeout must be 10..120 seconds")
    out = (ROOT / args.out).resolve()
    if out.exists():
        raise SystemExit("Refusing to reuse trial workspaces; choose a new --out")
    out.mkdir(parents=True)
    key = json.loads((Path.home() / ".opentrading/auth.json").read_text())["google"]["key"]
    os.environ["GOOGLE_API_KEY"] = key
    os.environ["GEMINI_API_KEY"] = key
    model = "google/gemini-3.5-flash-lite"
    rows = []
    manifest = {"model": model, "timeout_s": args.timeout, "retry": 0,
                "started_utc": datetime.now(timezone.utc).isoformat(),
                "credential_source": "opentrading stored key; ephemeral env normalization",
                "scope": "existing runners, three smoke tasks, no parity fixes"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    for arm in rb.ARMS:
        for tid in ("smoke-quote-01", "smoke-agg-01", "smoke-trap-01"):
            task = ROOT / "tasks/smoke" / tid
            trial_id = f"{tid}__{arm}__r1"
            tdir = out / "trials" / trial_id
            ws = rb.make_workspace(str(tdir / "ws"), str(task))
            instruction = (task / "instruction.md").read_text()
            log = str(tdir / "run.log")
            result = rb.run_trial(arm, ws, instruction, str(task), model, args.timeout, log)
            answer = result.get("answer_path")
            source = "file" if answer and Path(answer).exists() else None
            if source is None and result.get("answer_candidates"):
                answer = str(Path(ws) / "answer.json")
                Path(answer).write_text(json.dumps(result["answer_candidates"][-1], ensure_ascii=False))
                source = "extracted_input"
            if source is None:
                parsed = rb.extract_answer_json(result.get("final_text", ""))
                if parsed is not None:
                    answer = str(Path(ws) / "answer.json")
                    Path(answer).write_text(json.dumps(parsed, ensure_ascii=False))
                    source = "extracted"
            grade = rb.grade_answer(answer, str(task), str(tdir)) if answer else {}
            row = {"trial_id": trial_id, "task": tid, "arm": arm, "run": 1,
                   "model": model, "status": result["status"],
                   "success": grade.get("success", False), "fp": grade.get("fp", 0),
                   "error_type": grade.get("error_type", "khong_tra_loi"),
                   "wall_ms": result.get("wall_ms"), "tokens": result.get("tokens"),
                   "answer_source": source or "missing", "attempt": 1,
                   "workspace": str(Path(ws).relative_to(ROOT)),
                   "mcp_calls": rb.count_mcp_calls(log, str(task))}
            rows.append(row)
            with (out / "trials.jsonl").open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(json.dumps({k: row[k] for k in ("task", "arm", "status", "success", "error_type", "wall_ms", "answer_source", "mcp_calls")}), flush=True)
            if row["status"] != "ok":
                print(f"Stopping {arm} after infrastructure failure (no retry)", flush=True)
                break
    audit = ROOT / "audits/2026-11-04"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "smoke-evidence.json").write_text(json.dumps({"manifest": manifest, "trials": rows}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
