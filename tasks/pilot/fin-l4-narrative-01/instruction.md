# Kiểm chứng nhận định vàng & USD/VND cùng tăng

## Đề bài
Kiểm chứng nhận định sau:

> “Trong 5 phiên giao dịch gần nhất (26/10 → 30/10), giá vàng thế giới (XAUUSD) và tỷ giá USD/VND **đều có ít nhất một phiên giảm**.”

Đúng hay **sai**? Nêu số close từng phiên của cả hai chuỗi trong `note` để chứng minh.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "verdict": "đúng hoặc sai",
  "period": "26/10 → 30/10/2026",
  "source": "vn_msn_fx_gold",
  "note": "số close từng phiên của cả hai chuỗi"
}
```

- `note` nêu số close từng phiên của cả hai chuỗi để chứng minh nhận định.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
