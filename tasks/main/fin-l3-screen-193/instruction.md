# Sàng lọc nhóm tech_p

Trong 5 mã **CMG, ELC, VGI, CTR, FOX**: dùng số liệu P/E, P/B và ROE từ **`peer_compare`** — mã nào thỏa **ROE > 15% và P/E < 15**? Trả danh sách mã.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"pass": ["MÃ1", "MÃ2", "..."]},
  "period": "(kỳ dữ liệu tool)",
  "source": "peer_compare",
  "note": "P/E, P/B, ROE từng mã để lọc"
}
```

- Chỉ dùng số liệu `peer_compare` trả về (kỳ do tool cung cấp).

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

