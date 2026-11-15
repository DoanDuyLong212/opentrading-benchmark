#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oracle — tái tạo gold từ environment/payloads.json (self-contained)."""
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
    t = payloads["tools"][name]
    return t["envelope"] if isinstance(t, dict) and "envelope" in t else t


# === fam_util (inline) ===
# -*- coding: utf-8 -*-
"""fam_util.py — helper dùng chung cho các họ task (families).

Quy ước:
- env: dict payload_key -> body envelope (đã recorded).
- Mọi builder trả về dict task spec: title/q_md/schema_md/rules_md/scoring/expects|refusal.../solution/oracle.
- oracle: chuỗi code Python (thân) dùng các hàm check()/env() của ORACLE_HEAD — chạy được trong solution/oracle.py.
"""

UNITS = {
    "nghin_dong": ["nghìn đồng", "nghìn đ", "k đồng"],
    "ty_dong": ["tỷ đồng", "tỷ đ", "tỷ"],
    "trieu_dong": ["triệu đồng", "triệu đ"],
    "dong": ["đồng", "VND"],
    "usd": ["USD", "USDT"],
    "usd_oz": ["USD/oz", "USD oz"],
    "pct": ["%", "phần trăm"],
    "x": ["x", "lần"],
    "diem": ["điểm"],
}


def p30():
    return ["30/10", "30-10", "30.10", "2026-10-30"]


def pday(day):
    """tokens kỳ cho '29/10' | '30/10' | '01/11' ..."""
    d, m = day.split("/")
    return [day, day.replace("/", "-"), day.replace("/", "."), "2026-%s-%s" % (m, d)]


def pmonth(period):
    """'2026-09' -> tokens tháng 9/2026."""
    y, m = period.split("-")
    m = str(int(m))
    return ["tháng %s/%s" % (m, y), "%s/%s" % (m, y), "tháng %s" % m, "t%s/%s" % (m, y)]


def pq(q):
    """'Q3/2026' -> tokens."""
    n, y = q[1:].split("/")
    return [q, "quý %s/%s" % (n, y), "q%s %s" % (n, y), "q%s/%s" % (n, y[2:])]


def pq2(qa, qb):
    """two-quarter period 'Q3/2026 so với Q2/2026'."""
    return pq(qa) + ["so với"] + pq(qb)


def nextq(q):
    """'Q3/2026' -> 'Q4/2026'; 'Q4/2026' -> 'Q1/2027'."""
    n, y = q[1:].split("/")
    n, y = int(n), int(y)
    n2, y2 = (n + 1, y) if n < 4 else (1, y + 1)
    return "Q%d/%d" % (n2, y2)


def r2(x):
    return round(float(x) + 0.0, 2)


def val_check(gold, rel=0.005):
    return {"type": "value", "path": "value", "gold": gold, "tol": {"rel": rel}}


def val_check_abs(gold, abs_=0.1):
    return {"type": "value", "path": "value", "gold": gold, "tol": {"abs": abs_}}


def unit_check(keys):
    return {"type": "unit", "path": "unit", "accept": UNITS[keys]}


def period_check(tokens):
    return {"type": "period", "path": "period", "accept": tokens}


def src_check(*tokens):
    if len(tokens) == 1:
        return {"type": "str", "path": "source", "accept": list(tokens)}
    return {"type": "str_all", "path": "source", "accept": list(tokens)}


def evnum(numbers, min_hits=1, strings=()):
    return {"type": "evidence", "path": "note", "paths": ["note"], "numbers": list(numbers),
            "strings": list(strings), "min_hits": min_hits}


# --- tìm dòng trong bảng tài chính ---
def find_row(rows, pattern):
    import re
    for r in rows:
        if re.search(pattern, r["name"], re.IGNORECASE):
            return r
    return None


def fs_find(env_body, patterns):
    """trả về list (name, values-dict, unit) theo thứ tự patterns (mỗi pattern 1 dòng)."""
    rows = env_body["data"]["rows"]
    out = []
    for p in patterns:
        r = find_row(rows, p)
        out.append(r)
    return out


def units_str(k):
    return UNITS[k]


GF_UNIT = {
    "XAUUSD": ("usd_oz", "USD/oz"),
    "XAGUSD": ("usd_oz", "USD/oz"),
    "USDVND": ("dong", "đồng"),
    "EURVND": ("dong", "đồng"),
    "JPYVND": ("dong", "đồng"),
    "KRWVND": ("dong", "đồng"),
    "GBPUSD": ("usd", "USD"),
    "EURUSD": ("usd", "USD"),
    "USDJPY": ("jpy", "JPY"),
    "USDCNY": ("cny", "CNY"),
}
UNITS["jpy"] = ["JPY", "yên", "JPY/USD"]
UNITS["cny"] = ["CNY", "nhân dân tệ", "NDT"]


def _body(env_like, key):
    """Nhận 3 dạng: dict keyed (build), hàm env(name) (oracle), hoặc body envelope trực tiếp."""
    x = env_like
    if callable(x):
        x = x(key)
    if isinstance(x, dict) and "data" not in x and "envelope" not in x and key in x:
        x = x[key]
    if isinstance(x, dict) and "envelope" in x:
        x = x["envelope"]
    return x


def msn_series(env):
    return {x["symbol"]: x["closes"] for x in _body(env, "msn:main")["data"]["series"]}


def yf_item(env, ticker):
    for i in _body(env, "yf:main")["data"]["items"]:
        if i["ticker"] == ticker:
            return i
    return None


def cpi_rows(env):
    return _body(env, "cpi:full")["data"]["rows"]


def cpi_pick(env, name, period, kind):
    """kind: 'pct' (v<20) | 'index' (v>20). period dạng '2026-09'."""
    y, m = period.split("-")
    pv = "Tháng %d/%s" % (int(m), y)
    for r in cpi_rows(env):
        if r["n"] == name and r["p"] == pv:
            v = float(r["v"])
            if (kind == "pct" and v < 20) or (kind == "index" and v > 20):
                return v
    raise KeyError("cpi_pick miss: %s %s %s" % (name, period, kind))


def gdp_pick(env, period):
    n, y = period[1:].split("/")
    want = "Quý %s/%s" % (n, y)
    for r in _body(env, "gdp:full")["data"]["total"]:
        if r["p"] == want:
            return float(r["v"])
    raise KeyError("gdp_pick miss: %s" % period)


# === thân oracle ===
d = env('fs:PNJ')["data"]
dt = next(r for r in d["rows"] if "Doanh thu thuần" in r["name"])
ps = d["periods"]
check("growth", round((dt["values"][ps[-1]] / dt["values"][ps[-2]] - 1) * 100, 2), gold["solution"]["value"])

if problems:
    print("ORACLE MISMATCH:")
    [print(" -", p) for p in problems]
    sys.exit(2)
print("ORACLE OK — %s" % gold["task_id"])
