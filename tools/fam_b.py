# -*- coding: utf-8 -*-
"""fam_b.py — builders cho 14 họ task L3–L5."""
import re
from fam_util import (UNITS, p30, pday, pmonth, pq, pq2, nextq, r2, val_check, val_check_abs,
                      unit_check, period_check, src_check, evnum, fs_find, GF_UNIT,
                      msn_series, yf_item, cpi_pick, gdp_pick)
from fam_a import MACRO_CPI, MACRO_LABEL, SCHEMA_UNIT
from build_plan import GROUPS, PEER_GROUPS

SCHEMA_REFUSAL = '{\n  "value": null,\n  "reason": "lý do (nếu không trả lời được)",\n  "period": "%s",\n  "source": "%s",\n  "note": "kỳ có số mới nhất (nếu nêu)"\n}'
SCHEMA_VERDICT = '{\n  "verdict": "đúng hoặc sai",\n  "period": "%s",\n  "source": "%s",\n  "note": "số liệu chứng minh"\n}'

TICK_ACCEPT = {
    "GC=F": ["GC=F", "vàng", "gold"], "SI=F": ["SI=F", "bạc", "silver"],
    "CL=F": ["CL=F", "dầu", "WTI", "crude"], "BZ=F": ["BZ=F", "Brent"],
    "NG=F": ["NG=F", "khí", "natural gas", "gas"], "HG=F": ["HG=F", "đồng", "copper"],
    "BTC-USD": ["BTC-USD", "BTC", "bitcoin"], "ETH-USD": ["ETH-USD", "ETH", "ethereum"],
    "SOL-USD": ["SOL-USD", "SOL", "solana"], "BNB-USD": ["BNB-USD", "BNB"],
}


# ---------------------------------------------------------------- L3
def f_l3_agg(t, env):
    k = t["payloads"][0]; g = t["params"]["group"]; syms = GROUPS[g]
    qs = {q["symbol"]: q for q in env[k]["data"]["quotes"]}
    vals = {s: float(qs[s]["close"]) for s in syms}
    mean = r2(sum(vals.values()) / len(vals))
    lines = ", ".join(syms)
    schema = ('{\n  "values": {' + ", ".join('"%s": 0' % s for s in syms) + ', "mean": 0},\n'
              '  "unit": "đồng",\n  "period": "phiên 30/10/2026",\n  "source": "vn_equity_quote_batch",\n  "note": "(tuỳ chọn)"\n}')
    expects = [{"type": "value", "path": "values.%s" % s, "gold": vals[s], "tol": {"rel": 0.005}} for s in syms]
    expects += [{"type": "value", "path": "values.mean", "gold": mean, "tol": {"rel": 0.005}},
                unit_check("dong"), period_check(p30()), src_check("vn_equity_quote_batch")]
    oracle = ('q = {x["symbol"]: x["close"] for x in env(%r)["data"]["quotes"]}\n'
              'vals = [float(q[s]) for s in %r]\n'
              'check("mean", round(sum(vals) / len(vals), 2), gold["solution"]["mean"])\n'
              'for s, v in zip(%r, vals):\n    check(s, v, gold["solution"][s])\n') % (k, syms, syms)
    return {"title": "Bảng giá nhóm %s" % g, "family_code": "L3·B aggregate", "fb": "aggregation",
            "q": "Cho 5 mã **%s**: giá đóng cửa **phiên 30/10** của từng mã (theo **đồng**) và **trung bình** 5 mã là bao nhiêu?" % lines,
            "schema": schema, "rules": "", "scoring": "value",
            "expects": expects, "solution": dict(vals, mean=mean), "oracle": oracle}


SCREEN_FILTERS = [
    ("ROE > 15% và P/E < 15", "roe > 15 and pe < 15"),
    ("ROE > 12% và P/E < 15", "roe > 12 and pe < 15"),
    ("P/B < 1.5", "pb < 1.5"),
    ("P/E < 12", "pe < 12"),
    ("ROE > 20%", "roe > 20"),
]


def f_l3_screen(t, env):
    k = t["payloads"][0]; g = t["params"]["group"]
    rows = env[k]["data"]["rows"]
    def rr(x):
        return {r["symbol"]: r for r in rows}[x]
    chosen = None
    for label, expr in SCREEN_FILTERS:
        sel = sorted(s for s in [r["symbol"] for r in rows]
                     if eval(expr, {}, {s2: rr(s2)["p_e"] for s2 in [r["symbol"] for r in rows]}.copy() if False else
                             {s2: None for s2 in []} | {} | {}) ) if False else None
        # (dùng vòng lặp tường minh bên dưới)
        sel = []
        for r in rows:
            pe, pb, roe = r["p_e"], r["p_b"], r["roe"]
            if eval(expr):
                sel.append(r["symbol"])
        sel = sorted(sel)
        if 1 <= len(sel) <= len(rows) - 1:
            chosen = (label, expr, sel)
            break
    assert chosen, "screen: không filter nào hợp lệ cho %s" % g
    label, expr, sel = chosen
    head, peers = PEER_GROUPS[g]
    members = [head] + peers
    schema = '{\n  "values": {"pass": [' + ", ".join('"%s"' % s for s in sel) + ']},\n  "period": "2025",\n  "source": "peer_compare",\n  "note": "P/E, P/B, ROE từng mã để lọc"\n}'
    oracle = ('rows = env(%r)["data"]["rows"]\n'
              'sel = []\n'
              'for r in rows:\n'
              '    pe = r["p_e"]; pb = r["p_b"]; roe = r["roe"]\n'
              '    if %s:\n        sel.append(r["symbol"])\n'
              'check("screen", sorted(sel), gold["solution"]["pass"])\n') % (k, expr)
    return {"title": "Sàng lọc nhóm %s" % g, "family_code": "L3·A screen", "fb": "screening/filtering",
            "q": "Trong 5 mã **%s**: dùng số liệu P/E, P/B và ROE từ **`peer_compare`** — mã nào thỏa **%s**? Trả danh sách mã." % (", ".join(members), label),
            "schema": schema,
            "rules": "- Chỉ dùng số liệu `peer_compare` trả về (kỳ do tool cung cấp).", "scoring": "value",
            "expects": [{"type": "set", "path": "values.pass", "gold": sel},
                        period_check(["2025"]), src_check("peer_compare")],
            "solution": {"pass": sel, "filter": label}, "oracle": oracle}


def _movers(env):
    return env["movers:vn30"]["data"]


