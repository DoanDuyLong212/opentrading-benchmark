# Đòn bẩy hoạt động TTM DBC/VHC/SAB

Số liệu lấy từ `financial_statements` (KQKD: `statement="KQKD"`, cân đối kế toán: `statement="CDKT"`; theo quý: `period="quarter"`, theo năm: `period="year"`). Với **DBC, VHC, SAB**: so sánh 4 quý **Q3/2025–Q2/2026** với 4 quý **Q3/2024–Q2/2025**. Tính cho từng mã: **tăng trưởng doanh thu thuần TTM** (%), **tăng trưởng LN thuần từ HĐKD TTM** (%), và **đòn bẩy hoạt động** = tăng trưởng LN thuần từ HĐKD ÷ tăng trưởng doanh thu (lần). Mã nào có đòn bẩy hoạt động cao nhất?

Làm tròn kết quả tới **2 chữ số thập phân** (khối lượng và số tiền đồng: làm tròn tới số nguyên); xếp hạng/so sánh dùng số chưa làm tròn.

## Yêu cầu trả lời
Trả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:

```json
{
  "values": {
    "DBC": {
      "rev_growth": 0,
      "op_growth": 0,
      "op_leverage": 0
    },
    "VHC": {
      "rev_growth": 0,
      "op_growth": 0,
      "op_leverage": 0
    },
    "SAB": {
      "rev_growth": 0,
      "op_growth": 0,
      "op_leverage": 0
    },
    "highest": "MÃ"
  },
  "unit": "% / lần",
  "period": "(kỳ được hỏi)",
  "source": "financial_statements",
  "note": "(tuỳ chọn)"
}
```


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

