#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_plan.py — lập manifest 250 task chính (200 main + 50 holdout) + danh sách probe MCP.

Phân bổ chốt (khớp PHẦN 6 benchmark-plan.md):
  Mức: 40 main + 10 holdout (mỗi L1..L5);  Tỷ lệ thực thể: VN 128 · crypto 30 · vàng/FX 21 · macro 21 (main).
  Rule ≤2 task/thực thể (nhóm đếm riêng cho tác vụ theo rổ; macro đếm theo series@kỳ).
Sinh: tools/manifest.json + tools/probe_list.json (đã dedupe) + in bảng kiểm.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = "2026-11-01"

# ---------------------------------------------------------------------------
# POOLS — tất cả là thực thể MỚI (đã trừ 19 thực thể pilot)
# ---------------------------------------------------------------------------
VN = ("ACB STB VPB HDB TPB MSB VIB LPB EIB OCB "              # banks 10
      "VCI VIX SHS MBS FTS "                                   # securities 5
      "HSG NKG HT1 TLH VGS POM "                               # steel/materials 6
      "PNJ FRT KDC MSN SBT LTG ANV "                           # retail/consumer 7
      "CMG ELC VGI CTR FOX "                                   # tech/telecom 5
      "VIC KDH NLG DXG PDR SCR VRE KBC SZC IJC HHV CII "       # realestate 12
      "PVS BSR PLX PVD PVT POW NT2 GEG "                       # energy 8
      "REE PC1 HBC VCG CTD FCN GEX SAM "                       # industrial 8
      "HVN VJC GMD SCS HAH VOS VSC "                           # logistics 7
      "DBC BAF HAG DPM DCM CSV "                               # agri 6
      "DHG IMP TRA DBD "                                       # pharma 4
      "BMI MIG BIC "                                           # insurance 3
      "QNS SLS TNG MSH VCS PTB "                               # misc 6
      "HT1 BMP NTP VGC ").split()                              # materials 4
CRYPTO = ("ETHUSDT SOLUSDT BNBUSDT XRPUSDT DOGEUSDT ADAUSDT AVAXUSDT LINKUSDT TONUSDT DOTUSDT "
          "LTCUSDT TRXUSDT SHIBUSDT UNIUSDT ATOMUSDT XLMUSDT NEARUSDT APTUSDT ARBUSDT OPUSDT "
          "FILUSDT INJUSDT SUIUSDT POLUSDT").split()
GF = ("XAGUSD EURVND JPYVND USDJPY EURUSD GBPUSD USDCNY KRWVND "  # msn (XAUUSD, USDVND để dành — trừ khi cần)
      "GC=F SI=F NG=F HG=F BZ=F CL=F").split()                    # yf
FAKE_VN = ["ZZZ1", "XYZA", "QQV9", "QWER9", "XKCD9", "XXVX", "ZZXQ", "FAKE9",
           "ZQZQ", "XXYY", "QQQQ", "VVXX"]
FAKE_CRYPTO = ["FAKECOIN", "NOTCOIN", "XFAKE"]

# macro: series trong phản hồi CPI + GDP (đếm ≤2 theo series@kỳ)
MACRO_CPI = {
    "cpi_total": "CHỈ SỐ GIÁ TIÊU DÙNG",          # có 2 bản: index (level) và % so T12
    "core": "LẠM PHÁT CƠ BẢN",
    "cat_food": "Hàng ăn và dịch vụ ăn uống",
    "cat_food_sub_food": "- Thực phẩm",
    "cat_drink": "Đồ uống và thuốc lá",
    "cat_cloth": "May mặc, giày dép mũ nón",
    "cat_house": "Nhà ở và vật liệu xây dựng",
    "cat_devices": "Thiết bị và đồ dùng gia đình",
    "cat_med": "Thuốc và dịch vụ y tế",
    "cat_transport": "Giao thông",
    "cat_telecom": "Thông tin và truyền thông",
    "cat_edu": "Giáo dục",
    "cat_travel": "Văn hóa, giải trí và du lịch",
    "cat_other": "Hàng hóa và dịch vụ khác",
}

