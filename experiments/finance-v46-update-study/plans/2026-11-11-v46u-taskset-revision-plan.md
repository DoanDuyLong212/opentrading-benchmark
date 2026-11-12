# Kế hoạch sửa bộ task v46u (main 200 / holdout 50)

Ngày 2026-11-11. Chưa sửa task nào. Mọi bước thay đổi đề/gold/grader/contract đều cần amendment và user duyệt
(theo luồng đã chốt).

## 1. Hiện trạng (đã kiểm tra)
- main: 230 thư mục, gồm 183 task tài chính đủ điều kiện, 17 task quarantine (8 CPI mơ hồ, 9 narrative) và 30 task mem.
  Các task mem bị `task_eligibility` loại khỏi main (`separate_memory_multiturn_stratum`).
- holdout: 60 thư mục, gồm 44 task đủ điều kiện, 6 task quarantine và 10 task mem.
- Lặp template nặng (cùng tool, cùng bộ expects, chỉ đổi mã): bctc ×12, profile ×12, nonexist ×11, valuation ×9,
  growth ×8, screen ×8, future-fs ×8, margin ×7.
- Pilot (22 task, đủ các họ) cho thấy hiệu ứng trần: cả 3 arm đều 44/44. Bộ hiện tại hầu như không phân hoá.
- Chưa có dữ liệu main nào, nên việc cắt bớt chỉ có thể dựa vào cấu trúc (không nhìn kết quả).

### Task mem hiện tại có đo memory của harness không? KHÔNG.
- `memory_snapshot_server.py` cấp tool `benchmark_user_notebook_read` cho mọi arm.
  `memory_runner.py:138` chèn hướng dẫn dùng notebook vào prompt của mọi arm.
- Dữ kiện do controller ghi (`memory_operations` → `apply_operations`), không phải do harness tự nhớ.
- Arm main OT là `opentrading_baseline`, memory tắt. Còn `ot_memory_on` chỉ có trong driver mem riêng.
- Vì vậy các task này chỉ đo việc "model có đọc tool notebook do benchmark cấp hay không", và điều này giống nhau ở
  mọi harness. Chúng cũng không được tính vào main. Dev run (Nemotron) cho cả 3 arm ở mức tương đương (~0.39).

### Năng lực thật của từng harness (liên quan tới tính toán và memory)
- OT B0: tool MCP + `calculate` (sqrt, abs, min, max, sum, avg, ln, log10, exp, ^) + `compute`
  (pct_change, mean, sum, ratio, relative_strength, rank, share, annualize: đọc chuỗi theo ref nên không phải chép số).
  Không có stdev, product, correlation, drawdown hay IRR.
  Memory gốc: lệnh người dùng `/nho`, `/luandiem`, `/baihoc`, `/quyetdinh` ghi vào memory.db. Constraint được host
  tự chèn vào mọi lượt; luận điểm có phiên bản; có `memory_read`.
- OpenCode: chỉ có tool MCP. Benchmark đang chặn `execute/shell/write/...` (`run_opencode.py:45`), trong khi
  bản sản phẩm có bash. Không có kho memory xuyên phiên (ngoài AGENTS.md, vốn đã bị chặn ghi), chỉ có resume session.
- DSH: chỉ có tool MCP, do allowlist CORE loại các bundle `dsh-tool-bash*` và `dsh-tool-session-query`, dù bản
  sản phẩm có cả hai.
- Hệ quả: nhận định "chỉ OT tính chính xác" đúng trong cấu hình benchmark, vì shell của OC/DSH bị tắt. Phải công
  bố điều này (xem quyết định D1).

## 2. Cơ cấu đích
| Tầng | main | holdout |
|---|---:|---:|
| Core tài chính (giữ lại sau khi cắt) | 140 | 36 |
| Compute (mới, có bậc khó tăng dần) | 30 | 7 |
| Memory gốc (thiết kế lại) | 30 | 7 |
| **Tổng** | **200** | **50** |
Báo cáo: metric chính tính theo từng tầng. Tầng core là phép so sánh không thiên lệch. Tầng compute và memory được
thiết kế theo năng lực của OT, nên phải báo riêng, giả thuyết đăng ký trước, không gộp vào một con số "OT thắng".

## 3. Cắt bớt (không nhìn kết quả, quy tắc chốt trước khi có dữ liệu main)
- Chuyển 17 task quarantine của main và 6 của holdout sang `tasks-retired/`, kèm receipt. Mem cũ (30 + 10) cũng
  chuyển sang retired, thay bằng thiết kế ở mục 5.
- Quy tắc cap theo chữ ký template: mỗi chữ ký giữ tối đa N task. Chọn task giữ lại bằng luật cố định: đa dạng
  mã/kỳ/ngành trước, sau đó ưu tiên task nhiều expects hơn, hoà thì lấy id nhỏ. Không dùng kết quả pilot theo arm.
