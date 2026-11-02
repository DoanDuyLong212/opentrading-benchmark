# -*- coding: utf-8 -*-
"""fam_a.py — builders cho 12 họ task L1–L2. Trả về dict spec cho build_main.py."""
import re
from fam_util import (UNITS, p30, pday, pmonth, pq, pq2, nextq, r2, val_check, val_check_abs,
                      unit_check, period_check, src_check, evnum, fs_find, GF_UNIT,
                      msn_series, yf_item, cpi_pick, gdp_pick)

MACRO_CPI = {
    "cpi_total": "CHỈ SỐ GIÁ TIÊU DÙNG",
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
MACRO_LABEL = {"cpi_total": "CPI (chỉ số giá tiêu dùng)", "core": "lạm phát cơ bản"}

BCTC_ROWS = {
    "lnst_tong": ("Tổng LNST", r"^Tổng LNST", r"LNST của CĐ Ngân hàng mẹ"),
    "lnst_dn": ("LNST thu nhập DN", r"^LNST thu nhập DN", r"LNST của CĐ cty mẹ"),
    "lnst_me": ("LNST của CĐ cty mẹ", r"LNST của CĐ (cty|Ngân hàng) mẹ", r"^LNST thu nhập DN"),
    "doanh_thu": ("Doanh thu thuần", r"Doanh thu thuần", None),
    "loi_nhuan_gop": ("Lợi nhuận gộp", r"Lợi nhuận gộp", None),
}
BCTC_Q = {
    "lnst_tong": "Lợi nhuận sau thuế (LNST) **hợp nhất** quý gần nhất của **%s** là bao nhiêu? Quy ra **tỷ đồng**.",
    "lnst_dn": "Lợi nhuận sau thuế (LNST) **hợp nhất** quý gần nhất của **%s** là bao nhiêu? Quy ra **tỷ đồng**.",
    "lnst_me": "**LNST của cổ đông công ty mẹ** quý gần nhất của **%s** là bao nhiêu? Quy ra **tỷ đồng**.",
    "doanh_thu": "**Doanh thu thuần** quý gần nhất của **%s** là bao nhiêu? Quy ra **tỷ đồng**.",
    "loi_nhuan_gop": "**Lợi nhuận gộp** quý gần nhất của **%s** là bao nhiêu? Quy ra **tỷ đồng**.",
}
SCHEMA_UNIT = '{\n  "value": 0,\n  "unit": "%s",\n  "period": "%s",\n  "source": "%s",\n  "note": "(tuỳ chọn)"\n}'
SCHEMA_LINE = '{\n  "value": 0,\n  "unit": "%s",\n  "period": "%s",\n  "source": "%s",\n  "line": "tên dòng chỉ tiêu trong báo cáo",\n  "note": "(tuỳ chọn)"\n}'
# LƯU Ý (vá leak 02/11): KHÔNG còn schema riêng cho refusal — task bẫy dùng đúng
# SCHEMA_UNIT (value placeholder 0) để format đề không bộc lộ "đây là task từ chối".
# Quy tắc "không có dữ liệu → value null + lý do" nằm trong Ràng buộc chung của mọi task.


# ---------------------------------------------------------------- L1
def f_l1_quote_vn(t, env):
    k = t["payloads"][0]; sym = t["entity"]; d = env[k]["data"]
    v = float(d["last"]); dt = d["last_t"]
    sp = "phiên gần nhất"
    return {
        "title": "Giá đóng cửa %s" % sym, "family_code": "L1·A quote", "fb": "single-metric extraction",
        "q": "Giá đóng cửa (close) **phiên giao dịch gần nhất** của cổ phiếu **%s** là bao nhiêu?\n\nTrả lời theo đơn vị **nghìn đồng** (quy ước của MCP: `64,27` = 64.270 đ)." % sym,
        "schema": SCHEMA_UNIT % ("nghìn đồng", "phiên gần nhất (dd/mm/yyyy)", "vn_quote_history"),
        "rules": "- `unit` bắt buộc là **nghìn đồng**.\n- `period` nêu ngày phiên.",
        "scoring": "value",
        "expects": [unit_check("nghin_dong"), val_check(v), period_check(p30()), src_check("vn_quote_history")],
        "solution": {"value": v, "last_t": dt},
        "oracle": 'e = env(%r)\ncheck("last", float(e["data"]["last"]), gold["solution"]["value"])\ncheck("last_t", e["data"]["last_t"], gold["solution"]["last_t"])\n' % k,
    }


def f_l1_bctc(t, env):
    k = t["payloads"][0]; sym = t["entity"]; m = t["params"]["metric"]
    rows = env[k]["data"]["rows"]; periods = env[k]["data"]["periods"]
    label, pat, pat_alt = BCTC_ROWS[m]
    row = fs_find({"data": {"rows": rows}}, [pat])[0]
    p = periods[-1]; v = r2(row["values"][p] / 1e9)
    rejects = [pat_alt.replace("^", "").replace("(", "").replace(")", "").replace("|", " ")] if pat_alt else []
    expect_tokens = {"type": "tokens", "path": "line", "accept": [label], "reject": rejects}
    oracle = ('d = env(%r)["data"]\n'
              'row = next(r for r in d["rows"] if r["name"] == %r)\n'
              'p = d["periods"][-1]\n'
              'check("v_ty", round(row["values"][p] / 1e9, 2), gold["solution"]["value"])\n'
              'check("period", p, gold["solution"]["period"])\n') % (k, row["name"])
    return {
        "title": "%s — %s quý gần nhất" % (sym, label), "family_code": "L1·B bctc", "fb": "single-metric extraction (unit conversion)",
        "q": (BCTC_Q[m] % sym) + "\n\nGhi `line` = **đúng tên dòng chỉ tiêu** trong báo cáo bạn lấy số. Báo cáo gốc đơn vị VND.",
        "schema": SCHEMA_LINE % ("tỷ đồng", "quý gần nhất (VD: Q?/yyyy)", "financial_statements"),
        "rules": "- Bắt buộc ghi `line` = đúng **tên dòng chỉ tiêu** trong báo cáo (VD `%s`)." % label,
        "scoring": "value",
        "expects": [unit_check("ty_dong"), val_check(v), period_check(pq(p)), expect_tokens, src_check("financial_statements")],
        "solution": {"value": v, "period": p, "line": label},
        "oracle": oracle,
    }


def f_l1_quote_crypto(t, env):
    sym = t["entity"]; kind = t["params"]["kind"]
    if kind == "yf_price":
        it = yf_item(env, sym); v = float(it["price"])
        q = "Giá **%s** tại thời điểm snapshot của task là bao nhiêu, theo **USD**?" % sym
        expects = [val_check(v), unit_check("usd"), period_check(["2026-11-01", "01/11", "snapshot"]), src_check("yf_commodities")]
        oracle = 'it = yf_item(env("yf:main"), %r)\ncheck("price", float(it["price"]), gold["solution"]["value"])\n' % sym
        schema = SCHEMA_UNIT % ("USD", "(ngày dữ liệu)", "yf_commodities")
    elif kind == "ohlcv_close":
        k = t["payloads"][0]; cl = env[k]["data"]["closes"]; v = float(cl[-1]["c"])
        q = "Giá đóng cửa gần nhất của cặp **%s** (nguồn vnstock crypto) là bao nhiêu, theo **VND**?" % sym
        expects = [val_check(v), unit_check("dong"), period_check(["01/11", "2026-11-01"]), src_check("vn_crypto_ohlcv")]
        oracle = 'cl = env(%r)["data"]["closes"]\ncheck("close", float(cl[-1]["c"]), gold["solution"]["value"])\n' % k
        schema = SCHEMA_UNIT % ("đồng", "(ngày dữ liệu)", "vn_crypto_ohlcv")
    else:  # yf_chg (holdout)
        it = yf_item(env, sym); v = r2((it["price"] / it["prev"] - 1) * 100)
        q = "**%s** đã thay đổi bao nhiêu **%%** so với phiên trước (theo dữ liệu snapshot)?" % sym
        expects = [val_check_abs(v, 0.05), unit_check("pct"), src_check("yf_commodities")]
        oracle = 'it = yf_item(env("yf:main"), %r)\ncheck("chg", round((it["price"] / it["prev"] - 1) * 100, 2), gold["solution"]["value"])\n' % sym
        schema = SCHEMA_UNIT % ("%", "phiên gần nhất", "yf_commodities")
    return {"title": "Crypto — %s" % sym, "family_code": "L1·A quote", "fb": "single-metric extraction",
            "q": q, "schema": schema, "rules": "", "scoring": "value",
            "expects": expects, "solution": {"value": v}, "oracle": oracle}


def f_l1_quote_gf(t, env):
    sym = t["entity"]; day = t["params"]["day"]
    ser = msn_series(env)[sym]
    idx = -1 if day == "30/10" else -2
    v = float(ser[idx]["c"]); uk, us = GF_UNIT[sym]
    return {"title": "Giá đóng cửa %s phiên %s" % (sym, day), "family_code": "L1·A quote", "fb": "single-metric extraction",
            "q": "Giá đóng cửa **phiên %s/2026** của **%s** là bao nhiêu? (đơn vị: %s)" % (day, sym, us),
            "schema": SCHEMA_UNIT % (us, "(kỳ được hỏi)", "vn_msn_fx_gold"), "rules": "", "scoring": "value",
            "expects": [val_check(v), unit_check(uk), period_check(pday(day)), src_check("vn_msn_fx_gold")],
            "solution": {"value": v},
            "oracle": 'ser = msn_series(env)\ncheck("close", float(ser[%r][%d]["c"]), gold["solution"]["value"])\n' % (sym, idx)}


def f_l1_macro(t, env):
    pr = t["params"]; series = pr["series"]; period = pr["period"]; kind = pr.get("kind")
    if series == "gdp":
        v = gdp_pick(env, period); unit = "tỷ đồng"
        q = "**GDP** (tổng số, giá hiện hành) **%s** là bao nhiêu **tỷ đồng**?" % ("quý " + period[1:].lower().replace("q", ""))
        q = "**GDP** (tổng số, giá hiện hành) **%s** là bao nhiêu **tỷ đồng**?" % period.replace("Q", "quý ")
        expects = [val_check(v), unit_check("ty_dong"), period_check(pq(period)), src_check("vs_indicator_data")]
        oracle = 'check("gdp", gdp_pick(env, %r), gold["solution"]["value"])\n' % period
        schema = SCHEMA_UNIT % ("tỷ đồng", "(kỳ được hỏi)", "vs_indicator_data")
        title = "GDP %s" % period
    else:
        name = MACRO_CPI[series]; lab = MACRO_LABEL.get(series, "nhóm **%s**" % name)
        v = cpi_pick(env, name, period, kind)
        y, m = period.split("-"); mp = "tháng %d/%s" % (int(m), y)
        if kind == "pct":
            unit = "%"; q = "**%s** %s tăng bao nhiêu **%%** so với tháng 12/2025?" % (lab, mp)
            ub = "pct"
        else:
            unit = "điểm"; q = "Chỉ số giá **%s** %s (so với tháng 12/2025 = 100) là bao nhiêu **điểm**?" % (name, mp)
            ub = "diem"
        expects = [val_check_abs(v, 0.05), unit_check(ub), period_check(pmonth(period)), src_check("vs_indicator_data")]
        oracle = 'check("cpi", cpi_pick(env, %r, %r, %r), gold["solution"]["value"])\n' % (name, period, kind)
        schema = SCHEMA_UNIT % (unit, "(kỳ được hỏi)", "vs_indicator_data")
        title = "CPI %s — %s" % (series, mp)
    return {"title": title, "family_code": "L1·C macro", "fb": "single-metric extraction",
            "q": q, "schema": schema, "rules": "", "scoring": "value",
            "expects": expects, "solution": {"value": v}, "oracle": oracle}


# ---------------------------------------------------------------- L2
def f_l2_growth(t, env):
    k = t["payloads"][0]; sym = t["entity"]; d = env[k]["data"]
    dt = fs_find({"data": {"rows": d["rows"]}}, [r"Doanh thu thuần"])[0]
    periods = d["periods"]; pl, pp = periods[-1], periods[-2]
    vl, vp = float(dt["values"][pl]), float(dt["values"][pp])
    v = r2((vl / vp - 1) * 100)
    return {"title": "Tăng trưởng doanh thu %s (QoQ)" % sym, "family_code": "L2·A growth", "fb": "multi-step computation",
            "q": "Doanh thu thuần của **%s** **quý gần nhất** thay đổi bao nhiêu **%%** so với quý liền trước? (dấu âm nếu giảm)" % sym,
            "schema": SCHEMA_UNIT % ("%", "quý gần nhất so với quý liền trước", "financial_statements"),
            "rules": "- Giá trị gốc đơn vị VND — % thay đổi tính trên cùng đơn vị.",
            "scoring": "value",
            "expects": [val_check_abs(v, 0.1), unit_check("pct"), period_check(pq(pl)), src_check("financial_statements")],
            "solution": {"value": v},
            "oracle": ('d = env(%r)["data"]\n'
                       'dt = next(r for r in d["rows"] if "Doanh thu thuần" in r["name"])\n'
                       'ps = d["periods"]\n'
                       'check("growth", round((dt["values"][ps[-1]] / dt["values"][ps[-2]] - 1) * 100, 2), gold["solution"]["value"])\n') % k}


def f_l2_margin(t, env):
    k = t["payloads"][0]; sym = t["entity"]; d = env[k]["data"]
    rows = d["rows"]
    dt = fs_find({"data": {"rows": rows}}, [r"Doanh thu thuần"])[0]
    ln = next(x for x in fs_find({"data": {"rows": rows}}, [r"Lợi nhuận gộp về bán hàng", r"Lợi nhuận gộp hoạt động kinh doanh bảo hiểm"]) if x)
    p = d["periods"][-1]; i = len(d["periods"]) - 1
    v = r2(ln["values"][i] / dt["values"][i] * 100)
    return {"title": "Biên lợi nhuận gộp %s" % sym, "family_code": "L2·B margin", "fb": "multi-step computation",
            "q": "**Biên lợi nhuận gộp** của **%s** quý gần nhất là bao nhiêu **%%**? (lợi nhuận gộp ÷ doanh thu thuần)" % sym,
            "schema": SCHEMA_UNIT % ("%", "quý gần nhất", "financial_detail"),
            "rules": "", "scoring": "value",
            "expects": [val_check_abs(v, 0.1), unit_check("pct"), period_check(pq(p)), src_check("financial_detail")],
            "solution": {"value": v},
            "oracle": ('d = env(%r)["data"]\n'
                       'dt = next(r for r in d["rows"] if "Doanh thu thuần" in r["name"])["values"][-1]\n'
                       'ln = next(r for r in d["rows"] if "Lợi nhuận gộp" in r["name"])["values"][-1]\n'
                       'check("margin", round(ln / dt * 100, 2), gold["solution"]["value"])\n') % k}


def f_l2_ratio(t, env):
    k = t["payloads"][0]; sym = t["entity"]; v = float(env[k]["data"]["per"])
    return {"title": "P/E %s (valuation_run)" % sym, "family_code": "L2·C ratio", "fb": "single-metric extraction (source-pinned)",
            "q": "**P/E** của **%s** là bao nhiêu theo công cụ định giá **`valuation_run`** của MCP?" % sym,
            "schema": SCHEMA_UNIT % ("x", "snapshot 2026-11-01", "valuation_run"),
            "rules": "- Đề **chỉ định nguồn** `valuation_run`; nguồn khác có thể cho số khác và sẽ không được tính đúng.",
            "scoring": "value",
            "expects": [val_check(v), unit_check("x"), src_check("valuation_run")],
            "solution": {"value": v},
            "oracle": 'check("per", float(env(%r)["data"]["per"]), gold["solution"]["value"])\n' % k}


def f_l2_tech(t, env):
    k = t["payloads"][0]; sym = t["entity"]; v = float(env[k]["data"]["rsi14"])
    return {"title": "RSI-14 %s" % sym, "family_code": "L2·D technical", "fb": "single-metric extraction (computed)",
            "q": "**RSI-14** của **%s** trên khung ngày (**1D**) là bao nhiêu?" % sym,
            "schema": SCHEMA_UNIT % ("RSI-14", "(kỳ được hỏi)", "signals_technical"),
            "rules": "", "scoring": "value",
            "expects": [val_check_abs(v, 0.1), {"type": "unit", "path": "unit", "accept": ["RSI-14", "RSI 14", "RSI", "rsi14"]},
                        period_check(p30() + ["phiên gần nhất", "gần nhất"]), src_check("signals_technical")],
            "solution": {"value": v},
            "oracle": 'check("rsi", float(env(%r)["data"]["rsi14"]), gold["solution"]["value"])\n' % k}


def f_l2_crypto_x(t, env):
    sym = t["entity"]; pr = t["params"]; kind = pr["kind"]; day = pr["fx_day"]
    ser = msn_series(env)
    fx = float(ser["USDVND"][-1 if day == "30/10" else -2]["c"])
    if kind == "yf_to_vnd":
        it = yf_item(env, sym); v = r2(it["price"] * fx / 1e6)
        q = "Quy giá 1 **%s** (theo snapshot, USD) ra **VND** dùng tỷ giá **USD/VND đóng cửa phiên %s**. Trả lời theo **triệu đồng**." % (sym, day)
        expects = [val_check(v), unit_check("trieu_dong"), evnum([it["price"], fx], 2), src_check("yf_commodities", "vn_msn_fx_gold")]
        oracle = 'it = yf_item(env("yf:main"), %r)\nfx = float(msn_series(env)["USDVND"][%d]["c"])\ncheck("vnd_mtr", round(it["price"] * fx / 1e6, 2), gold["solution"]["value"])\n' % (sym, -1 if day == "30/10" else -2)
        schema = '{\n  "value": 0,\n  "unit": "triệu đồng",\n  "period": "snapshot 2026-11-01",\n  "source": "yf_commodities + vn_msn_fx_gold",\n  "note": "ghi rõ 2 số đầu vào (giá coin USD, tỷ giá)"\n}'
    else:  # yf_to_eur
        it = yf_item(env, sym); eu = float(ser["EURUSD"][-1]["c"]); v = r2(it["price"] / eu)
        q = "Quy giá 1 **%s** (theo snapshot, USD) ra **EUR** dùng tỷ giá **EUR/USD đóng cửa phiên 30/10**. Trả lời theo **EUR**." % sym
        expects = [val_check(v), {"type": "unit", "path": "unit", "accept": ["EUR"]}, evnum([it["price"], eu], 2), src_check("yf_commodities", "vn_msn_fx_gold")]
        oracle = 'it = yf_item(env("yf:main"), %r)\neu = float(msn_series(env)["EURUSD"][-1]["c"])\ncheck("eur", round(it["price"] / eu, 2), gold["solution"]["value"])\n' % sym
        schema = '{\n  "value": 0,\n  "unit": "EUR",\n  "period": "snapshot 2026-11-01",\n  "source": "yf_commodities + vn_msn_fx_gold",\n  "note": "ghi rõ 2 số đầu vào"\n}'
    return {"title": "Quy %s ra tiền pháp định" % sym, "family_code": "L2·E crypto-xasset", "fb": "cross-asset conversion",
            "q": q, "schema": schema, "rules": "- `note` **bắt buộc** nêu 2 số đầu vào (giá coin, tỷ giá).", "scoring": "value",
            "expects": expects, "solution": {"value": v}, "oracle": oracle}


def f_l2_gf_compare(t, env):
    sym = t["entity"]; day = t["params"]["day"]
    ser = msn_series(env)
    if sym in ser:
        cl = ser[sym]; idx = -1 if day == "30/10" else -2
        v = float(cl[idx]["c"]); prev = float(cl[idx - 1]["c"])
        oracle = 'cl = msn_series(env)[%r]\ncheck("close", float(cl[%d]["c"]), gold["solution"]["value"])\n' % (sym, idx)
    else:
        it = yf_item(env, sym); v = float(it["price"]); prev = float(it["prev"])
        oracle = 'it = yf_item(env("yf:main"), %r)\ncheck("price", float(it["price"]), gold["solution"]["value"])\n' % sym
    uk, us = GF_UNIT.get(sym, ("usd", "USD"))
    return {"title": "So sánh %s phiên %s" % (sym, day), "family_code": "L2·F fx", "fb": "single-metric + comparison",
            "q": "**%s** đóng cửa **phiên %s/2026** là bao nhiêu (**%s**)? So với phiên liền trước tăng hay giảm bao nhiêu — ghi trong `note`." % (sym, day, us),
            "schema": SCHEMA_UNIT % (us, "(kỳ được hỏi)", "vn_msn_fx_gold") ,
            "rules": "- `note` **bắt buộc** nêu số phiên liền trước hoặc mức thay đổi.", "scoring": "value",
            "expects": [val_check(v), unit_check(uk), period_check(pday(day)), evnum([prev], 1), src_check("vn_msn_fx_gold", "yf_commodities") if sym not in ser else src_check("vn_msn_fx_gold")],
            "solution": {"value": v, "prev": prev}, "oracle": oracle}


def f_l2_macro_calc(t, env):
    pr = t["params"]; calc = pr["calc"]; w = pr["window"]
    if calc == "gdp_qoq":
        qa, qb = "Q3/2026", "Q2/2026"
        va, vb = gdp_pick(env, qa), gdp_pick(env, qb); v = r2((va / vb - 1) * 100)
        q = "**GDP** (tổng số) **quý 3/2026** tăng bao nhiêu **%%** so với **quý 2/2026**?"
        period = pq2(qa, qb); sper = "quý được hỏi và kỳ đối chiếu"
        oracle = 'check("qoq", round((gdp_pick(env, %r) / gdp_pick(env, %r) - 1) * 100, 2), gold["solution"]["value"])\n' % (qa, qb)
    elif calc == "gdp_yoy":
        qa, qb = "Q3/2026", "Q3/2025"
        va, vb = gdp_pick(env, qa), gdp_pick(env, qb); v = r2((va / vb - 1) * 100)
        q = "**GDP** (tổng số) **quý 3/2026** tăng bao nhiêu **%%** so với **cùng kỳ năm trước** (quý 3/2025)?"
        period = pq2(qa, qb); sper = "quý được hỏi và cùng kỳ năm trước"
        oracle = 'check("yoy", round((gdp_pick(env, %r) / gdp_pick(env, %r) - 1) * 100, 2), gold["solution"]["value"])\n' % (qa, qb)
    elif calc == "cpi_gap":
        a = cpi_pick(env, "CHỈ SỐ GIÁ TIÊU DÙNG", "2026-09", "pct")
        b = cpi_pick(env, "LẠM PHÁT CƠ BẢN", "2026-09", "pct")
        v = r2(a - b)
        q = "**CPI** (chỉ số giá tiêu dùng, so tháng 12/2025) tháng 9/2026 cao hơn **lạm phát cơ bản** cùng tháng bao nhiêu **điểm %%**?"
        period = pmonth("2026-09"); sper = "tháng được hỏi"
        oracle = 'a = cpi_pick(env, "CHỈ SỐ GIÁ TIÊU DÙNG", "2026-09", "pct")\nb = cpi_pick(env, "LẠM PHÁT CƠ BẢN", "2026-09", "pct")\ncheck("gap", round(a - b, 2), gold["solution"]["value"])\n'
    else:  # cpi_avg / core_avg
        mon = w.split("/")[0].replace("T", "").split("-")
        months = list(range(int(mon[0]), int(mon[1]) + 1)); y = w.split("/")[1]
        name = "CHỈ SỐ GIÁ TIÊU DÙNG" if calc == "cpi_avg" else "LẠM PHÁT CƠ BẢN"
        vals = [cpi_pick(env, name, "%s-%02d" % (y, m), "pct") for m in months]
        v = r2(sum(vals) / len(vals))
        lab = "CPI (chỉ số giá tiêu dùng, so tháng 12/2025)" if calc == "cpi_avg" else "lạm phát cơ bản"
        q = "**%s** bình quân các tháng %s **%s** là bao nhiêu **%%**?" % (lab, ", ".join(str(m) for m in months), y)
        period = "T%s-T%s/%s" % (months[0], months[-1], y); sper = "kỳ bình quân được hỏi"
        oracle = 'vals = [cpi_pick(env, %r, "%s-%%02d" %% m, "pct") for m in %r]\ncheck("avg", round(sum(vals) / len(vals), 2), gold["solution"]["value"])\n' % (name, y, months)
    return {"title": "Macro — %s" % calc, "family_code": "L2·G macro-calc", "fb": "multi-step computation",
            "q": q, "schema": SCHEMA_UNIT % ("%", sper, "vs_indicator_data"),
            "rules": "", "scoring": "value",
            "expects": [val_check_abs(v, 0.1), unit_check("pct"), period_check(period if isinstance(period, list) else [period]), src_check("vs_indicator_data")],
            "solution": {"value": v}, "oracle": oracle}


FAMILIES_A = {
    "l1-quote-vn": f_l1_quote_vn,
    "l1-bctc": f_l1_bctc,
    "l1-quote-crypto": f_l1_quote_crypto,
    "l1-quote-gf": f_l1_quote_gf,
    "l1-macro": f_l1_macro,
    "l2-growth": f_l2_growth,
    "l2-margin": f_l2_margin,
    "l2-ratio": f_l2_ratio,
    "l2-tech": f_l2_tech,
    "l2-crypto-x": f_l2_crypto_x,
    "l2-gf-compare": f_l2_gf_compare,
    "l2-macro-calc": f_l2_macro_calc,
}