# ---------------------------------------------------------------------------
# RỔ (group) cho tác vụ theo rổ — mỗi rổ dùng 1 lần/họ, nhóm đếm riêng
# ---------------------------------------------------------------------------
GROUPS = {
    "banks1":  ["ACB", "STB", "VPB", "HDB", "TPB"],
    "sec1":    ["VCI", "VIX", "SHS", "MBS", "FTS"],
    "steel1":  ["HSG", "NKG", "POM", "TLH", "VGS"],
    "cons1":   ["PNJ", "FRT", "KDC", "MSN", "SBT"],
    "tech1":   ["CMG", "ELC", "VGI", "CTR", "FOX"],
    "bds1":    ["KDH", "NLG", "DXG", "PDR", "KBC"],
    "energy1": ["PVS", "PVD", "BSR", "PLX", "POW"],
    "util1":   ["REE", "PC1", "GEG", "NT2", "SAM"],
    "logi1":   ["GMD", "SCS", "HAH", "VOS", "VSC"],
    "agri1":   ["DBC", "BAF", "HAG", "DPM", "DCM"],
}
PEER_GROUPS = {  # head + 4 peers
    "banks_p":  ("VPB", ["ACB", "STB", "HDB", "TPB"]),
    "sec_p":    ("VIX", ["VCI", "SHS", "MBS", "FTS"]),
    "steel_p":  ("HSG", ["NKG", "POM", "TLH", "VGS"]),
    "cons_p":   ("FRT", ["PNJ", "KDC", "MSN", "SBT"]),
    "tech_p":   ("CMG", ["ELC", "VGI", "CTR", "FOX"]),
    "bds_p":    ("KDH", ["NLG", "DXG", "PDR", "KBC"]),
    "energy_p": ("PVS", ["PVD", "PVT", "PLX", "BSR"]),
    "pharma_p": ("DHG", ["IMP", "TRA", "DBD", "DBT"]),
}

# ---------------------------------------------------------------------------
# Máy đếm dùng thực thể (≤2 / thực thể; main và holdout TÁCH pool)
# ---------------------------------------------------------------------------
class Pool:
    def __init__(self, items):
        self.items = list(items)
        self.used = {x: 0 for x in self.items}
        self.cursor = 0

    def take(self, n, prefer=None):
        """Lấy n thực thể còn ≤1 lượt (ưu tiên prefer trước); trả về list."""
        out = []
        cand = [x for x in (prefer or []) if x in self.used and self.used[x] <= 1]
        for x in cand:
            if len(out) < n:
                self.used[x] += 1
                out.append(x)
        guard = 0
        while len(out) < n:
            if self.cursor >= len(self.items):
                self.cursor = 0
                if all(self.used[x] > 1 for x in self.items):
                    raise RuntimeError("Pool %s can kiet" % (self.items[:3],))
            x = self.items[self.cursor]
            self.cursor += 1
            guard += 1
            if guard > len(self.items) * 4:
                raise RuntimeError("Pool %s can kiet (guard)" % (self.items[:3],))
            if self.used[x] <= 1:
                self.used[x] += 1
                out.append(x)
        return out

    def take_clean(self, n):
        """Lấy n thực thể CHƯA dùng lần nào (dành cho holdout)."""
        out = [x for x in self.items if self.used[x] == 0][:n]
        if len(out) < n:
            raise RuntimeError("Het thuc the sach")
        for x in out:
            self.used[x] += 1
        return out


def mk(split, level, family, subject, entity, params, payloads):
    return {"split": split, "level": level, "family": family, "subject": subject,
            "entity": entity, "params": params, "payloads": payloads}


