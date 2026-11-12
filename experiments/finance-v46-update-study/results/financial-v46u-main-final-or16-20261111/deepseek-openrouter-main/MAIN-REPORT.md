# Báo cáo kết quả MAIN: Benchmark agent tài chính Việt Nam v4.6-update

**So sánh 3 harness:** OpenTrading (B0, `opentrading_baseline`), OpenCode, DSH. Cùng một model agent, cùng dữ liệu, cùng hợp đồng chấm.
**Phiên bản:** bộ gộp or16, chốt ngày 2026-11-12. Thư mục kết quả: `results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main`.

---

## 0. Tóm tắt

| Arm | **Primary /400** | Tỷ lệ | Δ so với B0 (CI95, bootstrap cặp theo task) | Core /280 | Compute /60 | Memory /60 | Chi phí agent |
|---|---:|---:|---|---:|---:|---:|---:|
| **OpenTrading (B0)** | **385** | **96.25%** | — | 272 | 53 | **60** | $1.498 |
| DSH | 362 | 90.50% | −5.75 pp [−9.25, −2.75] | 271 | 43 | 48 | $0.944 |
| OpenCode | 352 | 88.00% | −8.25 pp [−12.75, −4.25] | 271 | **54** | 27 | $0.972 |

1. **B0 dẫn đầu, khoảng cách có ý nghĩa thống kê.** CI95 so với cả hai arm đều không chứa 0.
2. **Khoảng cách đến từ memory và compute, không phải core.** Ở core (140 task tra cứu/tính đơn giản), ba arm gần như bằng nhau: 272 / 271 / 271, CI chứa 0.
3. **Memory:** B0 đạt 60/60 nhờ bộ nhớ native. Lưu ý thiết kế (đăng ký trước, amendment d): lệnh "ghi nhớ" đi vào kho memory của OT qua form `/nho` mà không tốn lượt model, còn OpenCode và DSH nhận cùng nội dung dưới dạng chat. Vì vậy tầng này đo năng lực bộ nhớ của sản phẩm, không đơn thuần đo khả năng nhớ của model (§8). DSH đạt 48/60: tra lại phiên cũ được nhưng hay áp tiêu chí đã lỗi thời. OpenCode đạt 27/60 vì không có bộ nhớ: 17 lần từ chối và 14 lần áp sai tiêu chí.
4. **Compute:** OpenCode 54 ≈ B0 53 > DSH 43. DSH mất 17 trial vì phần suy luận ẩn ăn hết trần 8192 token output mà harness không làm tiếp.
5. **Độ tin cậy:** audit PASS. Không có số liệu bịa nào được chấp nhận. FP trên câu bẫy là 0/22 ở cả ba arm. Judge khớp người chấm với κ = 0.85.
6. **Cái giá của B0:** dùng gấp khoảng 3.7 lần input token và khoảng 1.4 lần số request, chi phí cao hơn khoảng 55%. Nguyên nhân là prompt và schema tool rất nặng, cộng việc gọi `calculate` cho từng phép tính (xem §5, §7).

---

## 1. Thiết kế thí nghiệm

| Hạng mục | Giá trị |
|---|---|
| Model agent | `deepseek/deepseek-v4.1-flash-1017` qua OpenRouter, route trả phí do user cho phép. `effort=none` (backend vẫn tự suy luận ẩn) |
| Dữ liệu | MCP `opentrading` ở chế độ offline, snapshot cố định ngày 2026-11-01. Gold không bao giờ vào context của agent |
| Task main | 200 task: 140 core (L1–L5), 30 compute (C1–C4), 30 native-memory (M1–M5, nhiều phiên hội thoại) |
| Lịch chạy | 200 task × 3 arm × 2 run = **1200 trial**. Mẫu số luôn là mọi trial đã lên lịch |
| Giới hạn | 24 request/trial; 8192 output token/request; 3.6M token/trial; timeout 900 giây (memory 1800 giây) |
| Hợp đồng trả lời | Một object JSON gồm value(s), unit, period, source và evidence (call_id, payload_sha256, …) |
| Seal | `audits/seal/financial-v46u-seal-or16-ds.json`, freeze state `8146de99…f186`, giữ nguyên cho holdout |

**Định nghĩa metric chính (primary, judge-primary):** một trial đạt khi thỏa cả bốn điều kiện sau:
- judge chấm `correct`;
- **numeric gate** tất định: mọi field số nằm trong dung sai của gold;
- không có FP/FR theo luật: câu bẫy phải để value null, câu có đáp án thì không được từ chối;
- không bị review thủ công gỡ (review chỉ được REMOVE).

DNF luôn tính là không đạt.

## 2. Thành phần bộ gộp và thay đổi so với seal gốc

