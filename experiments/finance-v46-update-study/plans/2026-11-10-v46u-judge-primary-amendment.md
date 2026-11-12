# Amendment 2026-11-10 (b) — judge-primary financial correctness

Status: APPROVED by user 2026-11-10. Registered while the or10 pilot was running (≈110/132 trials
completed and observed live as strict pass/fail counts; no judge-primary score had been computed).
This disclosure is part of the amendment.

## Decision (user, 2026-11-10)
Benchmark flow B1 task → B2 answer → B3 grade, with the co-primary endpoint changed from strict
JSON/provenance success to **judge-primary financial correctness**. Strict grounded success remains
reported as a secondary diagnostic. B1 (finance prompt) is retired; B0 (opentrading_baseline) is the only
OpenTrading candidate.

## Definition (analysis/judge_primary.py)
Per scheduled trial, primary = 1 iff all hold:
1. Judge `nvidia/nemotron-3-ultra-550b-a55b` (OpenRouter, temp 0, reference-guided, tools/llm_judge.py)
   returns `correct`.
2. Deterministic numeric gate: every value field within the gold tolerance (parsed JSON, else every gold
   number present in the text within tolerance).
3. Rule-based anti-fabrication: no numeric `value` on a refusal trap (FP), not a false refusal.
4. Not rejected by the independent all-arm manual review (review only removes).
DNF (no final answer) = 0 and stays in the denominator; infra DNFs reported separately.

## Industry alignment
Vals AI Finance Agent (rubric LLM-judge + contradiction checks), FinanceBench (value+unit match with
rounding tolerance; LLM-judge variants validated against humans, κ≈0.65–0.77), MT-Bench (reference-guided
judge, cross-family), GAIA/FinQA (deterministic numeric scoring). Numbers are never decided by the LLM.

## Validity requirements
- Judge↔human agreement on ≥50 hand-labelled trials, κ ≥ 0.6, reported with every result; or9
  calibration: 88.7% agreement, all 6 disagreements were grader false-fails (A1/A7).
- Gold leak check: 0 hits over 1026 or10 captures (provider requests + workspace instructions).
- Every judge≠strict case manually reviewed; judge model id logged per call.
- Statistics unchanged: paired task bootstrap (seed 20261104), stable 2/2, full denominators.

## Calibration result (or10, analysis/labels/or10-kappa.json)
n=62 (all 16 disagreements + 44 seeded agreements + 2 judge-incorrect): agreement 0.984, Cohen κ 0.79,
judge FP 0, judge FN 1 (growth-01 period). Labeller = root review session (agent), content-only re-grade +
manual reading. Only 2 negatives → re-check κ on main. Judge model: free variant
`nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter free_model_daily_requests 1000/UTC day) with automatic
fallback to the paid id on 402/429; returned model id logged per call.

## Not changed
Sealed or10 artifacts, sealed grader, strict metrics, and the anti-fabrication audit. Main requires its own
amendment (request budget >1900, A8 schema fix, condition 'opentrading' → baseline, holdout migration, new seal).

## Judge prompt fix 2026-11-11 (found on the pilot, before main)
The judge read accept lists as exhaustive literals: 9/132 false "partial" (equivalent dates such as 30/10/2026,
"Tổng LNST" without "hợp nhất", an ungraded period field). SYSTEM now states that accept/reject lists are
equivalent alternatives (one semantic match suffices), equal dates/periods in other formats are correct, and only
expected fields are graded. Re-judge of the 132-trial pilot: 132/132 correct; re-calibration on the 62 labelled
trials: agreement 1.0, κ 1.0. Main uses this judge prompt (new seal required; tools fingerprint changed).
