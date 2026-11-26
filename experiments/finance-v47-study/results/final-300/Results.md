# Kết quả benchmark tài chính v4.7: OpenTrading vs OpenCode vs DSH

## 1. Cấu hình

| Hạng mục | Giá trị |
|---|---|
| Harness | **OpenTrading** (profile `machine`, runtime `ae7ec48`), **OpenCode**, **DSH** |
| Model agent (chung) | `deepseek/deepseek-v4.1-flash-1017` qua OpenRouter, temperature 0 |
| Bộ đề | **300 task tiếng Việt × 3 harness × 1 lượt = 900 trial** ([`tasks/`](tasks/), sha256 từng task trong [`tasks.sha256.json`](tasks.sha256.json)) |
| Nhóm task | compute 79 · investor 36 · lookup 112 · memory 59 · robustness 14 |
| Dữ liệu | Snapshot MCP đóng băng ngày 01/11/2026. Task investor chấm theo giá thật 31/10–23/11/2026 |
| Judge | Claude Haiku 5.5 (662 trial); Nemotron 3 Ultra kèm duyệt tay (238 trial OpenCode/DSH) |
| Phiên bản harness | OpenCode 2.4.1 / 2.1.2, DSH 0.2.2-rc.5 / 0.2.1-rc.2; OpenTrading một phiên bản cho cả 300 task |

**Cách chấm.** Một trial **đạt** khi thoả cả bốn điều kiện:
1. Judge chấm đúng.
2. Mọi trường số nằm trong sai số cho phép.
3. Không đưa số ở câu phải từ chối.
4. Không bị loại khi duyệt tay.

Mẫu số là toàn bộ trial: trial không có câu trả lời vẫn tính là không đạt.

## 2. Kết quả chính

| | **OpenTrading** | OpenCode | DSH |
|---|---:|---:|---:|
| **Đạt / 300** | **279 (93,0%)** | 245 (81,7%) | 266 (88,7%) |

So từng cặp trên cùng task (kiểm định dấu chính xác, hai phía):

| So sánh | OT thắng | OT thua | p |
|---|---:|---:|---:|
| OpenTrading vs OpenCode | 40 | 6 | 3,1·10⁻⁷ |
| OpenTrading vs DSH | 19 | 6 | 0,015 |

## 3. Theo nhóm và họ task

| Nhóm (task) | **OpenTrading** | OpenCode | DSH |
|---|---:|---:|---:|
| Compute (79) | **78** | 75 | 76 |
| Investor (36) | **19** | 16 | 16 |
| Lookup (112) | 110 | 110 | 110 |
| Memory (59) | **58** | 30 | 50 |
| Robustness (14) | 14 | 14 | 14 |

| Họ | Nội dung | Task | OT | OC | DSH |
|---|---|---:|---:|---:|---:|
| C1–C4 | Tính toán từ chuỗi giá | 56 | **56** | 54 | 55 |
| C5 | Chỉ số báo cáo tài chính (ROE, ROA, DuPont…) | 23 | **22** | 21 | 21 |
| L2–L5 | Tra cứu, so sánh nhiều nguồn | 112 | 110 | 110 | 110 |
| I1 | Chọn mã trong ngành có lãi hơn trung bình ngành | 5 | **4** | 2 | 2 |
| I2 | Chọn mã tăng nhiều nhất | 4 | 0 | 0 | 0 |
| I3 | Gắn cờ 2 mã rủi ro giảm sâu nhất | 5 | **4** | 1 | 2 |
| I4 | Danh mục 4 mã thắng trung bình | 3 | **3** | 1 | **3** |
| I5 | Chọn mã theo ràng buộc đã ghi nhớ | 3 | 1 | **2** | 1 |
| R1 | Khuyến nghị MUA / GIỮ / BÁN (ngưỡng ±2%) | 16 | 7 | **10** | 8 |
| M1–M2 | Ghi nhớ tiêu chí lọc đơn giản | 13 | 12 | **13** | **13** |
| M3 | Ghi nhớ nhiều phiên | 15 | **15** | 3 | 13 |
| M4 | Ghi nhớ quy tắc lọc | 11 | **11** | 1 | 9 |
| M5 | Thu hồi / ghi nhớ đã cũ | 7 | **7** | 3 | 6 |
| M6 | Quy ước tính và cập nhật | 13 | **13** | 10 | 9 |
| S2–S3 | Chỉ dẫn lẫn trong dữ liệu, dữ liệu cũ | 14 | 14 | 14 | 14 |

- 12 task cả ba harness đều trượt: I2 ×4, R1 ×4, cùng I1, I3, I5, C5 mỗi họ một task.
- 3 task chỉ OpenTrading trượt: `fin-i5-mem-743`, `fin-r1-call-781`, `fin-m2-screen-507` (không có câu trả lời).

## 4. Chất lượng câu trả lời

| Metric | **OpenTrading** | OpenCode | DSH |
|---|---:|---:|---:|
| Đúng định dạng JSON | **299/300** | 288/300 | 285/300 |
| Không có câu trả lời (DNF) | **1** | 6 | 6 |
| Từ chối sai (289 câu có đáp án) | **0** | 10 | 0 |
| Đưa số ở câu phải từ chối (11 câu) | 0 | 0 | 0 |
| Số nằm ngoài sai số | **1** | 15 | 5 |
| Judge: đúng / một phần / sai / không trả lời | **279** / 2 / 18 / 1 | 248 / 8 / 38 / 6 | 268 / 6 / 21 / 5 |

## 5. Chi phí, token, thời gian