def f_l3_top(t, env):
    k = t["params"]["kind"]; d = _movers(env)
    L = {"gainers": d["gainers"], "losers": d["losers"], "volume": d["volume_leaders"]}
    if k in ("gainers3", "losers3", "volume3"):
        which = k[:-1]; n = 3
        rows = L[which][:3]
        if which == "volume":
            cont = '"%d": {"symbol": "MÃ", "vol": 0, "close": 0}'
            schema = '{\n  "values": {\n    ' + ",\n    ".join(cont % i for i in range(1, 4)) + '\n  },\n  "period": "phiên 30/10/2026",\n  "source": "market_movers",\n  "note": "(tuỳ chọn)"\n}'
            expects = []
            for i, r in enumerate(rows, 1):
                expects += [{"type": "str", "path": "values.%d.symbol" % i, "accept": [r["symbol"]]},
                            {"type": "value", "path": "values.%d.vol" % i, "gold": float(r["vol"]), "tol": {"rel": 0.005}},
                            {"type": "value", "path": "values.%d.close" % i, "gold": float(r["close"]), "tol": {"rel": 0.005}}]
            q = "**Top 3 mã có khối lượng khớp lệnh lớn nhất** phiên gần nhất trong rổ **VN30** là những mã nào? Kèm khối lượng và giá đóng cửa (đồng)."
        else:
            cont = '"%d": {"symbol": "MÃ", "pct": 0, "close": 0}'
            schema = '{\n  "values": {\n    ' + ",\n    ".join(cont % i for i in range(1, 4)) + '\n  },\n  "period": "phiên 30/10/2026",\n  "source": "market_movers",\n  "note": "(tuỳ chọn)"\n}'
            expects = []
            for i, r in enumerate(rows, 1):
                expects += [{"type": "str", "path": "values.%d.symbol" % i, "accept": [r["symbol"]]},
                            {"type": "value", "path": "values.%d.pct" % i, "gold": r2(r["pct"]), "tol": {"abs": 0.05}},
                            {"type": "value", "path": "values.%d.close" % i, "gold": float(r["close"]), "tol": {"rel": 0.005}}]
            q = "**Top 3 mã %s mạnh nhất** phiên gần nhất trong rổ **VN30** (theo %% thay đổi) là những mã nào? Kèm %% và giá đóng cửa (đồng), theo đúng thứ hạng." % ("tăng" if which == "gainers" else "giảm")
        expects += [period_check(p30()), src_check("market_movers")]
        sol = {str(i): {"symbol": r["symbol"], "pct": r2(r["pct"]), "close": float(r["close"]),
                        **({"vol": float(r["vol"])} if which == "volume" else {})} for i, r in enumerate(rows, 1)}
        oracle = ('rows = env("movers:vn30")["data"][%r][:3]\n'
                  'for i, r in enumerate(rows, 1):\n'
                  '    s = gold["solution"][str(i)]\n'
                  '    check("sym%%d" %% i, r["symbol"], s["symbol"])\n'
                  '    check("close%%d" %% i, float(r["close"]), s["close"])\n') % ("gainers" if which == "gainers" else ("losers" if which == "losers" else "volume_leaders"))
        return {"title": "Top 3 VN30 (%s)" % which, "family_code": "L3·C movers", "fb": "ranking extraction",
                "q": q, "schema": schema, "rules": "- Giá theo **đồng** (bảng giá).", "scoring": "value",
                "expects": expects, "solution": sol, "oracle": oracle}
    if k in ("gainers5", "losers5", "volume5"):
        which = k[:-1]; rows = L[which][:5]
        keys = ('"1": {"symbol": "MÃ", "pct": 0, "close": 0}, ' * 5)
        schema = ('{\n  "values": {\n    ' + ",\n    ".join('"%d": {"symbol": "MÃ", "pct": 0, "close": 0}' % i for i in range(1, 6)) +
                  '\n  },\n  "period": "phiên 30/10/2026",\n  "source": "market_movers",\n  "note": "(tuỳ chọn)"\n}')
        expects = []
        for i, r in enumerate(rows, 1):
            expects += [{"type": "str", "path": "values.%d.symbol" % i, "accept": [r["symbol"]]},
                        {"type": "value", "path": "values.%d.pct" % i, "gold": r2(r["pct"]), "tol": {"abs": 0.05}},
                        {"type": "value", "path": "values.%d.close" % i, "gold": float(r["close"]), "tol": {"rel": 0.005}}]
        expects += [period_check(p30()), src_check("market_movers")]
        sol = {str(i): {"symbol": r["symbol"], "pct": r2(r["pct"]), "close": float(r["close"])} for i, r in enumerate(rows, 1)}
        oracle = ('rows = env("movers:vn30")["data"][%r][:5]\n'
                  'for i, r in enumerate(rows, 1):\n'
                  '    s = gold["solution"][str(i)]\n'
                  '    check("sym%%d" %% i, r["symbol"], s["symbol"])\n') % ("gainers" if which == "gainers" else ("losers" if which == "losers" else "volume_leaders"))
        return {"title": "Bảng 5 mã (%s)" % which, "family_code": "L3·C movers", "fb": "ranking extraction",
                "q": "Liệt kê **đầy đủ 5 mã %s mạnh nhất** phiên gần nhất trong rổ **VN30** (theo %% thay đổi, đúng thứ hạng), kèm %% và giá đóng cửa (đồng)." % ("tăng" if which == "gainers" else "giảm"),
                "schema": schema, "rules": "", "scoring": "value", "expects": expects, "solution": sol, "oracle": oracle}
    if k == "gap12":
        g1, g2 = d["gainers"][0], d["gainers"][1]
        v = r2(g1["pct"] - g2["pct"])
        return {"title": "Chênh lệch 2 mã tăng mạnh nhất", "family_code": "L3·C movers", "fb": "ranking computation",
                "q": "Trong rổ **VN30** phiên gần nhất: chênh lệch %% tăng giữa mã tăng mạnh nhất và mã tăng mạnh thứ hai là bao nhiêu **điểm %%**?",
                "schema": SCHEMA_UNIT % ("%", "phiên gần nhất", "market_movers"), "rules": "", "scoring": "value",
                "expects": [val_check_abs(v, 0.05), unit_check("pct"), src_check("market_movers")],
                "solution": {"value": v},
                "oracle": 'g = env("movers:vn30")["data"]["gainers"]\ncheck("gap", round(g[0]["pct"] - g[1]["pct"], 2), gold["solution"]["value"])\n'}
    # vol1_close
    v1 = d["volume_leaders"][0]
    return {"title": "Mã dẫn đầu khối lượng — giá đóng cửa", "family_code": "L3·C movers", "fb": "ranking lookup",
            "q": "Trong rổ **VN30** phiên gần nhất: mã dẫn đầu khối lượng khớp lệnh là mã nào, và giá đóng cửa của mã đó là bao nhiêu (**đồng**)?",
            "schema": '{\n  "values": {"symbol": "MÃ", "close": 0},\n  "unit": "đồng",\n  "period": "phiên gần nhất",\n  "source": "market_movers",\n  "note": "(tuỳ chọn)"\n}',
            "rules": "", "scoring": "value",
            "expects": [{"type": "str", "path": "values.symbol", "accept": [v1["symbol"]]},
                        {"type": "value", "path": "values.close", "gold": float(v1["close"]), "tol": {"rel": 0.005}},
                        unit_check("dong"), src_check("market_movers")],
            "solution": {"symbol": v1["symbol"], "close": float(v1["close"])},
            "oracle": 'v = env("movers:vn30")["data"]["volume_leaders"][0]\ncheck("sym", v["symbol"], gold["solution"]["symbol"])\ncheck("close", float(v["close"]), gold["solution"]["close"])\n'}


