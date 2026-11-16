"""Development inference is restricted to physical, lineage-bound devsmoke copies."""
import hashlib
import json
import os
import re
from pathlib import Path


def enabled():
    return os.environ.get("BENCH_V47_DEV") == "1"


def require_dev_split(split):
    if enabled() and split != "devsmoke":
        raise ValueError("BENCH_V47_DEV permits devsmoke only; pilot/main/holdout require authorization without the development bypass")


def tree_hash(task):
    files = {str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(task.rglob("*")) if p.is_file()
             and p.name != "development-lineage.json" and "__pycache__" not in p.parts
             and p.suffix != ".pyc"}
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()


def validate_dev_task(root, task):
    root, task = Path(root).absolute(), Path(task).absolute()
    expected = root / "tasks" / "devsmoke"
    if task.parent != expected or not task.name or task.name in (".", ".."):
        raise ValueError("Development task must be a direct devsmoke copy")
    # Reject links even when they currently resolve inside devsmoke: aliases hide lineage.
    for path in [root / "tasks", expected, task, *task.rglob("*")]:
        if path.is_symlink():
            raise ValueError("Development task symlink/alias forbidden: " + str(path))
    if task.resolve().parent != expected.resolve():
        raise ValueError("Development task escapes devsmoke")
    lineage = json.loads((task / "development-lineage.json").read_text())
    if (lineage.get("origin_split") not in ("main", "devsmoke")
            or not isinstance(lineage.get("origin_task_id"), str)
            or Path(lineage["origin_task_id"]).name != lineage["origin_task_id"]
            or lineage["origin_task_id"] in ("", ".", "..")
            or not lineage.get("reason")
            or not isinstance(lineage.get("origin_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", lineage["origin_sha256"])
            or lineage.get("copy_sha256") != tree_hash(task)):
        raise ValueError("Development task lineage missing, invalid, or changed: " + task.name)
    return lineage
