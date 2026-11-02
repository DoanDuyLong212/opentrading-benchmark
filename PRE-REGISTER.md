# PRE-REGISTER — Benchmark harness tài chính (DRAFT)

> Trạng thái: **DRAFT — chờ duyệt pilot**. Mọi thay đổi sau khi freeze phải ghi changelog
> và chỉ được sửa theo gate (G-T*/G-E*), không sửa âm thầm.

## 1. Câu hỏi nghiên cứu / giả thuyết
Harness tài chính chuyên biệt (OpenTrading) so với harness tổng quát (OpenCode) và DSH:
- H1: Success cao hơn ở L3–L5 (task sâu pipeline), chênh ≥ 7 điểm (d≈13%).
- H2: FP-rate thấp hơn trên task bẫy L4 (toàn vẹn dữ liệu).
- H3: Stable-correct (3/3 runs) cao hơn — độ tin cậy dùng-một-lần.

## 2. Đối tượng & điều kiện
- **Model duy nhất cả 3 arm**: DeepSeek V4.1 Flash qua opencode-go (Go plan $10/tháng).
- **Arms**: ① OpenTrading · ② OpenCode (vanilla) · ③ DSH.
- **Snapshot dữ liệu**: 2026-11-01 (mọi arm chạy trên MCP snapshot-replay cùng envelope).
- **Bảng giá freeze khi chạy** (Off-Peak — dự kiến): input $0.15 · output $0.60 · cached read $0.003
  (per 1M token). Peak (01–04 & 06–10 UTC): 0.30/1.20/0.006. Cache hit: bỏ (chưa chốt).
- **Key**: cần key `oc_sk_...` mới (key hiện tại api_key_expired, khảo sát 01/11/2026).

## 3. Bộ task & thiết kế chạy
- Pilot: **24 task tính điểm** (L1×5 · L2×6 · L3×6 · L4×4 · L5×3) + 3 smoke (không tính điểm).
- Main (sau pilot, đạt gate): **200 task** chia 40/mức; Phase 4 dự bị 400 (chỉ mở sau G4a–c).
- Runs: **3 runs độc lập/task/arm** (session sạch) — đủ cho Stable-correct.
- A/A test: 20 cặp (OpenTrading chạy 2 lần) trước khi tin mọi so sánh.
- L4 là mức bẫy — mọi run L4 đều được spot-check người 10% (ambiguous).
- Task tuyệt đối không sửa sau freeze trừ lỗi qua gate; ngân sách: 1.800 trial + A/A ≈ 6.000+
  call model (theo dõi hạn mức Go: $100/tháng).

## 4. Tiêu chí đo (chi tiết: benchmark-plan.md Phần 1)
① Success (value+unit+period khớp gold) · ② Stable-correct (3/3) · ③ FP-rate (bịa số trên trap) ·
④ Time p50/p90 · ⑤ Cost/task (1 bảng giá). **Không cộng điểm tổng**; N/A ≠ 0.

## 5. Phân tích
- Success theo từng mức L; khoảng tin cậy bootstrap (task-level clustering, 3 runs/task).
- So sánh cặp: **McNemar test + hiệu chỉnh Holm** (main 200). Pilot: mô tả + CI, không kết luận
  suy diễn mạnh (n nhỏ).
- Ngưỡng khẳng định gap (main): ≥7 điểm phần trăm (d≈13%).
- FP: tỷ lệ theo trap + tỷ lệ "ambiguous" phải dưới 10% tổng trial trap.

## 6. Gates
- G-E1..E8 (môi trường — xem Phần 2): snapshot server, allowlist tắt web/sentiment, pipeline A1d...
- G-T1..T3 (task — Phần 3): kiểm định 2 lớp A (3 check Terminal-Bench) + C (duyệt 2 lượt độc lập:
  chính tôi + agent khác — any-flag → sửa/loại; checklist 5 mục gồm memory-check + ambiguity-check).
- Pilot phải qua G-T trước khi freeze main.

## 7. Changelog
- 2026-11-01: khởi tạo. Pilot 24 sinh từ payload MCP thật; 5 task đổi nguồn/đề so với 5.5 vì
  dữ liệu thật (ghi trong PHẦN 6 benchmark-plan.md).
- 2026-11-02: **Sinh bộ chính 200 + holdout 50** (tools/build_main.py). Kiểm định tự động 6 nhóm:
  0 lỗi (250/250 oracle, self-test đúng/đột biến/rỗng, leak-scan, CTRF, null-probe 20/20).
  Thay đổi so với thiết kế do dữ liệu thực tế: crypto chuyển sang yf + vn_crypto_ohlcv (binance 429);
  bỏ movers 'hose' (partial); 2-nguồn dùng vn_equity_quote_batch thay vs_overview_trading;
  loại LTG/VIS/SBT khỏi họ BCTC (stale); POM → task định giá "dữ liệu một phần"; HDB làm bẫy future
  (trễ kỳ Q2/2026). Chi tiết: PHẦN 7 benchmark-plan.md.
- 2026-11-02: **Quy chế holdout** (Phần 7.4): 50 thẻ holdout niêm phong; không chạy trước freeze;
  mở đúng 1 lần sau freeze; kết quả chỉ dùng xác nhận, không tinh chỉnh ngược.
- 2026-11-02: Runner contract bổ sung: `environment/payloads.json` và `solution/` KHÔNG vào workspace
  agent (chống bypass MCP tool-use và đọc gold); snapshot-replay phục vụ đúng envelope đã ghi.
- 2026-11-02: **Vá 3 leak đáp án hệ thống (review độc lập)** — ① schema refusal hiển thị
  `"value": null` bộc lộ task bẫy qua format đề (32 task) → đồng bộ với value-schema
  (`"value": 0`); ② schema block chứa đúng token kỳ gold ở 113+ task → thay placeholder
  trung tính ("(kỳ được hỏi)"...) — kỳ chỉ được nêu ở thân câu hỏi khi là premise; ③ narrative
  một chiều (toàn bộ claim sai + rule lộ hướng "ít nhất 1 phiên giảm", 11 task) → sinh 2 chiều
  claim đúng/sai theo parity id (main 5+5, holdout 1+1), rule trung tính. Kèm: grader
  `verdict_hit` đổi sang longest-match-wins (đóng lỗ "không đúng vì..."), mở rộng leak-scan
  thành `tools/check_leaks.py` (6 lớp, 277 task → 0 leak), sửa NameError tiềm ẩn
  `rep[mutate_fail]` trong build_main, pilot-gen không còn ghi đè registry v2/PRE-REGISTER.
  Kiểm định sau vá: 277/277 oracle PASS, 277×3 self-test 0 fail, 0 leak, bất biến
  200/50/24/3 task + ID/level/entity. **FP-rate (H2) phải đo lại trên bộ đã vá.**
