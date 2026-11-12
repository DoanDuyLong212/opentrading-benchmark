# Preregistration: finance policy re-tune cho Super (2 rule)

Đăng ký 09/11/2026 TRƯỚC smoke re-run. Chỉ đổi 2 câu trong prompt_variants/finance/; KHÔNG đổi tools, gold, grader, gates, sampling, caps hay bất kỳ cấu hình nào khác.

## Failure 1: trap-empty r1 — khong_tra_loi
Grader refusal_reason: `bad=['contradictory availability assertion']` — model trích `availability = empty (fixture trống...)` trong refusal reason → lexical guard bắt.
**Rule thay đổi (citations.md)**: thêm "State the financial fact only; do not quote internal tool metadata fields (availability, count, fixture labels) in the reason."

## Failure 2: growth r2 — sai_ky
Model trả `period: "Q3/2026"` — thiếu Q2/2026 (kỳ so sánh). Instruction đã nói "Nêu rõ hai quý đối chiếu" nhưng policy chưa nhấn mạnh.
**Rule thay đổi (tools.md)**: thêm "For a growth or comparison answer, the period field must name both compared periods explicitly."

## Phạm vi KHÔNG đổi
Tools, payloads, gold, grader, gates, sampling (Super 1/0.95, DS 0/1), caps, arms, schedules, memory tasks.
## Tiêu chí thành công (đã đăng ký)
B1 ≥ B0 (strict + grounded) và grounded ≥ 20/24 → pilot OpenRouter :free.
## Nếu vẫn fail
Báo cáo per-arm, không retry chất lượng, không nâng cap.
