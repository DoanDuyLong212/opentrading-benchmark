#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oracle — tái tạo gold từ environment/payloads.json (self-contained, chưa hiệu chỉnh)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
payloads = json.load(open(os.path.join(HERE, "..", "environment", "payloads.json"), encoding="utf-8"))
gold = json.load(open(os.path.join(HERE, "gold.json"), encoding="utf-8"))
problems = []
def check(label, computed, expected):
    def _norm(x):
        if isinstance(x, float): return round(x, 4)
        if isinstance(x, dict): return {k: _norm(v) for k, v in sorted(x.items())}
        if isinstance(x, list): return [_norm(i) for i in x]
        return x
    if _norm(computed) != _norm(expected):
        problems.append("%s: computed=%r expected=%r" % (label, computed, expected))

rows = payloads["tools"]["peer:cons_p"]["envelope"]["data"]["rows"]
roe = {r["symbol"]: r["roe"] for r in rows}
check("set", sorted(s for s, v in roe.items() if v > 10), gold["solution"]["set"])

if problems:
    print("ORACLE MISMATCH — gold KHONG tai tao duoc tu payload:")
    for _p in problems: print(" -", _p)
    sys.exit(2)
print("ORACLE OK — gold tai tao duoc tu payload (%s)" % gold["task_id"])
