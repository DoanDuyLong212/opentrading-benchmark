# Frozen v4.2 smoke trace diagnosis

Read-only audit, 2026-11-06. No model inference, replay execution, grader changes, or frozen study edits. New derived artifacts: `audits/financial-prompt-v42/trace-evidence.json` and reproducible `trace-evidence-build.py`. The script reads captures/ledgers/payloads and validates recorded arguments against captured C2 JSON schemas; it does not import or execute study code. Paths below are workspace-relative to `/home/doanlong/extra/benchmark`.

Run root **R** = `experiments/finance-v42-study/results/financial-v42-smoke-20261106`. Read `opencode-review.md` §11 and `plans/2026-11-06-v42-replay-repair-contract-study.md` as preregistration/context, not current outcomes. §11's expected parity, 16–20/44 forecast and absolute calculation ceiling are not observations from this run. This is 18 smoke trials, six per canonical arm; there is no concurrent OT B0 cohort and no pilot inference/result here.

## Observed outcomes and stages

| Arm | Official primary | Semantic task grade | DNF | Successful numeric canary | Successful resolver refusal |
|---|---:|---:|---:|---:|---:|
| OT | 2/6 | 2/6 | 2/6 | HPG 2/2 | 0/2 |
| OC | 0/6 | 2/6 | 0/6 | HPG 0/2 | 0/2 strict; 2/2 semantic |
| DSH | 2/6 | 2/6 | 0/6 | HPG 0/2 | 2/2 |

Sources: `R/summary.json`, every `R/trials.jsonl` row, corresponding `trials/<id>/grade.json` and attempt `result.json`. Official/grounded correctness includes raw public contract validity. Do not substitute `grade.json`'s tolerant semantic success for official primary: OC trap `grade.json` passes but `trials.jsonl` marks both invalid because the actual response has markdown fences. Frozen v4.1/v3 graders also score OC 2/6; strict public contract, not refusal semantics, explains this delta.

- **`smoke-quote-01__opentrading__r1` and `r2`:** both request HPG with replayable default-equivalent arguments, retrieve `last=21`, `last_t=2026-10-30`, and produce raw JSON `21`/`21.0`, `nghìn đồng`, period `30/10/2026`, source `vn_quote_history`, with exact seven-field receipt. r1 explicitly supplies `days:365,interval:1D,summary:false`; r2 `days:365,interval:1D`. This is grounded numerical extraction, not a demonstrated arithmetic calculation.
- **`smoke-quote-01__opencode__r1/r2` and `__dsh__r1/r2`:** all four calls include unsupported `columns:[t,c]`; most also `days:1`, OC r2 uses365. All are rejected, then emit honest query-error null refusals with empty evidence and no corrected call. Missing unit/value failures are downstream of unsuccessful retrieval, not measured wrong conversion of a retrieved price.
- **`smoke-agg-01__opencode__r1/r2` and `__dsh__r1/r2`:** each generates five bank calls, all rejected. Both DSH batches and OC r1 use `columns:[c,t],days:1`; OC r2 uses365 but retains unsupported columns. All four emit fenced JSON; OC uses scalar `value:null` refusal, DSH a `values` map of nulls without required scalar refusal `value`. There are no retrieved operands and no computed mean. DSH's requested unit/period text is correct, but cannot make the null result numerically or evidentially correct.
- **`smoke-agg-01__opentrading__r1/r2`:** neither makes any tool call. First response is a `values` map of nulls, empty evidence and an untested claim that the tool cannot query a precise date. One bounded output correction repeats the same structure; native outcome fails. `result.json` has status error, empty final_text and `Machine-response contract failed after bounded correction: Non-null answer requires actual successful tool evidence.` The actual candidate survives in `run.log` and next request history; empty final_text must not be mistaken for no provider generation.
- **`smoke-trap-01__opentrading__r1/r2`:** one provider request each, no resolver call. Raw valid scalar null refusal says the symbol needs resolving first; it does not establish not-found. Both fail primary and semantics due missing evidence/action, not fabricated numeric claims.
- **`smoke-trap-01__opencode__r1/r2` and `__dsh__r1/r2`:** four actual successful empty resolver responses support their not-found/paraphrase refusals, with exact receipts. DSH uses raw JSON and passes. OC wraps JSON in fences and loses strict primary despite valid meaning and receipts. OC's official `grounded_correctness=false` must not be paraphrased as fabricated receipts: independent payload/ledger content supports the refusal.

