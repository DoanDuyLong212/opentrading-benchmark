# Main launch notes or16 (2026-11-11). Ngoài seal; không sửa amendment trong lúc chạy

Quyết định của user: "A chọn b. Sau khi chạy xong main thì kiểm tra hạn mức, đủ holdout thì lập tức chạy. Nhớ kiểm tra các
metric hoạt động chính xác, cả metric chính và phụ đã chốt".

1. **Bằng chứng pilot (ngoại lệ B):** `results/financial-v46u-pilot-final-or15-20261111/deepseek-openrouter-pilot`.
   - Gồm các dòng or15, trong đó chỉ 21 slot trượt được thay bằng kết quả chạy lại or15r/or15r2.
   - Audit PASS (auditor đã sửa) với 0 bằng chứng bịa.
   - Review tay 205/205 trial đạt, trong đó đọc tay 56 trial bị gắn cờ.
   - Judge-primary đủ 216/216; κ của judge theo lô là 1,0 (n=211, `analysis/labels/or15-batch-kappa.json`).
   - Qua cổng b0. Có `PILOT-REPORT.md` và `pilot-review-approval.json`.
2. **Kiểm tra metric** (trên pilot gộp, đối chiếu với kết quả tự chấm):
   - Đã khớp: primary OT/OC/DSH 72/66/67; strict 72/66/67; raw-format 72/72/68; DNF 0/0/4; FP 0/4; FR 0/4/0;
     ổn định 2/2 36/33/33; request; p50/p90; tách theo tầng và bậc; bootstrap; ma trận judge × strict; κ.
   - Đã sửa:
     - `required_data_coverage` không nhận khoá payload kiểu tên tool của task pilot cũ (trước đó ra giống nhau ở mọi arm);
     - thêm `usage_cost_usd` theo `usage.cost` của OpenRouter, kèm số lần gọi không có chi phí;
     - token của judge theo lô được phân bổ đều theo `batch_size`.
3. **Lỗi khi khởi chạy:** driver chỉ cho các arm trong `ARMS` chạy main/holdout, nên chặn `opentrading_baseline` (arm B0 đã
   đăng ký trong `arms_main`).
   - Đã sửa để nhận thêm các arm trong `arms_main`/`arms_holdout`.
   - Seal or16 đầu tiên bị chặn trước trial đầu tiên (0 request), đã xoá và dựng lại.
4. **Hỗ trợ holdout:**
   - Seal và approval có cờ `holdout_authorized_by_user`.
   - Chỉ chạy sau khi cohort main đã xong và audit PASS.
   - Supervisor dừng ở `await_root_holdout_budget_check` cho tới khi có `holdout-go.json`, file này chỉ được ghi sau khi
     kiểm hạn mức key.
   - Driver thêm cờ `--confirm-holdout`. Judge cho holdout tự dùng route trả phí với data_collection=deny.
5. **Judge cho main:** `grade_run_llm.py --batch 5 --follow`, chạy song song với main ngay từ trial đầu tiên.

## Sự cố hạ tầng OT trong main or16 (phát hiện 11:2x UTC)
- **Nguyên nhân:** khi dọn đĩa (bước C, ~09:17 UTC), study cũ `experiments/finance-v46-study` bị chuyển sang
  `/var/tmp/benchmark-archive/`. Trong khi đó `experiments/opentrading-runtime/node_modules` là symlink trỏ vào
  `finance-v46-study/.../node_modules`.
- **Hậu quả:**
  - `native_schema.ts` không tìm được `zod`, nên runner OT lỗi `CalledProcessError` sau ~10 ms, trước mọi request tới
    model.
  - 132 slot OT r1 (từ 09:17:17 đến 11:20:18) bị ghi `runner_error`, 0 request, 0 token. OC và DSH không bị ảnh hưởng.
- **Khắc phục:**
  - Đã chép lại `node_modules` (205 MB) về đúng đường dẫn cũ, nên symlink và nội dung không đổi so với lúc seal.
  - Trial OT kế tiếp (fin-m1-screen-505) chạy ok.
  - Đã kiểm: không còn symlink hỏng hay đường dẫn code nào trỏ vào thư mục đã chuyển.
- **Xử lý slot (sau khi main dừng ở cổng review, không chạy song song):**
  - Chạy lại đúng các slot OT có `status=runner_error` với `requests=0`, dùng cùng code/config/seal, theo cách đã làm
    với or15r.
  - Gộp kết quả dưới dạng thay thế cho lỗi hạ tầng: chỉ thay những slot chưa từng gọi model; mọi slot có ≥1 request giữ
    nguyên.
  - Báo cáo nêu rõ 132 slot gốc và kết quả trước/sau khi thay.
