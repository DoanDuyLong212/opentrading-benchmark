#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oracle — tái tạo gold từ environment/payloads.json (self-contained)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "environment", "payloads.json"), encoding="utf-8") as _f:
    payloads = json.load(_f)
with open(os.path.join(HERE, "gold.json"), encoding="utf-8") as _f:
    gold = json.load(_f)
problems = []
def check(label, computed, expected):
    def _norm(x):
        if isinstance(x, float): return round(x, 6)
        if isinstance(x, list): return [_norm(i) for i in x]
        return x
    if _norm(computed) != _norm(expected):
        problems.append("%s: computed=%r expected=%r" % (label, computed, expected))

qs = payloads["tools"]["batch:banks1"]["envelope"]["data"]["quotes"]
worst = min(qs, key=lambda q: q["pct"])
lnst = [r for r in payloads["tools"]["fs:TPB"]["envelope"]["data"]["rows"] if r["name"] == "Tổng LNST"][0]["values"]["Q3/2026"] / 1e9
check("symbol", worst["symbol"], gold["solution"]["symbol"])
check("pct_drop", round(worst["pct"], 2), gold["solution"]["pct_drop"])
check("lnst_bn", round(lnst, 2), gold["solution"]["lnst_bn"])

if problems:
    print("ORACLE MISMATCH — gold KHONG tai tao duoc tu payload:")
    for _p in problems: print(" -", _p)
    sys.exit(2)
print("ORACLE OK — gold tai tao duoc tu payload (%s)" % gold["task_id"])
