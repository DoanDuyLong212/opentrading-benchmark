# or15 pilot — manual judge of all strict failures (2026-11-11, user: "tự thực hiện judge")

LLM judge stopped at 19/216 by user. All 216 trials: strict grader pass = numbers within tolerance (trusted);
all 21 strict failures read one by one below. Audit: 5 auditor-gap errors, fixed (pending decision), 0 fabrication.

| Trial | Verdict | Cause |
|---|---|---|
| fin-l2-crypto-01 OT r1, r2 | CORRECT, graded wrong | value 2015.37 triệu đồng correct; note wrote 78.109 / 25.802 with thousand dots, evidence check needs 78109/25802 (contract number-format rule in note) |
| fin-l4-future-01 OT r1 | CORRECT, graded wrong | correct refusal (Q4/2026 not ended, data to Q3/2026); grader flags "contradictory availability" (known strictness, or11) |
| fin-l5-profile-01 OT r2 | REAL FAIL (OT) | calculate("cap/1000000000", unit "tỷ đồng") double-scaled (auto unit conversion + manual /1e9 → 0.000109); then 9 calls calculate("cap") without values → invalid_derivation + LoopGuard → reasoning-only, no answer at 17/24 requests |
| fin-c4-signal-808 OT r1 | CORRECT under ambiguous wording | selected/selected_pct/ann/all_pct all correct; "chênh lệch (điểm %)" read as difference of annualized (12.80) vs gold period difference (1.28) — task wording defect |
| fin-c3-maladder-806 OT r1 | CORRECT under ambiguous wording | all MA/gap values exact; "độ lệch lớn nhất" read as largest |deviation| (POW −7.00) vs gold signed max (GVR −0.50) — task wording defect |
| fin-c4-rebal-807 OC r1 | REAL FAIL (OC) | rebalance session off by one (03/08 instead of 04/08 = 60 sessions back); totals close, P1/P2 wrong. Task would be clearer with the date |
| fin-c3-maladder-806 DSH r1, r2; fin-c4-rebal-807 DSH r1, r2; fin-c4-signal-808 DSH r1, r2 | REAL FAIL (DSH) | hand-summing 60–120 prices in visible output hits the 8192 output-token cap → empty/"I'll fetch…" final (DNF, non-infra) |
| fin-m3-split-853 OC r1, r2; DSH r1, r2 | REAL FAIL (memory) | only the criterion from the resumed session (ROE>15%) applied; P/B<3 from the older session lost → FRT included |
| fin-m3-update-854 OC r1, r2 | REAL FAIL (memory) | fresh session, no access to criteria → refusal |
| fin-m4-port-855 OC r1, r2 | REAL FAIL (memory) | fresh session, portfolio unknown → no values |

Manual judge-primary (correct answers, rule FP/FR unchanged: 0 FP on traps):
| Arm | Core /44 | Compute /16 | Memory /12 | Total /72 |
|---|---:|---:|---:|---:|
| OpenTrading B0 | 43 | 16 (2 under ambiguous wording) | 12 | 71 |
| OpenCode | 44 | 15 | 6 | 65 |
| DSH | 44 | 10 (6 DNF token cap) | 10 | 64 |

Requests (core / compute / memory): OT 151/106/49, OC 99/46/95, DSH 94/32/82. Compute p90: OT 212 s, OC 47 s, DSH 43 s.

## Confirmation reruns (user 2026-11-11: fix OT 1,2,3 + reword; rerun only failed slots)
- or15r (OC, DSH failed slots, reworded tasks; audit PASS both): OC rebal-807 2/2 correct (date now explicit);
  OC memory 853/854/855 still fail (no cross-session memory, by design); DSH rebal-807 2/2 correct, m3-split-853 1/2,
  maladder-806 0/2 and signal-808 0/2 (8192 output-token cap while hand-summing, real).
- or15r (OT, first fix set) exposed two new issues → fixed: batch items carried derived chains with sub-call ids
  (auditor could not verify) → batch items are unverified; DeepSeek kept dropping `values` on long calculate calls
  (808 failed both runs, 14–22 requests) → ref-named variables bind to earlier compute/calculate results.
  Auditor: parallel identical calls in one message now count in LoopGuard proof order.
- or15r2 (OT, final code; audit PASS, 0 fabrication): 806 2/2, 808 2/2, crypto-01 2/2, profile-01 2/2, future-01 1/2
  (r2 = correct refusal graded wrong, same grader strictness). Fixes observed in use: compute batch (806, 808),
  ref-variables (808), scale_fixed (crypto-01, profile-01, 808).

Merged view (or15 + failed slots replaced; selective rerun can only raise scores; mixed code versions):
| Arm | Core /44 | Compute /16 | Memory /12 | Total /72 |
|---|---:|---:|---:|---:|
| OpenTrading B0 | 44 | 16 | 12 | 72 |
| OpenCode | 44 | 16 | 6 | 66 |
| DSH | 44 | 12 | 11 | 67 |
