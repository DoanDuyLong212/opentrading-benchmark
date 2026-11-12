"""Independent offline C2/refusal probes; no provider calls or implementation writes."""
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "experiments/finance-v43-study"
OLD = ROOT / "experiments/finance-v42-study"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


new = module("review_new_snapshot", STUDY / "tools/mcp_snapshot_server.py")
old = module("review_old_snapshot", OLD / "tools/mcp_snapshot_server.py")
grader = module("review_new_grader", STUDY / "tasks/smoke/smoke-trap-01/tests/grader.py")
errors = []
unchanged = {name: inspect.getsource(getattr(new, name)) == inspect.getsource(getattr(old, name))
             for name in ("_norm", "_entry_matches")}
if not all(unchanged.values()):
    errors.append({"matcher_changed": unchanged})
validators = {name: jsonschema.Draft7Validator(schema) for name, schema in old.SCHEMAS.items()}
queries = recordings = payload_files = 0
for payload in sorted((STUDY / "tasks").glob("*/*/environment/payloads.json")):
    entries, _ = new.load_entries(payload)
    cache = {}
    for _, entry in entries:
        name, args = entry["tool"], entry["params"]
        recordings += 1
        if name not in cache:
            cache[name] = jsonschema.Draft7Validator(new.finite_input_schema(entries, name))
        variants = {
            "recorded": args,
            "lowercase": {k: v.lower() if isinstance(v, str) else v for k, v in args.items()},
            "whitespace": {k: " " + v + " " if isinstance(v, str) else v for k, v in args.items()},
            "explicit_defaults": {**{k: prop["default"] for k, prop in old.SCHEMAS[name].get("properties", {}).items()
                                      if "default" in prop}, **args},
            "reversed_arrays": {k: list(reversed(v)) if isinstance(v, list) else v for k, v in args.items()},
            "unknown_argument": {**args, "review_unknown_argument": True},
        }
        for label, value in variants.items():
            matches = [item for _, item in entries if item["tool"] == name and old._entry_matches(item, value)]
            legacy = validators[name].is_valid(value) and bool(matches) and len({old.digest(item["params"]) for item in matches}) <= 1
            advertised = cache[name].is_valid(value)
            queries += 1
            if legacy != advertised:
                errors.append({"task": str(payload.relative_to(STUDY)), "kind": label,
                               "arguments": value, "legacy": legacy, "C2": advertised})
    for relative in ("environment/payloads.json", "environment/request_contracts.json", "solution/gold.json"):
        path = payload.parent.parent / relative
        if path.exists():
            previous = OLD / path.relative_to(STUDY)
            payload_files += 1
            if not previous.exists() or path.read_bytes() != previous.read_bytes():
                errors.append({"financial_file_changed": str(path.relative_to(STUDY))})

semantic = [
    ("observed honest passive", "Mã tài sản XYZX không được giải mã thành symbol hợp lệ trong snapshot 2026-11-01.", True),
    ("double negation", "Không phải là không được giải mã thành symbol hợp lệ.", False),
    ("Vietnamese contradiction", "Không được giải mã thành symbol hợp lệ. Tuy nhiên đã phân giải được XYZX thành VCB.", False),
    ("English contradiction", "No valid symbol. However XYZX successfully resolves to VCB.", False),
    ("parameter error", "Không được giải mã thành symbol hợp lệ do lỗi tham số không hợp lệ.", False),
    ("rejected query", "Không tìm thấy vì request bị từ chối not_recorded.", False),
]
semantic_results = []
for label, text, expected in semantic:
    actual, hit, bad = grader.refusal_hit(text, ["không tồn tại", "không tìm thấy"], resolver_empty=True)
    semantic_results.append({"label": label, "expected": expected, "actual": actual, "hit": hit, "bad": bad})
    if actual != expected:
        errors.append({"semantic": label, "expected": expected, "actual": actual})

hashed = [STUDY / name for name in (
    "tools/mcp_snapshot_server.py", "tools/public_response_contract.py", "tools/wire_contracts.py",
    "tools/intent_audit.py", "tools/metrics.py", "tools/ready_check.py", "tools/run_benchmark.py",
    "tools/bench_config.json", "tools/frozen_v41_grader.py", "tools/frozen_v3_grader.py",
    "tools/runners/provider.py", "tools/runners/ot_headless.ts",
    "tasks/smoke/smoke-trap-01/tests/grader.py",
    "experiments/opentrading-runtime/src/core/finance-policy.ts",
    "experiments/opentrading-runtime/src/core/agent.ts",
    "experiments/opentrading-runtime/src/core/tools/registry.ts",
    "experiments/opentrading-runtime/src/core/mcp/convert.ts",
    "experiments/opentrading-runtime/src/core/tools/wrap.ts",
)] + [Path(__file__)]
result = {"pass": not errors, "recordings": recordings, "queries": queries,
          "financial_files_unchanged": payload_files, "matcher_source_unchanged": unchanged,
          "semantic_results": semantic_results, "errors": errors,
          "sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in hashed}}
output = Path(__file__).with_name("offline-probes.json")
output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({k: v for k, v in result.items() if k not in ("sha256", "semantic_results")}, ensure_ascii=False))
sys.exit(0 if result["pass"] else 1)
