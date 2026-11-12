# Independent review of v4.6 and v4.6-update admission

2026-11-09. Reviewer: `/root/v46_independent_gate`, independent of the current financial and instrumentation implementation owners. Status: **NEW CANDIDATE NOT YET APPROVED**. No financial inference, source edits to frozen studies, or old-result rescoring was performed by this review.

## What the completed old Super R3 actually establishes

The run is complete at 96 scheduled trials (24/arm), manifest `844430b43028b57bad050471000f386f7d1cb7cf389c2911a6910afe276b598e`. It has **six**, not seven, unsuccessful OT-fin trials. Recorded strict/grounded scores: B0 18/18, B1 18/18, OpenCode 13/14, DSH 16/18. B1 therefore ties B0 and DSH on grounded financial correctness. Its one DNF is a regression against B0's zero. These are provisional development scores, not proof of superiority.

The original audit FAIL contains 16 errors: malformed generation inventories, ambiguous source-generation joins, and one unreconciled misspelled function occurrence. Do not waive these errors merely because several are auditing defects. The old quality gate also fails numerical canary/aggregate, grounded minimum, answerable minimum, perfect traps, and relative DNF requirements. No pilot/main promotion is admissible from this old run.

Read-only independent inspection covered **all 68 automatic strict-or-financial wins** across every arm: source/entity/period/unit/numerical value and accompanying narrative were consistent with these small frozen synthetic fixtures. Independent Decimal recomputation: growth15%, margin23%, ratio.13, mean52.86666666666666666666666667, cross-source difference.4, chain972 billion VND, scale92400 VND. All referenced seven-field source receipts joined unique successful MCP ledger rows. **670 raw capture hashes** (native/effective requests and raw responses with available hashes) matched; no code or task hashes differ from the saved manifest. This does not close failing SDK-generation joins and does not certify external market-source authenticity: fixtures explicitly are synthetic engineering data.

Actual effective sampling was identical across all four arms: temperature1, top_p.95, max output8192, common-gateway retry owner. Recorded provider rows: B1 107, B0 78, DSH78, OpenCode72. Native tool inventories intentionally differ by native product utility; capability parity is required rather than identical schemas. Clock difference remains declared: OT's native now is pinned, competitors expose their observed native clock. No evidence of an undisclosed within-model sampler difference was found.

## Six OT-fin failures, correctly separated

1. Trap-period r1: financially justified Q4/2026 unavailability refusal with authenticated evidence; a brittle lexical refusal matcher rejects it. This is a measurement-semantic weakness; retain the old fail.
2. Aggregate r1 and r2: correct common-date inputs81.7/34.8/42.1 and arithmetic rounded to52.87; error.003333333333 against unchanged absolute tolerance1e-6. Public instructions did not disclose precision. The candidate must communicate precision equally to all arms, not relax tolerance to rescue these rows.
3. Scale r1: actual runtime DNF, not formatting. After quote92.4 source unit `nghìn đồng`, native calculate rejected a model-supplied override `nghìn đồng/cổ phiếu`; the next upstream response ended as terminal424 `provider_finish_reason_missing` (34,588 bytes, usage unknown). This is a local unit-typing rejection followed by provider/SSE completion failure. Its costs/unknown usage stay preserved. Do not relax dimensional guards merely to remove this DNF.
4. Ratio r1: correct .13 mathematical ratio, but `unit:""` fails the meaningful unit contract. A separate real grader defect canonicalizes gold `tỷ lệ` to currency `ty_dong` through the broad `ty ` prefix. Fix dimensionless semantics in the new version for every arm; do not silently manufacture a unit on the old answer.
5. Resolve r2: right KDH price37.25, period/unit and both resolver/quote evidence receipts, but `source` lists only quote while gold requires both tools. Make the common public lineage requirement explicit; do not rescue old primary.

