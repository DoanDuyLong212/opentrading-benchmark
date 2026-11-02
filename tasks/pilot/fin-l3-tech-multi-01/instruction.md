# RSI thấp nhất trong 5 mã

## Đề bài
Trong 5 mã **HPG, HCM, VND, SSI, SHB** — mã nào có **RSI-14 khung ngày thấp nhất** và bằng bao nhiêu?

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"symbol": "MÃ", "rsi14": 0},
  "period": "đến phiên gần nhất (dd/mm/yyyy)",
  "source": "signals_technical",
  "note": "RSI của cả 5 mã để đối chiếu"
}
```


## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason`. Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
