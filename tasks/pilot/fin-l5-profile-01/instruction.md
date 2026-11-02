# Hồ sơ nhanh MWG

## Đề bài
Lập **hồ sơ nhanh** công ty **MWG**:
1. Doanh thu thuần **Q3/2026** (tỷ đồng)
2. Lợi nhuận gộp **Q3/2026** (tỷ đồng)
3. Biên lợi nhuận gộp **Q3/2026** (%)
4. **P/E**
5. Vốn hóa thị trường (**tỷ đồng**)

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {
    "revenue_q3_bn": 0,
    "gross_profit_q3_bn": 0,
    "gross_margin_pct": 0,
    "pe": 0,
    "market_cap_bn": 0
  },
  "period": "Q3/2026 + snapshot 2026-11-01",
  "source": "financial_detail + stock_overview",
  "note": "(tuỳ chọn)"
}
```

- Tên field đã ghi rõ đơn vị (`_bn` = tỷ đồng, `_pct` = %, `pe` = lần).
- `source` ghi **cả hai** tool đã dùng.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