def f_l3_tech_multi(t, env):
    g = t["params"]["group"]; kind = t["params"]["kind"]
    members = GROUPS[g]
    rs = {s: float(env["tech:" + s]["data"]["rsi14"]) for s in members}
    note_desc = ", ".join("%s %s" % (s, rs[s]) for s in members)
    schema_min = '{\n  "values": {"symbol": "MÃ", "rsi14": 0},\n  "period": "đến phiên 30/10/2026",\n  "source": "signals_technical",\n  "note": "RSI của cả 5 mã để đối chiếu"\n}'
    if kind in ("min_rsi", "max_rsi"):
        best = min(rs.values()) if kind == "min_rsi" else max(rs.values())
        winners = sorted([s for s in members if rs[s] == best])
        if len(winners) > 1:
            kind = "count_below"  # hòa → chuyển sang đếm
        else:
            sym = winners[0]
            q = "Trong 5 mã **%s** — mã nào có **RSI-14 khung ngày %s nhất** và bằng bao nhiêu?" % (", ".join(members), "thấp" if kind == "min_rsi" else "cao")
            oracle = ('rs = {s: float(env("tech:" + s)["data"]["rsi14"]) for s in %r}\n'
                      'b = %s(rs.values())\n'
                      'ws = sorted([s for s in rs if rs[s] == b])\n'
                      'check("sym", ws[0] if len(ws) == 1 else ws, gold["solution"]["symbol"])\n'
                      'check("rsi", float(rs[ws[0]]) if len(ws) == 1 else b, gold["solution"]["rsi14"])\n') % (members, "min" if kind == "min_rsi" else "max")
            return {"title": "RSI %s nhóm %s" % (kind, g), "family_code": "L3·D tech-multi", "fb": "multi-entity comparison",
                    "q": q, "schema": schema_min,
                    "rules": "- Trả đúng **mã** và **giá trị** RSI của mã đó.", "scoring": "value",
                    "expects": [{"type": "str", "path": "values.symbol", "accept": [sym]},
                                {"type": "value", "path": "values.rsi14", "gold": rs[sym], "tol": {"abs": 0.1}},
                                period_check(p30()), src_check("signals_technical"),
                                evnum([rs[s] for s in members], 2)],
                    "solution": {"symbol": sym, "rsi14": rs[sym]}, "oracle": oracle}
    # count_below
    th = None
    for c in [45, 40, 38, 36, 50]:
        n = sum(1 for s in members if rs[s] < c)
        if 1 <= n <= len(members) - 1:
            th = c; break
    assert th is not None, "tech count: no threshold for %s" % g
    cnt = sum(1 for s in members if rs[s] < th)
    q = "Trong 5 mã **%s**: có bao nhiêu mã có **RSI-14 (khung ngày) dưới %s**?" % (", ".join(members), th)
    oracle = ('rs = {s: float(env("tech:" + s)["data"]["rsi14"]) for s in %r}\n'
              'check("count", sum(1 for v in rs.values() if v < %s), gold["solution"]["count"])\n') % (members, th)
    return {"title": "Đếm RSI<%s nhóm %s" % (th, g), "family_code": "L3·D tech-multi", "fb": "multi-entity comparison",
            "q": q,
            "schema": '{\n  "values": {"count": 0},\n  "period": "đến phiên 30/10/2026",\n  "source": "signals_technical",\n  "note": "RSI của cả 5 mã để đối chiếu"\n}',
            "rules": "", "scoring": "value",
            "expects": [{"type": "value", "path": "values.count", "gold": cnt, "tol": {"abs": 0.001}},
                        period_check(p30()), src_check("signals_technical"), evnum([rs[s] for s in members], 2)],
            "solution": {"count": cnt}, "oracle": oracle}


def f_l3_crypto_multi(t, env):
    ticks = t["params"]["tickers"]; kind = t["params"]["kind"]
    pcts = {x: r2((yf_item(env, x)["price"] / yf_item(env, x)["prev"] - 1) * 100) for x in ticks}
    win = max(pcts, key=lambda x: pcts[x]) if kind == "max_chg" else min(pcts, key=lambda x: pcts[x])
    schema = ('{\n  "values": {\n    "pcts": {' + ", ".join('"%s": 0' % x for x in ticks) + '},\n'
              '    "winner": "MÃ"\n  },\n  "period": "phiên gần nhất",\n  "source": "yf_commodities",\n  "note": "(tuỳ chọn)"\n}')
    expects = [{"type": "value", "path": "values.pcts.%s" % x, "gold": pcts[x], "tol": {"abs": 0.1}} for x in ticks]
    expects += [{"type": "str", "path": "values.winner", "accept": TICK_ACCEPT[win]}, src_check("yf_commodities")]
    oracle = ('its = {x: yf_item(env("yf:main"), x) for x in %r}\n'
              'pcts = {x: round((its[x]["price"] / its[x]["prev"] - 1) * 100, 2) for x in its}\n'
              'for x, v in pcts.items():\n    check("pct_" + x, v, gold["solution"]["pcts"][x])\n'
              'b = %s(pcts.values())\n'
              'check("winner", max(pcts, key=pcts.get) if %r == "max_chg" else min(pcts, key=pcts.get), gold["solution"]["winner"])\n') % (ticks, "max" if kind == "max_chg" else "min", kind)
    return {"title": "So %% thay đổi %s" % "+".join(ticks), "family_code": "L3·E crypto-multi", "fb": "multi-asset comparison",
            "q": "Xét 3 tài sản ở **ngày giao dịch gần nhất**: %s. Tài sản nào **%% thay đổi so với phiên trước %s nhất**? Nêu %% thay đổi của cả 3." % (", ".join("`%s`" % x for x in ticks), "cao" if kind == "max_chg" else "thấp"),
            "schema": schema, "rules": "", "scoring": "value",
            "expects": expects, "solution": {"pcts": pcts, "winner": win}, "oracle": oracle}


def f_l3_index(t, env):
    sym = t["entity"]; k = t["payloads"][0]; kind = t["params"]["kind"]
    cl = env[k]["data"]["closes"]
    if kind == "pct_change":
        v = r2((cl[-1]["c"] / cl[0]["c"] - 1) * 100)
        return {"title": "%s 10 phiên" % sym, "family_code": "L3·F index", "fb": "temporal computation",
                "q": "**%s** thay đổi bao nhiêu **%%** trong 10 phiên giao dịch gần nhất — từ đóng cửa phiên **19/10** đến đóng cửa phiên **30/10**?" % sym,
                "schema": SCHEMA_UNIT % ("%", "19/10 → 30/10/2026", "vn_index_ohlcv"), "rules": "", "scoring": "value",
                "expects": [val_check_abs(v, 0.1), unit_check("pct"), period_check(["19/10", "30/10"]), src_check("vn_index_ohlcv")],
                "solution": {"value": v},
                "oracle": 'cl = env(%r)["data"]["closes"]\ncheck("chg", round((cl[-1]["c"] / cl[0]["c"] - 1) * 100, 2), gold["solution"]["value"])\n' % k}
    mx = max(cl, key=lambda x: x["c"]); d = mx["t"]; dd = "%s/%s" % (d[8:10], d[5:7])
    return {"title": "%s — phiên cao nhất" % sym, "family_code": "L3·F index", "fb": "temporal computation",
            "q": "Trong 10 phiên gần nhất (19/10 → 30/10), phiên nào **%s đóng cửa cao nhất** và mức đóng cửa đó là bao nhiêu điểm? (nêu ngày trong `note`)" % sym,
            "schema": '{\n  "values": {"value": 0},\n  "unit": "điểm",\n  "period": "19/10 → 30/10/2026",\n  "source": "vn_index_ohlcv",\n  "note": "ngày phiên cao nhất (dd/mm)"\n}',
            "rules": "", "scoring": "value",
            "expects": [{"type": "value", "path": "values.value", "gold": float(mx["c"]), "tol": {"rel": 0.005}},
                        unit_check("diem"), period_check(["19/10", "30/10"]), src_check("vn_index_ohlcv"),
                        evnum([], 1, strings=[dd])],
            "solution": {"value": float(mx["c"]), "date": d},
            "oracle": 'cl = env(%r)["data"]["closes"]\nmx = max(cl, key=lambda x: x["c"])\ncheck("max", float(mx["c"]), gold["solution"]["value"])\n' % k}


