# Đối chiếu 2 nguồn PLX

Đối chiếu giá đóng cửa **phiên 30/10** của **PLX** từ **hai nguồn**: (a) lịch sử nến **`vn_quote_history`** (nghìn đồng) và (b) bảng giá **`vn_equity_quote_batch`** (đồng). Hai nguồn có **khớp** không? Nêu giá theo **đồng** và sai khác trong `note`.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "verdict": "khớp hoặc không khớp",
  "value": 0,
  "unit": "đồng",
  "period": "phiên 30/10/2026",
  "source": "vn_quote_history + vn_equity_quote_batch",
  "note": "số từng nguồn + sai khác"
}
```

- `value` theo **đồng**.
- `source` ghi cả hai tool.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

