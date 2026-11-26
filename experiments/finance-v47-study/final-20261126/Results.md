# Kết quả benchmark tài chính v4.7: OpenTrading vs OpenCode vs DSH

## 1. Tổng quan

| Hạng mục | Giá trị |
|---|---|
| Harness so sánh | **OpenTrading** (`opentrading_machine`), **OpenCode**, **DSH** |
| Model agent (chung cho cả 3) | `deepseek/deepseek-v4.1-flash-1017` |
| Bộ task | **300 task × 3 harness × 1 lượt = 900 trial** |
| ↳ Khối A, bộ chính | 200 task: compute 69, investor 36, lookup 30, memory 51, robustness 14 |
| ↳ Khối B, bộ mở rộng | 100 task: lookup 82, compute 10, memory 8 |
| Judge | Claude Haiku 5.5 |
| Dữ liệu thị trường | Snapshot MCP ngày 01/11/2026. Task investor chấm theo giá thật 31/10–23/11/2026 |

**Cách chấm (điểm chính):** một trial **đạt** khi thoả cả bốn điều kiện:
- judge chấm "correct";
- mọi trường số nằm trong sai số cho phép;
- không bịa số (ở câu bẫy phải từ chối);
- không bị loại khi duyệt tay.

Task investor được chấm **tự động theo kết quả lãi/lỗ thật** sau ngày snapshot. **Mẫu số** là mọi trial; trial không trả lời vẫn tính là không đạt.

---

## 2. Kết quả chính

| | **OpenTrading** | OpenCode | DSH |
|---|---|---|---|
| **Khối A (200 task)** | **180/200 (90,0%)** | 145/200 (72,5%) | 166/200 (83,0%) |
| Khối B (100 task) | 99/100 (99,0%) | 100/100 (100%) | 100/100 (100%) |
| **Tổng 300 task** | **279/300 (93,0%)** | 245/300 (81,7%) | 266/300 (88,7%) |

**OpenTrading đứng đầu** ở khối A và tổng 300 task. Khối B quá dễ: cả 3 harness đều đạt gần tuyệt đối, nên không giúp phân biệt các harness.

### So từng cặp trên cùng task

Kiểm định dấu chính xác, hai phía.

| So sánh | Phạm vi | OT thắng | OT thua | p | Kết luận |
|---|---|---|---|---|---|
| OT vs OpenCode | Khối A | 37 | 4 | ≈ 1·10⁻⁷ | **OT hơn rõ rệt** |
| OT vs DSH | Khối A | 18 | 5 | ≈ 0,011 | **OT hơn, có ý nghĩa** |
| OT vs OpenCode | Tổng 300 | 40 | 6 | ≈ 3·10⁻⁷ | **OT hơn rõ rệt** |
| OT vs DSH | Tổng 300 | 19 | 6 | ≈ 0,015 | **OT hơn, có ý nghĩa** |

*Cặp khối A tính trên 181 task được chấm hoàn toàn bằng judge Haiku.*

---

## 3. Kết quả theo nhóm (khối A)

| Nhóm (số task) | **OpenTrading** | OpenCode | DSH |
|---|---|---|---|
| Compute (69) | **68 (98,6%)** | 65 (94,2%) | 66 (95,7%) |
| Investor (36) | **19 (52,8%)** | 16 (44,4%) | 16 (44,4%) |
| Lookup (30) | 28 (93,3%) | 28 (93,3%) | 28 (93,3%) |
| Memory (51) | **51 (100%)** | 22 (43,1%) | 42 (82,4%) |
| Robustness (14) | 14 (100%) | 14 (100%) | 14 (100%) |

### Theo họ task

