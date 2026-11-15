"""Fresh batch-3 memory-corpus audit (union: main 320-349 + pilot + memorydev + holdout 960-969).

Kế thừa validate_task của audit_v45_memory_corpus (batch-1) — KHÔNG sửa tool cũ.
Mở rộng scope: holdout fin-mem-960..969 + graders đã harmonize về bản chuẩn 6a67.
"""
import argparse, json
from pathlib import Path
import audit_v45_memory_corpus as base

STUDY = Path(__file__).resolve().parents[1]


def task_dirs():
    return ([*sorted((STUDY / "tasks/main").glob("fin-mem-*"))]
            + [*sorted((STUDY / "tasks/pilot").glob("fin-mem-*"))]
            + [*sorted((STUDY / "tasks/memorydev").glob("*"))]
            + [*sorted((STUDY / "tasks/holdout").glob("fin-mem-*"))])


def audit():
    rows = [base.validate_task(d) for d in task_dirs()]
    main_count = len(list((STUDY / "tasks/main").glob("*/task.toml")))
    return {
        "schema": "memory-corpus-audit-v45-batch3",
        "pass": all(r["pass"] for r in rows) and main_count <= 250,
        "main_total": main_count, "main_cap": 250,
        "memory_tasks": len(rows), "external_model_calls": 0,
        "scope": ("Oracle consistency, explicit operation source binding and construct inventory "
                  "(batch-3 union incl. holdout 960-969; graders harmonized to 6a67 standard). "
                  "Not external source authenticity or learned/persistent memory efficacy."),
        "rows": rows,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    result = audit()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}))
    raise SystemExit(0 if result["pass"] else 1)