def build(split, pools):
    """Xây manifest cho 'main'(200) hoặc 'holdout'(50) — bảng đếm tường minh cnt(main, hold)."""
    tasks = []
    vn, cr, gf, mu = pools["vn"], pools["cr"], pools["gf"], pools["mu"]
    is_main = split == "main"

    def cnt(m, h):
        return m if is_main else h

    # --- Danh sách tường minh (đã xác minh dữ liệu) — ĐĂNG KÝ USAGE TRƯỚC auto-take ---
    if is_main:
        BCTC = [("ACB", "lnst_tong"), ("STB", "lnst_tong"), ("VPB", "lnst_tong"), ("HDB", "lnst_tong"),
                ("TPB", "lnst_tong"), ("MSB", "lnst_tong"), ("VIB", "lnst_tong"), ("LPB", "lnst_tong"),
                ("EIB", "lnst_tong"), ("OCB", "lnst_tong"), ("HSG", "doanh_thu"), ("NKG", "lnst_me")]
        GROW = ["PNJ", "KDC", "MSN", "DBC", "DCM", "KBC", "HSG", "NKG"]
        MARG = ["VGC", "DCM", "PVS", "GMD", "HAG", "FRT", "ANV"]
        PROF = ["CTD", "FCN", "GEG", "GEX", "HBC", "NT2", "PC1", "POW", "PTB", "PVT", "REE", "SAM"]
        FUT = [x for (x, _m) in BCTC][:8]
        SRC2 = ["PVS", "PVD", "BSR", "PLX"]
    else:
        pass
        BCTC = [("POM", "lnst_dn"), ("TRA", "lnst_dn"), ("VCI", "lnst_dn")]
        GROW = ["VGS", "TRA"]
        MARG = ["BMI", "MIG"]
        PROF = ["VCG", "VCS"]
        FUT = ["POM", "VCI"]
        SRC2 = ["VGS"]
    _pre = {}
    for s in [x for (x, _m) in BCTC] + GROW + MARG + PROF + FUT + SRC2:
        _pre[s] = _pre.get(s, 0) + 1
    for s, u in _pre.items():
        vn.used[s] = vn.used.get(s, 0) + u
        assert vn.used[s] <= 2, "usage>2 sau pre: %s=%d" % (s, vn.used[s])

    # ---------------- L1 ----------------
    qv = ["EIB", "OCB", "VCI", "VIX", "SHS", "MBS", "FTS", "HT1"] if is_main else ["IJC", "HHV"]
    for s in qv:
        tasks.append(mk(split, "L1", "l1-quote-vn", "vn_stock", s, {}, ["vnq:" + s]))
    for (s, m) in BCTC:
        tasks.append(mk(split, "L1", "l1-bctc", "vn_stock", s, {"metric": m}, ["fs:" + s]))
    cr_l1 = ([("BTC-USD", "yf_price", ["yf:main"]), ("ETH-USD", "yf_price", ["yf:main"]),
              ("SOL-USD", "yf_price", ["yf:main"]), ("BNB-USD", "yf_price", ["yf:main"]),
              ("BTCUSDT", "ohlcv_close", ["cohlcv:BTCUSDT"])]
             if is_main else [("ETH-USD", "yf_chg", ["yf:main"])])
    for (s, k, pl) in cr_l1:
        tasks.append(mk(split, "L1", "l1-quote-crypto", "crypto", s, {"kind": k}, pl))
    for s in gf.take(cnt(5, 1)):
        tasks.append(mk(split, "L1", "l1-quote-gf", "gold_fx", s,
                        {"day": "30/10" if is_main else "29/10"}, ["msn:main", "yf:main"]))
    m1_main = [("cpi_total", "2026-09", "pct"), ("cpi_total", "2026-08", "pct"),
               ("core", "2026-09", "pct"), ("cat_transport", "2026-09", "pct"),
               ("cat_house", "2026-09", "pct"), ("cat_food", "2026-09", "index"),
               ("gdp", "Q3/2026", "value"), ("gdp", "Q2/2026", "value"),
               ("gdp", "Q1/2026", "value"), ("gdp", "Q4/2025", "value")]
    m1_hold = [("cat_med", "2026-09", "pct"), ("cat_telecom", "2026-09", "pct"),
               ("cat_travel", "2026-09", "index")]
    for (k, per, kind) in (m1_main[:10] if is_main else m1_hold):
        tasks.append(mk(split, "L1", "l1-macro", "macro", "%s@%s" % (k, per),
                        {"series": k, "period": per, "kind": kind}, ["cpi:full", "gdp:full"]))

    # ---------------- L2 ----------------
    for s in GROW:
        tasks.append(mk(split, "L2", "l2-growth", "vn_stock", s, {}, ["fs:" + s]))
    for s in MARG:
        tasks.append(mk(split, "L2", "l2-margin", "vn_stock", s, {}, ["fd:" + s]))
    for s in (["ANV", "CMG", "ELC", "CTR", "VGI"] if is_main else ["HHV"]):
        tasks.append(mk(split, "L2", "l2-ratio", "vn_stock", s, {}, ["val:" + s]))
    for s in (["ANV", "HVN", "KDC", "MSN", "VGC"] if is_main else ["SBT", "VCG"]):
        tasks.append(mk(split, "L2", "l2-tech", "vn_stock", s, {}, ["tech:" + s]))
    cr_l2 = ([("BTC-USD", "yf_to_vnd", ["yf:main", "msn:main"]), ("ETH-USD", "yf_to_vnd", ["yf:main", "msn:main"]),
              ("SOL-USD", "yf_to_vnd", ["yf:main", "msn:main"]), ("BNB-USD", "yf_to_vnd", ["yf:main", "msn:main"]),
              ("BTC-USD", "yf_to_eur", ["yf:main", "msn:main"])]
             if is_main else [("SOL-USD", "yf_to_vnd", ["yf:main", "msn:main"])])
    for (s, k, pl) in cr_l2:
        tasks.append(mk(split, "L2", "l2-crypto-x", "crypto", s,
                        {"kind": k, "fx_day": "30/10" if is_main else "29/10"}, pl))
    gf_l2 = gf.take(cnt(5, 1))
    for s in gf_l2:
        tasks.append(mk(split, "L2", "l2-gf-compare", "gold_fx", s,
                        {"day": "30/10" if is_main else "29/10"}, ["msn:main", "yf:main"]))
    m2_main = [("gdp_qoq", "Q3/2026 vs Q2/2026"), ("cpi_avg", "T7-T9/2026"), ("cpi_gap", "T9/2026"),
               ("core_avg", "T7-T9/2026"), ("gdp_yoy", "Q3/2026 vs Q3/2025")]
    m2_hold = [("cpi_avg", "T5-T7/2026")]
    for (k, w) in (m2_main[:5] if is_main else m2_hold):
        tasks.append(mk(split, "L2", "l2-macro-calc", "macro", "%s@%s" % (k, w),
                        {"calc": k, "window": w}, ["cpi:full", "gdp:full"]))

    # ---------------- L3 ----------------
    gk = list(GROUPS.items())
    for name, members in gk[:cnt(8, 2)]:
        tasks.append(mk(split, "L3", "l3-agg", "vn_stock", "GROUP:" + name, {"group": name}, ["batch:" + name]))
    pk = list(PEER_GROUPS.items())
    for name, (head, peers) in pk[:cnt(8, 2)]:
        tasks.append(mk(split, "L3", "l3-screen", "vn_stock", "PEER:" + name, {"group": name}, ["peer:" + name]))
    top_variants = [("vn30", "gainers3"), ("vn30", "losers3"), ("vn30", "volume3"),
                    ("vn30", "gainers5"), ("vn30", "losers5"), ("vn30", "volume5")]
    top_hold = [("vn30", "gap12"), ("vn30", "vol1_close")]
    for (u, k) in (top_variants[:6] if is_main else top_hold):
        tasks.append(mk(split, "L3", "l3-top", "vn_stock", "MOVERS:%s:%s" % (u, k), {"universe": u, "kind": k},
                        ["movers:" + u]))
    tm = [("banks1", "min_rsi"), ("sec1", "min_rsi"), ("sec1", "count_below_45"),
          ("bds1", "max_rsi"), ("energy1", "min_rsi")]
    for (g, k) in tm[:cnt(5, 1)]:
        tasks.append(mk(split, "L3", "l3-tech-multi", "vn_stock", "GROUP:" + g + ":" + k,
                        {"group": g, "kind": k}, ["techgrp:" + g]))
    cm = [(["GC=F", "CL=F", "BTC-USD"], "max_chg"), (["SI=F", "HG=F", "NG=F"], "min_chg"),
          (["ETH-USD", "SOL-USD", "BNB-USD"], "max_chg"), (["BZ=F", "NG=F", "CL=F"], "max_chg"),
          (["GC=F", "SI=F", "BTC-USD"], "min_chg"), (["HG=F", "BZ=F", "NG=F"], "min_chg"),
          (["ETH-USD", "BNB-USD", "BTC-USD"], "min_chg"), (["SOL-USD", "GC=F", "SI=F"], "max_chg")]
    for (tick, k) in cm[:cnt(8, 2)]:
        tasks.append(mk(split, "L3", "l3-crypto-multi", "crypto", "YF:" + "+".join(tick),
                        {"tickers": tick, "kind": k}, ["yf:main"]))
    for idx in ["VNINDEX", "HNXINDEX"][:cnt(2, 1)]:
        tasks.append(mk(split, "L3", "l3-index", "vn_stock", idx,
                        {"kind": "pct_change" if is_main else "max_close"}, ["idx:" + idx]))
    ma = [("max_cat", "2026-09"), ("count_ge_5", "2026"), ("gdp_max_q", "2026")]
    for (k, w) in ma[:cnt(3, 0)]:
        tasks.append(mk(split, "L3", "l3-macro-agg", "macro", "%s@%s" % (k, w),
                        {"agg": k, "window": w}, ["cpi:full", "gdp:full"]))

    # ---------------- L4 ----------------
    for s in FUT:
        tasks.append(mk(split, "L4", "l4-future", "vn_stock", s, {"metric": "lnst_tong"}, ["fs:" + s]))
    mf_main = [("cpi_total", "2026-10"), ("core", "2026-10"), ("gdp", "Q4/2026")]
    mf_hold = [("cat_transport", "2026-10")]
    for (k, per) in (mf_main if is_main else mf_hold):
        tasks.append(mk(split, "L4", "l4-future", "macro", "%s@%s" % (k, per),
                        {"series": k, "period": per}, ["cpi:full", "gdp:full"]))
    gf_fut = gf.take(cnt(3, 1), prefer=gf_l2)
    for s in gf_fut:
        tasks.append(mk(split, "L4", "l4-future", "gold_fx", "%s@%s" % (s, "31/10" if is_main else "01/11"),
                        {"date": "31/10" if is_main else "01/11"}, ["msn:main", "yf:main"]))
    fakes = (FAKE_VN[:8] + [FAKE_CRYPTO[0]]) if is_main else FAKE_VN[8:10]
    for s in fakes:
        subj = "crypto" if s in FAKE_CRYPTO else "vn_stock"
        tasks.append(mk(split, "L4", "l4-nonexist", subj, s, {}, ["res:" + s]))
    for s in (["ANV", "PDR", "SCR", "SBT"] if is_main else ["VJC"]):
        tasks.append(mk(split, "L4", "l4-narrative", "vn_stock", s, {"days": 10}, ["vnq10:" + s]))
    for s in (["ETHUSDT", "BTCUSDT"] if is_main else ["ETHUSDT"]):
        tasks.append(mk(split, "L4", "l4-narrative", "crypto", s,
                        {"days": 10 if is_main else 7}, ["cohlcv:" + s]))
    for s in (["XAGUSD", "EURVND", "JPYVND"] if is_main else []):
        tasks.append(mk(split, "L4", "l4-narrative", "gold_fx", s, {"days": 5}, ["msn:main"]))
    for s in SRC2:
        grp = "batch:energy1" if is_main else "batch:steel1"
        tasks.append(mk(split, "L4", "l4-2src", "vn_stock", s, {}, ["vnq:" + s, grp]))
    cr_src = ([("BTC", "BTC-USD", "BTCUSDT"), ("ETH", "ETH-USD", "ETHUSDT")] if is_main
              else [("ETH", "ETH-USD", "ETHUSDT")])
    for (nm, yfsym, ohsym) in cr_src:
        tasks.append(mk(split, "L4", "l4-2src", "crypto", nm, {"yf": yfsym, "ohlcv": ohsym},
                        ["yf:main", "cohlcv:" + ohsym, "msn:main"]))
    gf_src = [("XAGUSD", "SI=F"), ("XAUUSD", "GC=F")] if is_main else []
    for (a, b) in gf_src:
        tasks.append(mk(split, "L4", "l4-2src", "gold_fx", "%s vs %s" % (a, b),
                        {"msn_sym": a, "yf_sym": b}, ["msn:main", "yf:main"]))

    # ---------------- L5 ----------------
    for s in PROF:
        tasks.append(mk(split, "L5", "l5-profile", "vn_stock", s, {}, ["ov:" + s, "fd:" + s]))
    cr_prof = ([("SOL-USD", "profile"), ("BNB-USD", "profile")] if is_main else [("BTC-USD", "chg_vol")])
    for (s, k) in cr_prof:
        tasks.append(mk(split, "L5", "l5-profile", "crypto", s, {"kind": k}, ["yf:main"]))
    for name, (head, peers) in pk[:cnt(8, 2)]:
        tasks.append(mk(split, "L5", "l5-compare", "vn_stock", "PEER:" + name, {"group": name}, ["peer:" + name]))
    cmp_cr = ([("ETH-USD", "SOL-USD", "chg"), ("SOL-USD", "BNB-USD", "chg"), ("BTC-USD", "ETH-USD", "chg"),
               ("BTC-USD", "BNB-USD", "chg"), ("BTCUSDT", "ETHUSDT", "ohlcv_chg")]
              if is_main else [("SOL-USD", "BNB-USD", "gap")])
    for (a, b, k) in cmp_cr:
        pl = ["cohlcv:" + a, "cohlcv:" + b] if a.endswith("USDT") else ["yf:main"]
        tasks.append(mk(split, "L5", "l5-compare", "crypto", a, {"peer": b, "kind": k}, pl))
    for s in gf.take(cnt(3, 1)):
        tasks.append(mk(split, "L5", "l5-compare", "gold_fx", s,
                        {"kind": "pair" if is_main else "max_move"}, ["msn:main", "yf:main"]))
    vals = (["FOX", "VIC", "KDH", "NLG", "DXG", "PDR", "SCR", "VRE", "KBC", "POM"]
            if is_main else ["SCS", "HAH", "VOS"])
    for s in vals:
        tasks.append(mk(split, "L5", "l5-valuation", "vn_stock", s, {}, ["val:" + s]))

    return tasks


