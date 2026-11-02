# Hồ sơ nhanh VCS

Lập **hồ sơ nhanh** công ty **VCS** (quý gần nhất: Q2/2026):
1. Doanh thu thuần (tỷ đồng)
2. Lợi nhuận gộp (tỷ đồng)
3. Biên lợi nhuận gộp (%)
4. **P/E**
5. Vốn hóa thị trường (tỷ đồng)

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"revenue_q_bn": 0, "gross_profit_q_bn": 0, "gross_margin_pct": 0, "pe": 0, "market_cap_bn": 0},
  "period": "quý dữ liệu + snapshot",
  "source": "financial_detail + stock_overview",
  "note": "(tuỳ chọn)"
}
```

- `source` ghi cả hai tool.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

