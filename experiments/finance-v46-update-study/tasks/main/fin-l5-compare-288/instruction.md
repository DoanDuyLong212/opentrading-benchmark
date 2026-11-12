# Biến động 1 phiên NG=F vs XAUUSD

So sánh **% thay đổi 1 phiên gần nhất** của **NG=F** (theo `yf_commodities`, từ `prev` → `price`) và của **XAUUSD** (đóng cửa phiên 30/10/2026 so với phiên 29/10/2026, theo `vn_msn_fx_gold`): các % là bao nhiêu? Biến động của NG=F **mạnh hơn hay yếu hơn** XAUUSD (so |%|)?

## Yêu cầu trả lời
Trả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:

```json
{
  "values": {"sym_pct": 0, "xauusd_pct": 0, "so_sanh": "mạnh hơn hoặc yếu hơn"},
  "period": "phiên gần nhất (30/10/2026)",
  "source": "yf_commodities + vn_msn_fx_gold",
  "note": "(tuỳ chọn)"
}
```

- `sym_pct` là % thay đổi của NG=F; `xauusd_pct` là % thay đổi của XAUUSD. Biến động mạnh hơn = |%| lớn hơn.

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot được ghi trong hợp đồng dữ liệu dưới đây. Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Mọi số trong object JSON trả lời phải truy nguồn được từ tool MCP bạn đã gọi trong phiên này — không dùng kiến thức nền hay ghi nhớ.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog.

## Hợp đồng dữ liệu và bằng chứng
- Snapshot cố định: `2026-11-01`. Không cần đọc task.toml; metadata này được cung cấp trực tiếp trong đề.
- `source` là tên tool MCP; `evidence[].source` là nhà cung cấp trong `provenance.source`. Đây là hai namespace riêng.
- Thêm trường `evidence` vào object JSON trả lời: danh sách các đối tượng `{"tool":"tên tool", "source":"provenance.source", "as_of":"provenance.as_of", "call_id":"benchmark_evidence.call_id", "payload_sha256":"benchmark_evidence.payload_sha256", "matched_entry_id":"benchmark_evidence.matched_entry_id", "response_sha256":"benchmark_evidence.response_sha256"}` lấy từ phản hồi tool thực gọi. Dẫn đầy đủ các phản hồi cần thiết cho chỉ tiêu/mã/kỳ được hỏi (kể cả các mã riêng biệt cùng tool/nguồn/timestamp); catalog có thể chứa dữ liệu không liên quan. Không suy đoán timestamp và không dùng thời gian của máy làm as_of.
- Khi từ chối, bắt buộc có trường `value` với JSON `null`; chuỗi "null", thiếu trường, object hay số đều không hợp lệ. Thời kỳ phải nêu đúng năm, quý/tháng/ngày và đủ hai kỳ nếu đề yêu cầu so sánh.

## Hợp đồng biểu diễn số và nguồn chung (v4.6-update)
- Với kết quả số không được đề yêu cầu làm tròn, giữ độ chính xác của phép tính; xuất tối thiểu 6 chữ số sau dấu thập phân khi cần, sai số tuyệt đối không quá 0.000001. Không dùng số đã làm tròn để tính tiếp. Nếu dùng calculator, yêu cầu đủ độ chính xác thay vì mặc định 2 chữ số.
- Tỷ số không nhân 100 dùng nhãn đơn vị rõ ràng `tỷ lệ`, `dimensionless` hoặc `lần`; không để trống, không dùng đơn vị tiền hay `%` cho tỷ số này.
- `source` ghi đầy đủ tên các tool nguồn cần thiết để trả lời yêu cầu, gồm resolver nếu yêu cầu phân giải tên/mã, ngăn bằng ` + `. Ghi tên tool chính xác, không thêm tiền tố harness; utility tính toán được ghi ở lineage/note khi cần, không thay thế tool nguồn.
- `period` chỉ ghi kỳ/ngày của dữ liệu được hỏi (VD `30/10/2026`, `Q3/2026`, hoặc hai kỳ khi đề yêu cầu so sánh); không ghi kèm ngày snapshot, thời điểm lấy dữ liệu hay `as_of` vào trường này.