Thus “mostly financially correct” is a reasonable content diagnosis; “all seven are only formatting” is not supported. There are six final failures, one actual DNF, precision/lineage/unit/refusal semantics, and unresolved instrumentation joins. B1 additionally uses substantially more requests/tokens than controls, so even corrected form does not imply efficiency superiority.

## Previous approval independence

`approval-v46.json` identifies the OpenCode executor as the approving party and calls it independent of v4.5 owners. Independence from the previous version's owners does **not** establish independence from its own v4.6 changes. Its engineering claims are useful evidence, not an independently issued review of that implementation. The new candidate requires a distinct reviewer and exact code/task/runtime/config/admission pins after all changes and mutation fixtures close.

Product HEAD is `5705ada91033b05a1dd77f00eae39525b89e45bb`; the production checkout has expected local candidate changes, including package/lock/source patches, and is not a pristine Git tree. Hash/runtime parity and preservation receipts, not HEAD alone, must establish the actual executing build. This review does not authorize overwriting personal changes or installing a new candidate.

## New registration and blockers before launch

The candidate protocol is `experiments/finance-v46-update-study/plans/2026-11-09-v46-update-execution-protocol.md`. It preserves every original quality threshold, separates diagnostic pilot admission from qualification, and forbids MAIN/holdout/memory inference/v4.7 implementation. A failed quality smoke can still yield the explicitly requested diagnostic pilot only after both smoke cohorts finish and the given model's independent instrumentation, all-arm manual review, zero accepted fabrication and immutable pins pass. Unknown/failed measurement blocks pilot; it must not be patched in place and continued.

Before independent approval: close generation/SSE/parallel/malformed/unknown-tool/replay tracing fixtures; verify dimensional unit/precision/refusal boundary semantics across all arms; verify native accepted-output selection and reject raw-invalid rescue; actual native/effective inventory/capture parity and provider budgets; seal only smoke/pilot with explicit diagnostic authority; pause/hard-stop/completed-resume zero-call proofs; run applicable focused/full engineering checks and review residual failures without weakening tests. No financial call may occur until that approval binds exact final pins.

Evidence: `INDEPENDENT-OLD-R3-REVIEW.json` in this directory. Original results and their recorded primary metrics remain unchanged.

## Candidate review progress before final freeze

Independent inspection found no changes to any candidate payload, numerical gold, task metadata or oracle relative to original v4.6. Task changes consist of239 common financial instructions and254 primary grader copies (including15 preserved memory namespace variants). Both model configs now name the new protocol and allow only devsmoke/pilot. The seal maker rejects MAIN and binds diagnostic authority to the protected independent approval. `quality_gate` thresholds remain unchanged. The manual-review loader binds manifest, complete automatic-win decision coverage, artifact tree and automatic-audit bytes; its only effect on primary rows is removal of automatic wins.

Actual pinned Bun1.4.4 validation covered all254 non-holdout tasks and156 unique schemas,378 B0/B1 recorded-argument acceptance/unknown-field rejection checks, with zero failing schema and zero Unicode-pattern compilation errors. The two common utility schemas also compiled and correctly rejected missing required fields. No holdout input or model inference was used. Proof: `schema-verification/result.json`; binarySHA10702245766b225e70bbf6235fd6b47214fd94b4760d00ffaed8ab0df57ac235.

Root's actual four-arm common-calculation wire proof and native source→calculate→read_result→final wire proof are PASS with zero external calls. These validate the previously closed accepted paths; subsequent minimal rejection-origin/final-output fixes require affected final checks before approval. The full engineering suite is still being closed; this paragraph is not inference approval.

Independent reviewer identified an additional native occurrence blocker: maps keyed only by SDK ID preserve the first origin when a later real generation reuses the ID, conflating new occurrences and genuine replay. Root authorized a minimal generation-key fix and an actual SDK repeated-ID regression before freezing. The native terminal-invalid-final fallthrough was separately identified by the implementation owner and is being closed before qualification. The derived arithmetic auditor must share the prospective dimensionless-unit correction, with negative currency/ratio conversion tests. These are measurement/safety repairs, not v4.7 architecture features.