| Metric | **OpenTrading** | OpenCode | DSH |
|---|---:|---:|---:|
| Tổng chi phí (USD) | **0,68** | 1,25* | 1,19* |
| Chi phí / trial (USD) | **0,0023** | 0,0042 | 0,0040 |
| Chi phí / lần đạt (USD) | **0,0024** | 0,0051 | 0,0045 |
| Token đầu vào / trial (trung bình) | **55,9 nghìn** | 114,7 nghìn | 116,1 nghìn |
| Token đầu ra / trial (trung bình) | **3,0 nghìn** | 7,4 nghìn | 6,5 nghìn |
| Request model / trial | **3,8** | 6,8 | 7,2 |
| Lần gọi tool dữ liệu (MCP) / trial | 3,4 | 4,5 | 4,2 |
| Thời gian p50 | 36 giây | 48 giây | **31 giây** |
| Thời gian p90 | **95 giây** | 294 giây | 218 giây |
| Trial dài hơn 5 phút | **1** | 30 | 17 |

Chi phí là số tiền OpenRouter báo cho từng request. \*Ở 119 trial của mỗi harness OpenCode và DSH, chi phí được ước tính từ token theo giá niêm yết; giá thực tế có thể cao hơn.

## 6. Phân tích OpenTrading

**Điểm mạnh**
- **Memory 58/59.** OT áp dụng đúng quy tắc người dùng đã dặn qua nhiều phiên, kể cả khi quy tắc bị cập nhật hoặc thu hồi (M3–M6 đạt 100%).
  - OpenCode yếu nhất ở nhóm này (30/59): hay hết lượt request trước khi trả lời, hoặc áp dụng quy tắc cũ.
  - DSH đạt 50/59 nhưng trượt nhiều ở M6.
- **Tin cậy nhất.** 0 từ chối sai, 1 DNF, chỉ 1 lần số liệu nằm ngoài sai số (OpenCode 15, DSH 5).
- **Rẻ và gọn nhất.** Chi phí trên mỗi lần đạt bằng khoảng ½ hai harness kia, với khoảng ½ số token và số request. p90 thấp nhất (95 giây), chỉ 1 trial dài hơn 5 phút.
- **Dẫn đầu investor (19/36),** mạnh ở chọn mã trong ngành (I1), cảnh báo rủi ro (I3) và danh mục (I4).

**Điểm yếu**
- **Khuyến nghị MUA / GIỮ / BÁN (R1): 7/16,** thấp hơn OpenCode (10/16) và DSH (8/16).
  - Cả ba đều thua chiến lược "luôn bán" (11/16), vì thị trường giảm trong giai đoạn chấm.
  - Phân bố khuyến nghị của OT (8 BÁN / 6 MUA / 2 GIỮ) gần giống hai harness kia, nên OT trượt vì chọn sai từng mã chứ không phải vì thiên về MUA.
- **I2 (chọn mã tăng mạnh nhất): 0/4 ở cả ba harness.**
- **Câu tra cứu ngắn chậm hơn.** p50 cao hơn DSH, vì prompt hệ thống và bộ tool của OT lớn hơn. Lợi thế tốc độ chỉ thể hiện ở task dài, nhiều bước.

## 7. So sánh 3 harness

| Khía cạnh | **OpenTrading** | OpenCode | DSH |
|---|---|---|---|
| Tỷ lệ đạt | **93,0%, cao nhất** | 81,7% | 88,7% |
| Compute / lookup / robustness | Gần như ngang nhau | Gần như ngang nhau | Gần như ngang nhau |
| Memory | **58/59** | 30/59, yếu nhất | 50/59 |
| Investor | **19/36** | 16/36, tốt nhất ở R1 | 16/36 |
| Độ tin cậy | **1 DNF, 0 từ chối sai** | 6 DNF, 10 từ chối sai | 6 DNF |
| Chi phí / lần đạt | **$0,0024** | $0,0051 | $0,0045 |
| Thời gian p90 | **95 giây** | 294 giây | 218 giây |

**Kết luận.** OpenTrading đạt cao nhất, ổn định nhất và rẻ nhất. Khác biệt so với OpenCode và DSH có ý nghĩa thống kê, và đến chủ yếu từ nhóm memory cùng độ tin cậy. Ở compute, lookup và robustness, ba harness gần như ngang nhau. Riêng khuyến nghị MUA/GIỮ/BÁN, không harness nào vượt chiến lược "luôn bán".

## 8. Giới hạn

- Mỗi task chạy một lượt cho mỗi harness, nên không đo được độ ổn định khi chạy lại.
- Nhóm investor nhỏ (36 task) và chỉ phản ánh một giai đoạn thị trường giảm ba tuần. Nên xem đây là tín hiệu, không phải thước đo năng lực đầu tư.
- Lookup gần bão hoà (≥ 98% ở cả ba harness), nên ít giúp phân biệt.

## 9. Dữ liệu trong thư mục này

| File | Nội dung |
|---|---|
| `trials.jsonl` | 900 trial đầy đủ: câu trả lời cuối (`attempts[].final_text`), token, chi phí, thời gian, `manifest_sha256` |
| `judge.jsonl` | Kết quả chấm từng trial: verdict, lý do của judge, numeric gate, cờ `primary` |
| `manifests/` | Manifest của các lần chạy, đặt tên theo `manifest_sha256` |
| `tasks/` | 300 task (đề, dữ liệu snapshot, đáp án, grader) |
| `summary.json`, `summarize.py` | Mọi số trong báo cáo này; chạy `python3 summarize.py` để tính lại |

sha256: `trials.jsonl` `296339fe3d19763d139b6925e297db29835462fe9f47e5e62093709b4902f070` · `judge.jsonl` `bb896a6fcb3aa618a3986b9230448290a25a5bbd687af22c2b52901a9261c3fd`
