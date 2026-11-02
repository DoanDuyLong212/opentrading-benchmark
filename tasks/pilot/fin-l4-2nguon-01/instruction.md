# Đối chiếu 2 nguồn giá HPG

## Đề bài
Đối chiếu giá đóng cửa **phiên 30/10** của **HPG** từ **hai nguồn**: (a) lịch sử nến **`vn_quote_history`** và (b) bảng giao dịch **`vs_overview_trading`**. Hai nguồn có **khớp** nhau không? Nêu giá theo **đồng** và sai khác (nếu có) trong `note`.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "verdict": "khớp hoặc không khớp",
  "value": 0,
  "unit": "đồng",
  "period": "phiên 2026-10-30",
  "source": "vn_quote_history + vs_overview_trading",
  "note": "số từng nguồn + sai khác (nếu có)"
}
```

- `value` theo đơn vị **đồng** (chuẩn hóa 2 nguồn).
- `source` ghi **cả hai** tool đã dùng.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason`. Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