For each cited trial, `trace-evidence.json` supplies its unique attempt/result/capture paths, full final_text, calls, validity, accounting and public-contract errors; use those paths rather than assuming an attempt ID.

## C2 exposure, request validity and correction coverage

Actual first native/effective request captures advertise the finite `anyOf` constraints, public variants and repair metadata. On quote-history the accepted branch requires appropriate symbol; `days` absent or365, `summary` absent orfalse, `columns` absent ornull, `interval` absent or1D. Validity is a contract, not enforced provider constrained decoding: all generated calls must still be checked.

Independently validated all30 recorded MCP calls against the exact captured schemas: **30/30 C1 shape valid; 6/30 C2 valid**. C2 successes are two OT HPG plus four OC/DSH empty resolvers. All24 OC/DSH quote-history calls fail C2 and MCP returns `unsupported_snapshot_query`; none is a type error or actual absent financial data. Captured next requests contain the structured error: retryable=true, public allowed variants (e.g. `{symbol:HPG}`), failing argument paths, and explicit warning that rejection does not establish missing data. No corrected call follows. No rejected record has source/as_of/response receipt; rejection is not evidence of financial absence.

**Live smoke does not exercise OT's per-intent failed-call repair.** OT has two successful HPG calls and zero calls for the other four trials: zero eligible failed intents, zero corrected executions. Five bank intents are attempted by OC/DSH, not OT policy. Offline per-intent tests can establish implementation behavior, but this smoke cannot estimate live correction recovery or demonstrate regression of its five-intent state fix.

## Concrete premature-final and contract seam

`experiments/finance-v42-study/experiments/opentrading-runtime/src/core/agent.ts:1254` validates accepted finals. At1262–1273, if output issues exist but no eligible failed tool exists, rescue selects `toolChoice:"none"`; actual bank `0002-effective.json` confirms **none** on both repeats, whereas `0001-effective.json` is **auto**. This is output-format repair and disallows acquisition of the bank data missing from the first answer. It is not token exhaustion or five failed intents draining correction eligibility.

`finance-policy.ts:168` recognizes the alternative refusal only if scalar `value===null`. The bank null-map lacks that scalar, so it remains a success-shaped candidate; at213, undefined `value` is not null and empty evidence triggers the quoted non-null error. The second nudge gives a general evidence error and generic null-refusal instruction; it does not explicitly enumerate the missing scalar refusal branch or forbid retaining the nonempty values map. Model repeats the candidate. For trap, scalar refusal satisfies machine shape and no tool error exists, so the code has no correction to activate: a premature no-tool refusal can complete but still fail financial task grading.

This seam supports a separate acquisition/stop-policy study. It does not authorize broad retries, manufactured evidence, silent model argument replacement, or frozen-result repair.

## Prompt evidence and uncertainty

Actual first OT effective system prompt is identical across HPG/bank/trap:5368 characters/6865 UTF8 bytes. Read source `tools/prompt_variants/finance/{identity,tools,citations,style}.md` within study. It explicitly says minimal arguments, schema/finite variants, one correction per intent, exact raw JSON, alternative scalar refusal, no invented receipts, and sufficient entity/period coverage. There is no proven outright instruction to skip tools. The system is dense: source hierarchy, trading safety, period/scope/unit caveats, citation and formatting repeated in user contract. It does not operationally require acquiring evidence before a final “needs resolving” answer. Density and under-specified first-action priority are hypotheses to test; the trace proves skipped tools, not which sentence caused that behavior.

OC first HPG system is1917 ASCII bytes and says responses render as GFM; DSH is307 ASCII bytes. OC's native request user content also arrives quoted/escaped; this is a harness presentation difference worth independently testing. Neither GFM text nor escaping proves the cause of OC fences. OC also produces valid raw JSON HPG refusals; OT with larger context retrieves HPG correctly. Smaller context therefore does not by itself explain success/failure.

## Manual arithmetic, period, units and source check

