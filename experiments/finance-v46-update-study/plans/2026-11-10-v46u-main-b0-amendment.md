# Amendment 2026-11-10 (c) — B0-only study: fresh pilot → main under the judge-primary gate

Status: APPROVED by user 2026-11-10 ("thực hiện đi"). Registered before any inference of this study.

## Why a new study
The or10 pilot cohort is BLOCKED (instrumentation: OpenTrading native LoopGuard denial unbound in the
ledger auditor) and its corpus predates A8. Per protocol a blocked cohort cannot admit main; this
amendment registers a separate study (new seal, fresh pilot) instead of reusing or10, which stays
diagnostic and is never resumed.

## Changes (all before the new seal)
1. Auditor: `audit_v45_run.py` reconciles a pending generated call when the model-visible tool result is
   exactly the OpenTrading LoopGuard sentence for that tool AND at least count−1 earlier generated calls
   have the identical tool+arguments (`v46_rejection_proof.loop_guard_count`). Classified
   `native_loop_guard_denial`, never financial evidence. Verified on a copy of or10.
2. Corpus A8: one bullet in the common v4.6u contract of pilot/smoke/main/holdout instructions — `period`
   holds only the asked data period. Devsmoke untouched, so the audited or7 devsmoke cohort remains the
   honest prerequisite (same practice as or9/or10).
3. Holdout: 11 verbatim main replicas replaced (user decision); 50 financial tasks migrated into the
   study with the v4.6u contract (+A8) and study grader; 60-task holdout = 50 financial + 10 memory;
   44 financial eligible. Holdout opens once, after main, with its own receipt.
4. Arms: pilot and main = opentrading_baseline (B0), opencode, dsh (`arms_pilot`, `arms_main`); the
   `opentrading` alias is not redefined. B1 retired.
5. Gate `b0_judge_primary` (tools/b0_gate.py) replaces the B1 superiority gate: complete schedule,
   audit PASS with 0 accepted fabricated evidence, all-arm manual review complete with 0 accepted
   fabrications, judge-primary scored for every trial (tools/judge_primary.py), judge calibration
   κ ≥ 0.6 (analysis/labels/or10-kappa-free.json, protected by the seal). No superiority threshold.
   Main additionally needs `pilot-review-approval.json` written only after the user approves the pilot report.
6. Judge: `nvidia/nemotron-3-ultra-550b-a55b:free` (calibrated: 62/62, κ 1.0 vs labels; labeller is the
   review agent, only 2 negatives) with paid fallback on 402/429; one cohort may span UTC days on the free
   quota. Holdout: paid id only with OpenRouter `data_collection: deny` (verified provider BaseTen).
7. Budget: OpenRouter paid request cap 1900 → 8000 (used 1733; fresh pilot ≈520, main ≈4300,
   holdout ≈1000). Cost is reported from OpenRouter `usage.cost` (list price under-estimated or10 ≈2.8×);
   expected agent spend ≈ $4 against $8.41 remaining on the $10 key.

## Endpoints
Primary: judge-primary financial correctness (amendment b). Secondary: strict grounded success,
raw-format validity, FR/FP, DNF split infra/other, latency, requests, usage.cost, stable 2/2,
per-family, judge×strict matrix. Statistics: paired task bootstrap vs B0, full denominators.
