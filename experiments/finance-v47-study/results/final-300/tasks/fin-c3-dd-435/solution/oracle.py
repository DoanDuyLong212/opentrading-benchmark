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
SYMS = ['VHM', 'VIC']
from decimal import Decimal as _D
def _rows(s):
    k = ('idx:' if s in ('VNINDEX', 'VN30') else 'hist:') + s
    return env(k)['data']['closes']
def C(s, back=0): return _D(str(_rows(s)[-1 - back]['c']))
def V(s, back=0): return _D(_rows(s)[-1 - back]['v'])
def MC(s, n): return sum(C(s, i) for i in range(n)) / n
def MV(s, n): return sum(V(s, i) for i in range(n)) / n
def P(s, n): return (C(s) / C(s, n) - 1) * 100
def R(x): return float(round(_D(x), 4))
for _s in SYMS:
    check('rows_' + _s, len(_rows(_s)), 120)
    check('last_' + _s, _rows(_s)[-1]['t'], '2026-10-30')
"""Dated close/return contract, embedded verbatim in generated standalone oracles."""
import datetime
import math
import statistics


def dated_closes(rows, n, end='2026-10-30', calendar=None):
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError('window must contain at least one return')
    dates, values = [], []
    for row in rows:
        day = row['t']
        if not isinstance(day, str) or datetime.date.fromisoformat(day).isoformat() != day:
            raise ValueError('date must be canonical ISO YYYY-MM-DD')
        if dates and day <= dates[-1]:
            raise ValueError('dates must be unique and strictly chronological')
        raw = row['c']
        if isinstance(raw, bool):
            raise ValueError('close must be finite and positive')
        price = float(raw)
        if not math.isfinite(price) or price <= 0:
            raise ValueError('close must be finite and positive')
        dates.append(day)
        values.append(price)
    if len(dates) < n + 1:
        raise ValueError('insufficient closes: need n+1')
    if dates[-1] != end:
        raise ValueError('series must end on declared date')
    if calendar is not None and dates[-n-1:] != list(calendar)[-n-1:]:
        raise ValueError('missing or mismatched date in declared window')
    return list(zip(dates[-n-1:], values[-n-1:]))


def dated_returns(points):
    return [((a[0], b[0]), math.log(b[1] / a[1])) for a, b in zip(points, points[1:])]


def paired_returns(left, right):
    a, b = dated_returns(left), dated_returns(right)
    if len(a) < 2 or len(a) != len(b):
        raise ValueError('at least two paired returns required')
    if [r[0] for r in a] != [r[0] for r in b]:
        raise ValueError('return date intervals must match exactly')
    return [r[1] for r in a], [r[1] for r in b]


def series_corr(left, right):
    a, b = paired_returns(left, right)
    if statistics.variance(a) == 0 or statistics.variance(b) == 0:
        raise ValueError('correlation requires nonzero variance')
    return statistics.correlation(a, b)


def series_beta(left, right):
    a, b = paired_returns(left, right)
    variance = statistics.variance(b)
    if variance == 0:
        raise ValueError('benchmark variance must be nonzero')
    return statistics.covariance(a, b) / variance

_CALENDAR = ['2026-05-13', '2026-05-14', '2026-05-15', '2026-05-18', '2026-05-19', '2026-05-20', '2026-05-21', '2026-05-22', '2026-05-25', '2026-05-26', '2026-05-27', '2026-05-28', '2026-05-29', '2026-06-01', '2026-06-02', '2026-06-03', '2026-06-04', '2026-06-05', '2026-06-08', '2026-06-09', '2026-06-10', '2026-06-11', '2026-06-12', '2026-06-15', '2026-06-16', '2026-06-17', '2026-06-18', '2026-06-19', '2026-06-22', '2026-06-23', '2026-06-24', '2026-06-25', '2026-06-26', '2026-06-29', '2026-06-30', '2026-07-01', '2026-07-02', '2026-07-03', '2026-07-06', '2026-07-07', '2026-07-08', '2026-07-09', '2026-07-10', '2026-07-13', '2026-07-14', '2026-07-15', '2026-07-16', '2026-07-17', '2026-07-20', '2026-07-21', '2026-07-22', '2026-07-23', '2026-07-24', '2026-07-27', '2026-07-28', '2026-07-29', '2026-07-30', '2026-07-31', '2026-08-03', '2026-08-04', '2026-08-05', '2026-08-06', '2026-08-07', '2026-08-10', '2026-08-11', '2026-08-12', '2026-08-13', '2026-08-14', '2026-08-17', '2026-08-18', '2026-08-19', '2026-08-20', '2026-08-21', '2026-08-24', '2026-08-25', '2026-08-26', '2026-08-27', '2026-08-28', '2026-09-03', '2026-09-04', '2026-09-07', '2026-09-08', '2026-09-09', '2026-09-10', '2026-09-11', '2026-09-14', '2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18', '2026-09-21', '2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25', '2026-09-28', '2026-09-29', '2026-09-30', '2026-10-01', '2026-10-02', '2026-10-05', '2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-19', '2026-10-20', '2026-10-21', '2026-10-22', '2026-10-23', '2026-10-26', '2026-10-27', '2026-10-28', '2026-10-29', '2026-10-30']

import statistics as _st
def _points(s, n): return dated_closes(_rows(s), n, calendar=_CALENDAR)
def _cl(s, n): return [p for d, p in _points(s, n)]
def _lr(s, n): return [v for interval, v in dated_returns(_points(s, n))]
def VOL(s, n): return _st.stdev(_lr(s, n)) * math.sqrt(250) * 100
def DD(s, n):
    peak, worst = -1.0, 0.0
    for p in _cl(s, n):
        peak = max(peak, p); worst = min(worst, p / peak - 1)
    return worst * 100
def CORR(a, b, n): return series_corr(_points(a, n), _points(b, n))
def BETA(a, n): return series_beta(_points(a, n), _points('VNINDEX', n))
check('dd_VIC', R(DD('VIC', 119)), gold['solution']['VIC'])
check('dd_VHM', R(DD('VHM', 119)), gold['solution']['VHM'])


if problems:
    print("ORACLE MISMATCH:")
    [print(" -", p) for p in problems]
    sys.exit(2)
print("ORACLE OK — %s" % gold["task_id"])