def f_l3_macro_agg(t, env):
    k = t["params"]["agg"]
    if k == "max_cat":
        best = None
        for key, name in MACRO_CPI.items():
            if key in ("cpi_total", "core"):
                continue
            v = cpi_pick(env, name, "2026-09", "pct")
            if best is None or v > best[1]:
                best = (name, v)
        name, v = best
        label = name.lstrip("- ").strip()
        return {"title": "Nhóm CPI tăng cao nhất T9", "family_code": "L3·G macro-agg", "fb": "aggregation",
                "q": "Trong **các nhóm hàng** của CPI tháng 9/2026 (so với tháng 12/2025), nhóm nào **tăng cao nhất** và mức tăng là bao nhiêu **%%**?",
                "schema": '{\n  "values": {"category": "tên nhóm", "pct": 0},\n  "period": "Tháng 9/2026",\n  "source": "vs_indicator_data",\n  "note": "(tuỳ chọn)"\n}',
                "rules": "", "scoring": "value",
                "expects": [{"type": "str", "path": "values.category", "accept": [label]},
                            {"type": "value", "path": "values.pct", "gold": r2(v), "tol": {"abs": 0.05}},
                            period_check(pmonth("2026-09")), src_check("vs_indicator_data")],
                "solution": {"category": label, "pct": r2(v)},
                "oracle": ('best = None\n'
                           'for nm in %r:\n'
                           '    v = cpi_pick(env, nm, "2026-09", "pct")\n'
                           '    if best is None or v > best[1]:\n        best = (nm, v)\n'
                           'check("pct", round(best[1], 2), gold["solution"]["pct"])\n') % ([MACRO_CPI[key] for key in MACRO_CPI if key not in ("cpi_total", "core")],)}
    if k == "count_ge_5":
        cnt = 0; months = []
        for m in range(1, 10):
            v = cpi_pick(env, "CHỈ SỐ GIÁ TIÊU DÙNG", "2026-%02d" % m, "pct")
            if v >= 5.0:
                cnt += 1; months.append("tháng %d" % m)
        return {"title": "Đếm tháng CPI≥5%", "family_code": "L3·G macro-agg", "fb": "aggregation",
                "q": "Trong **9 tháng đầu năm 2026**, có bao nhiêu tháng **CPI (so tháng 12/2025)** tăng **từ 5,0%% trở lên**? (nêu các tháng trong `note`)",
                "schema": '{\n  "value": 0,\n  "unit": "tháng",\n  "period": "9T/2026",\n  "source": "vs_indicator_data",\n  "note": "liệt kê các tháng"\n}',
                "rules": "", "scoring": "value",
                "expects": [val_check_abs(cnt, 0.001), {"type": "unit", "path": "unit", "accept": ["tháng", "thang"]},
                            src_check("vs_indicator_data"), evnum([], 1, strings=months[:2])],
                "solution": {"value": cnt, "months": months},
                "oracle": 'check("cnt", sum(1 for m in range(1, 10) if cpi_pick(env, "CHỈ SỐ GIÁ TIÊU DÙNG", "2026-%02d" % m, "pct") >= 5.0), gold["solution"]["value"])\n'}
    # gdp_max_q
    qs = ["Q1/2026", "Q2/2026", "Q3/2026"]
    vq = {q: gdp_pick(env, q) for q in qs}
    wq = max(vq, key=lambda q: vq[q])
    return {"title": "GDP quý cao nhất 2026", "family_code": "L3·G macro-agg", "fb": "aggregation",
            "q": "Trong **3 quý đầu năm 2026**, **quý nào có GDP (tổng số) cao nhất** và giá trị là bao nhiêu **tỷ đồng**?",
            "schema": '{\n  "values": {"quarter": "Q?/2026", "value": 0},\n  "period": "3 quý/2026",\n  "source": "vs_indicator_data",\n  "note": "(tuỳ chọn)"\n}',
            "rules": "", "scoring": "value",
            "expects": [{"type": "str", "path": "values.quarter", "accept": pq(wq)},
                        {"type": "value", "path": "values.value", "gold": vq[wq], "tol": {"rel": 0.005}},
                        src_check("vs_indicator_data")],
            "solution": {"quarter": wq, "value": vq[wq]},
            "oracle": 'vq = {q: gdp_pick(env, q) for q in %r}\nwq = max(vq, key=lambda q: vq[q])\ncheck("q", wq, gold["solution"]["quarter"])\ncheck("v", vq[wq], gold["solution"]["value"])\n' % qs}


# ---------------------------------------------------------------- L4
REFUSE_TOKENS = ["chưa công bố", "chưa có", "chưa kết thúc", "không có", "không tồn tại",
                 "chưa phát hành", "chưa đến kỳ", "chưa có số liệu", "không có số liệu",
                 "chưa được công bố", "không có dữ liệu", "không đủ dữ liệu"]


def f_l4_future(t, env):
    subj = t["subject"]
    if subj == "vn_stock":
        k = t["payloads"][0]; sym = t["entity"]; d = env[k]["data"]
        latest = d["periods"][-1]; asked = nextq(latest)
        row = fs_find({"data": {"rows": d["rows"]}}, [r"LNST"])[0]
        bonus_v = r2(row["values"][latest] / 1e9)
        return {"title": "%s — %s (chưa công bố)" % (sym, asked), "family_code": "L4·E future-period", "fb": "unanswerable (period trap)",
                "q": "Lợi nhuận sau thuế của **%s** trong **%s** là bao nhiêu? Quy ra **tỷ đồng**." % (sym, asked),
                "schema": SCHEMA_REFUSAL % (asked, "financial_statements"), "rules": "", "scoring": "refusal",
                "refusal_tokens": REFUSE_TOKENS, "bonus_numbers": [bonus_v],
                "bonus_strings": [latest] + pq(latest),
                "solution": {"latest": latest, "asked": asked},
                "oracle": ('d = env(%r)["data"]\n'
                           'check("asked_absent", %r in d["periods"], False)\n'
                           'check("latest", d["periods"][-1], gold["solution"]["latest"])\n') % (k, asked)}
    if subj == "macro":
        pr = t["params"]; series = pr["series"]; period = pr["period"]
        if series == "gdp":
            q = "**GDP** (tổng số) **quý 4/2026** là bao nhiêu **tỷ đồng**?"
            schema = SCHEMA_REFUSAL % ("Q4/2026", "vs_indicator_data")
            bonus_numbers = [gdp_pick(env, "Q3/2026")]; bonus_strings = pq("Q3/2026")
            oracle = 'periods = [r["p"] for r in env("gdp:full")["data"]["total"]]\ncheck("absent", "Quý 4/2026" in periods, False)\n'
        else:
            name = MACRO_CPI[series]
            q = "**%s** **tháng 10/2026** tăng bao nhiêu phan-tram so với tháng 12/2025?" % name
            q = q.replace("phan-tram", "phần trăm (%)")
            schema = SCHEMA_REFUSAL % ("Tháng 10/2026", "vs_indicator_data")
            bonus_numbers = [cpi_pick(env, name, "2026-09", "pct")]; bonus_strings = pmonth("2026-09")
            oracle = 'rows = env("cpi:full")["data"]["rows"]\ncheck("absent", any(r["n"] == %r and r["p"] == "Tháng 10/2026" for r in rows), False)\n' % name
        return {"title": "Macro %s (chưa công bố)" % period, "family_code": "L4·E future-period", "fb": "unanswerable (period trap)",
                "q": q, "schema": schema, "rules": "", "scoring": "refusal",
                "refusal_tokens": REFUSE_TOKENS, "bonus_numbers": bonus_numbers, "bonus_strings": bonus_strings,
                "solution": {"asked": period}, "oracle": oracle}
    # gold_fx
    sym = t["entity"].split("@")[0]; day = t["params"]["date"]
    ser = msn_series(env)
    if sym in ser:
        cl = ser[sym]; last = cl[-1]
        q = "Giá đóng cửa của **%s** trong **phiên %s/2026** là bao nhiêu?" % (sym, day)
        schema = SCHEMA_REFUSAL % ("phiên %s/2026" % day, "vn_msn_fx_gold")
        bonus_numbers = [float(last["c"])]; bonus_strings = [last["t"], pday(last["t"].split("-")[2] + "/" + last["t"].split("-")[1])[0]]
        _d = "2026-%s-%s" % (day.split("/")[1], day.split("/")[0])
        oracle = 'cl = msn_series(env)[%r]\ncheck("no_day", [x for x in cl if x["t"] == %r], [])\n' % (sym, _d)
    else:
        it = yf_item(env, sym)
        q = "Giá đóng cửa của **%s** trong **phiên %s/2026** là bao nhiêu?" % (sym, day)
        schema = SCHEMA_REFUSAL % ("phiên %s/2026" % day, "yf_commodities")
        bonus_numbers = [it["price"]]; bonus_strings = ["snapshot"]
        oracle = 'check("no_series", True, True)\n'
    return {"title": "GF %s phiên %s (không có phiên)" % (sym, day), "family_code": "L4·E future-period", "fb": "unanswerable (period trap)",
            "q": q, "schema": schema, "rules": "", "scoring": "refusal",
            "refusal_tokens": REFUSE_TOKENS, "bonus_numbers": bonus_numbers, "bonus_strings": bonus_strings,
            "solution": {"sym": sym, "day": day}, "oracle": oracle}


