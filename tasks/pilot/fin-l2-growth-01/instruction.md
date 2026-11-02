# Tăng trưởng doanh thu VNM QoQ

## Đề bài
Doanh thu thuần của **VNM** **quý gần nhất** thay đổi bao nhiêu **%** so với quý liền trước (dấu âm nếu giảm)? Nêu rõ hai quý đối chiếu.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "%",
  "period": "quý gần nhất so với quý trước (VD: Q?/yyyy vs Q?/yyyy)",
  "source": "financial_statements",
  "note": "số liệu dùng để tính"
}
```

- Giá trị gốc đơn vị VND — % thay đổi tính trên cùng đơn vị.
- Dấu âm = giảm.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason`. Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
