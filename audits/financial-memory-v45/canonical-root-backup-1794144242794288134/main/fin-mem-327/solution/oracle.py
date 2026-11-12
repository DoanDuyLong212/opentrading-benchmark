#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oracle — tái tạo gold từ environment/payloads.json (self-contained)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
payloads = json.load(open(os.path.join(HERE, "..", "environment", "payloads.json"), encoding="utf-8"))
gold = json.load(open(os.path.join(HERE, "gold.json"), encoding="utf-8"))
problems = []
def check(label, computed, expected):
    def _norm(x):
        if isinstance(x, float): return round(x, 6)
        if isinstance(x, list): return [_norm(i) for i in x]
        return x
    if _norm(computed) != _norm(expected):
        problems.append("%s: computed=%r expected=%r" % (label, computed, expected))

tot = 0.0
for k, v in payloads["tools"].items():
    row = [r for r in v["envelope"]["data"]["rows"] if "doanh thu" in r["name"].lower()][0]
    tot += row["values"]["Q3/2026"] / 1e9
check("total_bn", round(tot, 2), gold["solution"]["total_bn"])

if problems:
    print("ORACLE MISMATCH — gold KHONG tai tao duoc tu payload:")
    for _p in problems: print(" -", _p)
    sys.exit(2)
print("ORACLE OK — gold tai tao duoc tu payload (%s)" % gold["task_id"])
