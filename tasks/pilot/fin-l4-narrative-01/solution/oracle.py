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


ser = {x["symbol"]: [p["c"] for p in x["closes"]] for x in env("vn_msn_fx_gold")["data"]["series"]}
xau, usd = ser["XAUUSD"], ser["USDVND"]
check("xau_not_increasing", all(xau[i + 1] > xau[i] for i in range(len(xau) - 1)), False)
check("usd_not_increasing", all(usd[i + 1] > usd[i] for i in range(len(usd) - 1)), False)
check("verdict", "sai", gold["solution"]["verdict"])

if problems:
    print("ORACLE MISMATCH — gold KHONG tai tao duoc tu payload:")
    for _p in problems:
        print(" -", _p)
    sys.exit(2)
print("ORACLE OK — gold tai tao duoc tu payload (%s)" % gold["task_id"])