def f_l4_nonexist(t, env):
    k = t["payloads"][0]; s = t["entity"]
    subj = "cặp **%s** (crypto)" % s if t["subject"] == "crypto" else "cổ phiếu **%s**" % s
    return {"title": "Mã %s (không tồn tại)" % s, "family_code": "L4·B nonexistent", "fb": "unanswerable (entity trap)",
            "q": "Giá đóng cửa gần nhất của %s là bao nhiêu (**đồng** nếu là cổ phiếu VN, **giá niêm yết** nếu là crypto)?" % subj,
            "schema": SCHEMA_REFUSAL % ("gần nhất", "symbol_resolve"), "rules": "", "scoring": "refusal",
            "refusal_tokens": REFUSE_TOKENS, "bonus_numbers": [], "bonus_strings": [],
            "solution": {"query": s},
            "oracle": 'd = env(%r)["data"]\ncheck("null", d["resolved"] is None, True)\ncheck("no_cand", d["candidates"], [])\n' % k}


def f_l4_narrative(t, env):
    subj = t["subject"]; sym = t["entity"]
    if subj == "vn_stock":
        k = t["payloads"][0]; cl = env[k]["data"]["closes"]; unit = "nghìn đồng"
        vs = [x["c"] for x in cl]; n = 10
        q = "Nhận định: “Trong **10 phiên gần nhất (19/10 → 30/10)**, giá đóng cửa của **%s** **tăng liên tục từng phiên**.”\n\nĐúng hay **sai**? Nêu số close từng phiên trong `note` để chứng minh." % sym
        schema = SCHEMA_VERDICT % ("19/10 → 30/10/2026", "vn_quote_history")
        period = ["19/10", "30/10"]
        oracle = 'cl = env(%r)["data"]["closes"]\nvs = [x["c"] for x in cl]\ncheck("not_rising", all(vs[i+1] > vs[i] for i in range(len(vs)-1)), False)\n' % k
    elif subj == "crypto":
        k = t["payloads"][0]; cl = env[k]["data"]["closes"]; vs = [x["c"] for x in cl]; unit = "VND"; n = 10
        q = "Nhận định: “Trong **10 ngày gần nhất**, giá đóng cửa của **%s** **tăng liên tục từng ngày**.”\n\nĐúng hay **sai**? Nêu số close từng ngày trong `note` để chứng minh." % sym
        schema = SCHEMA_VERDICT % ("10 ngày gần nhất", "vn_crypto_ohlcv")
        period = ["10 ngày"]
        oracle = 'cl = env(%r)["data"]["closes"]\nvs = [x["c"] for x in cl]\ncheck("not_rising", all(vs[i+1] > vs[i] for i in range(len(vs)-1)), False)\n' % k
    else:
        cl = msn_series(env)[sym]; vs = [x["c"] for x in cl]
        q = "Nhận định: “Trong **5 phiên gần nhất (26/10 → 30/10)**, giá đóng cửa của **%s** **tăng liên tục từng phiên**.”\n\nĐúng hay **sai**? Nêu số close từng phiên trong `note` để chứng minh." % sym
        schema = SCHEMA_VERDICT % ("26/10 → 30/10/2026", "vn_msn_fx_gold")
        period = ["26/10", "30/10"]
        oracle = 'cl = msn_series(env)[%r]\nvs = [x["c"] for x in cl]\ncheck("not_rising", all(vs[i+1] > vs[i] for i in range(len(vs)-1)), False)\n' % sym
    assert not all(vs[i + 1] > vs[i] for i in range(len(vs) - 1)), "narrative: chuỗi tăng liên tục — cần đổi claim"
    return {"title": "Kiểm chứng nhận định %s" % sym, "family_code": "L4·I narrative-check", "fb": "claim verification",
            "q": q, "schema": schema, "rules": "- `note` phải chứa số liệu thật chứng minh (ít nhất 1 phiên giảm).",
            "scoring": "verdict",
            "verdict_accept": ["sai", "false", "không đúng", "không chính xác"],
            "verdict_reject": ["đúng", "true", "chính xác"],
            "evidence": {"paths": ["note"], "min_hits": 1, "numbers": list(vs)},
            "solution": {"verdict": "sai"}, "oracle": oracle}


