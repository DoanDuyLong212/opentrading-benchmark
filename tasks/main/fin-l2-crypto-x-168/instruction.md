# Quy SOL-USD ra tiền pháp định

Quy giá 1 **SOL-USD** (theo snapshot, USD) ra **VND** dùng tỷ giá **USD/VND đóng cửa phiên 30/10**. Trả lời theo **triệu đồng**.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "triệu đồng",
  "period": "snapshot 2026-11-01",
  "source": "yf_commodities + vn_msn_fx_gold",
  "note": "ghi rõ 2 số đầu vào (giá coin USD, tỷ giá)"
}
```

- `note` **bắt buộc** nêu 2 số đầu vào (giá coin, tỷ giá).

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

