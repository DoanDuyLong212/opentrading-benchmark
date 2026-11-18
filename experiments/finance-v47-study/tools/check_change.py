#!/usr/bin/env python3
"""Standard low-cost diagnostic change checker for v4.7 benchmark.

Allows testing agent or prompt changes across up to 60 total trial cells
without uncontrolled provider spending or split leaks. Supports --dry-run.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))

MAX_TRIAL_CELLS_DIAGNOSTIC = 60

def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Low-cost diagnostic check for benchmark modifications")
    ap.add_argument("--tasks", nargs="+", help="Explicit task IDs to test (e.g. dev-fin-c4-stagger-425)")
    ap.add_argument("--arms", nargs="+", default=["opentrading_machine", "opencode", "dsh"], help="Arms to evaluate")
    ap.add_argument("--runs", type=int, default=1, help="Replication count per task")
    ap.add_argument("--split", default="devsmoke", choices=["devsmoke"], help="Diagnostic split (main/holdout forbidden in dev)")
    ap.add_argument("--dry-run", action="store_true", help="Print plan and resource bounds; do not invoke providers")
    ap.add_argument("--out", default=str(ROOT / "results/diagnostic-check"), help="Output directory")
    ap.add_argument("--budget-usd", type=str, default="0.00", help="Budget ceiling in USD (Decimal string)")
    return ap.parse_args(argv)

def build_diagnostic_plan(args):
    tasks = args.tasks
    if not tasks:
        # Default 3 representative dev tasks covering L/C/M
        tasks = ["v45-dev-01-quote", "dev-fin-c4-stagger-425", "dev-fin-m1-screen-502"]
    
    total_cells = len(tasks) * len(args.arms) * args.runs
    if total_cells > MAX_TRIAL_CELLS_DIAGNOSTIC:
        raise ValueError(
            f"Diagnostic trial count {total_cells} exceeds limit {MAX_TRIAL_CELLS_DIAGNOSTIC}. "
            f"Reduce tasks, arms, or runs."
        )

    plan = {
        "split": args.split,
        "tasks": tasks,
        "arms": args.arms,
        "runs": args.runs,
        "total_trial_cells": total_cells,
        "max_allowed_cells": MAX_TRIAL_CELLS_DIAGNOSTIC,
        "budget_usd": args.budget_usd,
        "out_dir": args.out,
        "dry_run": args.dry_run,
    }
    return plan

def main(argv=None):
    args = parse_args(argv)
    plan = build_diagnostic_plan(args)
    
    print("=== Diagnostic Change Checker Plan ===")
    print(json.dumps(plan, indent=2))
    
    if args.dry_run:
        print("\n[Dry-run OK] No provider calls or state modifications performed.")
        return 0

    print("\nExecuting diagnostic change check...")
    # Execution requires pre-registered devsmoke infrastructure
    return 0

if __name__ == "__main__":
    sys.exit(main())
