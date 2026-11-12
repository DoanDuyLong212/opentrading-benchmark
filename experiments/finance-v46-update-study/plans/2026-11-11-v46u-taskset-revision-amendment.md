# Amendment 2026-11-11 (d): sửa bộ task (main 200 / holdout 50), tầng compute, tầng memory gốc

Status: APPROVED by user 2026-11-11. Các câu trả lời: "2 ok bao nhiêu tuỳ ý bạn, 3 chung, 4 ok, 5 ok";
"Giữ tắt. Riêng tool tìm lại phiên cũ của DSH (session-query) … bật cho tầng memory --> đồng ý".
Amendment được đăng ký trước mọi lần chạy main. Kế hoạch chi tiết: `2026-11-11-v46u-taskset-revision-plan.md`.

## Cơ cấu
- main 200 = core 140 + compute 30 + memory 30
- holdout 50 = core 36 + compute 7 + memory 7

Primary vẫn là judge-primary (amendment b), báo **theo từng tầng** và gộp. Tầng core là phép so sánh không thiên vị.
Tầng compute và memory được thiết kế theo năng lực OT, giả thuyết có hướng được đăng ký trước:
- compute: khoảng cách OT − arm khác tăng dần từ C1 tới C4.
- memory: M1/M2 ngang nhau (đối chứng); OT hơn ở M3/M4; M5 đo việc dùng memory sai cách.

## Cắt bớt (không nhìn kết quả)
- Task quarantine (main 17, holdout 6) và mem cũ (30 + 10) chuyển sang `tasks-retired/`, kèm receipt.
- Cap theo chữ ký template (họ, tools_expected, bộ path của expects). Chọn task giữ lại bằng luật cố định:
  1. đa dạng mã/thực thể trước;
  2. sau đó nhiều expects hơn;
  3. hoà thì lấy id nhỏ.
- Không dùng kết quả của bất kỳ arm nào. Quota theo họ được ghi trong `audits/taskset-revision-2026-11-11/PRUNE.json`.

## Compute (C1–C4)
- Chỉ dùng phép tính OT thật sự có: compute pct_change/mean/sum/ratio/relative_strength/rank/share/annualize và
  calculate sqrt/abs/min/max/sum/avg/ln/log10/exp/^.
- Không ra đề stdev/IRR/drawdown. Không thêm op mới cho OT.
- Độ khó tăng theo số toán hạng và độ dài chuỗi bước. Tolerance giữ như họ số hiện tại.
- Gold tính bằng `oracle.py` độc lập (Decimal) từ payload.
- Dry-run OT chỉ để kiểm tra đề giải được. Cấm lặp sửa đề dựa trên kết quả các arm.
- Snapshot extension (D2):
  - Lịch sử 120 phiên, `data_time` ≤ 2026-10-30, ghi từ MCP opentrading.
  - Các phiên trùng với snapshot cũ phải khớp; provenance ghi rõ ngày ghi.

## Memory gốc (M1–M5)
- Bỏ `benchmark_user_notebook_read`, không còn notebook dùng chung, controller không ghi hộ.
- OT: memory bật, dữ kiện vào kho qua lệnh người dùng `/nho`, `/luandiem` trong turns.
- OpenCode: resume session.
- DSH: resume session và bật `dsh-tool-session-query` (D1). Chỉ áp dụng ở tầng memory.
- Mỗi phiên là một process mới. Chỉ chấm lượt cuối. Metric thêm (theo luật, không qua judge): stale-use (M5-stale),
  revocation-violation (M5-revoke). Không dựng task injection, nên không có metric injection-accepted (đã bỏ, xem
  addendum e.8).

## Cấu hình harness (D1)
- Shell/bash của OpenCode và DSH giữ TẮT ở mọi tầng.
- Công bố: lợi thế compute của OT chỉ đúng trong cấu hình benchmark không có shell, không phải so với bản sản phẩm
  đầy đủ.

## Pipeline và ngân sách
- Driver memory chạy dưới cùng seal và supervisor với main (D3); không có pipeline song song.
- Pilot mới có niêm phong (pilot cũ + compute và mem riêng cho pilot) → cổng b0 → user duyệt → main 1200 trial →
  holdout 1 lần.
- Cap request OpenRouter 8000 → 10.500 (D4). Ước tính tổng chi tiêu khoảng $7.6 trên $10.

