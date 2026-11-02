# Bảng giá 5 ngân hàng + trung bình

## Đề bài
Cho 5 mã **VCB, BID, CTG, TCB, MBB**: giá đóng cửa **phiên 30/10** của từng mã là bao nhiêu (theo **nghìn đồng**), và **trung bình** 5 mã là bao nhiêu?

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"VCB": 0, "BID": 0, "CTG": 0, "TCB": 0, "MBB": 0, "mean": 0},
  "unit": "nghìn đồng",
  "period": "phiên 2026-10-30",
  "source": "vn_quote_history",
  "note": "(tuỳ chọn)"
}
```

- Giá theo **nghìn đồng** (quy ước candles).

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason`. Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
