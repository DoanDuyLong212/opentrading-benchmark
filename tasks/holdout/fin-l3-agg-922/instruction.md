# Bảng giá nhóm sec1

Cho 5 mã **VCI, VIX, SHS, MBS, FTS**: giá đóng cửa **phiên 30/10** của từng mã (theo **đồng**) và **trung bình** 5 mã là bao nhiêu?

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"VCI": 0, "VIX": 0, "SHS": 0, "MBS": 0, "FTS": 0, "mean": 0},
  "unit": "đồng",
  "period": "phiên 30/10/2026",
  "source": "vn_equity_quote_batch",
  "note": "(tuỳ chọn)"
}
```


## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

