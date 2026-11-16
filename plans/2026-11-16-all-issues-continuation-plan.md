# Kế hoạch tiếp nhận fix toàn bộ issues (bản chờ duyệt)

**Ngày:** 2026-11-16 · **Người soạn:** opencode (tiếp nhận từ session codex)
**Kế hoạch gốc:** `plans/2026-11-16-all-issues-remediation-plan.md` (trong checkout
`/home/doanlong/extra/benchmark`, hiện **chưa được commit**)
**Trạng thái:** chờ user duyệt, chưa thực hiện thay đổi nào.

## 1. Hiện trạng codex để lại

| Hạng mục | Trạng thái | Bằng chứng |
|---|---|---|
| PR-01 dev gate (#14) | PR #24 mở, chờ FinDaHuman, chưa merge | 47 gate + 15 driver test; 215 test stack |
| PR-02 grader S (#9) | PR #25 mở, chờ FinDaHuman, chưa merge | 145 test; 38 task/receipt sinh lại |
| PR-03 series + clock (#12, #11) | PR #26 mở, chờ FinDaHuman, chưa merge | 36 test; 314/314 oracle |
| PR-04 phương pháp (#10, #13, #15) | **Dở**: code + test nằm trong worktree gitignored, chưa commit/push/PR | 54 test mới + 233 test stack pass |
| PR-05…PR-10 (#1, #2, #16–#22) | **Chưa làm**, chỉ có 2 báo cáo discovery | `reports/budget-discovery.md`, `reports/repro-discovery.md` |

Ba PR #24–#26 là chuỗi stacked (`main` → dev-gate → safety → series), không có CI
check, chưa có review nào. Session codex dừng lúc 23:35 vì hết quota.

## 2. Rủi ro phải xử lý trước khi làm tiếp

1. **PR-04 chỉ tồn tại trong `.remediation-workspaces/pr04`** — thư mục bị
   `.gitignore` (`*`), chưa commit. Mất máy/mất thư mục là mất toàn bộ.
2. **Kế hoạch gốc + evidence JSON chưa track** trong checkout chính.
3. PR-26 đang ghi `Closes #11`, nhưng #11 chỉ được xử lý bằng policy "S3
   diagnostic", chưa chứng minh clock parity. Cần chốt cách đóng issue.
4. `metrics.build_summary` lọc S **chỉ theo task ID** (`^fin-s\d-`). Một bản
   devsmoke S trong tương lai (`dev-fin-s1-…`) sẽ bị tính vào primary.
5. Chưa có CI trên PR, nên mọi tuyên bố test chỉ dựa trên log local.

## 3. Thứ tự thực hiện đề xuất

### Stage 0 — Bảo toàn việc đang dở (0,5 giờ)

- Commit PR-04 trong `pr04` (8 file sửa + 3 file mới), push `fix/v47-methodology`,
  mở PR vào `fix/v47-series-clock`, tag FinDaHuman.
- Copy kế hoạch gốc + `all-issues-review-evidence.json` vào nhánh này và commit
  riêng (không trộn vào PR-04).
- Không đụng `tasks-main-holdout.html` và `plans/2026-11-16-ot-v47-improvement-plan.md`
  trong checkout chính.

**Kiểm:** `git status` sạch trong worktree; branch có trên origin; PR mở được.

### Stage 1 — Hoàn tất PR-04 (0,5–1 ngày)

- Sửa điểm 4: eligibility lấy cả metadata stratum/tier của record, không chỉ ID;
  thêm test với alias `dev-fin-s1-*`.
- Thêm test cho `metrics.paired_statistics` loại S (hiện chỉ test judge/bootstrap).
- Chạy lại: 54 test mới + 233 test stack; `prune_saturated --dry-run` không đổi
  byte nào; gold/payload không đổi.
- Nhờ verifier độc lập kiểm 2 finding của phase 2 (cohort complete vs
  analysis_complete; nhãn cost của or16 evidence).

**Kiểm:** PR-04 xanh, reviewer sign-off, không sửa gold.

**Gate:** chỉ merge PR-04 sau khi FinDaHuman ghi quyết định #10/#13/#15 (hoặc
chấp nhận merge default thận trọng).

### Stage 2 — PR-05 ngân sách (1,5–3 ngày, tách 2 PR)

- **05a:** resolve config một lần; `--budget-usd` (Decimal, cấm thiếu/âm/NaN);
  caps thực ghi vào manifest; gateway từ chối trước khi gọi provider.
- **05b:** journal bền vững (reserve → fsync → dispatch → settle), khoá flock,
  idempotent resume, cost thiếu = unknown và chặn request kế; test crash ở 6 điểm.
- Không gọi model trả phí. Đây là checkpoint 16A.

**Kiểm:** zero budget → 0 request; boundary/exhaustion; retry bị tính; resume
không tạo trial/request trùng; 2 process không vượt reservation.

### Stage 3 — PR-06 + PR-07 tái lập & CI (2–4 ngày)

- **06:** fixture synthetic vào `tools/tests/fixtures/`; Bun locator theo
  `BENCH_BUN_BIN` nhưng hash phải khớp receipt trusted; tách calculator khỏi
  đường v4.7; version-scope test cũ; giữ provenance/anti-leak/resume test.
- **07:** CI offline (pytest active suite, oracle tái tạo gold, grader mutation,
  schema/hash, composition, split gate, mock budget); README v4.7; pin OT/Bun/
  OpenCode/DSH; xử lý final sandbox image (registry digest hoặc build receipt);
  sửa mô tả "math-only/no-shell" còn sót.
- Fixture/Bun/CI độc lập với quyết định phương pháp → có thể chạy song song PR-05.

**Kiểm:** clone mới + HOME sạch chạy offline xanh; sai Bun hash bị chặn; CI xanh
trên PR.

### Stage 4 — PR-08 lịch chạy & kiểm rẻ (1–2 ngày)

- `runs_by_stratum` (L 1, C/M/S 2), schedule materialize trước khi chạy, resume
  theo schedule đã seal; thống kê task-weighted + bootstrap theo task/tầng.
- `tools/check_change.py` với `--dry-run` in task list/caps/USD, không khởi động
  provider.
- Không chạy paid; chỉ test offline.

**Kiểm:** cùng seed → cùng lịch; đổi config/seed → resume fail; thống kê trên dữ
liệu tổng hợp biết trước kết quả.

### Stage 5 — PR-09 seal/canary và PR-10 main/holdout (gated)

- PR-09: gate v4.7 phân phiên bản, holdout receipt có nội dung/hash, seal
  schedule; canary 2 host ≤10 trial **chỉ sau khi có duyệt trả phí riêng**.
- PR-10: allocation main/holdout/reserve; mở holdout đúng 1 cohort sau khi main
  được duyệt; report provenance/cost/CI.
- Không tự suy authorization từ việc duyệt plan code.

### Stage 6 — Đóng tracker #23

- Đối chiếu 17 issue với PR/quyết định/receipt; chỉ đóng khi đúng điều kiện.

## 4. Ước lượng còn lại

PR-04: 0,5–1 · PR-05: 1,5–3 · PR-06+07: 2–4 · PR-08: 1–2 · PR-09: 1–2 ·
PR-10: 0,5–1,5 → **6,5–13,5 ngày công**, chưa tính thời gian FinDaHuman duyệt và
thời gian inference.

## 5. Cần user/FinDaHuman chốt

1. Duyệt thứ tự Stage 0 → 4 (Stage 5 chờ duyệt riêng).
2. Cách đóng #11: `Closes` (theo policy S3) hay đổi PR-26 thành `Refs #11` và
   đóng trong PR-04 khi policy toàn S được ghi? **Đề xuất: `Refs #11`.**
3. PR-04 merge ngay hay chờ quyết định #10/#13/#15? **Đề xuất: chờ quyết định.**
4. Cách thực thi: native (tôi làm tuần tự trong session này) hay subagent-driven
   (mỗi PR một subagent + reviewer). **Đề xuất: native cho Stage 0–1, subagent
   cho PR-05/06 chạy song song.**
5. Nơi làm việc: tiếp tục worktree `benchmark/fix-issues` này sau khi push nhánh
   `fix/v47-methodology` (đề xuất), hay giữ nguyên `extra/benchmark`.
