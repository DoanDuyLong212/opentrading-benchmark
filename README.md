# Benchmark harness tài chính Việt Nam — v4.7

Benchmark so sánh ba harness agent trên **cùng một model và cùng một bộ dữ liệu**:

- **OpenTrading**, harness chuyên về tài chính, dùng profile `machine`;
- **OpenCode**, harness đa dụng;
- **DeepSeek Harness (DSH)**, harness đa dụng.

Câu hỏi đặt ra: khi model và dữ liệu giữ nguyên, chỉ thay harness, thì câu trả lời tài chính đúng hơn, nhanh hơn và rẻ hơn đến mức nào.

Kết quả đầy đủ: [`Results.md`](experiments/finance-v47-study/final-20261126/Results.md).

## Cấu hình

| Hạng mục | Giá trị |
|---|---|
| Bộ đề | 300 task tiếng Việt × 3 harness × 1 lượt = 900 trial |
| Model (chung cho cả 3) | `deepseek/deepseek-v4.1-flash-1017`, temperature 0, không yêu cầu reasoning |
| Dữ liệu | Snapshot MCP đóng băng ngày 01/11/2026, phiên cuối là 30/10/2026; mọi đáp án tính từ snapshot bằng script |
| Tool model thấy | Tool dữ liệu MCP và shell tính toán; OpenTrading giữ thêm tool đọc kết quả đã lưu và tool memory chỉ đọc |
| Chấm điểm | Grader xác định, judge **Claude Haiku 5.5**, rồi duyệt tay |
| Task investor | Mua giả định tại giá đóng cửa 30/10/2026, chấm theo giá đóng cửa 23/11/2026 |

Một trial **đạt** khi thoả cả bốn điều kiện:

1. Judge chấm là đúng.
2. Mọi số nằm trong sai số cho phép.
3. Câu có đáp án là từ chối thì không được đưa ra số nào.
4. Không bị loại khi duyệt tay. Duyệt tay chỉ có thể loại một trial, không bao giờ nâng nó thành đạt.

Mẫu số là toàn bộ trial: trial không có câu trả lời cuối vẫn tính là không đạt.

## Kết quả

| Nhóm | Task | **OpenTrading** | OpenCode | DSH |
|---|---:|---:|---:|---:|
| Compute | 79 | **78** | 75 | 76 |
| Investor | 36 | **19** | 16 | 16 |
| Lookup | 112 | 110 | 110 | 110 |
| Memory | 59 | **58** | 30 | 50 |
| Robustness | 14 | 14 | 14 | 14 |
| **Tổng** | **300** | **279 (93,0%)** | 245 (81,7%) | 266 (88,7%) |

So sánh từng cặp trên cùng task bằng kiểm định dấu chính xác, hai phía:

- OpenTrading so với OpenCode: thắng 40, thua 6, p ≈ 3,1·10⁻⁷.
- OpenTrading so với DSH: thắng 19, thua 6, p ≈ 0,015.

| Thời gian, chi phí, độ tin cậy | **OpenTrading** | OpenCode | DSH |
|---|---:|---:|---:|
| Thời gian một trial, trung vị (s) | 36 | 47 | 31 |
| Thời gian một trial, p90 (s) | **97** | 300 | 228 |
| Trial dài hơn 5 phút | **1** | 30 | 17 |
| Request model / trial (trung bình) | **3,8** | 6,8 | 7,2 |
| Tổng chi phí (USD) | **0,68** | 1,29 | 1,23 |
| Chi phí / câu đúng (USD) | **0,0024** | 0,0053 | 0,0046 |
| Trả lời đúng định dạng | **299** | 288 | 285 |
| Từ chối sai (trên 289 câu có đáp án) | **0** | 10 | 0 |
| Đưa số ở câu phải từ chối (trên 11 câu) | 0 | 0 | 0 |
| Số nằm ngoài sai số | **1** | 15 | 5 |

Chi phí là số tiền nhà cung cấp model báo cho từng request. Riêng OpenCode và DSH ở 100 task, chi phí được ước tính từ số token theo cùng bảng giá.

**Tóm tắt kết quả:**

- Ở nhóm compute, lookup và robustness, ba harness chênh nhau không quá ba task.
- Khác biệt chủ yếu nằm ở **memory**: OpenTrading áp dụng đúng quy tắc người dùng đã dặn ở phiên trước, kể cả quy tắc đã được cập nhật hoặc thu hồi, ở 58/59 task.
- OpenTrading chậm hơn ở các câu tra cứu ngắn, vì prompt hệ thống và bộ tool của nó lớn hơn. Ngược lại, nó nhanh hơn hẳn ở task dài, nhiều bước.
- Không harness nào vượt chiến lược "luôn bán", vốn đạt 11/16 câu khuyến nghị mua, giữ, bán trong giai đoạn thị trường giảm này.

## Giới hạn

- Mỗi task chỉ chạy một lượt cho mỗi harness, nên benchmark không đo được độ ổn định khi chạy lại.
- Nhóm investor chỉ phản ánh một giai đoạn thị trường giảm kéo dài ba tuần (31/10–23/11/2026). Nên xem đây là tín hiệu, không phải thước đo năng lực đầu tư.
- Task memory do chính nhóm phát triển memory của OpenTrading viết.
- Judge chỉ được kiểm trước trên các câu rõ đúng và rõ sai: 200 câu có kiểm soát, Cohen's κ = 1,0.

## Cấu trúc repo

| Đường dẫn | Nội dung |
|---|---|
| `experiments/finance-v47-study/final-20261126/` | Kết quả cuối: `Results.md`, `FINAL-300-corrected.json` (kết quả từng trial sau khi chấm), `HAIKU-FINAL-300-report.json`, các amendment và script tạo báo cáo |
| `experiments/finance-v47-study/tasks/main/` | 200 task, mỗi task gồm đề, đáp án và grader; danh sách 100 task còn lại nằm trong `final-20261126/amendments/BLOCK-B-300-20261125.json` |
| `experiments/finance-v47-study/tools/` | Runner, gateway, judge, config `bench_config_v47.json` |
| `experiments/finance-v47-study/README.md` | Cách dựng toolchain ghim và kiểm tra offline |

Khi tái lập, đọc [`experiments/finance-v47-study/README.md`](experiments/finance-v47-study/README.md). Các bước kiểm tra offline không cần credential model.
