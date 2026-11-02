# P/E FPT theo valuation_run

## Đề bài
**P/E** của **FPT** là bao nhiêu theo công cụ định giá **`valuation_run`** của MCP?

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "x",
  "period": "snapshot 2026-11-01",
  "source": "valuation_run",
  "note": "giá và EPS dùng để tính"
}
```

- Đề **chỉ định nguồn** `valuation_run` — nguồn khác có thể cho số khác (VD P/E từ dữ liệu fundamentals) và sẽ **không** được tính đúng.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason`. Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
