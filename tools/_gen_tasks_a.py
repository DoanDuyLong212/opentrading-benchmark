# -*- coding: utf-8 -*-
"""Đặc tả task nhóm A: SMOKE (3) + L1 (5) + L2 (6)."""

TASKS_A = [
# ---------------------------------------------------------------- SMOKE
{
    "id": "smoke-quote-01", "group": "smoke", "title": "Smoke — giá đóng cửa HPG",
    "level": "SMOKE", "family": "smoke", "fb": "single-metric extraction",
    "entity": "HPG", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 10, "tools": ["vn_quote_history"], "payloads": ["qh_hpg"],
    "q_md": "## Đề bài\nGiá đóng cửa (close) **phiên giao dịch gần nhất** của cổ phiếu **HPG** là bao nhiêu? Trả lời theo **nghìn đồng** (quy ước của MCP: `64,27` = 64.270 đ).",
    "schema_md": '{\n  "value": 0,\n  "unit": "nghìn đồng",\n  "period": "phiên gần nhất (dd/mm/yyyy)",\n  "source": "vn_quote_history"\n}',
    "rules_md": "- `unit` phải là **nghìn đồng**.\n- `period` nêu ngày phiên.",
    "gold": {"scoring": "value", "expects": [
        {"type": "unit", "path": "unit", "accept": ["nghìn đồng", "nghìn đ", "k đồng"]},
        {"type": "value", "path": "value", "gold": 21.0, "tol": {"rel": 0.005}},
    ], "solution": {"value": 21.0}, "as_of": "2026-11-01T15:54:29.883479+07:00",
        "notes": "Smoke — tối giản schema, không tính vào điểm."},
    "oracle_body": 'e = env("vn_quote_history")\ncheck("last", float(e["data"]["last"]), gold["solution"]["value"])\n',
},
{
    "id": "smoke-agg-01", "group": "smoke", "title": "Smoke — trung bình 5 ngân hàng",
    "level": "SMOKE", "family": "smoke", "fb": "aggregation",
    "entity": "VCB+BID+CTG+TCB+MBB", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 10, "tools": ["vn_quote_history"], "payloads": ["banks5"],
    "q_md": "## Đề bài\nCho 5 mã **VCB, BID, CTG, TCB, MBB**: giá đóng cửa **phiên 30/10** của từng mã (theo **nghìn đồng**) và **trung bình** 5 mã là bao nhiêu?",
    "schema_md": '{\n  "values": {"VCB": 0, "BID": 0, "CTG": 0, "TCB": 0, "MBB": 0, "mean": 0},\n  "unit": "nghìn đồng",\n  "period": "phiên 2026-10-30",\n  "source": \'vn_quote_history\'\n}',
    "rules_md": "",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "values.VCB", "gold": 56.3, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.BID", "gold": 33.4, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.CTG", "gold": 30.3, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.TCB", "gold": 21.6, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.MBB", "gold": 19.3, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.mean", "gold": 32.18, "tol": {"rel": 0.005}},
        {"type": "unit", "path": "unit", "accept": ["nghìn đồng", "nghìn đ", "k đồng"]},
    ], "solution": {"VCB": 56.3, "BID": 33.4, "CTG": 30.3, "TCB": 21.6, "MBB": 19.3, "mean": 32.18},
        "as_of": "2026-11-01T15:57:50.079479+07:00", "notes": "Smoke — không tính điểm."},
    "oracle_body": ('b = {x["symbol"]: x["last"] for x in env("vn_quote_history")["data"]["banks"]}\n'
                    'vals = [b[s] for s in ["VCB", "BID", "CTG", "TCB", "MBB"]]\n'
                    'check("mean", round(sum(vals) / len(vals), 2), gold["solution"]["mean"])\n'
                    'for s in ["VCB", "BID", "CTG", "TCB", "MBB"]:\n'
                    '    check(s, float(b[s]), gold["solution"][s])\n'),
},
{
    "id": "smoke-trap-01", "group": "smoke", "title": "Smoke — mã không tồn tại",
    "level": "SMOKE", "family": "smoke", "fb": "unanswerable (entity trap)",
    "entity": "XYZX", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 10, "tools": ["symbol_resolve"], "payloads": ["resolve"],
    "q_md": "## Đề bài\nGiá đóng cửa gần nhất của cổ phiếu **XYZX** là bao nhiêu (**đồng**)?",
    "schema_md": '{\n  "value": null,\n  "reason": "lý do (nếu không trả lời được)",\n  "source": "symbol_resolve",\n  "note": "tuỳ chọn"\n}',
    "rules_md": "",
    "gold": {"scoring": "refusal",
             "refusal_tokens": ["không tồn tại", "không có", "không tìm thấy", "không hợp lệ", "mã không"],
             "solution": {"resolved_null": True},
             "as_of": "2026-11-01T15:57:53.093226+07:00", "notes": "Smoke — không tính điểm."},
    "oracle_body": 'd = env("symbol_resolve")["data"]\ncheck("resolved_null", d["resolved"] is None, True)\ncheck("no_candidates", d["candidates"], [])\n',
},
# ---------------------------------------------------------------- L1
{
    "id": "fin-l1-quote-01", "group": "pilot", "title": "Giá đóng cửa HPG (bẫy đơn vị nghìn↔đồng)",
    "level": "L1", "family": "L1·A quote", "fb": "single-metric extraction",
    "entity": "HPG", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 10, "tools": ["vn_quote_history"], "payloads": ["qh_hpg"],
    "q_md": "## Đề bài\nGiá đóng cửa (close) **phiên giao dịch gần nhất** của cổ phiếu **HPG** là bao nhiêu?\n\nTrả lời theo đơn vị **nghìn đồng** (quy ước của MCP: `64,27` = 64.270 đ).",
    "schema_md": '{\n  "value": 0,\n  "unit": "nghìn đồng",\n  "period": "phiên gần nhất (dd/mm/yyyy)",\n  "source": "vn_quote_history",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "- `unit` bắt buộc là **nghìn đồng** (đề yêu cầu).\n- `period` phải nêu rõ ngày phiên.",
    "gold": {"scoring": "value", "expects": [
        {"type": "unit", "path": "unit", "accept": ["nghìn đồng", "nghìn đ", "k đồng"]},
        {"type": "value", "path": "value", "gold": 21.0, "tol": {"rel": 0.005}},
        {"type": "period", "path": "period", "accept": ["30/10", "30-10", "30.10", "2026-10-30"]},
        {"type": "str", "path": "source", "accept": ["vn_quote_history"]},
    ], "solution": {"value": 21.0}, "as_of": "2026-11-01T15:54:29.883479+07:00",
        "notes": "Bẫy đơn vị: candles = nghìn đồng; trả 21000 với unit 'đồng' = sai đơn vị (unit check đứng trước value để error_type chuẩn = sai_don_vi)."},
    "oracle_body": 'e = env("vn_quote_history")\ncheck("last", float(e["data"]["last"]), gold["solution"]["value"])\ncheck("last_t", e["data"]["last_t"], "2026-10-30")\n',
},
{
    "id": "fin-l1-quote-02", "group": "pilot", "title": "Giá BTC tại snapshot",
    "level": "L1", "family": "L1·A quote", "fb": "single-metric extraction",
    "entity": "BTCUSDT", "asset": "crypto", "zone": "yellow", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 10, "tools": ["crypto_spot"], "payloads": ["btc"],
    "q_md": "## Đề bài\nGiá **Bitcoin** (cặp **BTCUSDT**) tại thời điểm snapshot của task là bao nhiêu, theo **USD**?",
    "schema_md": '{\n  "value": 0,\n  "unit": "USD",\n  "period": "snapshot 2026-11-01",\n  "source": "crypto_spot",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "- `period` ghi thời điểm snapshot (ngày lấy dữ liệu).",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 78109, "tol": {"rel": 0.005}},
        {"type": "unit", "path": "unit", "accept": ["USD", "USDT"]},
        {"type": "period", "path": "period", "accept": ["2026-11-01", "01/11", "snapshot"]},
        {"type": "str", "path": "source", "accept": ["crypto_spot"]},
    ], "solution": {"value": 78109}, "as_of": "2026-11-01T15:54:32.586909+07:00",
        "notes": "live 24h ticker → bắt buộc snapshot replay; zone yellow."},
    "oracle_body": 'tk = env("crypto_spot")["data"]["tickers"][0]\ncheck("btc_last", float(tk["last"]), gold["solution"]["value"])\n',
},
{
    "id": "fin-l1-gold-01", "group": "pilot", "title": "Vàng thế giới XAUUSD đóng cửa phiên gần nhất",
    "level": "L1", "family": "L1·A quote", "fb": "single-metric extraction",
    "entity": "XAUUSD", "asset": "gold_fx", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 10, "tools": ["vn_msn_fx_gold"], "payloads": ["fxgold"],
    "q_md": "## Đề bài\nGiá **vàng thế giới** (**XAUUSD**) đóng cửa phiên giao dịch gần nhất là bao nhiêu **USD/oz**? Nêu rõ phiên nào.",
    "schema_md": '{\n  "value": 0,\n  "unit": "USD/oz",\n  "period": "phiên gần nhất (dd/mm/yyyy)",\n  "source": "vn_msn_fx_gold",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 3875.02, "tol": {"rel": 0.005}},
        {"type": "unit", "path": "unit", "accept": ["USD/oz", "USD oz", "USD/ounce"]},
        {"type": "period", "path": "period", "accept": ["30/10", "30-10", "30.10", "2026-10-30"]},
        {"type": "str", "path": "source", "accept": ["vn_msn_fx_gold"]},
    ], "solution": {"value": 3875.02}, "as_of": "2026-11-01T15:54:32.785351+07:00",
        "notes": "Chuỗi XAUUSD trong vn_msn_fx_gold; chuỗi giảm 2 phiên cuối 4067.04→4020.42→3875.02."},
    "oracle_body": ('ser = {x["symbol"]: x["closes"] for x in env("vn_msn_fx_gold")["data"]["series"]}\n'
                    'check("xau_close", float(ser["XAUUSD"][-1]["c"]), gold["solution"]["value"])\n'
                    'check("xau_date", ser["XAUUSD"][-1]["t"][:10], "2026-10-30")\n'),
},
{
    "id": "fin-l1-bctc-01", "group": "pilot", "title": "LNST hợp nhất quý gần nhất của VCB (bẫy đơn vị VND→tỷ + bẫy dòng mẹ/hợp nhất)",
    "level": "L1", "family": "L1·B bctc", "fb": "single-metric extraction (unit conversion)",
    "entity": "VCB", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 15, "tools": ["financial_statements"], "payloads": ["fs_vcb"],
    "q_md": "## Đề bài\nLợi nhuận sau thuế (LNST) **hợp nhất** quý gần nhất của **VCB** là bao nhiêu? Quy đổi ra **tỷ đồng**.",
    "schema_md": '{\n  "value": 0,\n  "unit": "tỷ đồng",\n  "period": "quý gần nhất (VD: Q?/yyyy)",\n  "source": "financial_statements",\n  "line": "tên dòng chỉ tiêu trong báo cáo",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "- Bắt buộc ghi `line` = đúng **tên dòng chỉ tiêu** trong báo cáo bạn lấy số (VD `Tổng LNST`, `LNST của CĐ Ngân hàng mẹ`...).\n- Báo cáo gốc đơn vị VND — đáp án phải quy ra **tỷ đồng**.",
    "gold": {"scoring": "value", "expects": [
        {"type": "unit", "path": "unit", "accept": ["tỷ đồng", "tỷ đ", "tỷ"]},
        {"type": "value", "path": "value", "gold": 14550.96, "tol": {"rel": 0.005}},
        {"type": "period", "path": "period", "accept": ["Q2/2026", "quý 2/2026", "Q2 2026", "Q2/26"]},
        {"type": "tokens", "path": "line", "accept": ["Tổng LNST", "hợp nhất"],
         "reject": ["ngân hàng mẹ", "cty mẹ", "công ty mẹ"]},
        {"type": "str", "path": "source", "accept": ["financial_statements"]},
    ], "solution": {"value": 14550.96},
        "as_of": "2026-11-01T15:54:29.686603+07:00",
        "notes": "Hai dòng chỉ tiêu cách nhau 0.06% (14550.96 vs 14542.28) — tolerance KHÔNG phân biệt được; check `line` mới phân biệt. Quý gần nhất = Q2/2026 (Q3/2026 chưa công bố tại snapshot)."},
    "oracle_body": ('rows = env("financial_statements")["data"]["statements"]["Kết quả kinh doanh"]\n'
                    'row = next(r for r in rows if "Tổng LNST" in r["name"])\n'
                    'check("lnst_ty", round(row["values"]["Q2/2026"] / 1e9, 2), gold["solution"]["value"])\n'),
},
{
    "id": "fin-l1-macro-01", "group": "pilot", "title": "CPI tháng gần nhất (bẫy nhiều chuỗi chỉ số)",
    "level": "L1", "family": "L1·C macro", "fb": "single-metric extraction",
    "entity": "CPI", "asset": "macro", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 15, "tools": ["vs_indicator_data"], "payloads": ["cpi"],
    "q_md": "## Đề bài\nCPI (chỉ số giá tiêu dùng) cả nước **tháng gần nhất đã công bố** tăng bao nhiêu **%** so với tháng 12/2025? Nêu rõ tháng nào.",
    "schema_md": '{\n  "value": 0,\n  "unit": "%",\n  "period": "tháng gần nhất đã công bố (VD: Tháng ?/yyyy)",\n  "source": "vs_indicator_data",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 5.08, "tol": {"abs": 0.05}},
        {"type": "unit", "path": "unit", "accept": ["%", "phần trăm"]},
        {"type": "period", "path": "period", "accept": ["tháng 9/2026", "9/2026", "tháng 9", "09/2026", "t9/2026"]},
        {"type": "str", "path": "source", "accept": ["vs_indicator_data"]},
    ], "solution": {"value": 5.08}, "as_of": "2026-11-01T15:57:51.287003+07:00",
        "notes": "Tool trả nhiều chuỗi cùng khớp 'CPI': chỉ số gốc 105.08, % so T12 5.08, lạm phát cơ bản 4.45, các nhóm ngành... Chỉ 5.08 đúng."},
    "oracle_body": ('rows = env("vs_indicator_data")["data"]["rows"]\n'
                    'c = [r for r in rows if "CHỈ SỐ GIÁ TIÊU DÙNG" in r["indicator"] and float(r["value"]) < 20]\n'
                    'check("one_pct_row", len(c), 1)\n'
                    'check("cpi_pct", float(c[0]["value"]), gold["solution"]["value"])\n'),
},
# ---------------------------------------------------------------- L2
{
    "id": "fin-l2-growth-01", "group": "pilot", "title": "Tăng trưởng doanh thu VNM QoQ",
    "level": "L2", "family": "L2·A growth", "fb": "multi-step computation",
    "entity": "VNM", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 20, "tools": ["financial_statements"], "payloads": ["fs_vnm"],
    "q_md": "## Đề bài\nDoanh thu thuần của **VNM** **quý gần nhất** thay đổi bao nhiêu **%** so với quý liền trước (dấu âm nếu giảm)? Nêu rõ hai quý đối chiếu.",
    "schema_md": '{\n  "value": 0,\n  "unit": "%",\n  "period": "quý gần nhất so với quý trước (VD: Q?/yyyy vs Q?/yyyy)",\n  "source": "financial_statements",\n  "note": "số liệu dùng để tính"\n}',
    "rules_md": "- Giá trị gốc đơn vị VND — % thay đổi tính trên cùng đơn vị.\n- Dấu âm = giảm.",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": -2.03, "tol": {"abs": 0.1}},
        {"type": "unit", "path": "unit", "accept": ["%", "phần trăm"]},
        {"type": "period", "path": "period", "accept": ["Q3/2026", "quý 3/2026", "Q3 2026", "Q3/26"]},
        {"type": "str", "path": "source", "accept": ["financial_statements"]},
    ], "solution": {"value": -2.03}, "as_of": "2026-11-01T15:54:29.489141+07:00",
        "notes": "Q3/2026 = 18,465,190,628,493; Q2/2026 = 18,847,347,464,988 → -2.03%."},
    "oracle_body": ('row = env("financial_statements")["data"]["statements"]["Kết quả kinh doanh"][0]\n'
                    'v = row["values"]\n'
                    'check("growth_qoq", round((v["Q3/2026"] / v["Q2/2026"] - 1) * 100, 2), gold["solution"]["value"])\n'),
},
{
    "id": "fin-l2-margin-01", "group": "pilot", "title": "Biên lợi nhuận gộp MWG Q3/2026",
    "level": "L2", "family": "L2·B margin", "fb": "multi-step computation",
    "entity": "MWG", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 20, "tools": ["financial_detail"], "payloads": ["mwg_kqkd"],
    "q_md": "## Đề bài\n**Biên lợi nhuận gộp** của **MWG** quý **Q3/2026** là bao nhiêu **%**? (lợi nhuận gộp ÷ doanh thu thuần).",
    "schema_md": '{\n  "value": 0,\n  "unit": "%",\n  "period": "Q3/2026",\n  "source": "financial_detail",\n  "note": "số liệu dùng để tính"\n}',
    "rules_md": "",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 21.71, "tol": {"abs": 0.1}},
        {"type": "unit", "path": "unit", "accept": ["%", "phần trăm"]},
        {"type": "period", "path": "period", "accept": ["Q3/2026", "quý 3/2026", "Q3 2026", "Q3/26"]},
        {"type": "str", "path": "source", "accept": ["financial_detail"]},
    ], "solution": {"value": 21.71}, "as_of": "2026-11-01T15:54:29.386552+07:00",
        "notes": "LN gộp 11,421 / DT thuần 52,614 (đơn vị tỷ đồng) = 21.71%."},
    "oracle_body": ('d = env("financial_detail")["data"]\n'
                    'i = d["periods"].index("Q3/2026")\n'
                    'rows = d["rows"]\n'
                    'dt = next(r for r in rows if "Doanh thu thuần" in r["name"])["values"][i]\n'
                    'ln = next(r for r in rows if "Lợi nhuận gộp" in r["name"])["values"][i]\n'
                    'check("margin", round(ln / dt * 100, 2), gold["solution"]["value"])\n'),
},
{
    "id": "fin-l2-ratio-01", "group": "pilot", "title": "P/E FPT theo valuation_run (bẫy 2 nguồn khác số)",
    "level": "L2", "family": "L2·C ratio", "fb": "single-metric extraction (source-pinned)",
    "entity": "FPT", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 20, "tools": ["valuation_run"], "payloads": ["fpt_val"],
    "q_md": "## Đề bài\n**P/E** của **FPT** là bao nhiêu theo công cụ định giá **`valuation_run`** của MCP?",
    "schema_md": '{\n  "value": 0,\n  "unit": "x",\n  "period": "snapshot 2026-11-01",\n  "source": "valuation_run",\n  "note": "giá và EPS dùng để tính"\n}',
    "rules_md": "- Đề **chỉ định nguồn** `valuation_run` — nguồn khác có thể cho số khác (VD P/E từ dữ liệu fundamentals) và sẽ **không** được tính đúng.",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 8.75, "tol": {"rel": 0.005}},
        {"type": "unit", "path": "unit", "accept": ["x", "lần"]},
        {"type": "str", "path": "source", "accept": ["valuation_run"]},
    ], "solution": {"value": 8.75}, "as_of": "2026-11-01T15:54:35.771025+07:00",
        "notes": "valuation_run: price 52,700 / EPS trailing 6,021.21 = 8.75. vn_fundamentals cho P/E 20.96 (kỳ Q3/2026) — nguồn khác số khác, đúng chủ đích đề chỉ định nguồn."},
    "oracle_body": 'check("per", float(env("valuation_run")["data"]["per"]), gold["solution"]["value"])\n',
},
{
    "id": "fin-l2-tech-01", "group": "pilot", "title": "RSI-14 VCB khung ngày",
    "level": "L2", "family": "L2·D technical", "fb": "single-metric extraction (computed)",
    "entity": "VCB", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 15, "tools": ["signals_technical"], "payloads": ["tech"],
    "q_md": "## Đề bài\n**RSI-14** của **VCB** trên khung ngày (**1D**) là bao nhiêu?",
    "schema_md": '{\n  "value": 0,\n  "unit": "RSI-14",\n  "period": "đến phiên gần nhất (dd/mm/yyyy)",\n  "source": "signals_technical",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 44.01, "tol": {"abs": 0.1}},
        {"type": "unit", "path": "unit", "accept": ["RSI-14", "RSI 14", "RSI", "rsi14"]},
        {"type": "period", "path": "period", "accept": ["30/10", "30-10", "30.10", "2026-10-30"]},
        {"type": "str", "path": "source", "accept": ["signals_technical"]},
    ], "solution": {"value": 44.01}, "as_of": "2026-11-01T15:57:53.193466+07:00",
        "notes": "computed-local từ nến 1D; deterministic theo snapshot."},
    "oracle_body": ('rows = env("signals_technical")["data"]["rows"]\n'
                    'v = next(r for r in rows if r["symbol"] == "VCB")["rsi14"]\n'
                    'check("rsi14", float(v), gold["solution"]["value"])\n'),
},
{
    "id": "fin-l2-crypto-01", "group": "pilot", "title": "Quy BTC ra VND (cross-asset 2 nguồn)",
    "level": "L2", "family": "L2·E crypto-xasset", "fb": "cross-asset conversion",
    "entity": "BTCUSDT+USDVND", "asset": "crypto", "zone": "yellow", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 20, "tools": ["crypto_spot", "vn_msn_fx_gold"], "payloads": ["btc", "fxgold"],
    "q_md": "## Đề bài\nQuy giá 1 **Bitcoin** (cặp **BTCUSDT**, giá theo snapshot) ra **VND**, dùng tỷ giá **USD/VND đóng cửa phiên 30/10**. Trả lời theo **triệu đồng**.",
    "schema_md": '{\n  "value": 0,\n  "unit": "triệu đồng",\n  "period": "snapshot 2026-11-01",\n  "source": "crypto_spot + vn_msn_fx_gold",\n  "note": "ghi rõ giá BTC và tỷ giá dùng để tính"\n}',
    "rules_md": "- `note` **bắt buộc** nêu 2 số đầu vào (giá BTC, tỷ giá USD/VND).",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 2015.37, "tol": {"rel": 0.005}},
        {"type": "unit", "path": "unit", "accept": ["triệu đồng", "triệu đ", "million vnd"]},
        {"type": "evidence", "path": "note", "paths": ["note"], "numbers": [78109, 25802], "min_hits": 2},
        {"type": "str_all", "path": "source", "accept": ["crypto_spot", "vn_msn_fx_gold"]},
    ], "solution": {"value": 2015.37}, "as_of": "2026-11-01T15:54:32.586909+07:00",
        "notes": "78,109 × 25,802 = 2,015,368,418 VND = 2,015.37 triệu đồng."},
    "oracle_body": ('btc = env("crypto_spot")["data"]["tickers"][0]["last"]\n'
                    'ser = {x["symbol"]: x["closes"] for x in env("vn_msn_fx_gold")["data"]["series"]}\n'
                    'fx = ser["USDVND"][-1]["c"]\n'
                    'check("btc_vnd_mtr", round(btc * fx / 1e6, 2), gold["solution"]["value"])\n'),
},
{
    "id": "fin-l2-gold-01", "group": "pilot", "title": "Tỷ giá USD/VND phiên 30/10 + so phiên trước",
    "level": "L2", "family": "L2·F fx", "fb": "single-metric + comparison",
    "entity": "USDVND", "asset": "gold_fx", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 15, "tools": ["vn_msn_fx_gold"], "payloads": ["fxgold"],
    "q_md": "## Đề bài\nTỷ giá **USD/VND** đóng cửa **phiên 30/10** là bao nhiêu (**đồng/USD**)? So với phiên 29/10 **tăng hay giảm bao nhiêu đồng** — ghi phần so sánh trong `note`.",
    "schema_md": '{\n  "value": 0,\n  "unit": "đồng/USD",\n  "period": "phiên 2026-10-30",\n  "source": "vn_msn_fx_gold",\n  "note": "VD: nêu mức thay đổi so với phiên liền trước"\n}',
    "rules_md": "- `note` **bắt buộc** nêu số phiên 29/10 hoặc mức thay đổi.",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 25802, "tol": {"rel": 0.005}},
        {"type": "unit", "path": "unit", "accept": ["đồng/USD", "đồng", "VND"]},
        {"type": "period", "path": "period", "accept": ["30/10", "30-10", "30.10", "2026-10-30"]},
        {"type": "evidence", "path": "note", "paths": ["note"], "numbers": [25799],
         "strings": ["+3", "tăng 3", "tang 3"], "min_hits": 1},
        {"type": "str", "path": "source", "accept": ["vn_msn_fx_gold"]},
    ], "solution": {"value": 25802, "change": 3}, "as_of": "2026-11-01T15:54:32.785351+07:00",
        "notes": "Đổi đề so với 5.5 (SJC qua vn_retail_gold timeout 01/11) → dùng chuỗi USDVND của vn_msn_fx_gold. 30/10: 25802; 29/10: 25799; +3 đồng."},
    "oracle_body": ('ser = {x["symbol"]: x["closes"] for x in env("vn_msn_fx_gold")["data"]["series"]}\n'
                    'u = ser["USDVND"]\n'
                    'check("close_3010", float(u[-1]["c"]), gold["solution"]["value"])\n'
                    'check("change", float(u[-1]["c"]) - float(u[-2]["c"]), gold["solution"]["change"])\n'),
},
]
