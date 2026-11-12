# Pilot memory — rank ROE qua 2 lượt

Bài này chạy **nhiều lượt hội thoại**: driver gửi từng lượt theo `environment/turns.json`; các lượt trước là ngữ cảnh hội thoại với bạn. **CHỈ lượt cuối** yêu cầu object JSON cuối cùng theo schema dưới.

Lượt cuối: xếp hạng 5 mã theo ROE **giảm dần**, dùng số đã đọc ở lượt trước — **không gọi lại tool**.

```json
{"values": {"ranking": ["MÃ1", "MÃ2", "MÃ3", "MÃ4", "MÃ5"]}, "source": "peer_compare", "evidence": [...]}
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