| Nguồn | Số slot | Lý do và căn cứ |
|---|---:|---|
| or16 main | 1066 | Giữ nguyên mọi slot đã có ≥1 request |
| or16r | 132 | Slot OT r1 hỏng trước khi gọi model: symlink `node_modules` bị gãy khi dọn đĩa (runner_error, 0 request). User: "tạm dừng và bổ sung OT bị hỏng trước rồi chạy tiếp" |
| or16r2 | 1 | `fin-m3-update-520` OT r2, mất mạng lúc 14:38 UTC. User: "Có" |
| or16r3 | 1 | `fin-m3-update-520` OpenCode r2, cùng sự cố mất mạng. User: "2 backfill đi" |

- Tất cả các lần chạy lại dùng cùng code, config và freeze state.
- Chỉ thay những slot hạ tầng chưa tới được model, nên không có chuyện chọn lọc theo kết quả.
- or16r2 và or16r3 chạy runs=2 vì đó là đơn vị nhỏ nhất của driver, nhưng chỉ lấy slot r2. Ở or16r3, trial r1 dư ra bị lỗi native runner; trial này không được dùng.

**Amendment:**
- **(i) Judge batch + xác nhận đơn:** judge chấm theo batch 5. Mọi phán quyết khác `correct` được chấm lại đơn lẻ.
- **(j) Auditor, áp sau khi đã thấy kết quả, user duyệt:** áp cho toán hạng `calculate` mang cả tham chiếu nguồn lẫn `value` gõ tay mà runtime chỉ giữ value. Luật chỉ nới cho 2 trial OT, cả hai đều truy được nguồn. Danh sách công khai ở `audit-v45.json → amendment_j_relaxed_bindings`.
- Không đổi grader, numeric gate hay luật FP/FR. File trong `tools/` không bị sửa.

---

## 3. Kết quả chi tiết

### 3.1 Primary theo nhóm task
| Nhóm (n/arm) | B0 | OpenCode | DSH |
|---|---:|---:|---:|
| L1 tra cứu (44) | 44 | 44 | 44 |
| L2 tính 1 bước (58) | 58 | 57 | 58 |
| L3 đa mã/lọc (72) | 71 | 69 | 72 |
| L4 chuỗi/đối chiếu nguồn/bẫy (48) | 41 | 43 | 40 |
| L5 hồ sơ/so sánh (58) | 58 | 58 | 57 |
| **Core (280)** | **272** | **271** | **271** |
| C1 (16) | 15 | 16 | 16 |
| C2 (16) | 15 | 15 | 16 |
| C3 (16) | 16 | 15 | 9 |
| C4 (12) | 7 | 8 | 2 |
| **Compute (60)** | **53** | **54** | **43** |
| M1 ghi nhớ 1 tiêu chí (12) | 12 | 12 | 12 |
| M2 nhiều tiêu chí (12) | 12 | 11 | 11 |
| M3a tách phiên (8) | 8 | 0 | 3 |
| M3b cập nhật tiêu chí (8) | 8 | 0 | 8 |
| M4 tự áp dụng tiêu chí (12) | 12 | 0 | 6 |
| M5-revoke thu hồi tiêu chí (4) | 4 | 0 | 4 |
| M5-stale giá cũ trong bộ nhớ (4) | 4 | 4 | 4 |
| **Memory (60)** | **60** | **27** | **48** |
| **Tổng (400)** | **385** | **352** | **362** |

**Δ so với B0 (CI95):**
| Nhóm | DSH | OpenCode |
|---|---|---|
| Core | −0.36 pp [−1.43, 0.71] | −0.36 pp [−2.50, 1.79] |
| Compute | −16.7 pp [−31.7, −3.3] | +1.7 pp [−5.0, 8.3] |
| Memory | −20.0 pp [−33.3, −8.3] | −55.0 pp [−71.7, −36.7] |

Luật memory, đo bằng luật cứng: stale-use 0/4 và vi phạm thu hồi 0/4 ở cả ba arm.

### 3.2 Metric phụ
| Arm | Strict grounded | Raw format hợp lệ | DNF | FP/bẫy | FR/có đáp án | Ổn định 2/2 (/200 task) | Requests | Input token (cache read) | Output token | Chi phí | p50 / p90 (giây) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 | 384 | 396 | 1 | 0/22 | 0/378 | 190 | 1658 | 29.92M (22.28M, 74%) | 0.66M | $1.498 | 17.9 / 42.4 |
| OpenCode | 349 | 398 | 0 | 0/22 | 18/378 | 172 | 1167 | 8.19M (3.68M, 45%) | 0.79M | $0.972 | 17.4 / 53.1 |
| DSH | 357 | 382 | 17 | 0/22 | 0/378 | 177 | 1201 | 7.23M (2.90M, 40%) | 0.68M | $0.944 | 18.5 / 54.7 |

