#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oracle — tái tạo gold từ environment/payloads.json rồi đối chiếu solution/gold.json.

Exit 0 : gold tái tạo được từ payload (payload ⇄ gold khớp).
Exit 2 : lệch — KHÔNG dùng gold này; kiểm tra lại payload/gold.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "environment", "payloads.json"), encoding="utf-8") as _f:
    payloads = json.load(_f)
with open(os.path.join(HERE, "gold.json"), encoding="utf-8") as _f:
    gold = json.load(_f)

problems = []


def check(label, computed, expected):
    def _norm(x):
        if isinstance(x, float):
            return round(x, 6)
        if isinstance(x, list):
            return [_norm(i) for i in x]
        return x
    if _norm(computed) != _norm(expected):
        problems.append("%s: computed=%r expected=%r" % (label, computed, expected))


def env(name):
    return payloads["tools"][name]


items = env("yf_commodities")["data"]["items"]
pc = {i["ticker"]: (i["price"] / i["prev"] - 1) * 100 for i in items}
check("gold_pct", round(pc["GC=F"], 2), gold["solution"]["gold_pct"])
check("oil_pct", round(pc["CL=F"], 2), gold["solution"]["oil_pct"])
check("btc_pct", round(pc["BTC-USD"], 2), gold["solution"]["btc_pct"])
check("winner", max(pc, key=pc.get), gold["solution"]["winner"])

if problems:
    print("ORACLE MISMATCH — gold KHONG tai tao duoc tu payload:")
    for _p in problems:
        print(" -", _p)
    sys.exit(2)
print("ORACLE OK — gold tai tao duoc tu payload (%s)" % gold["task_id"])