def probe_list(tasks):
    """Dedupe payload key → (key, tool, params)."""
    spec = {}
    def add(key, tool, params):
        spec[key] = {"key": key, "tool": tool, "params": params}

    for t in tasks:
        for k in t["payloads"]:
            if k.startswith("vnq:"):
                s = k.split(":")[1]
                add(k, "vn_quote_history", {"symbol": s, "days": 5, "summary": True})
            elif k.startswith("vnq10:"):
                s = k.split(":")[1]
                add(k, "vn_quote_history", {"symbol": s, "days": 10, "summary": False})
            elif k.startswith("fs:"):
                add(k, "financial_statements", {"symbol": k.split(":")[1], "period": "quarter", "periods_n": 4})
            elif k.startswith("fd:"):
                add(k, "financial_detail", {"symbol": k.split(":")[1], "statement": "KQKD", "periods_n": 4})
            elif k.startswith("tech:"):
                add(k, "signals_technical", {"symbol": k.split(":")[1], "interval": "1D"})
            elif k.startswith("val:"):
                add(k, "valuation_run", {"symbol": k.split(":")[1]})
            elif k.startswith("ov:"):
                add(k, "stock_overview", {"symbol": k.split(":")[1]})
            elif k.startswith("vst:"):
                add(k, "vs_overview_trading", {"symbol": k.split(":")[1]})
            elif k.startswith("peer:"):
                name = k.split(":")[1]
                head, peers = PEER_GROUPS[name]
                add(k, "peer_compare", {"symbol": head, "peers": peers})
            elif k.startswith("batch:"):
                add(k, "vn_equity_quote_batch", {"symbols": GROUPS[k.split(":")[1]]})
            elif k.startswith("movers:"):
                add(k, "market_movers", {"top_n": 5, "universe": k.split(":")[1]})
            elif k.startswith("idx:"):
                add(k, "vn_index_ohlcv", {"symbol": k.split(":")[1], "count": 10})
            elif k.startswith("cs:"):
                pass  # crypto_spot: bỏ — binance 429 thường trực, đã chuyển sang yf + vn_crypto_ohlcv
            elif k.startswith("cohlcv:"):
                add(k, "vn_crypto_ohlcv", {"symbol": k.split(":")[1], "days": 10})
            elif k.startswith("res:"):
                add(k, "symbol_resolve", {"query": k.split(":")[1]})
            elif k.startswith("techgrp:"):
                g = GROUPS[k.split(":")[1]]
                for s in g:
                    add("tech:" + s, "signals_technical", {"symbol": s, "interval": "1D"})
            elif k == "msn:main":
                add(k, "vn_msn_fx_gold", {"symbols": ["XAUUSD", "XAGUSD", "USDVND", "EURVND", "JPYVND",
                                                      "USDJPY", "EURUSD", "GBPUSD", "USDCNY", "KRWVND"], "days": 8})
            elif k == "yf:main":
                add(k, "yf_commodities", {"tickers": ["GC=F", "SI=F", "NG=F", "HG=F", "BZ=F", "CL=F",
                                                      "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
                                                      "GBPUSD=X", "JPY=X"], "period": "5d", "interval": "1d"})
            elif k == "cpi:full":
                add(k, "vs_indicator_data", {"indicator": "CPI", "from_date": "2025-12-01"})
            elif k == "gdp:full":
                add(k, "vs_indicator_data", {"indicator": "GDP"})
    return spec