def f_l4_2src(t, env):
    subj = t["subject"]
    if subj == "vn_stock":
        kq = [k for k in t["payloads"] if k.startswith("vnq:")][0]
        kb = [k for k in t["payloads"] if k.startswith("batch:")][0]
        sym = t["entity"]
        last = float(env[kq]["data"]["last"]) * 1000
        b = {q["symbol"]: q for q in env[kb]["data"]["quotes"]}[sym]
        close = float(b["close"]); diff = abs(last - close)
        verdict = "khớp" if diff == 0 else "lệch"
        return {"title": "Đối chiếu 2 nguồn %s" % sym, "family_code": "L4·D two-source", "fb": "cross-source verification",
                "q": "Đối chiếu giá đóng cửa **phiên 30/10** của **%s** từ **hai nguồn**: (a) lịch sử nến **`vn_quote_history`** (nghìn đồng) và (b) bảng giá **`vn_equity_quote_batch`** (đồng). Hai nguồn có **khớp** không? Nêu giá theo **đồng** và sai khác trong `note`." % sym,
                "schema": '{\n  "verdict": "khớp hoặc không khớp",\n  "value": 0,\n  "unit": "đồng",\n  "period": "phiên 30/10/2026",\n  "source": "vn_quote_history + vn_equity_quote_batch",\n  "note": "số từng nguồn + sai khác"\n}',
                "rules": "- `value` theo **đồng**.\n- `source` ghi cả hai tool.", "scoring": "value",
                "expects": [{"type": "verdict", "path": "verdict", "accept": ["khớp", "match", "giống nhau", "không lệch"], "reject": ["không khớp", "lệch", "khác nhau"]},
                            val_check(close), unit_check("dong"), period_check(p30()),
                            src_check("vn_quote_history", "vn_equity_quote_batch")],
                "solution": {"close": close, "diff": diff, "match": diff == 0},
                "oracle": ('h = float(env(%r)["data"]["last"]) * 1000\n'
                           'b = {q["symbol"]: q for q in env(%r)["data"]["quotes"]}[%r]\n'
                           'check("close", float(b["close"]), gold["solution"]["close"])\n'
                           'check("match", h == float(b["close"]), gold["solution"]["match"])\n') % (kq, kb, sym)}
    if subj == "gold_fx":
        a = t["params"]["msn_sym"]; b = t["params"]["yf_sym"]
        va = float(msn_series(env)[a][-1]["c"]); vb = float(yf_item(env, b)["price"])
        v = r2(abs(va / vb - 1) * 100)
        return {"title": "Đối chiếu 2 nguồn %s vs %s" % (a, b), "family_code": "L4·D two-source", "fb": "cross-source verification",
                "q": "Đối chiếu giá **%s** từ hai nguồn: **`vn_msn_fx_gold`** (%.2f) và **`yf_commodities`** (`%s`, %.3f). Hai nguồn lệch nhau bao nhiêu **%%**?" % (a, va, b, vb),
                "schema": SCHEMA_UNIT % ("%", "phiên gần nhất", "vn_msn_fx_gold + yf_commodities"),
                "rules": "- Tính %% lệch giữa hai mức giá (lấy nguồn yf làm mốc).", "scoring": "value",
                "expects": [val_check_abs(v, 0.05), unit_check("pct"), src_check("vn_msn_fx_gold", "yf_commodities")],
                "solution": {"value": v, "msn": va, "yf": vb},
                "oracle": 'va = float(msn_series(env)[%r][-1]["c"])\nvb = float(yf_item(env("yf:main"), %r)["price"])\ncheck("diff", round(abs(va / vb - 1) * 100, 2), gold["solution"]["value"])\n' % (a, b)}
    # crypto: yf vs cohlcv quy đổi
    sym = t["entity"]; kind = t["params"].get("kind", "diff_pct")
    yfi = {"BTC": "BTC-USD", "ETH": "ETH-USD"}[sym]; oh = sym + "USDT"
    ko = "cohlcv:" + oh
    price = float(yf_item(env, yfi)["price"])
    fx = float(msn_series(env)["USDVND"][-1]["c"])
    cl = env[ko]["data"]["closes"]
    usd = float(cl[-1]["c"]) / fx
    if kind == "usd_gap":
        v = r2(abs(price - usd))
        q = "Hai nguồn giá **%s**: yfinance (%s, USD) và vnstock crypto (%s, VND quy đổi theo tỷ giá USD/VND 30/10). Giá quy đổi lệch bao nhiêu **USD** so với yfinance?" % (sym, yfi, oh)
        exp_v = [val_check_abs(v, 0.05), {"type": "unit", "path": "unit", "accept": ["USD"]}]
        oracle = 'price = float(yf_item(env("yf:main"), %r)["price"])\nfx = float(msn_series(env)["USDVND"][-1]["c"])\nusd = float(env(%r)["data"]["closes"][-1]["c"]) / fx\ncheck("gap", round(abs(price - usd), 2), gold["solution"]["value"])\n' % (yfi, ko)
        schema = SCHEMA_UNIT % ("USD", "phiên gần nhất", "yf_commodities + vn_crypto_ohlcv")
    else:
        v = r2(abs(usd / price - 1) * 100)
        q = "Hai nguồn giá **%s**: yfinance (%s, USD) và vnstock crypto (%s, VND quy đổi theo tỷ giá USD/VND 30/10). Hai nguồn lệch nhau bao nhiêu **%%**?" % (sym, yfi, oh)
        exp_v = [val_check_abs(v, 0.05), unit_check("pct")]
        oracle = 'price = float(yf_item(env("yf:main"), %r)["price"])\nfx = float(msn_series(env)["USDVND"][-1]["c"])\nusd = float(env(%r)["data"]["closes"][-1]["c"]) / fx\ncheck("diffpct", round(abs(usd / price - 1) * 100, 2), gold["solution"]["value"])\n' % (yfi, ko)
        schema = SCHEMA_UNIT % ("%", "phiên gần nhất", "yf_commodities + vn_crypto_ohlcv")
    return {"title": "Đối chiếu 2 nguồn %s (crypto)" % sym, "family_code": "L4·D two-source", "fb": "cross-source verification",
            "q": q, "schema": schema, "rules": "- Dùng tỷ giá USD/VND đóng cửa phiên 30/10 để quy đổi.", "scoring": "value",
            "expects": exp_v + [evnum([fx], 1), src_check("yf_commodities", "vn_crypto_ohlcv")],
            "solution": {"value": v, "price": price, "usd": r2(usd)}, "oracle": oracle}


# ---------------------------------------------------------------- L5
def f_l5_profile(t, env):
    subj = t["subject"]
    if subj == "vn_stock":
        sym = t["entity"]
        ko = "ov:" + sym; kf = "fd:" + sym
        d = env[kf]["data"]; periods = d["periods"]; p = periods[-1]
        dt = fs_find({"data": {"rows": d["rows"]}}, [r"Doanh thu thuần"])[0]["values"][-1]
        ln = next(x for x in fs_find({"data": {"rows": d["rows"]}}, [r"Lợi nhuận gộp về bán hàng", r"Lợi nhuận gộp hoạt động kinh doanh bảo hiểm"]) if x)["values"][-1]
        margin = r2(ln / dt * 100)
        tr = env[ko]["data"]["trading"]
        pe = float(tr["PE"]); mcap = r2(tr["MarketCapital"] / 1e9)
        schema = ('{\n  "values": {"revenue_q_bn": 0, "gross_profit_q_bn": 0, "gross_margin_pct": 0, "pe": 0, "market_cap_bn": 0},\n'
                  '  "period": "%s + snapshot",\n  "source": "financial_detail + stock_overview",\n  "note": "(tuỳ chọn)"\n}' % p)
        expects = [{"type": "value", "path": "values.revenue_q_bn", "gold": float(dt), "tol": {"rel": 0.005}},
                   {"type": "value", "path": "values.gross_profit_q_bn", "gold": float(ln), "tol": {"rel": 0.005}},
                   {"type": "value", "path": "values.gross_margin_pct", "gold": margin, "tol": {"abs": 0.1}},
                   {"type": "value", "path": "values.pe", "gold": pe, "tol": {"rel": 0.005}},
                   {"type": "value", "path": "values.market_cap_bn", "gold": mcap, "tol": {"rel": 0.005}},
                   src_check("financial_detail", "stock_overview")]
        oracle = ('d = env(%r)["data"]\n'
                  'dt = next(r for r in d["rows"] if "Doanh thu thuần" in r["name"])["values"][-1]\n'
                  'ln = next(r for r in d["rows"] if "Lợi nhuận gộp" in r["name"])["values"][-1]\n'
                  'tr = env(%r)["data"]["trading"]\n'
                  'check("rev", float(dt), gold["solution"]["revenue_q_bn"])\n'
                  'check("ln", float(ln), gold["solution"]["gross_profit_q_bn"])\n'
                  'check("m", round(ln / dt * 100, 2), gold["solution"]["gross_margin_pct"])\n'
                  'check("pe", float(tr["PE"]), gold["solution"]["pe"])\n'
                  'check("mc", round(tr["MarketCapital"] / 1e9, 2), gold["solution"]["market_cap_bn"])\n') % (kf, ko)
        return {"title": "Hồ sơ nhanh %s" % sym, "family_code": "L5·A profile", "fb": "company profile (multi-part)",
                "q": "Lập **hồ sơ nhanh** công ty **%s** (quý gần nhất: %s):\n1. Doanh thu thuần (tỷ đồng)\n2. Lợi nhuận gộp (tỷ đồng)\n3. Biên lợi nhuận gộp (%%)\n4. **P/E**\n5. Vốn hóa thị trường (tỷ đồng)" % (sym, p),
                "schema": schema, "rules": "- `source` ghi cả hai tool.", "scoring": "value",
                "expects": expects, "solution": {"revenue_q_bn": float(dt), "gross_profit_q_bn": float(ln),
                                                "gross_margin_pct": margin, "pe": pe, "market_cap_bn": mcap}, "oracle": oracle}
    # crypto
    sym = t["entity"]; kind = t["params"].get("kind", "profile")
    it = yf_item(env, sym)
    price = float(it["price"]); prev = float(it["prev"]); chg = r2((price / prev - 1) * 100)
    if kind == "chg_vol":
        schema = '{\n  "values": {"price": 0, "prev": 0, "change_pct": 0},\n  "period": "snapshot",\n  "source": "yf_commodities",\n  "note": "(tuỳ chọn)"\n}'
        expects = [{"type": "value", "path": "values.price", "gold": price, "tol": {"rel": 0.005}},
                   {"type": "value", "path": "values.prev", "gold": prev, "tol": {"rel": 0.005}},
                   {"type": "value", "path": "values.change_pct", "gold": chg, "tol": {"abs": 0.05}},
                   src_check("yf_commodities")]
        q = "Thống kê nhanh **%s**: giá hiện tại, giá phiên trước và **%% thay đổi** (theo snapshot) là bao nhiêu?" % sym
        oracle = ('it = yf_item(env("yf:main"), %r)\n'
                  'check("p", float(it["price"]), gold["solution"]["price"])\n'
                  'check("pr", float(it["prev"]), gold["solution"]["prev"])\n'
                  'check("chg", round((it["price"] / it["prev"] - 1) * 100, 2), gold["solution"]["change_pct"])\n') % sym
    else:
        schema = '{\n  "values": {"price": 0, "change_pct": 0},\n  "period": "snapshot",\n  "source": "yf_commodities",\n  "note": "(tuỳ chọn)"\n}'
        expects = [{"type": "value", "path": "values.price", "gold": price, "tol": {"rel": 0.005}},
                   {"type": "value", "path": "values.change_pct", "gold": chg, "tol": {"abs": 0.05}},
                   src_check("yf_commodities")]
        q = "Thống kê nhanh **%s**: giá hiện tại (USD) và **%% thay đổi** so với phiên trước (theo snapshot) là bao nhiêu?" % sym
        oracle = ('it = yf_item(env("yf:main"), %r)\n'
                  'check("p", float(it["price"]), gold["solution"]["price"])\n'
                  'check("chg", round((it["price"] / it["prev"] - 1) * 100, 2), gold["solution"]["change_pct"])\n') % sym
    return {"title": "Crypto profile %s" % sym, "family_code": "L5·A profile", "fb": "crypto quick profile",
            "q": q, "schema": schema, "rules": "", "scoring": "value",
            "expects": expects, "solution": {"price": price, "prev": prev, "change_pct": chg}, "oracle": oracle}