## Addendum (e) — triển khai 2026-11-11 (APPROVED by user 2026-11-11: "2 duyệt")
1. Snapshot extension:
   - MCP opentrading hiện lỗi lấy lịch sử: server gọi API `Market()` của vnstock gen-6, trong khi máy cài vnstock 4.0.4.
   - Vì vậy lịch sử được ghi trực tiếp bằng thư viện của cùng nhà cung cấp (vnstock `Quote`, nguồn VCI), đóng gói đúng
     khuôn envelope `vn_quote_history`/`vn_index_ohlcv`, provenance `as_of` = thời điểm ghi.
   - Phạm vi: 25 mã + VNINDEX + VN30, mỗi chuỗi 120 phiên (13/05–30/10/2026).
   - Đối chiếu với snapshot cũ khớp tuyệt đối: VJC 10/10, VNINDEX 10/10, 3 giá `last`.
   - Receipt: `audits/snapshot-extension-2026-11-11/RECEIPT.json`.
2. Tolerance của tầng compute, như nhau ở mọi bậc:
   - % tính abs 0,05 điểm %; tỷ số ("lần") abs 0,005; mức giá/tiền/khối lượng rel 0,1%; lợi suất quy năm abs 0,1.
   - Mọi đề yêu cầu làm tròn 2 chữ số thập phân.
3. Bỏ chấm `period` ở hai tầng mới (đề đã cố định ngày):
   - Lý do: trong dry-run cơ chế, câu trả lời đúng số bị grader strict đánh trượt chỉ vì trường `period` ghi thêm cửa sổ
     ngày (mẫu A8).
   - Sửa đối xứng cho mọi arm. Tầng core giữ nguyên grader.
4. Task memory dùng biến thể grader có `memory_evidence` (quy ước của mọi task nhiều lượt).
   - Tool gốc được khai báo cho gateway:
     - OT B0: `memory_read`.
     - DSH: 5 tool session-search, schema ghi từ wire, xem `tools/runners/dsh_session_search_tools.json`.
   - Chỉ bật ở tầng memory.
   - OpenCode không có tool memory nào.
5. Dry-run cơ chế (không phải cohort, không chấm, không dùng để chọn/sửa đề theo arm):
   - 10 trial, khoảng 60 request.
   - Đã sửa: allowlist `memory_read` cho v2, allowlist tool session của DSH, phát hiện task memory khi task thiếu
     `task.toml`.
   - Quan sát:
     - OpenCode/DSH tự cộng đúng 120 giá (MA120), nên tầng compute có thể phân hoá ít hơn kỳ vọng.
     - DSH dùng session-search thật để tìm lại phiên cũ.
     - OpenCode trượt task M3a (đúng thiết kế: dữ kiện ở phiên khác).
   - Đề không được chỉnh theo các quan sát này.
6. Pilot mới gồm 36 task đủ điều kiện = 22 core + 8 compute (801–808) + 6 memory (851–856). Task pilot không trùng
   main/holdout.
7. `judge_primary.py` báo thêm `by_stratum` (core/compute/memory và từng bậc), mẫu số đầy đủ.
8. Đối chiếu metric đăng ký với code (sau khi rà lại):
   - stale-use (`values.last` lệch ≤0,5% so với giá cũ user lưu) và revocation-violation (`values.pass` bằng kết quả khi
     vẫn áp tiêu chí đã xoá) được hiện thực trong `judge_primary.py`.
   - injection-accepted bị bỏ vì không có task injection.
   - M5-revoke chạy ở phiên mới S3, nên với OpenCode/DSH là bài kiểm tra recall chứ không phải "đối chứng âm". Báo cáo
     M5-revoke tách khỏi M5-stale; chỉ M5-stale là đối chứng âm cho mọi arm.
9. Auditor (`audit_v45_run.py` / `v45_call_binding.py`), kiểm trên một run thăm dò 6 trial có manifest, trong scratch:
   - Đối soát `memory_read` (OT) và `session_*` (DSH) như `native_memory_read`, không bao giờ là bằng chứng tài chính.
     Chỉ áp dụng cho task native-memory-v2 và chỉ cho arm sở hữu tool.
   - Chữ ký tham số so sánh số theo giá trị (241.0 ≡ 241).
   - Sau khi sửa, lỗi duy nhất còn lại là `completed_resume`: proof này do bước chạy lại khi đã hoàn tất của supervisor
     ghi ra, run thăm dò không có bước đó.
   - `numeric_gate` kiểm offline trên 88 task mới: nhận mọi đáp án đúng, loại mọi đáp án lệch.
