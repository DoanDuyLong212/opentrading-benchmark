"""Guarded batch-3 memory sync: study → canonical root.

- THÊM MỚI: main fin-mem-332..349 (18) + holdout fin-mem-960..969 (10).
- HARMONIZE: grader 320..331 + p01 (1f06 → 6a67) — chỉ file tests/grader.py được phép đổi.
- BẢO VỆ: base 200 MAIN + 50 holdout nonmemory bất biến; batch-1 task trees khác study
  bất kỳ ngoài grader ⇒ chặn; destination mới phải chưa tồn tại; before-map guard +
  backup + receipt. Holdout payload = chính batch-3 tasks (không đọc holdout ngoài phạm vi).
"""
import argparse, hashlib, json, shutil, time
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def tree(d):
    return {str(p.relative_to(d)): sha(p) for p in sorted(d.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


NEW = [("main", f"fin-mem-{i}") for i in range(332, 350)] + \
      [("holdout", f"fin-mem-{i}") for i in range(960, 970)]
UPD = [("main", f"fin-mem-{i}") for i in range(320, 332)] + [("pilot", "fin-mem-p01")]
AUDIT_DIR = ROOT / "audits" / "financial-memory-v45-batch3"


def base_tree(split):
    return {p.name: tree(p) for p in sorted((ROOT / "tasks" / split).iterdir())
            if p.is_dir() and not p.name.startswith("fin-mem-")}


def apply(review_path, execute=False):
    review = Path(review_path)
    r = json.loads(review.read_text())
    audit_path = AUDIT_DIR / "corpus-audit.json"
    a = json.loads(audit_path.read_text())
    if not r.get("independent_review_pass") or r.get("corpus_audit_sha256") != sha(audit_path) or not a.get("pass"):
        raise ValueError("Independent offline approval must bind the current batch-3 memory corpus audit")
    rows = {row["task"]: row for row in a["rows"]}
    # 1) study trees phải khớp audit
    for split, tid in NEW + UPD:
        d = STUDY / "tasks" / split / tid
        if tree(d) != rows[tid]["task_tree"]:
            raise ValueError("Audited study task changed: " + tid)
    # 2) destinations
    for split, tid in NEW:
        if (ROOT / "tasks" / split / tid).exists():
            raise ValueError("New destination exists; preserve user content: " + tid)
    for split, tid in UPD:
        dest = ROOT / "tasks" / split / tid
        src = STUDY / "tasks" / split / tid
        if not dest.exists():
            raise ValueError("Expected existing destination: " + tid)
        dd, ds = tree(dest), tree(src)
        if set(dd) != set(ds):
            raise ValueError("Unexpected file-set change (no overwrite): " + tid)
        changed = {k for k in dd if dd[k] != ds[k]}
        if changed - {"tests/grader.py"}:
            raise ValueError("Only grader harmonization allowed; user changes detected: %s %r" % (tid, sorted(changed)))
    # 3) bases bất biến
    old200 = base_tree("main")
    old_hold = base_tree("holdout")
    if len(old200) != 200:
        raise ValueError("Expected exactly 200 retained nonmemory MAIN tasks")
    if len(old_hold) != 50:
        raise ValueError("Expected exactly 50 retained nonmemory HOLDOUT tasks")
    # 4) before-map guard
    before_path = AUDIT_DIR / "MEMORY-ROOT-BEFORE-batch3.json"
    if execute:
        before = json.loads(before_path.read_text())
        for rel, expected in before["updated_dest_files"].items():
            p = ROOT / rel
            if not p.exists() or sha(p) != expected:
                raise ValueError("User changes detected; no overwrite: " + rel)
    else:
        before = {
            "updated_dest_files": {str(p.relative_to(ROOT)): sha(p) for split, tid in UPD
                                   for p in sorted((ROOT / "tasks" / split / tid).rglob("*"))
                                   if p.is_file() and "__pycache__" not in p.parts},
            "base200": {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for k, v in old200.items()},
            "base_holdout": {k: hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for k, v in old_hold.items()},
        }
        before_path.write_text(json.dumps(before, indent=1) + "\n")
    result = {
        "schema": "guarded-memory-only-sync-v45-batch3", "dry_run": not execute,
        "main_before": 212, "main_after": 230, "holdout_before": 50, "holdout_after": 60, "pilot_after": 25,
        "new_tasks": len(NEW), "updated_tasks": len(UPD),
        "holdout_access": "batch-3 holdout tasks ARE the sync payload (no external holdout inspection)",
        "review_sha256": sha(review), "audit_sha256": sha(audit_path),
        "base200_sha256": hashlib.sha256(json.dumps(before["base200"], sort_keys=True).encode()).hexdigest(),
        "base_holdout_sha256": hashlib.sha256(json.dumps(before["base_holdout"], sort_keys=True).encode()).hexdigest(),
    }
    if execute:
        backup = AUDIT_DIR / ("canonical-root-backup-" + str(time.time_ns()))
        backup.mkdir()
        for split, tid in UPD:
            dest = ROOT / "tasks" / split / tid
            if dest.exists():
                shutil.copytree(dest, backup / split / tid)
        for split, tid in NEW + UPD:
            source = STUDY / "tasks" / split / tid
            dest = ROOT / "tasks" / split / tid
            dest.mkdir(parents=True, exist_ok=True)
            for p in sorted(source.rglob("*")):
                if not p.is_file() or "__pycache__" in p.parts:
                    continue
                target = dest / p.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                temp = target.with_name(target.name + ".v45-sync-tmp")
                temp.write_bytes(p.read_bytes())
                temp.replace(target)
        # post-checks
        if base_tree("main") != old200:
            raise RuntimeError("Unexpected base200 mutation")
        if base_tree("holdout") != old_hold:
            raise RuntimeError("Unexpected base holdout mutation")
        n_main = sum(1 for p in (ROOT / "tasks" / "main").iterdir() if p.is_dir())
        n_hold = sum(1 for p in (ROOT / "tasks" / "holdout").iterdir() if p.is_dir())
        n_pilot = sum(1 for p in (ROOT / "tasks" / "pilot").iterdir() if p.is_dir())
        if n_main != 230 or n_hold != 60 or n_pilot != 25:
            raise RuntimeError("Unexpected counts main=%d holdout=%d pilot=%d" % (n_main, n_hold, n_pilot))
        for split, tid in NEW + UPD:
            if tree(ROOT / "tasks" / split / tid) != tree(STUDY / "tasks" / split / tid):
                raise RuntimeError("Post-sync tree mismatch: " + tid)
        result["counts"] = {"main": n_main, "holdout": n_hold, "pilot": n_pilot}
        result["backup"] = str(backup)
        (backup / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", required=True)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    print(json.dumps(apply(args.review, args.execute), indent=2))
