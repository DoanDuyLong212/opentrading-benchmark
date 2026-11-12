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

rsis = {k.split(":")[1]: v["envelope"]["data"]["rsi14"] for k, v in payloads["tools"].items() if k.startswith("tech:")}
low = min(rsis, key=rsis.get)
rows = payloads["tools"]["fd:PVS"]["envelope"]["data"]["rows"]
gp = [r for r in rows if "gộp" in r["name"].lower()][0]["values"][-1]
rev = [r for r in rows if "doanh thu" in r["name"].lower()][0]["values"][-1]
check("symbol", low, gold["solution"]["symbol"])
check("rsi14", rsis[low], gold["solution"]["rsi14"])
check("margin_pct", round(gp / rev * 100, 2), gold["solution"]["margin_pct"])

if problems:
    print("ORACLE MISMATCH — gold KHONG tai tao duoc tu payload:")
    for _p in problems: print(" -", _p)
    sys.exit(2)
print("ORACLE OK — gold tai tao duoc tu payload (%s)" % gold["task_id"])