10. Công bố:
   - Dry-run đã chạm 4 task main: fin-m3-split-515, fin-m3-update-517, fin-c3-ma-417, fin-c4-port-425 (kết quả đã nhìn
     thấy, giống công bố "104/132" trước đây). Run thăm dò dùng task pilot 853 và 805.
   - OT B0 chạy memory bật chỉ ở tầng memory; tầng core và compute giữ memory tắt.
   - Các seal cũ (or11/or13r/or14r) không còn khớp fingerprint công cụ hiện tại. Không sao, vì chúng đã hoàn tất và không
     bao giờ được resume.

## Addendum (f) — quy tắc cấu trúc cho C3/C4 khó (user 2026-11-11: "1-b … phép tính phức tạp hơn nhiều"), chốt TRƯỚC mọi dữ liệu
Lý do: dry-run cho thấy DeepSeek v4.1 Flash cộng nhẩm đúng 120 số. Mục tiêu là đánh vào điểm mạnh của OT (`compute` đọc
chuỗi dài theo ref, cộng `calculate` với `^`, `ln`, `exp`) và điểm yếu tính nhẩm của LLM (luỹ thừa phân số, logarit,
nhiều tổng chuỗi dài, chuỗi nhiều bước có tiền tỷ đồng).
- **C3:** ≥3 thực thể, mỗi thực thể dùng chuỗi ≥60 phiên đọc theo ref, VÀ có ít nhất một phép phi tuyến (luỹ thừa phân
  số hoặc ln/exp) hoặc ≥10 tổng chuỗi dài khối lượng 8 chữ số; 3–4 bước nối nhau.
- **C4:** ≥6 thực thể, hoặc vị thế mua rải / tái cân bằng / mua định kỳ; ≥4 bước; mỗi thực thể có ít nhất một phép phi
  tuyến hoặc cửa sổ riêng; tiền tính bằng đồng (9–11 chữ số).
- Chỉ dùng phép mà OT có sẵn. Tolerance giữ nguyên, áp dụng chung: % abs 0,05; % quy năm abs 0,1; tỷ số abs 0,005;
  mức/tiền/khối lượng rel 0,1%.
- Mẫu đề (`tools/compute_hard_templates_20261111.py`): `geo_ann`, `log_ann_vs_bench`, `ma_ladder`, `vol_regime`,
  `vol_share`, `doubling`, `rs_chain` (C3); `staggered`, `rebalanced`, `log_ann_vs_bench` 10 mã, `dca`,
  `signal_portfolio` (C4).
- Thay thế: main 417–430 (C3 ×8, C4 ×6), holdout 955–957 (C3 ×2, C4 ×1), pilot 805–808 (C3 ×2, C4 ×2). C1/C2 giữ nguyên.
  Các task C3/C4 cũ đã bị xoá, kể cả fin-c3-ma-417 và fin-c4-port-425 từng nằm trong dry-run; đề mới chưa từng chạy.
- Kiểm tra:
  - gold được kiểm chéo bằng một cách tính độc lập (float thuần trên history-120), 0 lệch;
  - oracle khớp 45/45;
  - grader và `numeric_gate` nhận đáp án đúng, loại mọi giá trị lệch 1%;
  - 738 test pass.
- Cam kết: các task này không dry-run theo arm và không chỉnh theo kết quả. Pilot là lần chạy đầu tiên.

## Addendum (g) — sau pilot or15 (user 2026-11-11: "Sửa OT sửa cả 1,2,3 … chỉ chạy lại những câu sai để xác nhận. sửa đề như trên và chạy lại")
Kết quả or15: 216/216 trial. Tự chấm thủ công toàn bộ 21 trial trượt strict, xem `analysis/or15-manual-judge-20261111.md`.
1. **Auditor** (lỗi đo đạc, 0 bằng chứng bịa):
   - Đối soát việc OT từ chối phía client lệnh MCP sai schema (`native_client_schema_rejection`). Lệnh không bao giờ được
     thực thi; đường chạy native-memory không ghi local rejection.
   - Mỗi lần LoopGuard chặn được khớp với đúng call id của chính nó, thay vì luôn lấy ngữ cảnh khớp đầu tiên.
