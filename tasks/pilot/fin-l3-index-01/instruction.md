# VN-Index 10 phiên tăng bao nhiêu %

## Đề bài
**VN-Index** thay đổi bao nhiêu **%** trong 10 phiên giao dịch gần nhất — từ đóng cửa phiên **19/10** đến đóng cửa phiên **30/10**?

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "%",
  "period": "19/10 → 30/10/2026",
  "source": "vn_index_ohlcv",
  "note": "close đầu và close cuối dùng để tính"
}
```


## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason`. Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
