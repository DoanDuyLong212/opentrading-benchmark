# Đối chiếu 2 nguồn XAGUSD vs SI=F

Đối chiếu giá **XAGUSD** từ hai nguồn: **`vn_msn_fx_gold`** (49.10) và **`yf_commodities`** (`SI=F`, 49.276). Hai nguồn lệch nhau bao nhiêu **%**?

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "%",
  "period": "phiên gần nhất",
  "source": "vn_msn_fx_gold + yf_commodities",
  "note": "(tuỳ chọn)"
}
```

- Tính %% lệch giữa hai mức giá (lấy nguồn yf làm mốc).

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

