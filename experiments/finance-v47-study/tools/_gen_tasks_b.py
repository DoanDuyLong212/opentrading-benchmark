# -*- coding: utf-8 -*-
"""Đặc tả task nhóm B: L3 (6) + L4 (4) + L5 (3)."""

TASKS_B = [
# ---------------------------------------------------------------- L3
{
    "id": "fin-l3-screen-01", "group": "pilot", "title": "Sàng lọc 5 ngân hàng: ROE>20% và P/E<10",
    "level": "L3", "family": "L3·A screen", "fb": "screening/filtering",
    "entity": "VCB+BID+CTG+TCB+MBB", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 5,
    "band": "15–60 phút", "limit": 60, "tools": ["peer_compare"], "payloads": ["peer"],
    "q_md": "## Đề bài\nTrong 5 mã **VCB, BID, CTG, TCB, MBB** — dùng số liệu P/E và ROE từ **`peer_compare`** — những mã nào thỏa **đồng thời**: ROE > 20% **và** P/E < 10? Trả danh sách mã.",
    "schema_md": '{\n  "values": {"pass": ["MÃ1", "MÃ2"]},\n  "period": "(kỳ dữ liệu tool)",\n  "source": "peer_compare",\n  "note": "P/E và ROE từng mã dùng để lọc"\n}',
    "rules_md": "- Chỉ dùng số liệu mà `peer_compare` trả về (kỳ do tool cung cấp); không thay bằng nguồn khác.",
    "gold": {"scoring": "value", "expects": [
        {"type": "set", "path": "values.pass", "gold": ["CTG", "MBB"]},
        {"type": "period", "path": "period", "accept": ["2025"]},
        {"type": "str", "path": "source", "accept": ["peer_compare"]},
    ], "solution": {"pass": ["CTG", "MBB"]}, "as_of": "2026-11-01T15:58:02.647158+07:00",
        "notes": "Đổi nguồn so với 5.5 (stock_screener chỉ enrich 5/30 symbols, candidates rỗng) → dùng peer_compare universe 5. CTG (ROE 21.23, PE 5.55), MBB (21.57, 6.36); BID ROE 19.43 trượt."},
    "oracle_body": ('rows = env("peer_compare")["data"]["rows"]\n'
                    'ok = sorted(r["symbol"] for r in rows if r["roe"] > 20 and r["p_e"] < 10)\n'
                    'check("screen", ok, gold["solution"]["pass"])\n'),
},
{
    "id": "fin-l3-agg-01", "group": "pilot", "title": "Bảng giá 5 ngân hàng + trung bình",
    "level": "L3", "family": "L3·B aggregate", "fb": "aggregation",
    "entity": "VCB+BID+CTG+TCB+MBB", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 5,
    "band": "15–60 phút", "limit": 45, "tools": ["vn_quote_history"], "payloads": ["banks5"],
    "q_md": "## Đề bài\nCho 5 mã **VCB, BID, CTG, TCB, MBB**: giá đóng cửa **phiên 30/10** của từng mã là bao nhiêu (theo **nghìn đồng**), và **trung bình** 5 mã là bao nhiêu?",
    "schema_md": '{\n  "values": {"VCB": 0, "BID": 0, "CTG": 0, "TCB": 0, "MBB": 0, "mean": 0},\n  "unit": "nghìn đồng",\n  "period": "(kỳ được hỏi)",\n  "source": "vn_quote_history",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "- Giá theo **nghìn đồng** (quy ước candles).",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "values.VCB", "gold": 56.3, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.BID", "gold": 33.4, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.CTG", "gold": 30.3, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.TCB", "gold": 21.6, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.MBB", "gold": 19.3, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.mean", "gold": 32.18, "tol": {"rel": 0.005}},
        {"type": "unit", "path": "unit", "accept": ["nghìn đồng", "nghìn đ", "k đồng"]},
        {"type": "period", "path": "period", "accept": ["30/10", "30-10", "30.10", "2026-10-30"]},
        {"type": "str", "path": "source", "accept": ["vn_quote_history"]},
    ], "solution": {"VCB": 56.3, "BID": 33.4, "CTG": 30.3, "TCB": 21.6, "MBB": 19.3, "mean": 32.18},
        "as_of": "2026-11-01T15:57:50.079479+07:00",
        "notes": "Đổi nguồn so với 5.5 (vn_equity_quote_batch unavailable 01/11) → 5 lời gọi vn_quote_history. Trung bình: 160.9/5 = 32.18."},
    "oracle_body": ('b = {x["symbol"]: x["last"] for x in env("vn_quote_history")["data"]["banks"]}\n'
                    'vals = [b[s] for s in ["VCB", "BID", "CTG", "TCB", "MBB"]]\n'
                    'check("mean", round(sum(vals) / len(vals), 2), gold["solution"]["mean"])\n'
                    'for s in ["VCB", "BID", "CTG", "TCB", "MBB"]:\n'
                    '    check(s, float(b[s]), gold["solution"][s])\n'),
},
{
    "id": "fin-l3-top-01", "group": "pilot", "title": "Top 3 mã tăng mạnh nhất VN30",
    "level": "L3", "family": "L3·C movers", "fb": "ranking extraction",
    "entity": "VN30", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 30,
    "band": "15–60 phút", "limit": 45, "tools": ["market_movers"], "payloads": ["movers"],
    "q_md": "## Đề bài\n**Top 3 mã tăng mạnh nhất** phiên gần nhất trong rổ **VN30** (theo % tăng) là những mã nào? Kèm **% tăng** và **giá đóng cửa** (theo **đồng**) của từng mã, theo đúng thứ hạng.",
    "schema_md": '{\n  "values": {\n    "1": {"symbol": "MÃ", "pct": 0, "close": 0},\n    "2": {"symbol": "MÃ", "pct": 0, "close": 0},\n    "3": {"symbol": "MÃ", "pct": 0, "close": 0}\n  },\n  "period": "(kỳ được hỏi)",\n  "source": "market_movers",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "- Giá theo **đồng** (bảng giá — khác candles nghìn đồng).",
    "gold": {"scoring": "value", "expects": [
        {"type": "str", "path": "values.1.symbol", "accept": ["GAS"]},
        {"type": "value", "path": "values.1.pct", "gold": 2.63, "tol": {"abs": 0.05}},
        {"type": "value", "path": "values.1.close", "gold": 78000, "tol": {"rel": 0.005}},
        {"type": "str", "path": "values.2.symbol", "accept": ["VHM"]},
        {"type": "value", "path": "values.2.pct", "gold": 1.45, "tol": {"abs": 0.05}},
        {"type": "value", "path": "values.2.close", "gold": 63000, "tol": {"rel": 0.005}},
        {"type": "str", "path": "values.3.symbol", "accept": ["NVL"]},
        {"type": "value", "path": "values.3.pct", "gold": 0.48, "tol": {"abs": 0.05}},
        {"type": "value", "path": "values.3.close", "gold": 10400, "tol": {"rel": 0.005}},
        {"type": "period", "path": "period", "accept": ["30/10", "30-10", "30.10", "2026-10-30", "phiên gần nhất", "gần nhất"]},
        {"type": "str", "path": "source", "accept": ["market_movers"]},
    ], "solution": {"top": [{"symbol": "GAS", "pct": 2.63, "close": 78000},
                            {"symbol": "VHM", "pct": 1.45, "close": 63000},
                            {"symbol": "NVL", "pct": 0.48, "close": 10400}]},
        "as_of": "2026-11-01T15:57:50.290909+07:00",
        "notes": "Top 3/5 gainers: GAS +2.63%, VHM +1.45%, NVL +0.48% (SAB +0.24%, BVH 0%)."},
    "oracle_body": ('g = env("market_movers")["data"]["gainers"][:3]\n'
                    'for i, r in enumerate(g, 1):\n'
                    '    sol = gold["solution"]["top"][i - 1]\n'
                    '    check("top%d_symbol" % i, r["symbol"], sol["symbol"])\n'
                    '    check("top%d_pct" % i, round(r["percent_change"], 2), sol["pct"])\n'
                    '    check("top%d_close" % i, float(r["close_price"]), sol["close"])\n'),
},
{
    "id": "fin-l3-tech-multi-01", "group": "pilot", "title": "RSI thấp nhất trong 5 mã",
    "level": "L3", "family": "L3·D tech-multi", "fb": "multi-entity comparison",
    "entity": "HPG+HCM+VND+SSI+SHB", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 5,
    "band": "15–60 phút", "limit": 45, "tools": ["signals_technical"], "payloads": ["tech"],
    "q_md": "## Đề bài\nTrong 5 mã **HPG, HCM, VND, SSI, SHB** — mã nào có **RSI-14 khung ngày thấp nhất** và bằng bao nhiêu?",
    "schema_md": '{\n  "values": {"symbol": "MÃ", "rsi14": 0},\n  "period": "(kỳ được hỏi)",\n  "source": "signals_technical",\n  "note": "RSI của cả 5 mã để đối chiếu"\n}',
    "rules_md": "",
    "gold": {"scoring": "value", "expects": [
        {"type": "str", "path": "values.symbol", "accept": ["SSI"]},
        {"type": "value", "path": "values.rsi14", "gold": 39.97, "tol": {"abs": 0.1}},
        {"type": "period", "path": "period", "accept": ["30/10", "30-10", "30.10", "2026-10-30", "phiên gần nhất", "gần nhất"]},
        {"type": "str", "path": "source", "accept": ["signals_technical"]},
    ], "solution": {"symbol": "SSI", "rsi14": 39.97}, "as_of": "2026-11-01T15:57:53.193466+07:00",
        "notes": "RSI: HPG 51.9, HCM 40.87, VND 41.97, SSI 39.97, SHB 43.57 → thấp nhất SSI."},
    "oracle_body": ('rows = [r for r in env("signals_technical")["data"]["rows"] if r["symbol"] != "VCB"]\n'
                    'm = min(rows, key=lambda r: r["rsi14"])\n'
                    'check("symbol", m["symbol"], gold["solution"]["symbol"])\n'
                    'check("rsi14", float(m["rsi14"]), gold["solution"]["rsi14"])\n'),
},
{
    "id": "fin-l3-crypto-01", "group": "pilot", "title": "So % thay đổi vàng–dầu–BTC",
    "level": "L3", "family": "L3·E crypto-multi", "fb": "multi-asset comparison",
    "entity": "GC=F+CL=F+BTC-USD", "asset": "crypto", "zone": "yellow", "pairs": [], "cap": 3,
    "band": "15–60 phút", "limit": 45, "tools": ["yf_commodities"], "payloads": ["yf"],
    "q_md": "## Đề bài\nXét 3 tài sản ở **ngày giao dịch gần nhất**: vàng futures (**GC=F**), dầu thô WTI (**CL=F**), Bitcoin (**BTC-USD**). Tài sản nào **% thay đổi so với phiên trước cao nhất**? Nêu % thay đổi của cả 3 tài sản.",
    "schema_md": '{\n  "values": {"gold_pct": 0, "oil_pct": 0, "btc_pct": 0, "winner": "MÃ"},\n  "period": "phiên gần nhất",\n  "source": "yf_commodities",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "- % thay đổi tính từ `prev` → `price` trong dữ liệu tool.",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "values.gold_pct", "gold": -3.29, "tol": {"abs": 0.1}},
        {"type": "value", "path": "values.oil_pct", "gold": 2.08, "tol": {"abs": 0.1}},
        {"type": "value", "path": "values.btc_pct", "gold": 0.77, "tol": {"abs": 0.1}},
        {"type": "str", "path": "values.winner", "accept": ["CL=F", "CL", "dầu thô", "dầu WTI", "WTI", "crude"]},
        {"type": "str", "path": "source", "accept": ["yf_commodities"]},
    ], "solution": {"gold_pct": -3.29, "oil_pct": 2.08, "btc_pct": 0.77, "winner": "CL=F"},
        "as_of": "2026-11-01T15:57:51.193584+07:00",
        "notes": "Đổi nguồn so với 5.5 (crypto_spot batch 10 mã dính Binance 429) → yf_commodities 3 tài sản. GC -3.29%, CL +2.08%, BTC +0.77% → CL cao nhất. Không check period (semantics ngày đóng của yfinance không rõ 30 hay 31/10)."},
    "oracle_body": ('items = env("yf_commodities")["data"]["items"]\n'
                    'pc = {i["ticker"]: (i["price"] / i["prev"] - 1) * 100 for i in items}\n'
                    'check("gold_pct", round(pc["GC=F"], 2), gold["solution"]["gold_pct"])\n'
                    'check("oil_pct", round(pc["CL=F"], 2), gold["solution"]["oil_pct"])\n'
                    'check("btc_pct", round(pc["BTC-USD"], 2), gold["solution"]["btc_pct"])\n'
                    'check("winner", max(pc, key=pc.get), gold["solution"]["winner"])\n'),
},
{
    "id": "fin-l3-index-01", "group": "pilot", "title": "VN-Index 10 phiên tăng bao nhiêu %",
    "level": "L3", "family": "L3·F index", "fb": "temporal computation",
    "entity": "VNINDEX", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "15–60 phút", "limit": 45, "tools": ["vn_index_ohlcv"], "payloads": ["index10"],
    "q_md": "## Đề bài\n**VN-Index** thay đổi bao nhiêu **%** trong 10 phiên giao dịch gần nhất — từ đóng cửa phiên **19/10** đến đóng cửa phiên **30/10**?",
    "schema_md": '{\n  "value": 0,\n  "unit": "%",\n  "period": "(kỳ được hỏi)",\n  "source": "vn_index_ohlcv",\n  "note": "close đầu và close cuối dùng để tính"\n}',
    "rules_md": "",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "value", "gold": 3.06, "tol": {"abs": 0.1}},
        {"type": "unit", "path": "unit", "accept": ["%", "phần trăm"]},
        {"type": "period", "path": "period", "accept": ["19/10", "30/10", "2026-10-19", "2026-10-30"]},
        {"type": "str", "path": "source", "accept": ["vn_index_ohlcv"]},
    ], "solution": {"value": 3.06}, "as_of": "2026-11-01T15:57:50.289394+07:00",
        "notes": "1689.84 → 1741.62 = +3.06%."},
    "oracle_body": ('bars = env("vn_index_ohlcv")["data"]["bars"]\n'
                    'check("n_bars", len(bars), 10)\n'
                    'check("chg_10s", round((bars[-1]["close"] / bars[0]["close"] - 1) * 100, 2), gold["solution"]["value"])\n'),
},
# ---------------------------------------------------------------- L4
{
    "id": "fin-l4-future-01", "group": "pilot", "title": "LNST DGC Q4/2026 (kỳ chưa công bố)",
    "level": "L4", "family": "L4·E future-period", "fb": "unanswerable (period trap)",
    "entity": "DGC", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 30, "tools": ["financial_statements"], "payloads": ["fs_dgc"],
    "q_md": "## Đề bài\nLợi nhuận sau thuế của **DGC** trong **quý 4/2026** là bao nhiêu? Quy ra **tỷ đồng**.",
    "schema_md": '{\n  "value": 0,\n  "unit": "tỷ đồng",\n  "period": "Q4/2026",\n  "source": "financial_statements",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "",
    "gold": {"scoring": "refusal",
             "refusal_tokens": ["chưa công bố", "chưa có", "chưa kết thúc", "không có", "không tồn tại",
                                "chưa phát hành", "chưa đến kỳ", "không có số liệu", "chưa có số liệu",
                                "chưa được công bố"],
             "bonus_numbers": [478.16, 506.68],
             "bonus_strings": ["Q3/2026", "quý 3/2026", "Q3 2026"],
             "solution": {"q4_absent": True, "latest": "Q3/2026", "latest_lnst_me_bn": 478.16},
             "as_of": "2026-11-01T15:57:50.285524+07:00",
             "notes": "Q4/2026 chưa kết thúc tại snapshot (01/11/2026). Kỳ có số mới nhất: Q3/2026 — LNST cty mẹ 478.16 tỷ, hợp nhất 506.68 tỷ."},
    "oracle_body": ('d = env("financial_statements")["data"]\n'
                    'check("q4_absent", "Q4/2026" not in d["periods"], True)\n'
                    'check("latest", d["periods"][-1], gold["solution"]["latest"])\n'
                    'rows = d["statements"]["Kết quả kinh doanh"]\n'
                    'me = next(r for r in rows if "cty mẹ" in r["name"])["values"]["Q3/2026"]\n'
                    'check("lnst_me_q3_bn", round(me / 1e9, 2), gold["solution"]["latest_lnst_me_bn"])\n'),
},
{
    "id": "fin-l4-nonexist-01", "group": "pilot", "title": "Giá mã XYZX (mã không tồn tại)",
    "level": "L4", "family": "L4·B nonexistent", "fb": "unanswerable (entity trap)",
    "entity": "XYZX", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "<15 phút", "limit": 20, "tools": ["symbol_resolve"], "payloads": ["resolve"],
    "q_md": "## Đề bài\nGiá đóng cửa gần nhất của cổ phiếu **XYZX** là bao nhiêu (**đồng**)?",
    "schema_md": '{\n  "value": 0,\n  "unit": "đồng",\n  "period": "gần nhất",\n  "source": "symbol_resolve",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "",
    "gold": {"scoring": "refusal",
             "refusal_tokens": ["không tồn tại", "không có", "không tìm thấy", "không hợp lệ",
                                "mã không", "không có mã", "không có dữ liệu", "không phải mã"],
             "solution": {"resolved_null": True},
             "as_of": "2026-11-01T15:57:53.093226+07:00",
             "notes": "symbol_resolve('XYZX') → resolved null, candidates [] , availability empty."},
    "oracle_body": ('d = env("symbol_resolve")["data"]\n'
                    'check("resolved_null", d["resolved"] is None, True)\n'
                    'check("no_candidates", d["candidates"], [])\n'),
},
{
    "id": "fin-l4-narrative-01", "group": "pilot", "title": "Kiểm chứng nhận định vàng & USD/VND cùng tăng",
    "level": "L4", "family": "L4·I narrative-check", "fb": "claim verification",
    "entity": "XAUUSD+USDVND", "asset": "gold_fx", "zone": "green", "pairs": [], "cap": 0,
    "band": "15–60 phút", "limit": 30, "tools": ["vn_msn_fx_gold"], "payloads": ["fxgold"],
    "q_md": "## Đề bài\nKiểm chứng nhận định sau:\n\n> “Trong 5 phiên giao dịch gần nhất (26/10 → 30/10), giá vàng thế giới (XAUUSD) và tỷ giá USD/VND **đều có ít nhất một phiên giảm**.”\n\nĐúng hay **sai**? Nêu số close từng phiên của cả hai chuỗi trong `note` để chứng minh.",
    "schema_md": '{\n  "verdict": "đúng hoặc sai",\n  "period": "26/10 → 30/10/2026",\n  "source": "vn_msn_fx_gold",\n  "note": "số close từng phiên của cả hai chuỗi"\n}',
    "rules_md": "- `note` nêu số close từng phiên của cả hai chuỗi để chứng minh nhận định.",
    "gold": {"scoring": "verdict",
             "verdict_accept": ["đúng", "true", "chính xác"],
             "verdict_reject": ["sai", "false", "không đúng", "không chính xác"],
             "evidence": {"paths": ["note"], "min_hits": 1,
                          "numbers": [3875.02, 4020.42, 4067.04, 25799, 25832, 25852]},
             "solution": {"verdict": "đúng"},
             "as_of": "2026-11-01T15:54:32.785351+07:00",
             "notes": "Biến thể claim ĐÚNG (vá 2 chiều 02/11): XAUUSD giảm 2 phiên cuối (4067.04 → 4020.42 → 3875.02) và USDVND có 2 phiên giảm (25841 → 25832, 25852 → 25799) → cả hai chuỗi đều có ít nhất một phiên giảm → nhận định ĐÚNG."},
    "oracle_body": ('ser = {x["symbol"]: [p["c"] for p in x["closes"]] for x in env("vn_msn_fx_gold")["data"]["series"]}\n'
                    'xau, usd = ser["XAUUSD"], ser["USDVND"]\n'
                    'check("xau_has_down", any(xau[i + 1] < xau[i] for i in range(len(xau) - 1)), True)\n'
                    'check("usd_has_down", any(usd[i + 1] < usd[i] for i in range(len(usd) - 1)), True)\n'
                    'check("verdict", "đúng", gold["solution"]["verdict"])\n'),
},
{
    "id": "fin-l4-2nguon-01", "group": "pilot", "title": "Đối chiếu 2 nguồn giá HPG",
    "level": "L4", "family": "L4·D two-source", "fb": "cross-source verification",
    "entity": "HPG", "asset": "vn_stock", "zone": "green",
    "pairs": ["vn_quote_history", "vs_overview_trading"], "cap": 0,
    "band": "15–60 phút", "limit": 30, "tools": ["vn_quote_history", "vs_overview_trading"],
    "payloads": ["qh_hpg", "vs_hpg"],
    "q_md": "## Đề bài\nĐối chiếu giá đóng cửa **phiên 30/10** của **HPG** từ **hai nguồn**: (a) lịch sử nến **`vn_quote_history`** và (b) bảng giao dịch **`vs_overview_trading`**. Hai nguồn có **khớp** nhau không? Nêu giá theo **đồng** và sai khác (nếu có) trong `note`.",
    "schema_md": '{\n  "verdict": "khớp hoặc không khớp",\n  "value": 0,\n  "unit": "đồng",\n  "period": "(kỳ được hỏi)",\n  "source": "vn_quote_history + vs_overview_trading",\n  "note": "số từng nguồn + sai khác (nếu có)"\n}',
    "rules_md": "- `value` theo đơn vị **đồng** (chuẩn hóa 2 nguồn).\n- `source` ghi **cả hai** tool đã dùng.",
    "gold": {"scoring": "value", "expects": [
        {"type": "verdict", "path": "verdict", "accept": ["khớp", "match", "giống nhau", "bằng nhau", "không lệch", "không chênh"],
         "reject": ["không khớp", "lệch", "khác nhau"]},
        {"type": "value", "path": "value", "gold": 21000, "tol": {"rel": 0.005}},
        {"type": "unit", "path": "unit", "accept": ["đồng", "VND"]},
        {"type": "period", "path": "period", "accept": ["30/10", "30-10", "30.10", "2026-10-30"]},
        {"type": "str_all", "path": "source", "accept": ["vn_quote_history", "vs_overview_trading"]},
    ], "solution": {"close": 21000, "match": True},
        "as_of": "2026-11-01T15:59:53.366224+07:00",
        "notes": "vn_quote_history: 21 (nghìn đồng) = 21000 đồng; vs_overview_trading: ClosePrice 21000 (đồng) → khớp, sai khác 0. Bẫy đơn vị 2 nguồn."},
    "oracle_body": ('h = float(env("vn_quote_history")["data"]["last"]) * 1000\n'
                    'vs = env("vs_overview_trading")["data"]["overview"]["data"][0]\n'
                    'check("vs_close", float(vs["ClosePrice"]), gold["solution"]["close"])\n'
                    'check("match", h == float(vs["ClosePrice"]), gold["solution"]["match"])\n'),
},
# ---------------------------------------------------------------- L5
{
    "id": "fin-l5-profile-01", "group": "pilot", "title": "Hồ sơ nhanh MWG (multi-part)",
    "level": "L5", "family": "L5·A profile", "fb": "company profile (multi-part)",
    "entity": "MWG", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "15–60 phút", "limit": 60, "tools": ["financial_detail", "stock_overview"],
    "payloads": ["mwg_kqkd", "mwg_ov"],
    "q_md": "## Đề bài\nLập **hồ sơ nhanh** công ty **MWG**:\n1. Doanh thu thuần **Q3/2026** (tỷ đồng)\n2. Lợi nhuận gộp **Q3/2026** (tỷ đồng)\n3. Biên lợi nhuận gộp **Q3/2026** (%)\n4. **P/E**\n5. Vốn hóa thị trường (**tỷ đồng**)",
    "schema_md": '{\n  "values": {\n    "revenue_q3_bn": 0,\n    "gross_profit_q3_bn": 0,\n    "gross_margin_pct": 0,\n    "pe": 0,\n    "market_cap_bn": 0\n  },\n  "period": "Q3/2026 + snapshot 2026-11-01",\n  "source": "financial_detail + stock_overview",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "- Tên field đã ghi rõ đơn vị (`_bn` = tỷ đồng, `_pct` = %, `pe` = lần).\n- `source` ghi **cả hai** tool đã dùng.",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "values.revenue_q3_bn", "gold": 52614, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.gross_profit_q3_bn", "gold": 11421, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.gross_margin_pct", "gold": 21.71, "tol": {"abs": 0.1}},
        {"type": "value", "path": "values.pe", "gold": 9.75, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.market_cap_bn", "gold": 109201.36, "tol": {"rel": 0.005}},
        {"type": "str_all", "path": "source", "accept": ["financial_detail", "stock_overview"]},
    ], "solution": {"revenue_q3_bn": 52614, "gross_profit_q3_bn": 11421, "gross_margin_pct": 21.71,
                    "pe": 9.75, "market_cap_bn": 109201.36},
        "as_of": "2026-11-01T15:59:30.783891+07:00",
        "notes": "MarketCapital 109,201,362,364,000 đ = 109,201.36 tỷ. Nguồn KQKD (financial_detail) và overview (stock_overview) khác base: Revenue LTM trong overview (156,836 tỷ) ≠ DT quý — đề hỏi quý nên phải dùng financial_detail."},
    "oracle_body": ('d = env("financial_detail")["data"]\n'
                    'p = env("stock_overview")["data"]["trading"]\n'
                    'i = d["periods"].index("Q3/2026")\n'
                    'dt = next(r for r in d["rows"] if "Doanh thu thuần" in r["name"])["values"][i]\n'
                    'ln = next(r for r in d["rows"] if "Lợi nhuận gộp" in r["name"])["values"][i]\n'
                    'check("revenue_bn", float(dt), gold["solution"]["revenue_q3_bn"])\n'
                    'check("gross_bn", float(ln), gold["solution"]["gross_profit_q3_bn"])\n'
                    'check("margin", round(ln / dt * 100, 2), gold["solution"]["gross_margin_pct"])\n'
                    'check("pe", float(p["PE"]), gold["solution"]["pe"])\n'
                    'check("mcap_bn", round(p["MarketCapital"] / 1e9, 2), gold["solution"]["market_cap_bn"])\n'),
},
{
    "id": "fin-l5-compare-01", "group": "pilot", "title": "Bảng so sánh 5 ngân hàng + xếp hạng ROE",
    "level": "L5", "family": "L5·B compare", "fb": "peer comparison (multi-part)",
    "entity": "VCB+BID+CTG+TCB+MBB", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 5,
    "band": "15–60 phút", "limit": 60, "tools": ["peer_compare"], "payloads": ["peer"],
    "q_md": "## Đề bài\nDùng **`peer_compare`** lập bảng **P/E, P/B, ROE** của 5 mã **VCB, BID, CTG, TCB, MBB**, rồi **xếp hạng 5 mã theo ROE từ cao xuống thấp**.",
    "schema_md": '{\n  "values": {\n    "VCB": {"pe": 0, "pb": 0, "roe": 0},\n    "BID": {"pe": 0, "pb": 0, "roe": 0},\n    "CTG": {"pe": 0, "pb": 0, "roe": 0},\n    "TCB": {"pe": 0, "pb": 0, "roe": 0},\n    "MBB": {"pe": 0, "pb": 0, "roe": 0}\n  },\n  "ranking": ["MÃ1", "MÃ2", "..."],\n  "period": "(kỳ dữ liệu tool)",\n  "source": "peer_compare",\n  "note": "(tuỳ chọn)"\n}',
    "rules_md": "- Đúng kỳ mà `peer_compare` trả về (bội số theo giá cuối kỳ báo cáo — tool ghi rõ trong `note`).\n- `ranking` đủ 5 mã, đúng thứ tự.",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "values.VCB.pe", "gold": 12.66, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.VCB.pb", "gold": 2.14, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.VCB.roe", "gold": 16.73, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.BID.pe", "gold": 9.11, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.BID.pb", "gold": 1.57, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.BID.roe", "gold": 19.43, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.CTG.pe", "gold": 5.55, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.CTG.pb", "gold": 1.07, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.CTG.roe", "gold": 21.23, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.TCB.pe", "gold": 9.76, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.TCB.pb", "gold": 1.38, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.TCB.roe", "gold": 16.03, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.MBB.pe", "gold": 6.36, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.MBB.pb", "gold": 1.43, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.MBB.roe", "gold": 21.57, "tol": {"rel": 0.005}},
        {"type": "list_order", "path": "ranking", "gold": ["MBB", "CTG", "BID", "VCB", "TCB"]},
        {"type": "period", "path": "period", "accept": ["2025"]},
        {"type": "str", "path": "source", "accept": ["peer_compare"]},
    ], "solution": {
        "VCB": {"pe": 12.66, "pb": 2.14, "roe": 16.73},
        "BID": {"pe": 9.11, "pb": 1.57, "roe": 19.43},
        "CTG": {"pe": 5.55, "pb": 1.07, "roe": 21.23},
        "TCB": {"pe": 9.76, "pb": 1.38, "roe": 16.03},
        "MBB": {"pe": 6.36, "pb": 1.43, "roe": 21.57},
        "ranking": ["MBB", "CTG", "BID", "VCB", "TCB"]},
        "as_of": "2026-11-01T15:58:02.647158+07:00",
        "notes": "ROE desc: MBB 21.57 > CTG 21.23 > BID 19.43 > VCB 16.73 > TCB 16.03."},
    "oracle_body": ('rows = env("peer_compare")["data"]["rows"]\n'
                    'for r in rows:\n'
                    '    sol = gold["solution"][r["symbol"]]\n'
                    '    check(r["symbol"] + "_pe", float(r["p_e"]), sol["pe"])\n'
                    '    check(r["symbol"] + "_pb", float(r["p_b"]), sol["pb"])\n'
                    '    check(r["symbol"] + "_roe", float(r["roe"]), sol["roe"])\n'
                    'rk = [r["symbol"] for r in sorted(rows, key=lambda x: -x["roe"])]\n'
                    'check("ranking", rk, gold["solution"]["ranking"])\n'),
},
{
    "id": "fin-l5-valuation-01", "group": "pilot", "title": "Định giá FPT: giá, P/E, P/B",
    "level": "L5", "family": "L5·C valuation", "fb": "valuation summary (multi-part)",
    "entity": "FPT", "asset": "vn_stock", "zone": "green", "pairs": [], "cap": 0,
    "band": "15–60 phút", "limit": 60, "tools": ["valuation_run"], "payloads": ["fpt_val"],
    "q_md": "## Đề bài\nChạy định giá **FPT** bằng **`valuation_run`**: giá được dùng để tính là bao nhiêu (**đồng**), **P/E** và **P/B** là bao nhiêu?",
    "schema_md": '{\n  "values": {"price": 0, "per": 0, "pb": 0},\n  "period": "snapshot 2026-11-01",\n  "source": "valuation_run",\n  "note": "EPS/BVPS dùng để tính"\n}',
    "rules_md": "- `price` theo **đồng**.",
    "gold": {"scoring": "value", "expects": [
        {"type": "value", "path": "values.price", "gold": 52700, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.per", "gold": 8.75, "tol": {"rel": 0.005}},
        {"type": "value", "path": "values.pb", "gold": 2.05, "tol": {"rel": 0.005}},
        {"type": "str", "path": "source", "accept": ["valuation_run"]},
    ], "solution": {"price": 52700, "per": 8.75, "pb": 2.05},
        "as_of": "2026-11-01T15:54:35.771025+07:00",
        "notes": "Tool không trả fair-value range (chỉ multiples) → đề chỉ hỏi price/per/pb, trung thực với năng lực tool. Lưu ý: FPT giá 52,700 đ ở đây là giá tool dùng (nguồn vnstock.equity_quote_batch)."},
    "oracle_body": ('d = env("valuation_run")["data"]\n'
                    'check("price", float(d["price"]), gold["solution"]["price"])\n'
                    'check("per", float(d["per"]), gold["solution"]["per"])\n'
                    'check("pb", float(d["pb"]), gold["solution"]["pb"])\n'),
},
]
