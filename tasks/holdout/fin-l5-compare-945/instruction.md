# So sánh nhóm sec_p + xếp hạng ROE

Dùng **`peer_compare`** lập bảng **P/E, P/B, ROE** của 5 mã **VIX, VCI, SHS, MBS, FTS**, rồi **xếp hạng 5 mã theo ROE giảm dần**.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "values": {
    "VIX": {"pe": 0, "pb": 0, "roe": 0},
    "VCI": {"pe": 0, "pb": 0, "roe": 0},
    "SHS": {"pe": 0, "pb": 0, "roe": 0},
    "MBS": {"pe": 0, "pb": 0, "roe": 0},
    "FTS": {"pe": 0, "pb": 0, "roe": 0}
  },
  "ranking": ["MÃ1", "MÃ2", "..."],
  "period": "(kỳ dữ liệu tool)",
  "source": "peer_compare",
  "note": "(tuỳ chọn)"
}
```

- Đúng kỳ mà tool trả về.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

