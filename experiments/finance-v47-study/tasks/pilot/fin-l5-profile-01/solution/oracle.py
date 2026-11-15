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


d = env("financial_detail")["data"]
p = env("stock_overview")["data"]["trading"]
i = d["periods"].index("Q3/2026")
dt = next(r for r in d["rows"] if "Doanh thu thuần" in r["name"])["values"][i]
ln = next(r for r in d["rows"] if "Lợi nhuận gộp" in r["name"])["values"][i]
check("revenue_bn", float(dt), gold["solution"]["revenue_q3_bn"])
check("gross_bn", float(ln), gold["solution"]["gross_profit_q3_bn"])
check("margin", round(ln / dt * 100, 2), gold["solution"]["gross_margin_pct"])
check("pe", float(p["PE"]), gold["solution"]["pe"])
check("mcap_bn", round(p["MarketCapital"] / 1e9, 2), gold["solution"]["market_cap_bn"])

if problems:
    print("ORACLE MISMATCH — gold KHONG tai tao duoc tu payload:")
    for _p in problems:
        print(" -", _p)
    sys.exit(2)
print("ORACLE OK — gold tai tao duoc tu payload (%s)" % gold["task_id"])
