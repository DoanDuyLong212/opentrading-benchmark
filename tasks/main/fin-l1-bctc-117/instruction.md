# EIB — Tổng LNST quý gần nhất

Lợi nhuận sau thuế (LNST) **hợp nhất** quý gần nhất của **EIB** là bao nhiêu? Quy ra **tỷ đồng**.

Ghi `line` = **đúng tên dòng chỉ tiêu** trong báo cáo bạn lấy số. Báo cáo gốc đơn vị VND.

## Yêu cầu trả lời
Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:

```json
{
  "value": 0,
  "unit": "tỷ đồng",
  "period": "quý gần nhất (VD: Q?/yyyy)",
  "source": "financial_statements",
  "line": "tên dòng chỉ tiêu trong báo cáo",
  "note": "(tuỳ chọn)"
}
```

- Bắt buộc ghi `line` = đúng **tên dòng chỉ tiêu** trong báo cáo (VD `Tổng LNST`).

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot của task (`task.toml` → `snapshot_date`). Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong `answer.json` phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