- Strict = grader tất định cũ, chấm cả JSON và provenance, sau khi review đã gỡ. Strict và primary lệch nhau rất ít, chứng tỏ hai cách chấm nhất quán.
- Cột DNF ở đây dùng định nghĩa judge-primary. `summary.json` dùng định nghĩa v45 và đếm thêm các ca không trích được đáp án: B0 4, OpenCode 2, DSH 18.
- Tổng chi phí agent cho main là **$3.41**. Chi phí judge là $0 (NVIDIA NIM và OpenRouter free).

---

## 4. Phân tích lỗi của cả ba arm

Mỗi trial không đạt primary được gán đúng một nhóm lỗi bằng `analysis/classify_main_errors_or16.py`. Chi tiết từng trial ở `analysis/out/or16-main-errors.json`.

| Nhóm lỗi | B0 | OpenCode | DSH | Mô tả |
|---|---:|---:|---:|---|
| DNF do chạm trần output token | 0 | 0 | **17** | Suy luận ẩn dùng hết 8192 token, câu trả lời bị cắt hoặc rỗng |
| DNF do chạm trần request | 1 | 0 | 0 | Vượt 24 request (`Lỗi 424 upstream_attempt_cap_exceeded`) |
| Không có object đáp án | **2** | 0 | 0 | Text cuối là lời gọi tool DSML thô |
| Từ chối sai ở task memory | 0 | **17** | 0 | "Không có tiêu chí đã ghi nhớ" |
| Từ chối sai ở task khác | 0 | 1 | 0 | `l3-top-202`: tool lỗi biến thể nên agent bỏ cuộc |
| Chọn sai tập/mã | 1 | **17** | 11 | Memory áp tiêu chí cũ hoặc thiếu tiêu chí; ngoài ra lọc ngưỡng sai |
| Sai đại lượng | 4 | 6 | 0 | Hiểu sai nghĩa field (`positions`) hoặc sai công thức |
| Quy ước dấu | 7 | 5 | 8 | Đúng độ lớn nhưng ngược dấu so với gold |
| Làm tròn vượt dung sai | 0 | 1 | 1 | |
| Bị review gỡ | 0 | 1 | 1 | Khẳng định sai trong phần diễn giải |
| **Tổng không đạt** | **15** | **48** | **38** | |

### 4.1 OpenTrading (B0): 15 trial trượt
- **Quy ước dấu (7):** các task `2src-259/260/302` hỏi "hai nguồn lệch nhau bao nhiêu %" và `chain-305` hỏi "giảm mạnh nhất (ghi % vào `pct_drop`)". B0 trả số có dấu, ví dụ −0.61%, kèm diễn giải đúng chiều, trong khi gold là độ lớn hoặc ngược lại. Đây là chỗ đề mơ hồ (§8). Cả ba arm đều dính.
- **Hiểu sai field `positions` (4):** gặp ở `c4-stagger-425/430`, cả 2 run. Schema chỉ ghi `positions: {HPG: 0, …}`. B0 điền giá trị hiện tại bằng đồng thay vì lợi suất năm kép (%). Mọi field tổng hợp khác đều đúng. OpenCode mắc đúng lỗi này. DSH hiểu đúng nhưng lại bị DNF.
- **Lời gọi tool DSML lọt ra làm câu trả lời (2):** gặp ở `c1-chg-402` r2 và `c4-rebal-426` r2. DeepSeek đôi khi trả lời gọi tool dưới dạng văn bản `<｜DSML｜ calls>…` thay vì `tool_calls`. Runtime OT không nhận ra, coi đó là câu trả lời cuối và kết thúc lượt. **Đây là lỗi riêng của B0** (§7).
- **Chạm trần request (1):** `c2-ma-409` r2 gọi `calculate` cho từng giá trị đến request thứ 25 thì bị cắt.
- **Lọc thiếu mã (1):** `l3-screen-191` r1 bỏ sót POM, mã có P/E và P/B âm nhưng vẫn thỏa ngưỡng số học. OpenCode r1 cũng mắc đúng lỗi này.

### 4.2 OpenCode: 48 trial trượt
- **Không có bộ nhớ native, dẫn tới 33 trial memory trượt:** 17 lần từ chối ("không có bộ tiêu chí trong phiên này"), 14 lần chọn sai do áp tiêu chí của lượt cuối hoặc tự đoán (`m3-split`, `m4-rule`), 1 trial bị review gỡ và 1 lỗi làm tròn (`m2-port-511`). OpenCode chỉ qua được M1, M2 và M5-stale, tức các task mà thông tin nằm ngay trong phiên hiện tại.
- **1 trial "đúng do may mắn" bị review gỡ:** `m3-update-520` r2 (bản back-fill). Agent tự bịa tiêu chí "P/E < 15, P/B < 1.5, ROE > 12" trong khi tiêu chí thật là P/E < 10 và P/B < 1,2, rồi tình cờ ra đúng tập {PVS, PVT}.
- **Compute tốt (54/60):** OpenCode không có máy tính, mọi phép tính nằm trong phần suy luận. Khi bị cắt ở 8192 token, harness vẫn gửi thêm request để model hoàn thành (§5.3).
- Lỗi khác: hiểu sai `positions` (4), `c2-ann-414` ra +123.95% thay vì −55.35% (sai công thức), `l2-growth-143`, `c3-geo-424` chọn sai mã tốt nhất, `l3-crypto-multi-215` chọn sai mã thắng, và quy ước dấu (5).

