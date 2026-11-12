# v4.4 final read-only forensics

This is a supplemental explanation of the existing 48 smoke trials, not a replacement audit or rerun. Benchmark source, graders, auditor, captures and results were read only. No financial inference, quality retry, tests or pilot was run. Frozen audit FAIL and supervisor block at smoke-deepseek-audit remain in force; neither pilot is eligible. The evidence companion records original absolute paths, byte hashes, all 48 trial summaries, all 17 compute rows, provider failures and two independently reconstructed duplicate joins.

## Measured outcomes and failure stages

| Model | Arm | Strict primary /6 | Semantic /6 | DNF /6 | FR /4 answerable | Successful source MCP | Compute rejected |
|---|---|---:|---:|---:|---:|---:|---:|
| Bolt | B0 | 2 | 2 | 0 | 4 | 2 | 0 |
| Bolt | B1 | 2 | 2 | 0 | 4 | 2 | 0 |
| Bolt | OC | 1 | 2 | 0 | 4 | 2 | 0 |
| Bolt | DSH | 1 | 1 | 0 | 4 | 2 | 0 |
| DeepSeek | B0 | 0 | 3 | 3 | 0 | 13 | 3 |
| DeepSeek | B1 | 2 | 2 | 4 | 0 | 13 | 4 |
| DeepSeek | OC | 0 | 3 | 3 | 0 | 14 | 6 |
| DeepSeek | DSH | 1 | 3 | 3 | 0 | 9 | 4 |

Source: pinned `/home/doanlong/extra/benchmark/audits/financial-prompt-v44/independent-evidence.json`, recomputed raw-ledger counts in companion. The strict wins include trap refusals; they are not numeric wins. In Bolt every answerable numeric trial fails required retrieval; all 16 answerable trials are false refusals, not demonstrated arithmetic failures. Bolt made 35 unsupported-snapshot quote calls, 8 successful resolver calls, no successful quote or compute call. B1's two wins are traps. Its six acquisition entries yielded two resolver successes, one local invalid quote request and three no-call candidates. The quote r2 bounded correction entered with tools auto but returned another candidate without generating a corrected call. No budget/timeout provider errors occurred in Bolt; all24 trials have complete reported usage.

Bolt examples of unsupported query arguments are quote `days:1, interval:1D, columns:[t,c]`, aggregate `days:365, interval:1D, columns:[c,t]`. The public finite replay variants were not selected. B1 quote r1 says days/interval are required despite a public supported simple symbol request; aggregate no-call candidates state historical data unavailable without trying an allowed request. These are failures to use the exposed contract, not evidence that the source lacked the values.

DeepSeek retrieved42 quote responses and7 resolver responses successfully. Required-data coverage is21/24 trials (B0/B1/DSH5 each; OC6). Seven aggregation trials acquired all5 bank inputs, attempted compute, then failed before an answer; DSH aggregate r2 failed provider model metadata validation before retrieval. There is no actual completed aggregate calculation to grade as an arithmetic success or failure. All17 MCP computations rejected deterministically before arithmetic.

## Exact compute rejection mechanism

All17 requests use operation mean and source-matching `input_unit`/`output_unit` `nghìn đồng/cổ phiếu`. The7 first attempts select one operand at `/data/`; the10 later attempts select5 operands at `/data`. All selected call IDs join to successful quote calls from the same trial. There is no observed bad unit, wrong session reference, wrong entity or mixed recorded period rejection. A valid leaf here is `/data/last`, with explicit `last_t=2026-10-30` and matching source units; none of the17 requests selects that leaf. Source bank values visible in F captures are56.3,33.4,30.3,21.6,19.3 (mean32.18), but this independent arithmetic does not turn a missing final into a model success.

`tools/analytics_compute.py:12` permits schema pattern `^/data(?:/|$)`, so `/data` and `/data/` are schema-valid. `traverse`, line34, requires `/data/`, then traverses every pointer token. `/data/` indexes the empty key inside data, producing KeyError whose string is `''`; `/data` raises `numeric source path must be under /data/`. The source wrapper `tools/mcp_snapshot_server.py:298` serializes both as `invalid_derivation`, `retryable_with_corrected_arguments:true`, with generic numeric-leaf guidance. Thus the two error messages are explained by actual call arguments and source, without executing compute or weakening validation.

