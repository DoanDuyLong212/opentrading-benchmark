# So % thay đổi vàng–dầu–BTC

## Đề bài
Xét 3 tài sản ở **ngày giao dịch gần nhất**: vàng futures (**GC=F**), dầu thô WTI (**CL=F**), Bitcoin (**BTC-USD**). Tài sản nào **% thay đổi so với phiên trước cao nhất**? Nêu % thay đổi của cả 3 tài sản.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"gold_pct": 0, "oil_pct": 0, "btc_pct": 0, "winner": "MÃ"},
  "period": "phiên gần nhất",
  "source": "yf_commodities",
  "note": "(tuỳ chọn)"
}
```

- % thay đổi tính từ `prev` → `price` trong dữ liệu tool.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