- **Thực hiện** (user: "tạm dừng và bổ sung OT bị hỏng trước rồi thực hiện chạy tiếp"):
  - Pause mềm main or16 ở 526/1200; supervisor dừng ở trạng thái `paused`.
  - Seal `audits/seal/financial-v46u-seal-or16r-ds.json` (`analysis/make_seal_or16r.py`):
    - cùng freeze state với or16 (8146de99…);
    - split main, arm `opentrading_baseline`, runs=1, đúng 132 task bị hỏng.
  - Kết quả ghi vào `results/financial-v46u-or16r-ds-20261111/main-opentrading_baseline`; judge theo lô chạy kèm.
  - Khi bổ sung xong thì `v45_control continue`, rồi chạy lại supervisor or16 với `--resume`.

## Main xong (18:1x UTC) và dựng main gộp
- **Trạng thái:** or16 main chạy đủ 1200/1200 trial. Supervisor `blocked` vì audit thư mục gốc FAIL: 132 lỗi
  `provider_ledger` đến từ các slot hỏng hạ tầng, cộng 2 trial OT r2 auditor không khớp được tham số.
- **Main gộp** `results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main`
  (`analysis/build_main_final_or16.py`):
  - lấy or16, chỉ thay 132 slot OT r1 có runner_error và 0 request bằng kết quả or16r;
  - gộp các lớp judge: NIM → các phần chạy song song p0..p2 → confirm (i) → fix → sửa tay.
- **Audit:** chạy với amendment (j) (`analysis/audit_v45_amended.py`, doc
  `plans/2026-11-11-v46u-auditor-typed-value-amendment.md`, user chọn "Amendment auditor").
  - Kết quả PASS, 0 lỗi, 0 bằng chứng bịa được chấp nhận.
  - Chỉ nới binding cho 2 trial (174, 258 OT r2); giá trị gõ tay ở cả hai đều truy được về nguồn.
- **Review:** 1090 trial thắng, loại 1 (`fin-m2-port-511__dsh__r2`, ghi "3 mã đều lỗ" trong khi GAS +11,43%).
  - Đọc tay 6 trial bị gắn cờ, 45 mẫu phân tầng và 32 câu khẳng định chung.
- **Kiểm trước holdout:**
  - freeze state vẫn là 8146de99…, `validate_seal` ok;
  - route judge holdout `--route openrouter-deny` đã probe ok trên 1 trial main (provider deny, ~$0,0015/câu);
  - key còn $2,77, ước tính holdout ~$0,85 cho agent và ≤$1 cho judge.
- **User (18:3x UTC):** "Khoan chạy holdout, tôi sẽ yêu cầu chạy sau. Hiện tại cần main đã".
  - Chưa ghi `holdout-go.json`, chưa sửa `state.json` của supervisor.
- **Vẫn là infra DNF trong mẫu số:** `fin-m3-update-520` OT r2 (mạng mất 14:38 UTC). Có back-fill hay không do user quyết.

## 2026-11-12 — Chốt main (người chấm = Claude, được user ủy quyền)
- 53 dòng judge unparseable/timeout được chấm lại đơn lẻ qua NIM (`llm-graded-nim-retry00/01.jsonl`); 1200/1200 có phán quyết hợp lệ.
- Nhãn tay: `analysis/labels/or16-main-labels.jsonl`; κ = 0.850 (n = 71) trong `analysis/labels/or16-main-kappa.json`; 1 REMOVE (chg-402) đã áp, 4 override nâng điểm để ở `proposed_pending_user`.
- Primary (bảo thủ, chưa áp 4 override nâng điểm đang chờ duyệt): B0 383, DSH 361, OC 351 (/400); gate `b0_judge_primary` PASS. Nếu duyệt cả 4: 385/362/352. Báo cáo: `results/financial-v46u-main-final-or16-20261111/deepseek-openrouter-main/MAIN-REPORT.md`.
- Còn mở: back-fill `fin-m3-update-520` OC r2 (mất mạng), user duyệt các override, holdout (chờ lệnh).
- 2026-11-12 (sau): user "1 nâng điểm, 2 backfill đi" → 4 override áp; or16r3 (`audits/seal/financial-v46u-seal-or16r3-ds.json`) back-fill `fin-m3-update-520` OC r2 (ok; r1 dư = native runner error, không dùng). Win back-fill bị REMOVE (bịa tiêu chí ghi nhớ, đúng do trùng hợp). Chốt: B0 385, DSH 362, OC 352; gate PASS; báo cáo nộp = MAIN-REPORT.md (viết lại), lỗi theo `analysis/classify_main_errors_or16.py`.