def f_l5_compare(t, env):
    subj = t["subject"]
    if subj == "vn_stock":
        k = t["payloads"][0]; g = t["params"]["group"]; rows = env[k]["data"]["rows"]
        syms = [r["symbol"] for r in rows]
        schema = ('{\n  "values": {\n    ' + ",\n    ".join('"%s": {"pe": 0, "pb": 0, "roe": 0}' % s for s in syms) +
                  '\n  },\n  "ranking": ["MÃ1", "MÃ2", "..."],\n  "period": "2025",\n  "source": "peer_compare",\n  "note": "(tuỳ chọn)"\n}')
        expects = []
        for r in rows:
            expects += [{"type": "value", "path": "values.%s.pe" % r["symbol"], "gold": float(r["p_e"]), "tol": {"rel": 0.005}},
                        {"type": "value", "path": "values.%s.pb" % r["symbol"], "gold": float(r["p_b"]), "tol": {"rel": 0.005}},
                        {"type": "value", "path": "values.%s.roe" % r["symbol"], "gold": float(r["roe"]), "tol": {"rel": 0.005}}]
        rk = [r["symbol"] for r in sorted(rows, key=lambda x: -x["roe"])]
        expects += [{"type": "list_order", "path": "ranking", "gold": rk}, period_check(["2025"]), src_check("peer_compare")]
        oracle = ('rows = env(%r)["data"]["rows"]\n'
                  'for r in rows:\n'
                  '    s = gold["solution"][r["symbol"]]\n'
                  '    check(r["symbol"] + "_pe", float(r["p_e"]), s["pe"])\n'
                  '    check(r["symbol"] + "_pb", float(r["p_b"]), s["pb"])\n'
                  '    check(r["symbol"] + "_roe", float(r["roe"]), s["roe"])\n'
                  'rk = [r["symbol"] for r in sorted(rows, key=lambda x: -x["roe"])]\n'
                  'check("ranking", rk, gold["solution"]["ranking"])\n') % k
        sol = {r["symbol"]: {"pe": float(r["p_e"]), "pb": float(r["p_b"]), "roe": float(r["roe"])} for r in rows}
        sol["ranking"] = rk
        return {"title": "So sánh nhóm %s + xếp hạng ROE" % g, "family_code": "L5·B compare", "fb": "peer comparison (multi-part)",
                "q": "Dùng **`peer_compare`** lập bảng **P/E, P/B, ROE** của 5 mã **%s**, rồi **xếp hạng 5 mã theo ROE giảm dần**." % ", ".join(syms),
                "schema": schema, "rules": "- Đúng kỳ mà tool trả về.", "scoring": "value",
                "expects": expects, "solution": sol, "oracle": oracle}
    if t["entity"].endswith("USDT"):
        ka = "cohlcv:" + t["entity"]; kb = "cohlcv:" + t["params"]["peer"]
        ca = env[ka]["data"]["closes"]; cb = env[kb]["data"]["closes"]
        pa = r2((ca[-1]["c"] / ca[-2]["c"] - 1) * 100); pb_ = r2((cb[-1]["c"] / cb[-2]["c"] - 1) * 100)
        win = t["entity"] if abs(pa) > abs(pb_) else t["params"]["peer"]
        schema = '{\n  "values": {"%s_pct": 0, "%s_pct": 0, "winner": "MÃ"},\n  "period": "phiên cuối",\n  "source": "vn_crypto_ohlcv",\n  "note": "(tuỳ chọn)"\n}' % (t["entity"], t["params"]["peer"])
        expects = [{"type": "value", "path": "values.%s_pct" % t["entity"], "gold": pa, "tol": {"abs": 0.05}},
                   {"type": "value", "path": "values.%s_pct" % t["params"]["peer"], "gold": pb_, "tol": {"abs": 0.05}},
                   {"type": "str", "path": "values.winner", "accept": [win, win.replace("USDT", "")]},
                   src_check("vn_crypto_ohlcv")]
        oracle = 'ca = env(%r)["data"]["closes"]\ncb = env(%r)["data"]["closes"]\ncheck("a", round((ca[-1]["c"] / ca[-2]["c"] - 1) * 100, 2), gold["solution"]["values"][%r])\ncheck("b", round((cb[-1]["c"] / cb[-2]["c"] - 1) * 100, 2), gold["solution"]["values"][%r])\n' % (ka, kb, t["entity"] + "_pct", t["params"]["peer"] + "_pct")
        return {"title": "So %% biến động %s vs %s" % (t["entity"], t["params"]["peer"]), "family_code": "L5·B compare", "fb": "crypto pair comparison",
                "q": "So sánh **%% thay đổi phiên cuối** của hai cặp **%s** và **%s** (nguồn vnstock crypto). Cặp nào **biến động mạnh hơn** (|%%| lớn hơn)? Nêu %% của cả hai." % (t["entity"], t["params"]["peer"]),
                "schema": schema, "rules": "- Biến động mạnh hơn = giá trị tuyệt đối %% thay đổi lớn hơn.", "scoring": "value",
                "expects": expects, "solution": {"values": {t["entity"] + "_pct": pa, t["params"]["peer"] + "_pct": pb_}, "winner": win}, "oracle": oracle}
    if t["subject"] == "gold_fx":
        sym = t["entity"]; ser = msn_series(env)
        if sym in ser:
            cl = ser[sym]; chg = r2((cl[-1]["c"] / cl[0]["c"] - 1) * 100)
        else:
            it = yf_item(env, sym); chg = r2((it["price"] / it["prev"] - 1) * 100)
        ucl = ser["USDVND"]; uchg = r2((ucl[-1]["c"] / ucl[0]["c"] - 1) * 100)
        strong = "mạnh hơn" if abs(chg) > abs(uchg) else "yếu hơn"
        return {"title": "Biến động %s vs USDVND" % sym, "family_code": "L5·B compare", "fb": "cross-asset comparison",
                "q": "Trong 5 phiên gần nhất (26/10 → 30/10): **%% thay đổi của %s** và của **USDVND** lần lượt là bao nhiêu? Biến động của %s **mạnh hơn hay yếu hơn** USDVND (so |%%|)?" % (sym, sym),
                "schema": '{\n  "values": {"sym_pct": 0, "usdvnd_pct": 0, "so_sanh": "mạnh hơn hoặc yếu hơn"},\n  "period": "26/10 → 30/10/2026",\n  "source": "vn_msn_fx_gold",\n  "note": "(tuỳ chọn)"\n}',
                "rules": "", "scoring": "value",
                "expects": [{"type": "value", "path": "values.sym_pct", "gold": chg, "tol": {"abs": 0.05}},
                            {"type": "value", "path": "values.usdvnd_pct", "gold": uchg, "tol": {"abs": 0.05}},
                            {"type": "verdict", "path": "values.so_sanh", "accept": [strong], "reject": ["mạnh hơn" if strong == "yếu hơn" else "yếu hơn"]},
                            src_check("vn_msn_fx_gold")],
                "solution": {"sym_pct": chg, "usdvnd_pct": uchg, "so_sanh": strong},
                "oracle": 'ser = msn_series(env)\ncheck("usd", round((ser["USDVND"][-1]["c"] / ser["USDVND"][0]["c"] - 1) * 100, 2), gold["solution"]["usdvnd_pct"])\n'}
    # crypto pairs (yf)
    a = t["entity"]; b = t["params"]["peer"]; kind = t["params"].get("kind", "chg")
    ia, ib = yf_item(env, a), yf_item(env, b)
    pa = r2((ia["price"] / ia["prev"] - 1) * 100); pbb = r2((ib["price"] / ib["prev"] - 1) * 100)
    if kind == "gap":
        v = r2(abs(abs(pa) - abs(pbb)))
        return {"title": "Chênh %% biến động %s vs %s" % (a, b), "family_code": "L5·B compare", "fb": "crypto pair comparison",
                "q": "Chênh lệch **%% biến động** (giá trị tuyệt đối) giữa **%s** và **%s** phiên gần nhất là bao nhiêu **điểm %%**?" % (a, b),
                "schema": SCHEMA_UNIT % ("%", "phiên gần nhất", "yf_commodities"), "rules": "", "scoring": "value",
                "expects": [val_check_abs(v, 0.05), unit_check("pct"), src_check("yf_commodities")],
                "solution": {"value": v},
                "oracle": ('ia = yf_item(env("yf:main"), %r)\nib = yf_item(env("yf:main"), %r)\n'
                           'pa = (ia["price"] / ia["prev"] - 1) * 100\npb = (ib["price"] / ib["prev"] - 1) * 100\n'
                           'check("gap", round(abs(abs(pa) - abs(pb)), 2), gold["solution"]["value"])\n') % (a, b)}
    win = a if abs(pa) > abs(pbb) else b
    schema = '{\n  "values": {"%s_pct": 0, "%s_pct": 0, "winner": "MÃ"},\n  "period": "phiên gần nhất",\n  "source": "yf_commodities",\n  "note": "(tuỳ chọn)"\n}' % (a, b)
    expects = [{"type": "value", "path": "values.%s_pct" % a, "gold": pa, "tol": {"abs": 0.05}},
               {"type": "value", "path": "values.%s_pct" % b, "gold": pbb, "tol": {"abs": 0.05}},
               {"type": "str", "path": "values.winner", "accept": TICK_ACCEPT[win]},
               src_check("yf_commodities")]
    oracle = ('ia = yf_item(env("yf:main"), %r)\nib = yf_item(env("yf:main"), %r)\n'
              'check("a", round((ia["price"] / ia["prev"] - 1) * 100, 2), gold["solution"]["values"][%r])\n'
              'check("b", round((ib["price"] / ib["prev"] - 1) * 100, 2), gold["solution"]["values"][%r])\n') % (a, b, a + "_pct", b + "_pct")
    return {"title": "So %% biến động %s vs %s" % (a, b), "family_code": "L5·B compare", "fb": "multi-asset comparison",
            "q": "So sánh **%% thay đổi phiên gần nhất** của **%s** và **%s**: các %% là bao nhiêu và tài sản nào **biến động mạnh hơn** (|%%| lớn hơn)?" % (a, b),
            "schema": schema, "rules": "- Biến động mạnh hơn = |%%| lớn hơn.", "scoring": "value",
            "expects": expects, "solution": {"values": {a + "_pct": pa, b + "_pct": pbb}, "winner": win}, "oracle": oracle}