### 4.3 DSH: 38 trial trượt
- **17 DNF ở C3/C4 do chạm trần output.** Ở request thứ hai, `reasoning_tokens = 8192` (toàn bộ trần). Câu trả lời bị cắt (invalid_json) hoặc rỗng. **DSH không làm tiếp khi bị cắt vì độ dài**, trong khi OpenCode thì có. Ba trial bị DNF (`stagger-430` r1, `rebal-426` r1, `stagger-425` r2) đã ghi được số đúng trong phần bị cắt, nhưng vẫn tính là không đạt.
- **Memory qua `session_search` chỉ được một phần, 11 trial chọn sai:** DSH tìm lại được phiên cũ nhưng ở `m3-split` (tiêu chí rải qua nhiều phiên) và `m4-rule` (tự áp tiêu chí) thì hay áp thiếu hoặc áp tiêu chí lỗi thời. M3a đạt 3/8, M4 đạt 6/12.
- **1 trial bị review gỡ:** `m2-port-511` r2 ghi "3 mã đều lỗ" trong khi GAS +11.43%.
- Quy ước dấu (8). Làm tròn (1): `l5-compare-285`.

---

## 5. Giải thích các metric bất thường

### 5.1 Vì sao input token của B0 lớn gấp khoảng 3.7 lần (29.9M so với 7–8M)
Lấy trung vị trên request cuối của 80 trial mỗi arm:

| Thành phần mỗi request | B0 | OpenCode | DSH |
|---|---:|---:|---:|
| System prompt | **8.2 KB** | 2.0 KB | 0.3 KB |
| Schema tool | **12.6 KB** (4 tool) | 3.8 KB (1 tool MCP) | 4.0 KB (1 tool MCP) |
| Input token mỗi request (p50) | **11.1k** | 4.1k | 3.8k |
| Số request mỗi trial (trung bình) | **4.14** | 2.92 | 3.00 |

1. **Prompt và schema cố định nặng khoảng 20 KB mỗi request**, gấp 3–4 lần hai arm còn lại.
   - System prompt của OT viết cho người dùng cuối trong terminal: quy tắc bảng, biểu đồ, chú giải thuật ngữ, kịch bản dự đoán, và cả câu "không dán JSON". Phần lớn nội dung này không liên quan tới hợp đồng benchmark.
   - Schema của `calculate` (5.4 KB) và `compute` (5.7 KB) chiếm phần lớn.
2. **Nhiều request hơn vì tính toán đi qua tool.** Prompt yêu cầu "không tự tính nhẩm: mọi số phải tính bằng `calculate`".
   - Ở C4, B0 gọi trung bình khoảng 28 lần `calculate` mỗi trial (168 lần trên 6 trial mẫu), mỗi lần một biểu thức. Trong khi đó `compute` dạng batch gần như không được dùng (1 lần).
   - Nhóm compute của B0 tốn trung bình 7.35 request và khoảng 238k input token mỗi trial.
3. **Toàn bộ context được gửi lại ở mọi request.** Vì vậy chi phí tăng theo số request nhân kích thước prompt.

Prompt caching hấp thụ 74% input của B0, nên chi phí chỉ cao hơn khoảng 55% chứ không gấp 3.7 lần. Dù vậy đây vẫn là điểm nên tối ưu đầu tiên (§7).

### 5.2 Vì sao B0 có p90 thấp nhất (42s so với 53–55s) dù nhiều request hơn
Tách theo nhóm task:

| Wall time p50 / p90 (giây) | B0 | OpenCode | DSH |
|---|---|---|---|
| Core | 15.2 / 24.5 | 15.3 / 25.2 | 17.3 / 23.6 |
| Compute | 26.9 / **84.9** | 26.6 / 67.5 | 23.5 / 45.3 |
| Memory | **35.0 / 52.6** | 50.4 / 95.6 | 62.5 / 113.5 |

- p90 tính trên toàn bộ 400 trial nên bị **nhóm memory chi phối**: 40 trial chậm nhất của DSH gồm 37 trial memory, của OpenCode gồm 26 trial memory.
- **B0 nhanh ở memory** vì theo thiết kế giao thức, lệnh "ghi nhớ giúp tôi" được đưa vào kho memory của OT qua form `/nho` (native, không gọi model). OpenCode và DSH phải xử lý cùng câu đó như một lượt chat. Trung bình B0 chỉ có 2.53 lượt model trên 3.67 lượt hội thoại, và 4.68 request mỗi trial. DSH gọi model ở mọi lượt (3.67) và còn dùng `session_search` / `session_event_read` để tìm lại phiên cũ, nên tốn 7.97 request. OpenCode tốn 5.78 request.
- **Ngược lại, B0 là arm chậm nhất ở compute (p90 85s)** vì vòng lặp `calculate`. DSH trông nhanh ở compute chỉ vì nhiều trial dừng sớm do bị cắt.
- Tóm lại, p90 tổng thấp của B0 là nhờ memory, không phải vì B0 nhanh đồng đều.