Repair eligibility and identity are distinct defects worth studying separately. `finance-policy.ts:29` allowlists correction codes but does not include `invalid_derivation`. Its schema-derived scope removes only declared repair fields; deterministic compute declares none, so changing pointer paths/operand count changes the intent identity. In F both initial `/data/` and later `/data` requests are labeled separate `initial` intents6 and7 with correction_used0. They are not a measured successful same-intent repair. The terminal third call repeats intent7 exactly and is correctly blocked locally. Error-text wrappers preserve the JSON rejection body in model context, but the local correction classifier does not grant repair solely because text contains retryable:true. This explains why a generic server retry hint is not equivalent to an available native bounded correction.

DeepSeek B1 has zero acquisition enter events. Its two completed trials skip acquisition because candidate_has_actual_support and actual_empty_response; other trials die during provider/tool continuation. Acquisition does not restart a fatal request, and `acquisitionDecision` explicitly stops when an actual failed intent requires repair/terminal handling. General phase_events21 in pinned mechanism totals also includes tool-end events; it is not21 acquisitions.

## The frozen auditor's two local-rejection errors

Independent reconstruction proves duplicate rejections for both F aggregate trials; neither is a changed-scope/mixed-intent rejection:

| Trial | Original SDK call (MCP reached) | Local duplicate SDK call | Original MCP call ID |
|---|---|---|---|
| F aggregate r1 | chatcmpl-tool-b12a5933cae278af | chatcmpl-tool-877445b470d906d5 | 61bb4b6f-93f7-4569-8d8c-fa2d280c350e |
| F aggregate r2 | chatcmpl-tool-92f3120d5358c5c6 | chatcmpl-tool-8aceaeab56ebc26b | 392392df-9fe6-4673-96a2-983845850fa7 |

Both duplicate tool-start arguments equal the original byte-equivalent parsed JSON, including all5 call IDs, `/data` paths and units. Their local rawInput equals those arguments. Both original tool-end and local duplicate carry finance-intent-7, original_sdk_call_id pointing to the table's original ID. The rejection is `Repeated or already pending/successful intent; do not replay this request.` The phrase covers repeats of failed arguments as well as pending/successful states; here original status is failed. Both generating provider request4 ledgers contain the duplicate SDK ID; original IDs occur in request3. Native request5 capture contains the actual assistant duplicate call and corresponding local tool error, while earlier captures contain the original call. The MCP ledger has exactly one row matching these arguments, representing the original rejected execution, and no third compute row. All operand IDs independently join to successful source calls in that trial.

Exact evidence paths:

- r1: `/home/doanlong/extra/benchmark/experiments/finance-v44-study/results/financial-v44-smoke-deepseek-20261107-startupfix1/trials/smoke-agg-01__opentrading_finance__r1/attempts/01-ddb279a46ee6/`: `run.log` original start/end110/111, duplicate120/121; `mcp.jsonl`; `provider.jsonl`; `provider-requests/0005-native.json`.
- r2: same cohort, `trials/smoke-agg-01__opentrading_finance__r2/attempts/01-3482089719c5/`: `run.log` original109/110, duplicate115/116; corresponding ledger and request5 capture.

Each aggregate has8 generated SDK calls=7 MCP rows+1 local rejection. Across six B1 DeepSeek trials:19 generated=17 MCP+2 independently proven local duplicates. Pinned local_rejections0 is a count of auditor-accepted rejections, not proof that these local runtime events do not exist.

The auditor's dispatch in `tools/ready_check.py:288` invokes its newer intent helper only for schema profile finite-replay-c2. Compute is deterministic-derivation-v44 and falls into the legacy branch, whose recognized reason list at358 excludes the new duplicate phrase. This produces each Unrecognized policy guard rejection and consequent reconciliation error. The general `tools/intent_audit.py` helper already recognizes the phrase for C2, but that does not authorize editing the frozen auditor or retroactively applying a different audit. The original four errors, audit_controls_pass:false and supervisor block remain preserved. This supplemental reconstruction establishes a narrower fact: the two missing joins have legitimate local duplicate explanations; it does not flip the full operational gate to PASS.

