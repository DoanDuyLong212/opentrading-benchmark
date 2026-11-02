# Quy BTC ra VND

## Đề bài
Quy giá 1 **Bitcoin** (cặp **BTCUSDT**, giá theo snapshot) ra **VND**, dùng tỷ giá **USD/VND đóng cửa phiên 30/10**. Trả lời theo **triệu đồng**.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "triệu đồng",
  "period": "snapshot 2026-11-01",
  "source": "crypto_spot + vn_msn_fx_gold",
  "note": "ghi rõ giá BTC và tỷ giá dùng để tính"
}
```

- `note` **bắt buộc** nêu 2 số đầu vào (giá BTC, tỷ giá USD/VND).

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason`. Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).
