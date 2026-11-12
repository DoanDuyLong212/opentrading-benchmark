# MIGRATION — corpus wave-2 stage-1 (08/11/2026)

Người thực thi: OpenCode agent theo ủy quyền trực tiếp của user (phần này supersedes tư cách giám định "không sửa artifact" — chỉ áp dụng cho `tasks/main`).

## Nội dung
- **+10 task mới** (bảng dưới) — chỉ ghép envelope **đã ghi** từ snapshot 2026-11-01; không capture mới, không bịa dữ liệu.
- **−10 task cũ** → `audits/2026-11-07-corpus-wave2/removed/` (nguyên nhân: dead-weight cách ly / trùng template / WARN đã xác nhận khi review L1–L5).
- Kết quả: **main = 200** (L1 34 · L2 36 · L3 41 · L4 49 · L5 40) · confirmatory **183/200** (trước: 178/200) · vi phạm ANV ≤2/entity đã gỡ (4→2).

## Task thêm
| ID | Level·Family | Nguồn envelope | Gold |
|---|---|---|---|
| fin-l3-breadth-301 | L3·B (breadth) | agg-186 (batch:bds1) | 1 up (DXG) / 4 down |
| fin-l4-2src-302 | L4·D | ratio-160 + compare-279 | lệch P/E VGI = 6.19% (base=valuation_run, formula trong đề) |
| fin-l4-chain-303 | L4·F (mới) | tech-204 + compare-276 | FTS 35.22 → P/E 27.12 |
| fin-l4-chain-304 | L4·F | tech-207 + margin-151 | PVS 35.86 → margin 9.62% |
| fin-l4-chain-305 | L4·F | agg-181 + bctc-113 | TPB −1.94% → LNST 2,351.20 tỷ |
| fin-l4-chain-306 | L4·F | top-198 + growth-141 | PNJ → doanh thu 6,994.69 tỷ |
| fin-l4-future-307 | L4·E | quote-104 | refusal VIX 01/11 (CN) + bonus 12.0 |
| fin-l4-future-308 | L4·E | quote-106 | refusal MBS 02/09 (lễ) + bonus 15.0 |
| fin-l4-nonexist-309 | L4·B | khung nonexist-235 | refusal FPT2 (near-miss, resolver null) |
| fin-l4-nonexist-310 | L4·B | như trên | refusal VCBX |

Chi tiết đủ + hash: `MIGRATION.json`. Wave-2 stage-2 (17 task, cần capture mới): resolver-quote L1×6, resolver-twist L2×4, dossier L5×4, mcap/RSI-1W/top5-volume L4×3 — xem `MIGRATION.json.wave2_pending`.

## Checklist trước khi đóng băng main (bắt buộc)
1. Re-hash toàn bộ split (task-sha256 mới) + seal mới.
2. task-quality.json bản kế nhiệm (thêm 10 entry, bỏ 10, `source_review_status` riêng cho 2 envelope offline-constructed).
3. README/PRE-REGISTER: 200 (34/36/41/49/40), eligible 183; family mới `L4·F two-step chain` + breadth-variant.
4. `analyze.py`: báo cáo per-family để tách điểm nhóm chain/2src khi so arm.
5. Không đụng holdout (11 clone + 10 share-payload là việc riêng trước khi mở holdout).