def main():
    pools = {"vn": Pool(VN), "cr": Pool(CRYPTO), "gf": Pool(GF),
             "mu": Pool(list(MACRO_CPI.keys()) + ["gdp"])}
    main_tasks = build("main", pools)
    # holdout: pool thực thể sạch riêng (không đụng main) — reset riêng bằng take_clean
    pools2 = {"vn": Pool(VN), "cr": Pool(CRYPTO), "gf": Pool(GF),
              "mu": Pool(list(MACRO_CPI.keys()) + ["gdp"])}
    # đánh dấu các thực thể đã được main dùng (usage>0) để holdout tránh
    for x, u in pools["vn"].used.items():
        pools2["vn"].used[x] = 99 if u else 0
    for x, u in pools["cr"].used.items():
        pools2["cr"].used[x] = 99 if u else 0
    # GF: pool nhỏ (14) — holdout dùng chung pool với counter RIÊNG (task holdout vẫn mới;
    # tái dùng thực thể gf giữa 2 split chấp nhận được, ghi chú registry)
    pools2["gf"] = Pool(GF)
    for x, u in pools["mu"].used.items():
        pools2["mu"].used[x] = 99 if u else 0
    # take_clean lọc used==0
    for p in pools2.values():
        p.items = [x for x in p.items if p.used[x] == 0]
        p.used = {x: 0 for x in p.items}
    hold_tasks = build("holdout", pools2)

    for split, ts in (("main", main_tasks), ("holdout", hold_tasks)):
        for i, t in enumerate(ts, 1):
            t["id"] = "fin-%s-%s-%d" % (t["level"].lower(), t["family"].split("-", 1)[1], 100 + i if split == "main" else 900 + i)

    # kiểm bảng
    from collections import Counter
    for split, ts in (("main", main_tasks), ("holdout", hold_tasks)):
        lv = Counter(t["level"] for t in ts)
        sub = Counter(t["subject"] for t in ts)
        fam = Counter(t["family"] for t in ts)
        print("== %s: %d task ==" % (split, len(ts)))
        print("  theo mức:", dict(sorted(lv.items())))
        print("  theo loại:", dict(sorted(sub.items())))
        print("  theo họ:", dict(sorted(fam.items())))
    # kiểm usage ≤2 (main + holdout riêng)
    for name, p in (("main", pools), ("holdout", pools2)):
        bad = {k: v for k, v in p["vn"].used.items() if v > 2}
        badc = {k: v for k, v in p["cr"].used.items() if v > 2}
        badg = {k: v for k, v in p["gf"].used.items() if v > 2}
        print("  usage>2 [%s]: vn=%s cr=%s gf=%s" % (name, bad, badc, badg))
    # overlap main/holdout singles
    m_set = {t["entity"] for t in main_tasks if ":" not in t["entity"]}
    h_set = {t["entity"] for t in hold_tasks if ":" not in t["entity"]}
    ov = m_set & h_set
    print("  overlap main∩holdout (single):", ov if ov else "KHONG")

    probes = probe_list(main_tasks + hold_tasks)
    print("== probe list: %d key ==" % len(probes))
    bytool = Counter(v["tool"] for v in probes.values())
    print("  theo tool:", dict(sorted(bytool.items())))

    with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"snapshot": SNAP, "main": main_tasks, "holdout": hold_tasks}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(HERE, "probe_list.json"), "w", encoding="utf-8") as f:
        json.dump(sorted(probes.values(), key=lambda x: (x["tool"], x["key"])), f, ensure_ascii=False, indent=1)
    print("đã ghi manifest.json + probe_list.json")


if __name__ == "__main__":
    main()
