# Biến động JPYVND vs USDVND

Trong 5 phiên gần nhất (26/10 → 30/10): **% thay đổi của JPYVND** và của **USDVND** lần lượt là bao nhiêu? Biến động của JPYVND **mạnh hơn hay yếu hơn** USDVND (so |%|)?

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {"sym_pct": 0, "usdvnd_pct": 0, "so_sanh": "mạnh hơn hoặc yếu hơn"},
  "period": "26/10 → 30/10/2026",
  "source": "vn_msn_fx_gold",
  "note": "(tuỳ chọn)"
}
```


## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

