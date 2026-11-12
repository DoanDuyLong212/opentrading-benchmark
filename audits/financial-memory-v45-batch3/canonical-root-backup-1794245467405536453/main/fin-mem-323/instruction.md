# Memory stratum — fin-mem-323

Chỉ chấm lượt cuối. Các lượt trước ở turns.json là cùng thông tin ban đầu cho mọi arm; không đưa seed vào phiênB ngoài kênh memory đã đăng ký.

Tra giá XAGUSD hiện tại theo snapshot. Tính gap_pct=(ngưỡng mua trong kế hoạch của tôi - giá hiện tại)/giá hiện tại*100; dương nghĩa là giá đang dưới ngưỡng. Đơn vị giá USD/oz; nêu đủ ngưỡng mua, mục tiêu, cắt lỗ đã được người dùng cho trước. Trả đúng một object JSON theo hợp đồng công khai.

```json
{"values": {"price": 0, "gap_pct": 0}, "plan": {"buy_limit": 0, "target": 0, "stop": 0}, "unit": "USD/oz", "period": "(ngày nguồn)", "source": "vn_msn_fx_gold", "evidence": [], "memory_evidence": []}
```

## Ràng buộc chung
- Chỉ dùng dữ liệu từ MCP `opentrading`, đúng snapshot được ghi trong hợp đồng dữ liệu dưới đây. Cấm `web_search`, `web_fetch`, `sentiment_score`.
- Số liệu thị trường/BCTC phải truy nguồn MCP trong trial này. Ràng buộc/nhãn riêng/danh mục do người dùng nêu ở lượt trước là dữ kiện người dùng, dẫn memory_evidence từ trace user-fact riêng; không giả seven-field market receipt cho dữ kiện người dùng.
- Nếu dữ liệu không tồn tại / chưa được công bố: đặt `value: null` và nêu lý do trong trường `reason` (hoặc `note`). Tuyệt đối không bịa số.
- Số viết bằng dấu chấm thập phân (VD `12.34`), không dùng dấu ngăn cách hàng nghìn.
- `source` ghi tên tool MCP chính xác như trong catalog (VD `vn_quote_history`).

## Hợp đồng dữ liệu và bằng chứng
- Snapshot cố định: `2026-11-01`. Không cần đọc task.toml; metadata này được cung cấp trực tiếp trong đề.
- `source` là tên tool MCP; `evidence[].source` là nhà cung cấp trong `provenance.source`. Đây là hai namespace riêng.
- Thêm trường `evidence` vào object JSON trả lời: danh sách các đối tượng `{"tool":"tên tool", "source":"provenance.source", "as_of":"provenance.as_of", "call_id":"benchmark_evidence.call_id", "payload_sha256":"benchmark_evidence.payload_sha256", "matched_entry_id":"benchmark_evidence.matched_entry_id", "response_sha256":"benchmark_evidence.response_sha256"}` lấy từ phản hồi tool thực gọi. Dẫn đầy đủ các phản hồi cần thiết cho chỉ tiêu/mã/kỳ được hỏi (kể cả các mã riêng biệt cùng tool/nguồn/timestamp); catalog có thể chứa dữ liệu không liên quan. Không suy đoán timestamp và không dùng thời gian của máy làm as_of.
- Khi từ chối, bắt buộc có trường `value` với JSON `null`; chuỗi "null", thiếu trường, object hay số đều không hợp lệ. Thời kỳ phải nêu đúng năm, quý/tháng/ngày và đủ hai kỳ nếu đề yêu cầu so sánh.
