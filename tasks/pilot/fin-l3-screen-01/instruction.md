# Sàng lọc 5 ngân hàng: ROE>20% và P/E<10

## Đề bài
Trong 5 mã **VCB, BID, CTG, TCB, MBB** — dùng số liệu P/E và ROE từ **`peer_compare`** — những mã nào thỏa **đồng thời**: ROE > 20% **và** P/E < 10? Trả danh sách mã.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"pass": ["MÃ1", "MÃ2"]},
  "period": "(kỳ dữ liệu tool)",
  "source": "peer_compare",
  "note": "P/E và ROE từng mã dùng để lọc"
}
```

- Chỉ dùng số liệu mà `peer_compare` trả về (kỳ do tool cung cấp); không thay bằng nguồn khác.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