- Dự kiến main (183 → 140, cắt 43): bctc 12→7, profile 14→7, nonexist 11→5, valuation 10→6, growth 8→5,
  screen 8→5, future 14→6 (vẫn giữ đủ câu bẫy để đo FP), margin 7→5, quote-vn 6→5, quote-gf 5→3, quote-crypto 5→3.
  Các họ còn lại giữ nguyên.
- Holdout (44 → 36, cắt 8): cũng theo cap, ưu tiên cắt bctc, valuation, future, nonexist, profile.
- Sản phẩm: `audits/taskset-revision-2026-11-11/PRUNE.json` (lý do từng task) và cập nhật `CORPUS-MIGRATION.json`.

## 4. Tầng compute (30 main + 7 holdout)
Trục khó là số toán hạng và độ dài chuỗi bước, không phải siết tolerance (tolerance giữ như họ số hiện tại,
rel ≈ 0.5%).
| Bậc | main | Ví dụ | Kỳ vọng |
|---|---:|---|---|
| C1 dễ | 8 | % thay đổi giữa 2 phiên; P/E = giá / EPS (đổi nghìn đồng ↔ đồng); chênh lệch giá vàng SJC và thế giới | cả 3 làm được |
| C2 vừa | 8 | CAGR 3 năm (^(1/3)); trung bình 10 phiên; annualize LNST 3 quý; P/E bình quân gia quyền 5 mã; quy đổi oz → lượng → VND | OC/DSH bắt đầu sai |
| C3 khó | 8 | mean/sum 60–120 phiên theo ref; relative strength mã vs VNINDEX 60 phiên; share vốn hoá 15–20 mã; rank theo tỷ số tự tính trên 15 mã | chủ yếu OT đúng |
| C4 rất khó | 6 | chuỗi 3–4 bước nhiều đơn vị (giá trị danh mục 8 vị thế gồm VND/USD/USDT/oz); log-return = ln(cuối/đầu) qua nhiều bước; tổng hợp nhiều quý rồi annualize rồi so sánh | gần như chỉ OT |
Holdout: C1 2, C2 2, C3 2, C4 1.
- Chỉ dùng phép tính OT thực sự có. Không làm câu stdev/volatility/IRR/drawdown, vì OT cũng sẽ trượt. Không thêm op
  mới cho OT chỉ để phục vụ đề (nếu muốn thêm op thì đó là thay đổi sản phẩm riêng, cần duyệt riêng).
- Dữ liệu: snapshot hiện có chuỗi dài nhất 10 phiên (chuỗi 350 dòng duy nhất là CPI, đang quarantine). C3/C4 cần
  chuỗi 60–120 phiên, nên phải mở rộng snapshot (D2): ghi lại lịch sử có `data_time ≤ 2026-10-30` từ MCP
  opentrading, kiểm tra 10 phiên trùng khớp với snapshot cũ, ghi provenance ngày ghi. Nếu không mở rộng, C3/C4 chỉ
  làm được với ≤10 phiên × nhiều mã (khó vừa) và sẽ yếu đi.
- Mỗi task có `oracle.py` tính gold độc lập bằng Decimal từ payload, gold audit thủ công, grader và expects cùng
  khuôn hiện tại.
- Dry-run OT trên task mới chỉ để kiểm tra giải được (sửa đề nếu đề mơ hồ). Không lặp sửa đề cho tới khi OT thắng
  và arm khác thua: đó là chọn mẫu theo kết quả, bị cấm và phải ghi rõ trong amendment.

## 5. Tầng memory gốc (30 main + 7 holdout)
Nguyên tắc: bỏ notebook dùng chung. Mỗi harness chỉ dùng cơ chế gốc của mình. Kịch bản gồm nhiều phiên tách biệt
(người dùng quay lại vào ngày khác); chỉ chấm lượt cuối.
- OT: memory bật, dữ kiện vào kho qua đúng đường sản phẩm (`/nho ...`, `/luandiem ...` do người dùng gõ trong
  turns.json). Controller không ghi hộ.
