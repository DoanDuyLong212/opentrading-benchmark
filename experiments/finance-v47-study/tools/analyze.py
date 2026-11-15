#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analyze.py — phân tích metric A1–A4 + B1–B6 cho MỘT results dir (cũ hoặc mới).

Cách dùng:
    python3 tools/analyze.py results/smoke3_20261103 [--json]
Ghi summary.json vào results dir (nếu chưa có) và in dashboard.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import metrics  # noqa: E402


def main():
    if len(sys.argv) < 2 or not os.path.isdir(sys.argv[1]):
        print("Cách dùng: python3 tools/analyze.py <results-dir> [--json]")
        sys.exit(2)
    out = os.path.abspath(sys.argv[1])
    summary = metrics.build_summary(out)
    spath = os.path.join(out, "summary.json")
    with open(spath, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    if "--json" in sys.argv:
        print(json.dumps(summary, ensure_ascii=False, indent=1))
    else:
        print("analyze: %s (model=%s, n=%d)" % (out, summary["model"], summary["n_trials"]))
        metrics.print_summary(summary)
    print("summary.json: %s" % spath)


if __name__ == "__main__":
    main()