Independently read `experiments/finance-v42-study/tasks/smoke/<task>/environment/payloads.json`, then compare to `<task>/solution/gold.json`; no gold is supplied to model or used to change study files.

- HPG recorded data: last21, last_t/data_time2026-10-30; units explicitly nghìn đồng/cổ phiếu. Therefore21 nghìn đồng =21,000đ, with answer source tool `vn_quote_history`, provider `vnstock`, as_of2026-11-01T15:54:29.883479+07:00. Both OT answers preserve requested thousands unit and correct session date. Recorded payload confirms latest recorded session; this is a frozen snapshot, not verification against a live market.
- Bank recorded rows all have last_t2026-10-30: VCB56.3, BID33.4, CTG30.3, TCB21.6, MBB19.3 nghìn đồng/cổ phiếu. Independently,56.3+33.4=89.7; +30.3=120; +21.6=141.6; +19.3=160.9; **160.9/5=32.18** nghìn đồng. Matches gold exactly using decimal arithmetic. Provider vnstock, as_of2026-11-01T15:57:50.079479+07:00. All five distinct selected-row receipts would be needed for a grounded full result. No trial reaches these operands through successful calls, so this is audit verification of answerability, not credited model recovery.
- XYZX recorded resolver: resolved=null, ambiguous=false, candidates=[], availability=empty; vnstock+local as_of2026-11-01T15:57:53.093226+07:00. This supports OC/DSH not-found refusal. OT never obtains it.

## Resource and evidence limits

34/34 recorded provider requests succeed HTTP200 with usage; actual response model strings identify `nvidia/nemotron-3.5-bolt-e4b`. Each request cap2048 output, observed maximum379 output tokens; total trial inputs range2671–6793 and outputs47–474. All trials use1 or2 requests against24 cap, maximum55.576s against240s trial limit; recorded conservative next-input byte estimates remain well below48000 policy-token cap. No trace indicates cap exhaustion, output truncation, provider timeout or required native stall recovery. Input totals OT30663, OC28744, DSH23047; output totals1637/1646/1906 respectively. Cache-read counts are present; byte estimates are not measured token counts. Frozen reports should preserve absent reasoning accounting as absent, not infer zero from trial fields.

Only OT HPG retrieves financial numeric evidence. Consequently the blocked per-arm numeric canary is substantively justified; OT's2/6 does not establish superiority/parity generally, causal benefit over concurrent B0, or arithmetic ceiling. Errors labelled `sai_so`/`sai_don_vi` are grader symptoms; reading traces prevents mistaking unreachable arithmetic for failed arithmetic.

## Separate studies supported by existing evidence

1. **Acquisition and finite-request action study first.** Register common C2 presentations that make accepted minimal requests easy to select, preserve same finite set, and test semantic action-before-final guidance/stop gate against concurrent native B0/B1. Measure generated C1/C2 validity, required intent acquisition, initial no-tool finals and refusal grounding. Do not silently auto-rewrite args. Four OT no-call failures and24 OC/DSH C2 rejections are direct evidence for this priority.
2. **Separate output-contract recovery study.** Explicitly identify scalar refusal versus success map, raw-object requirements, and missing evidence acquisition. Keep formatting correction distinct from a bounded acquisition opportunity; guard per-intent/global budgets and retain all previous errors. Report semantic correctness, raw contract validity, DNF and fabrication separately. Two OC semantic refusals lost only to fences, and both OT null-map candidates failed after correction, provide concrete cases.
3. **Controlled live repair study, preregistered separately.** Introduce eligible same-intent failures through a declared interface challenge (not gold-specific prompt edits), compare policyON/OFF concurrent, preserve financial meaning. Current smoke gives zero live OT repair opportunities; do not infer policy gain or failure from its lack of activations.
4. **Compute/unit track after acquisition can be measured.** Hold operands/source/period fixed and compare direct arithmetic with deterministic compute tools, including negation and wrong-period negatives and provenance transfer.32.18 is independently answerable, but current all-bank failure occurs before arithmetic. No empirical basis here for an absolute Bolt computational ceiling or guaranteed +6–12 task gain.

All studies need new versioned protocol/source/manifests, sealed endpoints and gates, preserved v4.2 scores and an explicit budget. These are proposals, not launched inference or permission to promote software.