### 5.3 Vì sao DSH có 17 DNF còn OpenCode thì không (cùng model, cùng trần)
- Backend DeepSeek vẫn suy luận ẩn dù `effort=none`.
- Ở các task C3/C4, request thứ hai của cả hai arm đều bị cắt ở `reasoning_tokens = 8192`.
- Trên toàn bộ request ở nhóm compute, B0 có **0** request chạm trần, OpenCode có 18 request (15 trial), DSH có 17 request (17 trial, đúng bằng 17 DNF).
- **OpenCode** gửi thêm một request (ví dụ `stagger-425` r1: request 3 dùng 2170 token) và hoàn thành.
- **DSH** coi kết quả bị cắt là kết thúc, nên ra invalid_json hoặc không trả lời.
- **B0** né được vì đẩy phép tính ra tool `calculate`, nên phần suy luận ngắn hơn.

### 5.4 Các metric khác
- **OpenCode có 18 FR, DSH và B0 có 0:** 17/18 là task memory (§4.2). Đây không phải "thận trọng tốt" mà là thiếu năng lực nhớ.
- **Raw format của DSH 382 thấp hơn hai arm còn lại (396/398):** gần như toàn bộ do 17 DNF bị cắt giữa chừng.
- **FP = 0/22 ở cả ba arm:** cả ba đều từ chối đúng các câu bẫy (mã không tồn tại, kỳ chưa công bố).
- **Ổn định 2/2 (cùng task đạt ở cả 2 run):** B0 190/200 > DSH 177 > OpenCode 172. Thứ tự giống primary.

---

## 6. Chấm điểm: judge và người chấm

### 6.1 Judge LLM
- Model: `nvidia/nemotron-3-ultra-550b-a55b`, temperature 0. Khác họ với model agent, chấm có đáp án tham chiếu.
- Judge thấy câu hỏi, gold (expects, dung sai, refusal tokens) và câu trả lời nguyên văn; trả về `correct` / `partial` / `incorrect` kèm các field sai.
- Route: NVIDIA NIM cho phần lớn; 25 trial qua OpenRouter `:free` (không fallback sang route trả phí). Không gặp 429.
- Chế độ: batch 795, single_fallback 325, single_confirm 73. 7 trial `no_answer` không cần judge.
- **53 phán quyết lỗi** (50 rỗng/unparseable và 3 timeout) được chấm lại đơn lẻ và đều ra kết quả hợp lệ. Cache chỉ lưu phán quyết hợp lệ.
- **Judge so với grader strict:** đồng ý ở 1182/1200 trial. Bất đồng 18 trial: 14 ca strict trượt nhưng judge đạt, 4 ca strict đạt nhưng judge trượt.

### 6.2 Người chấm (Claude, user ủy quyền: "bạn đảm nhận thay tôi chấm và trả kết quả cuối cho main")
**Hiệu chỉnh judge:** đọc tay toàn bộ 18 ca bất đồng, cộng 30 ca ngẫu nhiên cùng trượt và 30 ca ngẫu nhiên cùng đạt (seed 20261112).
- Nhãn ở `analysis/labels/or16-main-labels.jsonl`.
- 7 ca có vấn đề quy ước dấu bị loại khỏi κ vì đề mơ hồ.

| n | Đồng thuận | **κ Cohen** | Judge đúng/đạt | Judge bỏ sót (FN) | Judge chấm nhầm đạt (FP) | Judge đúng/trượt |
|---:|---:|---:|---:|---:|---:|---:|
| 71 | 92.96% | **0.850** | 42 | 4 | 1 | 24 |

Mẫu được làm giàu bằng ca bất đồng, nên κ trên toàn bộ trial nhiều khả năng còn cao hơn. κ = 0.85 vượt ngưỡng κ ≥ 0.6 đã đăng ký cho gate `b0_judge_primary`.

**Kiểu lỗi của judge (5 ca, đều đã sửa bằng override):**
| Trial | Judge | Người chấm | Kiểu lỗi |
|---|---|---|---|
| fin-l1-bctc-115 DSH r2 | partial | correct | Đọc nhầm: trích "1924872" và "t tỷ đồng", hai chuỗi không có trong đáp án |
| fin-m2-screen-507 OpenCode r2 | incorrect | correct | Đọc nhầm: trích mã "FSN" không có trong đáp án |
| fin-l2-growth-141 B0 r2 | partial | correct | Quá khắt khe: "Q3/2026 so với Q2/2026" có chứa "Q3/2026" |
| fin-l2-growth-144 B0 r2 | partial | correct | Như trên |
| fin-c1-chg-402 B0 r2 | correct | **incorrect** | Chấm nhầm đạt: text cuối là lời gọi tool DSML, judge tự suy ra −5500 từ biểu thức |

