# Independent smoke review — v4.4 (OpenCode agent, 07/11/2026)

Reviewer: agent ngoài, không thuộc nhóm implementation/audit của codex. Phạm vi: gate review độc lập sau khi
cả hai smoke v4.4 chạy xong (bolt + deepseek, `startupfix1`), kiểm tra cả lý do supervisor block. Chỉ đọc +
chạy lại phép tính gate từ `trials.jsonl`/summary/audit logs; không inference, không sửa artifact.

## Kết luận

1. **Cả hai strata đều FAIL quality gate** — vì vậy ngay cả khi audit không block, **pilot v4.4 không được mở**
   theo đúng luật predeclared (B1 cần ≥4/6 strict; thực tế bolt 2/6, flash 2/6; điều kiện "mọi condition ≥1
   strict numeric win" vỡ ở B0/OC = 0 trên flash).
2. **Supervisor block ở `smoke-deepseek-audit` là lỗi khớp audit-tooling, không phải gian lận**: auditor
   (`audit-completed-run.py`) gặp class mới `policy_guard_rejected` (native finance-policy chặn replay
   `analytics_compute`) và báo *"Unrecognized policy guard rejection"* + `tool_call_reconciliation` fail trên
   `smoke-agg-01__opentrading_finance__r1/r2` → theo luật "infrastructure/audit failure stops", chain dừng an
   toàn. **Cách sửa đúng: cập nhật auditor nhận diện class guard này (vẫn đếm là local rejection, đối chiếu
   qua intent ledger) — KHÔNG hạ gate, KHÔNG bỏ audit.**
3. **Không có evidence fabrication** (claimed_evidence_mismatch = 0 mọi arm; smoke_financial_canary 1/1 check
   pass ở các trial được check) — dữ liệu dùng được cho phân tích.

## 1. Bảng gate — deepseek flash (24/24 trial, tự tính lại)

| Điều kiện predeclared | OT-fin | OT-B0 | OC | DSH | Verdict |
|---|---|---|---|---|---|
| Strict primary /6 | **2** | 0 | 0 | 1 | **FAIL** (B1 cần ≥4) |
| Mọi condition ≥1 strict numeric win | 1 (quote r1) | 0 | 0 | 1 (quote r2) | **FAIL** |
| False refusal ≤1/4 answerable | 0 | 0 | 0 | 0 | PASS (nhưng 12/24 trial là DNF/error — FR=0 vì không ai kịp trả lời) |
| Trap FP 0/2 | 0 | 0 | 0 | 0 | PASS |
| DNF 0/6 | 4 | 3 | 3 | 3 | **FAIL** |
| Smoke financial canary | checked 1, failed 0 | — | — | checked 1, failed 0 | PASS (trên trial có numeric win) |

→ **pilot-deepseek: SKIP. Cả 2 pilot của v4.4 đều không chạy trong vòng này.**

## 2. Bốn phát hiện khoa học từ trace (tự tay đọc ledger/run.log)

### 2.1 B2 uptake đạt được trên flash — nhưng 0/17 thành công vì path semantics

`compute_calls`: OT-fin 4 · B0 3 · **OC 6** · DSH 4 = **17 gọi compute (vs 0/24 trên bolt!)**, `compute_successes: 0`
mọi arm, nguyên nhân đồng nhất `mcp_error_invalid_derivation` (4/3/6/4). Case điển hình (agg OT-fin r1):
model gọi `mean` với `path:"/data/"` rồi `path:"/data"` → cả hai bị reject; đúng phải là **`/data/last`** (lá số).
Guidance hiện tại không nói tên lá cụ thể → **mọi arm đều chết ở cùng một chỗ**. Đây là seam thiết kế tool
(pointer phải trỏ leaf, error không gợi ý leaf) — sửa 1 dòng guidance sẽ mở B2 thật.

### 2.2 Strict public contract = sát thủ số 1 trên flash

`public_contract_invalid_trials`: OT-fin 4 · B0 6 · OC 6 · DSH 5 (21/24 trial!). Đối chiếu grader song song:
`frozen_v41_primary` = 2/3/3/3 và `frozen_v3_primary` = 2/3/3/3 — **tức dưới grader đóng băng cũ, mọi arm
"đúng" nhiều hơn gấp đôi**; chênh lệch nằm ở hợp đồng raw-JSON v4.4 (flash phát DSML fences/văn thừa:
`<｜DSML｜ calls>` rò trong assistant text). Bài học: **đo "năng lực tài chính" đang bị trộn với "kỷ luật
format model"** — cần tách hai chỉ số này khi báo cáo.

### 2.3 403 NVIDIA storm giết 12/24 trial flash

`native_status_error`: OT-fin 4 · B0 3 · OC 2 · DSH 3 = **12 error-class trial** (`stage_dnf` tương ứng), run.log
chết bằng `"API key không hợp lệ hoặc không có quyền (403)"` sau khi tool-call đã ok (case agg OT-fin: 5/5
bank call ok → compute reject ×2 → request kế tiếp 403). Đúng dạng nhiễu route §9. **Khoảng 1/3 mẫu flash
chết vì hạ tầng, không phải model** — mọi kết luận chất lượng trên flash phải điều chỉnh theo mẫu lệch này.

### 2.4 OT là arm duy nhất có acquisition machinery vận hành — và chính nó gây block

`phase_events`: OT-fin **21**, các arm khác 0 — per-intent state + guard hoạt động thật. Nhưng guard chặn
replay compute (lần thử 3 giống lần 2) tạo class rejection auditor chưa biết → chain block. Nghịch lý cần
ghi: **cơ chế riêng của OT vừa là lợi thế duy nhất (2/6 strict, quote+trap pass) vừa là nguyên nhân block
chuỗi** — vì auditor chưa theo kịp taxonomy của candidate.

## 3. Đối chiếu bolt vs flash (2 strata cùng fail gate)

| | Bolt (24) | Flash (24) |
|---|---|---|
| Strict primary (B1) | 2/6 (toàn trap) | 2/6 (quote r1 + trap r2 — **có numeric win**) |
| Compute calls | **0** | **17** (0 success) |
| public_contract_invalid | ít (trap r2 OC/DSH) | **21/24 trial** |
| Error/403-class | 2 (khong_tra_loi) | **12** |
| Premature refusal (không gọi tool) | nặng (OT-B1 agg 0 call) | **hết** (mọi arm gọi tool; retrieval agg 5/5 ok ở OT-fin) |

Đọc mối quan hệ: **prompt gọn + model mạnh giải được retrieval** (agg 5/5 bank ok lần đầu tiên trong lịch sử
study); **nhưng hai tầng mới lộ ra**: (a) tầng compute-path semantics, (b) tầng format-strict × model thỏa
thích sinh fences. Cùng 403 infra. Không tầng nào là "OT yếu hơn" — đó là 3 seam của thiết kế v4.4.

## 4. Khuyến nghị cho vòng kế tiếp (cho codex/root — theo thứ tự)

1. **Sửa auditor** nhận diện `policy_guard_rejected` (kèm reconciliation qua intent ledger) — điều kiện mở
   lại chain; giữ nguyên tiêu chí gate.
2. **Sửa guidance của `analytics_compute`**: error message nêu đúng leaf mẫu (`/data/last`) hoặc chấp nhận
   leaf-derivation khi path trỏ object có đúng 1 trường số — preregister trước khi đổi (đây là common tool).
3. **Xử lý 403**: retry-backoff ở driver level cho error-class 403 (hiện retry 0), hoặc phân tách stratum
   flash sang khung giờ/route ổn định; ghi rõ trial 403-class để tái tính trên mẫu sạch.
4. **Tách metric**: báo song song strict-primary vs semantic vs frozen-v41/v3 primary (đã có sẵn triple
   grading) — tránh đọc "OT kém" khi thực chất là "contract gắt hơn".
5. Nếu chạy lại smoke flash sau 1-4: kỳ vọng hợp lý là compute success > 0 và contract-invalid giảm; gate
   B1 ≥4/6 vẫn là điều kiện pilot — không nới.

## 5. Phạm vi không covered

- Không verify native TypeScript suite của vòng sau fix auditor (native owner sở hữu).
- Không tái đếm 17 compute-call bằng tay (dựa counts của auditor + đọc 2 case đại diện OT-fin agg r1/r2,
  DSH/B0/OC qua counts `mcp_error_invalid_derivation`).
- Không đánh giá pilot 176 (chưa chạy, đã bị chặn hợp lệ).

Nguồn: `results/financial-v44-smoke-{bolt,deepseek}-20261107-startupfix1/{trials.jsonl, summary.json}`;
`audits/financial-prompt-v44/supervisor-startupfix1/{state.json, smoke-{bolt,deepseek}-audit.log,
smoke-bolt-diagnostic.json}`; `plans/2026-11-07-v44-compute-acquisition-study.md`; trace per-trial
(attempts/*/mcp.jsonl + run.log) cho agg/trap OT-fin flash; §12-§13 của `opencode-review.md`.
