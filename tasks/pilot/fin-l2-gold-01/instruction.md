# Tỷ giá USD/VND phiên 30/10 + so phiên trước

## Đề bài
Tỷ giá **USD/VND** đóng cửa **phiên 30/10** là bao nhiêu (**đồng/USD**)? So với phiên 29/10 **tăng hay giảm bao nhiêu đồng** — ghi phần so sánh trong `note`.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "đồng/USD",
  "period": "(kỳ được hỏi)",
  "source": "vn_msn_fx_gold",
  "note": "VD: nêu mức thay đổi so với phiên liền trước"
}
```

- `note` **bắt buộc** nêu số phiên 29/10 hoặc mức thay đổi.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