Ngoài ra có 2 override từ ngày 2026-11-11 (user duyệt) cho `nonexist-236/238` B0 r1: judge bị lẫn dữ liệu giữa các trial trong cùng batch.
- **4 override nâng điểm được user duyệt ngày 2026-11-12 ("1 nâng điểm").** Nếu không áp, kết quả là B0 383, DSH 361, OpenCode 351; thứ hạng và kết luận không đổi.
- Numeric gate còn chặn thêm 1 ca judge chấm `correct` nhưng sai dấu (`2src-260` B0 r2). Đây là ví dụ cho thấy vì sao phần số phải chấm bằng luật.

**Review mọi trial thắng của cả ba arm (chỉ được REMOVE):**
- Xét 1092 trial thắng. 255 bị cờ narrative (số trong lời diễn giải không có trong payload).
  - 204 được giải thích tự động bằng re-derivation chặt: số ± payload, artifact dấu chấm hàng nghìn kiểu Việt Nam, hoặc phép tính từ hai số khác đã nêu.
  - Phần còn lại được đọc tay.
- Đọc tay thêm mẫu phân tầng 45 trial, 32 câu khẳng định dạng "đều/cả N…", và toàn bộ trial thắng ở task memory có nêu ngưỡng tiêu chí.
- **Gỡ 2 trial:** `fin-m2-port-511` DSH r2 (khẳng định sai "3 mã đều lỗ") và `fin-m3-update-520` OpenCode r2 (bịa tiêu chí ghi nhớ).
- **0 trường hợp bịa số được chấp nhận.** Audit tất định: PASS, `fabricated_evidence_accepted = 0`.

---

## 7. Review harness và đề xuất cải thiện OpenTrading

### 7.1 Điểm mạnh của B0 cần giữ
- **Bộ nhớ native (60/60):** áp đúng tiêu chí qua cập nhật, thu hồi và nhiều phiên. Kho memory có cấu trúc (form `/nho`, ghi không cần model) cộng với `memory_read` khi trả lời là khác biệt lớn nhất so với OpenCode và DSH. Kết quả này phụ thuộc vào việc người dùng ghi nhớ qua form; với lệnh ghi nhớ gõ tự do trong chat thì chưa được đo.
- **Tính toán qua tool có kiểm tra đơn vị và gắn nguồn (`calculate`/`compute`):** không bị cắt do suy luận dài như DSH, và mọi số đều truy được nguồn.
- **Policy tài chính chặt:** 0 FP, 0 FR, ổn định 2/2 cao nhất (190/200).

### 7.2 Điểm cần cải thiện, theo thứ tự ưu tiên
| # | Vấn đề (bằng chứng) | Đề xuất | Tác động dự kiến |
|---|---|---|---|
| 1 | **Lời gọi tool DSML lọt ra làm câu trả lời cuối:** 2 trial mất (`c1-chg-402`, `c4-rebal-426`). Không có chỗ nào trong `src/core/agent.ts` xử lý markup `<｜DSML｜ calls>` | Ở bước nhận câu trả lời cuối, phát hiện markup tool-call trong text. Hoặc parse nó thành `tool_calls` rồi chạy tiếp, hoặc đẩy qua nhánh `financial_rejected_final` có sẵn để yêu cầu model gọi lại đúng định dạng | +2 trial; loại bỏ một kiểu lỗi đặc thù của DeepSeek |
| 2 | **Vòng lặp `calculate` từng phép:** khoảng 28 lần mỗi trial ở C4, compute trung bình 7.35 request, p90 85s, 1 DNF do chạm trần request (`c2-ma-409`) | Cho `calculate` nhận nhiều biểu thức trong một lần gọi; prompt và mô tả tool hướng model gom phép tính hoặc dùng `compute` batch | Giảm request và token ở compute khoảng 2–3 lần; giảm p90 compute; tránh chạm trần |
| 3 | **Prompt và schema cố định khoảng 20 KB mỗi request:** 11.1k input token/request so với khoảng 4k của OpenCode/DSH; chi phí cao hơn 55% | Tách profile prompt: chế độ API/benchmark bỏ các phần về bảng, biểu đồ, chú giải thuật ngữ và kịch bản. Rút gọn mô tả `calculate`/`compute` (hiện 5.4 KB và 5.7 KB). Chỉ nạp `read_result` khi đã có kết quả bị dọn | Giảm 40–60% input token; giảm chi phí và độ trễ mỗi request |
| 4 | **Prompt mâu thuẫn với hợp đồng đầu ra:** prompt ghi "không dán JSON hay kết quả thô" trong khi task yêu cầu JSON; hiện chỉ vá bằng chú thích môi trường ở cuối (commit 70d0ae2) | Đưa hợp đồng đầu ra của caller (JSON schema) thành chỉ dẫn hạng cao hơn style, thay vì vá ở cuối | Raw format 396 → khoảng 400; bớt rủi ro ở task mới |
| 5 | **Không biết trần request bên ngoài:** OT chỉ tóm tắt khi hết `maxSteps` nội bộ, còn trần 24 request bên ngoài thì cắt luôn ở request 25 | Đồng bộ `maxSteps` với trần của caller (truyền qua config), để bước cuối luôn ép ra câu trả lời (`toolChoice: none` + SUMMARY_PROMPT đã có) | Không còn DNF do chạm trần request |
| 6 | **Hiểu sai nghĩa field theo schema:** `positions` điền giá trị bằng đồng thay vì lợi suất % (4 trial) | Bước kiểm tra cuối của finance policy: đối chiếu đơn vị và ý nghĩa field với đề (đề nói "lợi suất năm kép của từng vị thế") trước khi chốt | +4 trial nếu sửa được; đề cũng nên nêu rõ đơn vị (§8) |
| 7 | **Quy ước dấu:** 7 trial | Khi đề hỏi "lệch bao nhiêu %" hoặc "% giảm", ghi rõ quy ước dấu trong `note`; mặc định độ lớn khi đề không nói chiều. Chủ yếu nên sửa ở đề (§8) | Phụ thuộc vào cách sửa đề |

