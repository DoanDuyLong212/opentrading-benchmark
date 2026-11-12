#!/usr/bin/env python3
"""Read-only audit of development/main tasks; never evaluates the sealed holdout.

Writes evidence only under --out. No provider calls and no task regeneration.
"""
import argparse
import collections
import contextlib
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_main import synthesize
from mcp_snapshot_server import load_entries, select_envelope
import metrics


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def set_field(obj, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        obj = obj[part]
    obj[parts[-1]] = value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="audits/contract-v2/acceptance")
    args = parser.parse_args()
    out = (ROOT / args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if out == ROOT / "audits/2026-11-04":
        raise SystemExit("Historical audit output is immutable; choose a new --out directory")
    report = {"scope": "main + pilot + smoke; holdout counts/hashes only", "splits": {},
              "checks": {}, "examples": {}, "oracle_failures": [], "leaks": [],
              "numeric_consistency": {"matched": 0, "mismatches": [], "unmatched_paths": []}}
    # Hashing holdout files does not expose questions/answers to any agent/model.
    manifest = {}
    for split in ("main", "pilot", "smoke", "holdout"):
        dirs = sorted((ROOT / "tasks" / split).glob("*/task.toml"))
        report["splits"][split] = len(dirs)
        for meta in dirs:
            for p in sorted(meta.parent.rglob("*")):
                if p.is_file() and p.suffix in (".py", ".md", ".toml", ".json"):
                    manifest[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    totals = collections.Counter()
    families = collections.Counter()
    payload_sets = collections.defaultdict(list)
    payload_envelopes = set()
    checks_missing = collections.Counter()
    cases = collections.defaultdict(list)
    from check_leaks import scan_task
    with tempfile.TemporaryDirectory(prefix="benchmark-audit-") as td:
        tmp = Path(td)
        prev = Path.cwd()
        os.chdir(tmp)
        try:
            cache = {}
            for split in ("main", "pilot", "smoke"):
                for meta_path in sorted((ROOT / "tasks" / split).glob("*/task.toml")):
                    task = meta_path.parent
                    tid = task.name
                    meta = tomllib.loads(meta_path.read_text())
                    gold = json.loads((task / "solution/gold.json").read_text())
                    entries, _ = load_entries(task / "environment/payloads.json")
                    def numeric_leaves(value, path=""):
                        if isinstance(value, dict):
                            for k,v in value.items():
                                yield from numeric_leaves(v, (path+"."+k).strip("."))
                        elif isinstance(value, (int,float)) and not isinstance(value,bool):
                            yield path,value
                    leaves=list(numeric_leaves(gold.get("solution", {})))
                    for exp in gold.get("expects", []):
                        if exp["type"] != "value": continue
                        key=exp.get("path", "value").split(".")[-1]
                        candidates=[v for k,v in leaves if k.split(".")[-1] == key]
                        if not candidates:
                            report["numeric_consistency"]["unmatched_paths"].append([tid,exp.get("path","value")])
                        elif any(math.isclose(v,exp["gold"],rel_tol=1e-8,abs_tol=1e-6) for v in candidates):
                            report["numeric_consistency"]["matched"] += 1
                        else:
                            report["numeric_consistency"]["mismatches"].append([tid,exp.get("path","value"),exp["gold"],candidates])
                    if split == "main":
                        families[meta.get("family", "?")] += 1
                        payload_sets[digest([v for _, v in entries])].append(tid)
                        payload_envelopes.update(digest(v["envelope"]) for _, v in entries)
                        types = {e["type"] for e in gold.get("expects", [])}
                        for typ in ("unit", "period", "str", "str_all"):
                            if typ not in types:
                                checks_missing[typ] += 1
                        totals["main_scoring_" + gold.get("scoring", "value")] += 1
                    p = subprocess.run([sys.executable, str(task / "solution/oracle.py")],
                                       capture_output=True, text=True, timeout=15)
                    totals["oracles_checked"] += 1
                    if p.returncode:
                        report["oracle_failures"].append(tid)
                    for kind, detail in scan_task(str(task)):
                        report["leaks"].append([tid, kind, detail])
                    grader = task / "tests/grader.py"
                    h = hashlib.sha256(grader.read_bytes()).hexdigest()
                    if h not in cache:
                        cache[h] = runpy.run_path(str(grader), run_name="audit_import")

                    def grade(answer, override=None):
                        ap, gp, op = tmp / "a.json", tmp / "g.json", tmp / "grade.json"
                        ap.write_text(json.dumps(answer, ensure_ascii=False))
                        gp.write_text(json.dumps(override or gold, ensure_ascii=False))
                        argv = sys.argv
                        sys.argv = [str(grader), str(ap), "-g", str(gp), "-o", str(op)]
                        try:
                            with contextlib.redirect_stdout(io.StringIO()):
                                cache[h]["main"]()
                            return json.loads(op.read_text())
                        finally:
                            sys.argv = argv

                    correct = synthesize(gold)
                    for label, answer in [("correct", correct), ("mutated", synthesize(gold, True)), ("empty", {})]:
                        result = grade(answer)
                        totals[label + "_tested"] += 1
                        if result["success"]:
                            totals[label + "_passed"] += 1
                        elif label == "correct":
                            cases["correct_rejected"].append(tid)
                    blanket = {"value": None, "reason": "Chưa công bố, không tồn tại, không có dữ liệu, unavailable, not found"}
                    if grade(blanket)["success"]:
                        cases["blanket_refusal_passed"].append(tid)
                    for exp in gold.get("expects", []):
                        if exp["type"] == "period":
                            bad = copy.deepcopy(correct)
                            # Literal opposite period: the required token appears only in a negation.
                            set_field(bad, exp.get("path", "period"), "Q1/1900; KHÔNG PHẢI " + exp["accept"][0])
                            totals["wrong_period_tested"] += 1
                            if grade(bad)["success"]:
                                cases["wrong_period_passed"].append(tid)
                        if exp["type"] in ("str", "str_all") and exp.get("path") == "source":
                            bad = copy.deepcopy(correct)
                            set_field(bad, "source", "KHÔNG dùng " + " hoặc ".join(exp["accept"]) + "; nguồn thực tế: invented")
                            totals["wrong_source_tested"] += 1
                            if grade(bad)["success"]:
                                cases["negated_source_passed"].append(tid)
                    if gold.get("scoring") == "refusal":
                        for label, value in [("refusal_nonnull_text", "12345 đồng"), ("refusal_nonnull_object", {"amount": 12345})]:
                            bad = copy.deepcopy(correct)
                            bad["value"] = value
                            totals[label + "_tested"] += 1
                            if grade(bad)["success"]:
                                cases[label + "_passed"].append(tid)
                    # Any invented instrument must be rejected, even if this task records one symbol only.
                    for _, item in entries:
                        if "symbol" in item.get("params", {}):
                            totals["unknown_symbol_tested"] += 1
                            try:
                                select_envelope(entries, item["tool"], {"symbol": "AUDIT_DOES_NOT_EXIST_999"})
                                cases["unknown_symbol_returned_data"].append(tid)
                            except (KeyError, ValueError):
                                pass
                            break
        finally:
            os.chdir(prev)
    report["checks"] = dict(totals)
    report["counterexamples"] = {k: {"n": len(v), "tasks": v} for k, v in cases.items()}
    report["main"] = {"families": dict(families), "unique_payload_sets": len(payload_sets),
                      "unique_envelopes": len(payload_envelopes),
                      "shared_payload_sets": [v for v in payload_sets.values() if len(v) > 1],
                      "missing_check_type": dict(checks_missing)}
    # Public telemetry only; no raw logs, credentials or prompts copied into evidence.
    report["historical_runs"] = {}
    for p in sorted((ROOT / "results").glob("*/trials.jsonl")):
        rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        report["historical_runs"][p.parent.name] = {
            "n": len(rows), "success": sum(bool(r.get("success")) for r in rows),
            "models": sorted({r.get("model", "unknown") for r in rows}),
            "by_arm": {a: {"n": sum(r["arm"] == a for r in rows),
                           "token_rows": sum(r["arm"] == a and bool(r.get("tokens")) for r in rows),
                           "sum_wall_ms": sum(r.get("wall_ms", 0) for r in rows if r["arm"] == a)}
                       for a in {r["arm"] for r in rows}}}
    report["metric_counterexamples"] = {
        "dnf_success_answered_over_one": metrics.dnf_rate([
            {"status": "timeout", "success": True}, {"status": "ok", "success": True}]),
        "missing_output_gets_price": metrics.cost_of_trial({"input": 1000}, {"input": .15, "output": .6}),
        "negative_value_dispersion": metrics.answer_dispersion([
            {"task": "negative", "success": True, "_answer": {"value": -10}},
            {"task": "negative", "success": True, "_answer": {"value": -12}}])}
    report["acceptance"] = {
        "all_valid_fixtures_pass": totals["correct_tested"] == totals["correct_passed"],
        "all_adversarial_probes_rejected": not any(cases.values()),
        "oracles_pass": not report["oracle_failures"],
        "leak_scan_clean": not report["leaks"],
        "solution_expectation_consistent": not report["numeric_consistency"]["mismatches"],
        "independent_source_review_complete": False}
    report["technical_acceptance_pass"] = all(v for k,v in report["acceptance"].items() if k != "independent_source_review_complete")
    (out / "audit-evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (out / "task-sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"splits": report["splits"], "checks": report["checks"],
                      "counterexamples": {k: v["n"] for k, v in report["counterexamples"].items()},
                      "oracle_failures": len(report["oracle_failures"]), "leaks": len(report["leaks"]),
                      "main": {k: v for k, v in report["main"].items() if k != "shared_payload_sets"},
                      "metric_counterexamples": report["metric_counterexamples"], "acceptance":report["acceptance"]}, ensure_ascii=False, indent=2))
    if not report["technical_acceptance_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
