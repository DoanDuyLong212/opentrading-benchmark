# Top 3 VN30

**Top 3 mã tăng mạnh nhất** phiên gần nhất trong rổ **VN30** (theo % thay đổi) là những mã nào? Kèm % và giá đóng cửa (đồng), theo đúng thứ hạng.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {
    "1": {"symbol": "MÃ", "pct": 0, "close": 0},
    "2": {"symbol": "MÃ", "pct": 0, "close": 0},
    "3": {"symbol": "MÃ", "pct": 0, "close": 0}
  },
  "period": "(kỳ được hỏi)",
  "source": "market_movers",
  "note": "(tuỳ chọn)"
}
```

- Giá theo **đồng** (bảng giá).

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