### 7.3 Ghi chú về OpenCode và DSH (để đối chiếu)
- **OpenCode:** compute tốt nhờ tự làm tiếp sau khi bị cắt vì độ dài. Nhưng không có memory nên thua 33/60 trial memory. Prompt và schema gọn nên rẻ nhất trên mỗi request.
- **DSH:** prompt rất gọn (0.3 KB), rẻ nhất về tổng chi phí. Hai điểm yếu là (1) không làm tiếp khi `finish_reason = length` (17 DNF), và (2) memory dựa trên tìm kiếm phiên nên dễ áp tiêu chí lỗi thời.

### 7.4 OT nên học gì từ OpenCode và DSH
Dù xếp sau B0 về primary, hai arm kia làm tốt hơn B0 ở một số điểm có số liệu chứng minh:

| Học từ | Điểm làm tốt hơn (bằng chứng trong main) | Gợi ý áp dụng cho OT |
|---|---|---|
| OpenCode | **Tự làm tiếp khi bị cắt vì độ dài:** chạm trần 8192 output ở 18 request (15 trial) nhưng không có DNF nào, vì harness gửi thêm request để model hoàn thành | Thêm cơ chế làm tiếp khi `finish_reason = length` hoặc reasoning chạm trần. Hiện OT không bị cắt chỉ nhờ vòng `calculate`; khi gom phép tính (§7.2 #2) và rút gọn prompt, suy luận dài ra thì sẽ cần cơ chế này |
| OpenCode | **Compute ít vòng mà vẫn đúng:** 54/60 (C4 8/12 so với 7/12 của B0) với trung bình 2.73 request/trial, so với 7.35 của B0; p90 compute 67s so với 85s | Cho model tự tính trong phần suy luận rồi **kiểm tra lại một lần** bằng `calculate`/`compute` batch, thay vì bắt mỗi phép tính phải là một lượt tool. Vẫn giữ nguồn và đơn vị nhưng bớt vòng lặp |
| OpenCode | **Tuân thủ hợp đồng đầu ra tốt nhất:** raw format 398/400 (B0 396) | Ưu tiên schema JSON của caller hơn quy tắc trình bày cho terminal (§7.2 #4) |
| OpenCode, DSH | **Prompt và schema gọn:** system 2.0 KB / 0.3 KB, schema tool khoảng 4 KB, khoảng 4k input token/request (B0 11.1k). Tổng chi phí $0.97 / $0.94 so với $1.50 | Có một profile "API/benchmark" tối giản; tách các khối style, citations, chart và glossary khỏi prompt khi caller đã định nghĩa định dạng đầu ra |
| DSH | **Ít lượt nhất ở câu dễ:** core trung bình 2.15 request/trial (OpenCode 2.32, B0 3.34) mà primary core ngang B0 (271 so với 272) | Câu tra cứu hoặc tính 1 bước thì trả lời ngay sau khi lấy dữ liệu: bỏ câu dẫn trước lượt tool, bỏ lượt `calculate` khi số đã có sẵn trong payload |
| DSH | **Hiểu đúng nghĩa field theo đề:** ở `c4-stagger-425/430`, DSH điền `positions` = lợi suất năm kép (%) đúng ý đề, trong khi B0 và OpenCode điền giá trị bằng đồng. Đáp án của DSH vẫn bị DNF vì bị cắt | Trước khi chốt, đối chiếu từng field của schema với câu chữ trong đề (đại lượng, đơn vị). Có thể làm thành một check trong finance policy (§7.2 #6) |
| DSH | **Nhớ được từ lịch sử hội thoại, không cần form:** `session_search` / `session_event_read` tìm lại phiên cũ, đạt M3b 8/8 khi tiêu chí được nói trong chat | Bộ nhớ OT hiện dựa vào form `/nho`. Nên có thêm đường dự phòng là tìm trong phiên cũ khi người dùng nói "ghi nhớ" bằng chat tự do, nhằm tránh phụ thuộc vào thao tác form (điều kiện thiết kế đã nêu ở §8) |
| DSH | **Ghi rõ dấu vết tiêu chí trong `note`:** ví dụ "P/E < 20 (thay ngưỡng P/E < 15 trước đó)", "tiêu chí P/E < 25 đã bị thu hồi" | Khi áp dụng memory, ghi trong câu trả lời tiêu chí nào đang hiệu lực và tiêu chí nào đã bị thay hoặc thu hồi, để người dùng và reviewer kiểm được |

**Không nên học:** DSH không làm tiếp khi bị cắt (17 DNF), DSH hay áp tiêu chí lỗi thời khi tiêu chí rải qua nhiều phiên (M3a 3/8, M4 6/12), và OpenCode thiếu bộ nhớ nên từ chối hoặc bịa tiêu chí (33 trial memory trượt). Ở các điểm này B0 đang làm đúng và cần giữ.

---

## 8. Hạn chế và việc nên sửa ở bộ đề
1. **Quy ước dấu chưa rõ** ở `2src-259/260/302` và `chain-305/306`: 20 trial trên cả ba arm đúng độ lớn nhưng ngược dấu. Theo nguyên tắc "sửa đề, không sửa grader", vòng sau nên ghi rõ "lấy giá trị tuyệt đối" hoặc "(nguồn A − nguồn B)/B". Kết quả lần này **không cứu điểm** cho các trial đó.
2. **Schema `positions` thiếu đơn vị** ở `c4-stagger-425/430`: nên ghi "`positions`: lợi suất năm kép (%) của từng vị thế".
3. **Tầng memory và compute được thiết kế theo năng lực OT** (amendment d, có giả thuyết theo hướng đã đăng ký trước: "OT hơn ở M3/M4"). OT nhận lệnh ghi nhớ qua form `/nho` native không tốn lượt model; DSH được bật tool `session-query` riêng cho tầng memory; OpenCode không có tool memory. Vì vậy khoảng cách ở memory phản ánh năng lực sản phẩm theo giao thức này, không phải so sánh thuần năng lực nhớ của model. Core (140 task) mới là phép so sánh không thiên lệch, và ở đó ba arm ngang nhau.
4. **`effort=none` không tắt được suy luận ẩn** của backend DeepSeek, nên trần 8192 output phạt nặng những harness không làm tiếp (DSH).
5. **Người chấm là Claude theo ủy quyền của user.** Mọi nhãn, override và quyết định REMOVE đều kèm bằng chứng trong `analysis/labels/` để user kiểm lại.
6. **Amendment (j) áp sau khi đã thấy kết quả.** Luật chỉ ảnh hưởng 2 trial và đã được công khai.
7. **Holdout chưa chạy** (chờ lệnh của user). Main chỉ là bằng chứng trên tập đề đã công bố.

## 9. Tái lập và artifact
```
python3 analysis/finalize_main_or16.py                 # merge + audit (j) + review + summary.json
python3 -c "import sys;sys.path.insert(0,'tools');import judge_primary,b0_gate;P='results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main';judge_primary.run_dir(P);print(b0_gate.b0_gate(P,'analysis/labels/or16-main-kappa.json'))"
python3 analysis/classify_main_errors_or16.py          # bảng lỗi §4
```
| File | Nội dung |
|---|---|
| `trials.jsonl`, `MAIN-MERGE.json` | 1200 dòng trial và nguồn của từng slot |
| `llm-graded.jsonl` | Phán quyết judge cuối cùng (theo các lớp + override) |
| `judge-primary.jsonl`, `judge-primary-summary.json` | Primary từng trial, bootstrap, phân tầng |
| `audit-v45.json` | Audit tất định + amendment (j) |
| `financial-review.json`, `review-evidence.jsonl` | Review mọi trial thắng của cả ba arm |
| `summary.json` | Metric phụ v45 |
| `analysis/labels/or16-main-labels.jsonl`, `or16-main-kappa.json`, `or16-manual-overrides.json`, `or16-review-hand-read.json` | Phần chấm của người chấm |
| `analysis/out/or16-main-errors.json` | Phân loại lỗi từng trial |