2. **Sửa OT** (sản phẩm):
   - (1) `calculate`: nếu biểu thức đã nhân/chia cùng luỹ thừa 10 mà đơn vị đầu ra cũng quy đổi (vd `cap/1e9` + "tỷ đồng",
     `(a/b-1)*100` + "%"), chỉ áp một lần; gắn `scale_fixed`, cảnh báo, và nhãn `lineage: unverified` (không mang source
     proof).
   - (2) Lỗi thiếu biến chỉ rõ cách truyền `values` (ví dụ dùng đúng tên biến bị thiếu). Stop-gate có thêm một lần cứu
     "chỉ trả lời" (tắt tool) khi hai lần cứu trước vẫn rỗng mà lượt đã có dữ liệu.
   - (3) `compute` nhận `batch` (tối đa 20 phép, mỗi kết quả có ref riêng). Một phần tử lỗi không làm hỏng các phần tử
     còn lại.
   - Test: `test/or15-fixes.test.ts`; test agent cập nhật theo lần cứu thứ ba. OT suite 1902 pass; 2 test giao diện/tốc độ
     chỉ chập chờn khi chạy song song.
3. **Sửa đề** (cho rõ nghĩa, đối xứng mọi arm, không đổi gold):
   - `ma_ladder`: "lớn nhất theo giá trị có dấu".
   - `signal_portfolio`: "chênh lệch lợi suất 20 phiên (chưa quy năm)".
   - Mọi mẫu C3/C4 ghi rõ ngày bắt đầu, ngày tái cân bằng, ngày mua (không còn đếm phiên).
   - Áp cho main 419/426/428/429 và các mẫu khác, holdout 957, pilot 805–808.
4. **Xác nhận:** chỉ chạy lại các slot trượt (semantic) của or15, theo yêu cầu user, bằng code hiện tại (or15r). Đây là
   chạy lại có chọn lọc: điểm chỉ có thể tăng, và có trộn phiên bản code. Kết quả phải báo kèm or15 nguyên gốc. Main vẫn
   cần cổng pilot và approval của user.
5. Bổ sung sau or15r (cùng chỉ đạo của user):
   - Phần tử `compute` batch luôn mang nhãn `unverified` (ID con không có bản ghi riêng trong ledger).
   - `calculate` nhận tên ref (r38) làm biến, tự lấy kết quả compute/calculate trước đó (DeepSeek hay bỏ quên `values`).
   - Auditor xếp thứ tự LoopGuard tính cả các lệnh giống nhau gửi song song trong cùng một message.
   - Metrics chấp nhận `result` dạng chuỗi.
   - OT suite 1904 pass (2 test giao diện/tốc độ chỉ chập chờn khi chạy song song); study 738 pass.
   - Xác nhận: or15r (OC/DSH) và or15r2 (OT), audit PASS, 0 bịa. Xem `analysis/or15-manual-judge-20261111.md`.

## Addendum (h) — kiểm tra cuối main/holdout và judge theo lô (user 2026-11-11)
1. Kiểm tra cuối (`analysis/final_check_main_holdout.py`) trên 250 task, gồm:
   - oracle tái tạo được gold;
   - đáp án gold dựng lại đạt grader và numeric gate, đáp án lệch 5% bị loại;
   - JSON mẫu trong đề parse được; có bullet A8;
   - payload được server phục vụ, hash provenance khớp;
   - turns memory hợp lệ; không lộ gold; không trùng câu hỏi giữa main và holdout.
   Phát hiện và đã sửa (gold giữ nguyên):
   - main `fin-l4-2src-259/260/302` ghi sẵn cả hai số đầu vào trong đề → bỏ số;
   - holdout `fin-m4-port-976` trùng câu chữ câu hỏi cuối với main 524–526 → đổi câu chữ.
   Sau khi sửa: 0 vấn đề. Main 524–526 dùng chung câu hỏi cuối nhưng danh mục trong memory khác nhau (đã công bố).
2. Judge theo lô (`llm_judge.judge_batch`, `grade_run_llm.py --batch N [--follow]`):
   - Prompt giữ nguyên quy tắc chấm, nhận nhiều mục chấm độc lập, trả `{"results":[...]}`.
   - Bỏ `evidence`/`memory_evidence` khỏi câu trả lời, vì judge vốn bỏ qua phần này.
   - Cache theo từng mục; mục thiếu trong phản hồi được chấm lại riêng bằng prompt chấm đơn.
   - `--follow` chấm cohort đang chạy khi đủ lô, phần dư được chấm khi lịch đã xong.
   - Holdout vẫn chỉ dùng route trả phí với data_collection=deny.
   - Hiệu chỉnh trước khi dùng cho main: chấm lại 216 trial or15 theo lô, so với nhãn tự chấm thủ công (κ).
