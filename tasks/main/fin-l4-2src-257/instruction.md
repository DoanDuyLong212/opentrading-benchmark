# Đối chiếu 2 nguồn BTC

Hai nguồn giá **BTC**: yfinance (BTC-USD, USD) và vnstock crypto (BTCUSDT, VND quy đổi theo tỷ giá USD/VND 30/10). Hai nguồn lệch nhau bao nhiêu **%**?

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "%",
  "period": "phiên gần nhất",
  "source": "yf_commodities + vn_crypto_ohlcv",
  "note": "(tuỳ chọn)"
}
```

- Dùng tỷ giá USD/VND đóng cửa phiên 30/10 để quy đổi.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