| Họ | Nội dung | Task | OT | OC | DSH |
|---|---|---|---|---|---|
| C5 | Chỉ số từ báo cáo tài chính (ROE, ROA, DuPont, đòn bẩy…) | 23 | **22** | 21 | 21 |
| I1 | Chọn 1 mã trong ngành có lãi hơn trung bình ngành | 5 | **4** | 2 | 2 |
| I2 | Chọn mã tăng nhiều nhất | 4 | 0 | 0 | 0 |
| I3 | Gắn cờ 2 mã có rủi ro giảm sâu nhất | 5 | **4** | 1 | 2 |
| I4 | Danh mục 4 mã thắng trung bình | 3 | **3** | 1 | **3** |
| I5 | Chọn mã theo ràng buộc đã ghi nhớ | 3 | 1 | **2** | 1 |
| R1 | Khuyến nghị MUA / GIỮ / BÁN (ngưỡng ±2%) | 16 | 7 | **10** | 8 |
| M3 | Ghi nhớ nhiều phiên | 15 | **15** | 3 | 13 |
| M4 | Ghi nhớ quy tắc lọc | 11 | **11** | 1 | 9 |
| M5 | Thu hồi ghi nhớ | 5 | **5** | 1 | 4 |
| M6 | Ghi nhớ quy ước tính và cập nhật | 13 | **13** | 10 | 9 |
| S2 / S3 | Chỉ dẫn lẫn trong dữ liệu / dữ liệu cũ | 14 | 14 | 14 | 14 |

- **12 task cả 3 harness đều trượt:** I2 ×4, R1 ×4, và I1, I3, I5, C5 mỗi họ 1.
- **2 task chỉ OpenTrading trượt** (hai harness kia đều đạt): `fin-i5-mem-743`, `fin-r1-call-781`.

---

## 4. Chất lượng câu trả lời

| Metric | Phạm vi | **OpenTrading** | OpenCode | DSH |
|---|---|---|---|---|
| Đạt theo grader tự động (không dùng judge) | Khối A | **173** | 140 | 161 |
| Câu trả lời đúng định dạng JSON | Khối A | **200/200** | 188/200 | 186/200 |
| Không trả lời được (DNF) | Khối A | **0** | 6 | 6 |
| Từ chối sai (câu trả lời được) | Khối A | **0/192** | 10/192 | 0/192 |
| Trả lời ở câu bẫy (đáng lẽ phải từ chối) | Khối A | 0/8 | 0/8 | 0/8 |
| Bị loại vì sai số liệu | Khối A | **1** | 15 | 5 |
| Judge: đúng / một phần / sai / không trả lời | Khối A | **180** / 2 / 18 / 0 | 148 / 8 / 38 / 6 | 168 / 6 / 21 / 5 |
| Từ chối sai | Tổng 300 | **0/289** | 10/289 | 0/289 |
| Trả lời ở câu bẫy | Tổng 300 | 0/11 | 0/11 | 0/11 |

---

## 5. Chi phí, token, thời gian

| Metric | Phạm vi | **OpenTrading** | OpenCode | DSH |
|---|---|---|---|---|
| Chi phí / trial | Khối A | **$0,0030** | $0,0061 | $0,0058 |
| Chi phí / lần đạt | Khối A | **$0,0033** | $0,0084 | $0,0070 |
| Token đầu vào (trung bình) | Khối A | **74 nghìn** | 166 nghìn | 169 nghìn |
| Token đầu ra (trung bình) | Khối A | **4,0 nghìn** | 10,5 nghìn | 9,2 nghìn |
| Thời gian p50 | Khối A | **46 giây** | 72 giây | 47 giây |
| Thời gian p90 | Khối A | **117 giây** | 401 giây | 297 giây |
| Số lần gọi tool dữ liệu (MCP, trung bình) | Khối A | 4,4 | 5,9 | 5,4 |
| Chi phí / trial | Khối B | $0,0008 | $0,0008 | $0,0007 |
| Thời gian p50 / p90 | Khối B | 29 / 38 giây | 16 / 30 giây | 17 / 31 giây |
| **Tổng chi phí** | 300 task | **$0,68** | $1,29 | $1,23 |

Chi phí lấy từ số tiền OpenRouter báo cho từng request. Riêng OpenCode và DSH ở khối B là ước tính từ số token theo cùng bảng giá.

---

## 6. Phân tích OpenTrading

### Điểm mạnh
- **Memory tuyệt đối (51/51).** OT áp dụng đúng quy tắc người dùng đã dặn qua nhiều phiên, kể cả khi quy tắc bị cập nhật hoặc thu hồi (M3, M4, M5, M6 đều 100%).
  - OpenCode yếu nhất ở nhóm này (43%). Nó hay hết lượt request trước khi trả lời, hoặc áp dụng sai quy tắc mới nhất.
  - DSH khá (82%) nhưng trượt nhiều ở M6 (quy ước tính ROE và cập nhật ràng buộc).
- **Tin cậy nhất:**
  - 0 trial bỏ dở, 0 lần từ chối sai, 100% câu trả lời đúng định dạng.
  - Chỉ 1 lần bị loại vì sai số liệu, so với 15 của OpenCode và 5 của DSH.