- OC/DSH: cơ chế gốc là resume session trước đó (`--session`). Có cho DSH bật `session-query` hay không là D1.
- Đối chứng công bằng (để kết quả không chỉ là "người kia mất trí nhớ"):
| Bậc | main | Cấu trúc | Kỳ vọng |
|---|---:|---|---|
| M1 cùng phiên | 6 | dữ kiện ở đầu hội thoại, 8–10 lượt nhiễu, hỏi cuối | cả 3 (đối chứng) |
| M2 một phiên trước | 6 | phiên A nêu dữ kiện, phiên B hỏi; OC/DSH được resume A | cả 3 (đối chứng) |
| M3 nhiều phiên + cập nhật/thu hồi | 8 | ràng buộc ở S1, danh mục ở S2, sửa ở S3, hỏi ở S4 (resume chỉ nối được 1 phiên) | memory có cấu trúc thắng |
| M4 ràng buộc tự áp + tính toán | 6 | "/nho loại mã P/E>25", "/nho danh mục 3 mã, giá vốn…"; phiên sau hỏi lãi/lỗ hoặc lọc rổ mà không nhắc lại | OT (memory + calc) |
| M5 đối chứng âm | 4 | giá cũ lưu trong memory phải gọi lại tool; dữ kiện đã thu hồi phải bỏ; chỉ dẫn lạ trong dữ liệu tool không được ghi nhớ | phạt dùng memory sai |
Holdout: M1 1, M2 1, M3 2, M4 2, M5 1.
- Kiểm tra khả thi trước khi viết đề: chạy OT memory-on trên `tasks/memorydev` với `/nho` thật (bỏ
  `memory_operations`), xác nhận dữ kiện sống qua phiên mới; và kiểm tra resume của OC/DSH.
- Metric: judge-primary của lượt cuối + numeric gate; thêm stale-use, revocation-violation, injection-accepted
  (theo luật).
- Pipeline: driver mem phải chạy dưới cùng seal và supervisor với main (D3). Nếu chạy riêng thì đó là pipeline song
  song, bị cấm.

## 6. Thứ tự thực hiện (sau khi duyệt)
1. Viết amendment `2026-11-11-v46u-taskset-revision-amendment.md` (nội dung kế hoạch này, cộng quy tắc cap, giả
   thuyết từng tầng, cấm chọn mẫu theo kết quả). User duyệt.
2. Cắt bớt và retire (receipt, test đếm 140/36).
3. Mở rộng snapshot (nếu D2 = có), kiểm tra trùng khớp và provenance.
4. Viết 37 task compute: oracle, gold audit, leak check, dry-run OT để kiểm tra giải được.
5. Driver memory gốc: bỏ notebook, thêm lệnh `/nho` vào turns, resume cho OC/DSH, gộp vào supervisor/seal main,
   auditor và test. Sau đó viết 37 task mem và dry-run khả thi.
6. Pilot mới có niêm phong: pilot cũ + 8 compute + 6 mem riêng cho pilot (không lấy task main), cổng b0 → user
   duyệt.
7. Main: 200 × 3 arm × 2 run = 1200 trial. Holdout mở 1 lần sau main (gold holdout qua route trả phí,
   deny data collection).

## 7. Ngân sách ước tính
- Pilot mới khoảng 700 request (~$0.5). Main: core+compute khoảng 4.100 request, mem khoảng 1.500 request, tổng
  khoảng 5.600 request (~$4). Holdout khoảng 1.300 request (~$1).
- Tổng tiền: khoảng $2.07 đã tiêu + khoảng $5.5, tức khoảng $7.6, vẫn dưới trần $10 của key. Nhưng bộ đếm request
  (2426/8000) sẽ vượt, nên cần nâng cap lên khoảng 10.500 (D4).
- Judge: 1.200 + 300 lượt chấm, dùng quota free trải qua nhiều ngày UTC; holdout dùng route trả phí.

## 8. Quyết định cần user
- D1. Shell của OpenCode/DSH và session-query của DSH: giữ tắt (khi đó "chỉ OT tính chính xác" chỉ đúng trong cấu
  hình benchmark, phải công bố) hay bật theo bản sản phẩm (OC/DSH sẽ tính được bằng bash, khoảng cách compute có
  thể biến mất)?
- D2. Mở rộng snapshot bằng lịch sử ≤ 30/10/2026 cho C3/C4: có hay không?
- D3. Gộp tầng memory vào cùng seal/supervisor với main: đồng ý?
- D4. Nâng cap request OpenRouter lên khoảng 10.500 (ước tính khoảng $7.6/$10 tổng): đồng ý?
- D5. Cơ cấu 140 + 30 + 30 / 36 + 7 + 7 và quy tắc cap: đồng ý? Sau đó tôi viết amendment để duyệt.

## 9. Trả lời của user (2026-11-11)
- D1: GIỮ TẮT shell của OpenCode/DSH (công bố: lợi thế compute chỉ đúng trong cấu hình không shell). BẬT `dsh-tool-session-query` cho DSH ở tầng memory (user đồng ý).
- D2: đồng ý, độ dài do Claude chọn → 120 phiên giao dịch (khoảng 6 tháng) cho cổ phiếu, chỉ số, FX/vàng và crypto
  dùng trong C3/C4, `data_time` ≤ 2026-10-30.
- D3: memory chạy chung seal/supervisor với main.
- D4: nâng cap request lên 10.500.
- D5: đồng ý cơ cấu 140/30/30, 36/7/7 và quy tắc cap.
