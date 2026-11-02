# Kiểm chứng nhận định ANV

Nhận định: “Trong **10 phiên gần nhất (19/10 → 30/10)**, giá đóng cửa của **ANV** **tăng liên tục từng phiên**.”

Đúng hay **sai**? Nêu số close từng phiên trong `note` để chứng minh.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "verdict": "đúng hoặc sai",
  "period": "19/10 → 30/10/2026",
  "source": "vn_quote_history",
  "note": "số liệu chứng minh"
}
```

- `note` phải chứa số liệu thật chứng minh (ít nhất 1 phiên giảm).

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