- **Hiệu quả nhất:**
  - Trên bộ chính, OT tốn **khoảng ½ chi phí** và **khoảng ½ token** so với hai harness kia.
  - Thời gian p90 thấp nhất (117 giây so với 297–401 giây), tức OT ít khi bị kéo dài bất thường.
- **Investor dẫn đầu nhóm** (19/36). OT mạnh rõ ở chọn mã trong ngành (I1: 4/5), cảnh báo rủi ro (I3: 4/5) và xây danh mục (I4: 3/3).

### Điểm yếu
- **Khuyến nghị MUA / GIỮ / BÁN (R1): 7/16, thấp hơn OpenCode (10/16) và DSH (8/16).**
  - Cả 3 harness đều **thấp hơn chiến lược ngây thơ "luôn bán" (11/16)**, vì thị trường giảm trong giai đoạn đánh giá (đáp án: 11 BÁN, 5 MUA).
  - Phân bố khuyến nghị của OT (8 BÁN / 6 MUA / 2 GIỮ) gần giống hai harness kia (OC 9 / 6 / 1, DSH 7 / 6 / 2). OT không thiên về MUA; nó trượt vì chọn sai ở từng mã.
- **Chọn mã tăng nhiều nhất (I2): 0/4 ở cả 3 harness**, thấp hơn mức chọn ngẫu nhiên (khoảng 17%). Dự đoán mã tăng mạnh nhất trong 3 tuần từ dữ liệu quá khứ gần như không làm được.
- **Chọn mã theo ràng buộc đã ghi nhớ có cập nhật (I5): 1/3.**
- **Task dễ (khối B):** OT chậm hơn hai harness kia (p50 29 giây so với 16–17 giây), vì prompt hệ thống và bộ tool của OT nặng hơn. Lợi thế tốc độ của OT chỉ thể hiện ở task dài, nhiều bước.

---

## 7. So sánh 3 harness

| Khía cạnh | **OpenTrading** | OpenCode | DSH |
|---|---|---|---|
| Độ chính xác bộ chính | **90,0%, cao nhất** | 72,5%, thấp nhất | 83,0% |
| Compute / lookup / robustness | Rất cao, ngang nhau | Rất cao, ngang nhau | Rất cao, ngang nhau |
| Memory | **100%** | 43%, yếu nhất | 82% |
| Investor | **Dẫn đầu (19/36)**: mạnh ở chọn mã, rủi ro, danh mục | 16/36: tốt nhất ở R1 | 16/36 |
| Độ tin cậy | **0 bỏ dở, 0 từ chối sai** | 6 bỏ dở, 10 từ chối sai | 6 bỏ dở |
| Chi phí / lần đạt | **$0,0033, rẻ nhất** | $0,0084 | $0,0070 |
| Thời gian p90 | **117 giây** | 401 giây | 297 giây |

**Kết luận:** OpenTrading là harness tốt nhất trong benchmark này: **chính xác nhất, ổn định nhất, rẻ nhất**. Nó vượt OpenCode và DSH với khác biệt có ý nghĩa thống kê. Khác biệt đến chủ yếu từ nhóm memory, cùng với độ tin cậy và hiệu quả chi phí. Ở các task tính toán và tra cứu thuần, ba harness gần như ngang nhau. Riêng khuyến nghị MUA/GIỮ/BÁN, không harness nào vượt được chiến lược ngây thơ.

---

## 8. Lưu ý khi đọc

- Mỗi task chạy **1 lượt cho mỗi harness**, nên benchmark không có chỉ số độ ổn định khi chạy lại.
- Nhóm investor có cỡ mẫu nhỏ (36 task) và chỉ phản ánh **một giai đoạn thị trường** (31/10–23/11/2026, xu hướng giảm). Nên xem đây là tín hiệu định hướng.
- Khối B gồm task dễ: cả 3 harness đều gần tuyệt đối. **Khối A là thước đo chính.**
- Ở khối B và 19 task của khối A, OpenCode và DSH dùng **kết quả của phiên bản harness trước đó** (OpenCode 2.1.2, DSH 0.2.1), được chấm bằng judge và grader của phiên bản đó. Phần so sánh sạch nhất là **181 task khối A chấm hoàn toàn bằng Haiku** (mục 2).
