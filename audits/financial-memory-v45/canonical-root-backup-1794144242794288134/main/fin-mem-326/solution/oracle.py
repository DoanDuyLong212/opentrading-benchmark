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

lnst = {}
for k, v in payloads["tools"].items():
    if k.startswith("fs:"):
        rows = v["envelope"]["data"]["rows"]
        last_p = v["envelope"]["data"]["periods"][-1]  # quý gần nhất CỦA TỪNG MÃ (HDB trễ kỳ → Q2/2026)
        row = [r for r in rows if r["name"] == "Tổng LNST"][0]
        lnst[k.split(":")[1]] = row["values"][last_p] / 1e9
pe = {r["symbol"]: r["p_e"] for r in payloads["tools"]["peer:banks_p"]["envelope"]["data"]["rows"]}
check("highest_lnst", max(lnst, key=lnst.get), gold["solution"]["highest_lnst"])
check("lowest_pe", min(pe, key=pe.get), gold["solution"]["lowest_pe"])

if problems:
    print("ORACLE MISMATCH — gold KHONG tai tao duoc tu payload:")
    for _p in problems: print(" -", _p)
    sys.exit(2)
print("ORACLE OK — gold tai tao duoc tu payload (%s)" % gold["task_id"])