def f_l5_valuation(t, env):
    k = t["payloads"][0]; sym = t["entity"]; d = env[k]["data"]
    if d.get("per") is not None:
        schema = '{\n  "values": {"price": 0, "per": 0, "pb": 0},\n  "period": "snapshot 2026-11-01",\n  "source": "valuation_run",\n  "note": "EPS/BVPS dùng để tính"\n}'
        expects = [{"type": "value", "path": "values.price", "gold": float(d["price"]), "tol": {"rel": 0.005}},
                   {"type": "value", "path": "values.per", "gold": float(d["per"]), "tol": {"rel": 0.005}},
                   {"type": "value", "path": "values.pb", "gold": float(d["pb"]), "tol": {"rel": 0.005}},
                   src_check("valuation_run")]
        oracle = ('d = env(%r)["data"]\ncheck("price", float(d["price"]), gold["solution"]["price"])\ncheck("per", float(d["per"]), gold["solution"]["per"])\ncheck("pb", float(d["pb"]), gold["solution"]["pb"])\n') % k
        return {"title": "Định giá %s" % sym, "family_code": "L5·C valuation", "fb": "valuation summary (multi-part)",
                "q": "Chạy định giá **%s** bằng **`valuation_run`**: giá được dùng để tính (đồng), **P/E** và **P/B** là bao nhiêu?" % sym,
                "schema": schema, "rules": "- `price` theo **đồng**.", "scoring": "value",
                "expects": expects, "solution": {"price": float(d["price"]), "per": float(d["per"]), "pb": float(d["pb"])}, "oracle": oracle}
    # partial (POM): chỉ có price/eps/bvps
    schema = '{\n  "values": {"price": 0, "eps": 0},\n  "period": "snapshot 2026-11-01",\n  "source": "valuation_run",\n  "note": "P/E có tính được không — giải thích"\n}'
    expects = [{"type": "value", "path": "values.price", "gold": float(d["price"]), "tol": {"rel": 0.005}},
               {"type": "value", "path": "values.eps", "gold": float(d["eps"]), "tol": {"rel": 0.005}},
               {"type": "tokens", "path": "note", "accept": ["âm", "không tính được", "không xác định"], "reject": []},
               src_check("valuation_run")]
    oracle = ('d = env(%r)["data"]\ncheck("price", float(d["price"]), gold["solution"]["price"])\ncheck("eps", float(d["eps"]), gold["solution"]["eps"])\ncheck("partial", "per" in d, False)\n') % k
    return {"title": "Định giá %s (dữ liệu một phần)" % sym, "family_code": "L5·C valuation", "fb": "valuation summary (partial data)",
            "q": "Chạy định giá **%s** bằng **`valuation_run`**: giá và **EPS** là bao nhiêu? **P/E có tính được không** — nêu rõ trong `note` (kèm lý do)." % sym,
            "schema": schema, "rules": "", "scoring": "value",
            "expects": expects, "solution": {"price": float(d["price"]), "eps": float(d["eps"])}, "oracle": oracle}


FAMILIES_B = {
    "l3-agg": f_l3_agg,
    "l3-screen": f_l3_screen,
    "l3-top": f_l3_top,
    "l3-tech-multi": f_l3_tech_multi,
    "l3-crypto-multi": f_l3_crypto_multi,
    "l3-index": f_l3_index,
    "l3-macro-agg": f_l3_macro_agg,
    "l4-future": f_l4_future,
    "l4-nonexist": f_l4_nonexist,
    "l4-narrative": f_l4_narrative,
    "l4-2src": f_l4_2src,
    "l5-profile": f_l5_profile,
    "l5-compare": f_l5_compare,
    "l5-valuation": f_l5_valuation,
}
