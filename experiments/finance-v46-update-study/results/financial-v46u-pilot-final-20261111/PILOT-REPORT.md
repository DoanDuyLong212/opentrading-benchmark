# Pilot report — DeepSeek v4.1 Flash (OpenRouter), B0-only, judge-primary (2026-11-11)

Model `deepseek/deepseek-v4.1-flash-1017`; 22 eligible pilot tasks × 3 arms × 2 runs = 132 trials.
Judge: OpenRouter `nvidia/nemotron-3-ultra-550b-a55b:free` (all 132 calls returned that id).

## Composition (user-directed targeted rerun — disclose with every number)
- Base: or11 pilot (sealed, audit PASS, all-arm manual review: 121 wins, 1 removed).
- The 11 or11 failed slots were rerun under the latest code (OT tool-deadlock fix + relaxed native calculator,
  no shared calculators, auditor/OT constant consistency): or13r (9 slots) + or14r (OT agg-01 r1/r2).
  All rerun audits PASS, 0 accepted fabricated evidence; all rerun wins manually reviewed.
- Selective rerun can only raise scores and mixes code versions (121 slots from or11, which still had the shared
  calculators and the pre-fix OT). Unmodified or11 is reported alongside. Not a sealed b0 gate cohort.

## Primary: judge-primary financial correctness (judge correct ∧ numeric gate ∧ no fabrication ∧ not removed)
| Arm | Final (merged) | or11 unmodified (pre-fix) |
|---|---:|---:|
| OpenTrading B0 | **44/44** | 38/44 |
| OpenCode | **43/44** (1 removed by manual review) | 39/44 |
| DSH | **44/44** | 39/44 |
Paired task bootstrap vs B0 (final): DSH 0.0 [0, 0]; OpenCode −2.3 pp [−6.8, 0.0]. No arm is distinguishable.
(or11 judge column was produced by the earlier judge prompt; see "Judge fix".)

## Secondary
| Arm | Strict grounded | Raw format valid | DNF (infra) | FP / traps | FR / answerable | Stable 2/2 tasks | Requests | p50 / p90 s | usage.cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| OpenTrading B0 | 44/44 | 44 | 0 (0) | 0/4 | 0/40 | 22/22 | 192 | 19.6 / 41.2 | $0.137 |
| OpenCode | 44/44 | 44 | 0 (0) | 0/4 | 0/40 | 21/22 | 135 | 17.9 / 31.7 | $0.097 |
| DSH | 44/44 | 44 | 0 (0) | 0/4 | 0/40 | 22/22 | 129 | 20.9 / 31.5 | $0.073 |
or11 unmodified strict: OT 37, OpenCode 43, DSH 41 (OT: 5 tool-blocked DNFs, 1 corrupted evidence hash, 1 grader
refusal-strictness case).

## Findings that drove fixes
1. OT tool deadlock: the OT prompt forbade self-computed figures while its native calculator rejected unit-less
   sources, typed operands and literal expressions → reasoning-only empty answers. Fixed (prompt fallback; native
   calculator verified-first with lenient unverified results; per-share unit equivalence; formula constants).
2. Shared analytics calculators removed (user): calculation is each harness's own capability.
3. Auditor/OT consistency: formula constants aligned; OT keeps the true per-share dimension in its output unit.
4. Judge fix: the judge treated accept lists as exhaustive literals (9/132 false "partial" on equivalent dates like
   30/10/2026, on "Tổng LNST" without "hợp nhất", and on an ungraded period field). Prompt now states accept lists are
   equivalent alternatives and only expected fields are graded. Re-judge: 132/132 correct; calibration on the 62
   labelled trials: agreement 1.0, κ 1.0 (labeller = review agent; only 2 negatives).
5. Grader A8 (period with snapshot date) still exists in the grader; main instructions already carry the A8 bullet.

## Cost / budget
OpenRouter paid requests used: 2426 / 8000. Key spend so far ≈ $2.07 of $10. Judge: free quota.

## Open before main
- Main needs a sealed pilot cohort that passes the b0_judge_primary gate under the current code (this merged view is
  diagnostic). Options: accept this report as the pilot evidence by explicit user decision, or run the sealed or14
  pilot (132 trials, ≈ 500 requests, ≈ $0.35).
- Main: 183 tasks × 3 arms × 2 runs = 1098 trials ≈ 4,300 requests ≈ $3; judge on the free quota across UTC days.