## Provider errors, completion and format

DeepSeek66 gateway requests comprise57 upstream attempts,52 with reported usage,14 missing/partial-usage requests; only12/24 trials have complete usage. Terminal provider ledger errors total14:

| Error | Requests | Upstream attempted? | Interpretation |
|---|---:|---|---|
| token budget exhausted before request | 7 | no | One for each aggregate trial that reached compute; conservative actual-usage plus next-input UTF8-byte estimate plus2048 output reserve exceeds48000 policy |
| provider response model mismatch | 3 | yes | response_models=[] in DSH quote r1, DSH aggregate r2, F trap r1; absent validated response identity, not evidence of a different actual model |
| TimeoutError | 2 | yes | B0 trap r1 and F quote r2, each~240.5s request deadline |
| previous upstream usage unknown; further requests denied | 2 | no | Same two timeout trials: safe continuation denial, not additional upstream inference |

No recorded trial-deadline overrun (all timely), cancellation or max24-request termination explains these failures. These raw results do not preserve provider response bodies or upstream finish_reason fields; native request captures record requests, not raw responses. Therefore malformed provider finish cannot be separately counted or causally asserted. Runtime traces contain leaked DSML text and OC12 step_finish reason tool-calls, demonstrating tool-form text leakage/continuation, not a reliable upstream finish-reason census. Missing model metadata could reflect empty/nonconforming stream or error payload; the exact wire body is unavailable. Native OT maps several gateway403 errors into an API-key/access-denied message; OC wraps budget403 as provider.auth and DSH as AUTH. Those labels do not establish credentials were wrong. Ledger error classes above are the supported diagnosis.

Format is a separate loss from retrieval and arithmetic. DeepSeek8 finals start with Markdown fences (B0's3 completed finals, OC's3 extractable finals, DSH's2 trap finals). Frozen graders recover semantic correctness in these cases; current public contract rejects surrounding fences. OC trap r2 finishes with prose and no parseable answer despite status ok, hence DNF under common metrics. DSH aggregate r1 preserves DSML text as a final but no answer; it remains DNF. B1's remaining2 completed finals are strict-valid; its4 DNFs cannot be rescued by JSON formatting. Bolt has5 fenced finals and16 retrieval failures; fixing fences alone would not make numeric refusals correct.

## Separate future study priorities (no implementation authorized here)

1. First stabilize observable provider outcomes: preserve redacted raw response metadata/finish reasons and distinguish metadata missing, timeout, budget denial and auth in native error wrappers. Use recorded failures/offline fixtures before a new sealed cohort; never replay old financial tasks as an unregistered quality retry.
2. Prove the deterministic compute public contract against pointer-parent/empty-key failure classes and explicit source leaf examples; align runtime repair eligibility with structured invalid_derivation semantics while preserving successful-source, unit, period and duplicate protections. Independently measure correction of an original intent separately from a newly scoped request. Do not silently fix pointer paths or infer operands for the model.
3. Independently extend auditor coverage to every public schema profile with SDK-generation→local-or-MCP→model-visible-result proofs, including duplicate failed args, new-scope rejections, same-batch duplicates and tampered/missing events. Preserve v4.4 auditor and original FAIL; validate a future auditor on a separate immutable version.
4. Study retrieval contract selection for Bolt: simple public request vs unsupported requested variants; measure source coverage after one acquisition, schema rejection and bounded correction separately. Acquisition must remain a measured opportunity, not forced tool success or a cue to manufacture calls.
5. Study raw JSON contract adherence and actual answer continuation after successful quote retrieval independently from financial numeric correctness. Retain strict primary, semantic-only, entity/date/unit/canary and receipt-join outcomes as separate endpoints.
6. Only then preregister a new multi-arm common-compute cohort with unchanged model budgets or an explicitly randomized budget treatment, measured stopping reasons and no mid-cohort tuning. Both smokes are small known regression clusters: no permanent model ceiling, prompt-length causal effect, predicted score gain, superiority or production promotion follows from these48 trials.
