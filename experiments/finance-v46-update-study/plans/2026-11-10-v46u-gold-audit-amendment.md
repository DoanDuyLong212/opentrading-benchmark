# Amendment 2026-11-10 — gold audit fixes + secondary LLM judge (pre-inference for or10)

Registered before any or10 financial request. User-directed (2026-11-10): review benchmark flow,
audit every task/gold, run DeepSeek v4.1 Flash via OpenRouter (pilot first, main only after the
pilot is reviewed), secondary judge = OpenRouter `nvidia/nemotron-3-ultra-550b-a55b`.

## Corpus changes (audits/gold-audit-2026-11-10/)

Applied by `tools/apply_gold_audit_20261110.py`, registered in `audits/CORPUS-MIGRATION.json`
(81 files incl. 12 root-holdout files), receipt `patch-receipt.json`. No gold number of an existing
question changed. Summary: A1 session date stated where tools return no date (17 study tasks, 3
pilot); A2 compare-288..290 rewritten to answerable 1-session comparisons; A3 gf-compare-174/175
source = yf_commodities; A4 2src-257/258 three-tool source; A5 top-202 (exact duplicate of 201)
rewritten to volume top-5; A6 winner/symbol fields reject other candidates (22 tasks); A7 comparison
tasks state that `period` holds only the asked session (found by judge calibration on the superseded
or9 answers: 3/3 arms falsely failed fin-l2-gold-01; affects every arm equally); B2–B5 wording.
Judge calibration on or9 (53 answers): 88.7% agreement with sealed content label, all 6
disagreements were grader period false-fails (3 = A1, 3 = A7), manually confirmed. Deferred: B7 (fin-mem-349 alias; memory-corpus receipt) and root-holdout migration to the
v4.6u contract incl. 11 verbatim main replicas (C1). Verification: 342/342 oracles, synthesized
correct answers pass and mutants fail on 289 non-memory tasks, 53 or9 answers regraded with 0 flips,
625+8 tests pass.

## Runs

- or9 pilot (paused 53/132) is SUPERSEDED (corpus changed); kept immutable, diagnostic only. Its
  old `llm-graded*` files were produced by the cache-collision judge and are invalid.
- or10 pilot: same config `tools/bench_config_deepseek_openrouter.json`, same arms
  (opentrading_baseline, opencode, dsh), seed, caps and 2 repeats; new seal
  `audits/seal/financial-v46u-seal-or10-ds.json`. Devsmoke tasks and runtime are unchanged by this
  amendment, so the audited or7 devsmoke cohort is reused as the pilot prerequisite (same practice
  as or9), disclosed here.
- Main stays forbidden by this study's seal; a separate amendment after pilot review is required.

## Secondary judge

`tools/llm_judge.py` + `tools/grade_run_llm.py` (rewritten). Reference-guided single-answer grading
with the full public question, scoring type, expected fields with tolerances, refusal tokens and
notes; cache keyed by sha256(model+prompt); graded attempt selected exactly; no-answer recorded
without a call. Diagnostic only: never rescues a sealed failure; every grader≠judge case goes to
`llm-disagreements.jsonl` for manual review. Calibration against manual labels is reported before the
judge numbers are used in any comparison.
