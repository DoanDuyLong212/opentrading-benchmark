# So % biến động BTCUSDT vs ETHUSDT

So sánh **% thay đổi phiên cuối** của hai cặp **BTCUSDT** và **ETHUSDT** (nguồn vnstock crypto). Cặp nào **biến động mạnh hơn** (|%| lớn hơn)? Nêu % của cả hai.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"BTCUSDT_pct": 0, "ETHUSDT_pct": 0, "winner": "MÃ"},
  "period": "phiên cuối",
  "source": "vn_crypto_ohlcv",
  "note": "(tuỳ chọn)"
}
```

- Biến động mạnh hơn = giá trị tuyệt đối %% thay đổi lớn hơn.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

