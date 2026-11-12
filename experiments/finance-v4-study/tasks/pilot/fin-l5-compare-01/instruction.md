# Bảng so sánh 5 ngân hàng + xếp hạng ROE

## Đề bài
Dùng **`peer_compare`** lập bảng **P/E, P/B, ROE** của 5 mã **VCB, BID, CTG, TCB, MBB**, rồi **xếp hạng 5 mã theo ROE từ cao xuống thấp**.

## Yêu cầu trả lời
Trả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:

```json
{
  "values": {
    "VCB": {"pe": 0, "pb": 0, "roe": 0},
    "BID": {"pe": 0, "pb": 0, "roe": 0},
    "CTG": {"pe": 0, "pb": 0, "roe": 0},
    "TCB": {"pe": 0, "pb": 0, "roe": 0},
    "MBB": {"pe": 0, "pb": 0, "roe": 0}
  },
  "ranking": ["MÃ1", "MÃ2", "..."],
  "period": "(kỳ dữ liệu tool)",
  "source": "peer_compare",
  "note": "(tuỳ chọn)"
}
```

- Đúng kỳ mà `peer_compare` trả về (bội số theo giá cuối kỳ báo cáo — tool ghi rõ trong `note`).
- `ranking` đủ 5 mã, đúng thứ tự.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot được ghi trong hợp đồng dữ liệu dưới đây. Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong object JSON trả lời phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).

## Hợp đồng dữ liệu và bằng chứng
- Snapshot cố định: `2026-11-01`. Không cần đọc task.toml; metadata này được cung cấp trực tiếp trong đề.
- `source` là tên tool MCP; `evidence[].source` là nhà cung cấp trong `provenance.source`. Đây là hai namespace riêng.
- Thêm trường `evidence` vào object JSON trả lời: danh sách các đối tượng `{"tool":"tên tool", "source":"provenance.source", "as_of":"provenance.as_of", "call_id":"benchmark_evidence.call_id", "payload_sha256":"benchmark_evidence.payload_sha256", "matched_entry_id":"benchmark_evidence.matched_entry_id", "response_sha256":"benchmark_evidence.response_sha256"}` lấy từ phản hồi tool thực gọi. Dẫn đầy đủ các phản hồi cần thiết cho chỉ tiêu/mã/kỳ được hỏi (kể cả các mã riêng biệt cùng tool/nguồn/timestamp); catalog có thể chứa dữ liệu không liên quan. Không suy đoán timestamp và không dùng thời gian của máy làm as_of.
- Khi từ chối, bắt buộc có trường `value` với JSON `null`; chuỗi "null", thiếu trường, object hay số đều không hợp lệ. Thời kỳ phải nêu đúng năm, quý/tháng/ngày và đủ hai kỳ nếu đề yêu cầu so sánh.
