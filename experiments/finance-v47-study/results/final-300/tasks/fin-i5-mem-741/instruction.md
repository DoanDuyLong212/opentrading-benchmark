# Nhà đầu tư I5 — ràng buộc ghi nhớ (loại ngành)

Bài nhiều phiên hội thoại (driver gửi theo `environment/turns.json`); chỉ chấm lượt cuối.

**Bài mô phỏng danh mục giấy (paper trading), không phải khuyến nghị đầu tư.** Giả định hôm nay là 01/11/2026: dữ liệu chỉ tới phiên **30/10/2026**, và lệnh được coi là mua tại **giá đóng cửa phiên 30/10/2026**. Kết quả được chấm bằng giá đóng cửa thực tế các phiên **31/10–23/11/2026** (bạn không có dữ liệu này). Phân tích theo cách bạn thấy tốt nhất từ dữ liệu được cung cấp. **Bắt buộc phải chọn** đúng như yêu cầu: để trống/null, từ chối, chọn mã ngoài danh sách hoặc sai số lượng mã đều tính là sai.

Trong **VCB**, **MBB**, **VHM**, **KDH**, **FPT**, **HPG**, **GAS**, **MWG**: chọn **đúng 1 mã** để mua thêm, **tuân thủ mọi ràng buộc tôi đã nhờ bạn ghi nhớ** (còn hiệu lực). Đạt khi mã bạn chọn được phép mua theo các ràng buộc đó và có lợi suất (giá đóng cửa 23/11/2026 so với 30/10/2026) **cao hơn trung bình** của các mã được phép mua trong danh sách.

Dữ liệu có sẵn: `vn_quote_history` (`symbol`=<mã>, `days=170`: 120 phiên giá đóng cửa/khối lượng tới 30/10/2026) cho từng mã; `vn_index_ohlcv` (`symbol="VNINDEX"`, `count=120`); `financial_statements` (`symbol`=<mã>, `period="quarter"`, `statement="KQKD"` hoặc `"CDKT"`, quý Q3/2024–Q2/2026) cho: KDH, FPT, HPG, GAS, MWG. Phải xem giá của **mọi** mã ứng viên trước khi chọn.

## Yêu cầu trả lời
Trả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:

```json
{
  "values": {
    "pick": "MÃ"
  },
  "source": "vn_quote_history",
  "reason": "(lý do ngắn: dữ liệu và lập luận đã dùng)"
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

