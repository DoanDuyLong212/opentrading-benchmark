# Independent completed smoke audit v4.1

06/11/2026, Asia/Bangkok. **Smoke completed; readiness certificate failed; pilot did not start.** No extra inference, retuning, grader changes, trial replacement, production installation or second resume occurred in this review.

The supervisor ended `blocked`, stage `certificate`, exit 1. Its certificate log records passing harness checks, MCP roundtrip, isolation, grader checks and **297 regressions**, then rejects live parity because smoke contains execution/tool-path failures. The qualified native engineering gate was not a guarantee of successful live behavior.

## Integrity and official results

Exactly **18 unique scheduled trials = 3 tasks × 2 runs × 3 canonical arms**, six per arm. Manifest fingerprint: `ca5a7c6ab59e1ecc7472be00cca8a5b8a5751a975d67082194129599d9234245`. Canonical OT selects the finance candidate. **Concurrent OT baseline was not run.**

The prepared offline verifier was executed once by the coordinator after completion. It freshly graded stored answers with both actual task and frozen-v3 graders, writing temporary outputs; missing answers remained failures. It checked manifest/schedule, frozen source/dependencies/protocol/tasks, ledger replay, seven-field joins and actual model-visible receipts, native/effective captures/policy, condition/prompt/clock bindings and tool-call reconciliation. All 18 fresh grade records are preserved; **zero audit discrepancies**. This reviewer inspected the results and manually closed the findings below; no second regrade was needed.

| Condition | Official primary /6 | Frozen-v3 /6 | Answered /6 | DNF /6 | False refusal / answerable-started | Claimed evidence mismatch |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| OT candidate | 1 | 1 | 4 | 2 | 2/4 | 0 |
| OpenCode | 2 | 2 | 6 | 0 | 4/4 | 2 |
| DSH | 2 | 2 | 6 | 0 | 4/4 | 3 |

FP is zero for all conditions, each with two unanswerable-started trials. OT false refusal is 2/2 among answered answerable questions, versus 2/4 answerable-started; its two aggregation DNF explain the denominator difference. The smaller count is not demonstrated refusal improvement.

There are **40 actual provider requests**, all HTTP200 with complete usage, and **80 native/effective captures**. No fallback or unknown usage was observed. MCP has **42 executions: 6 successful, 36 rejected**, all rejections `not_recorded`, not raw-schema/C1 type failures. There are no native local schema rejections. All six successes are the nonexistent-symbol resolver task; no quote/aggregation query retrieved the needed financial data.

| Condition | Requests with usage | Input tokens | Output tokens |
| --- | ---: | ---: | ---: |
| OT candidate | 16/16 | 47,257 | 2,320 |
| OpenCode | 12/12 | 24,700 | 2,597 |
| DSH | 12/12 | 19,242 | 2,722 |

No unsupported monetary cost is inferred. There is no 176-trial cohort, four-condition /44 ranking, candidate-minus-baseline estimate or pilot guard assessment. Three smoke tasks and two repeats cannot prove broad superiority or causal candidate regression against an unrun baseline.

## Verified failure mechanisms

**Schema-valid requests missed exact replay.** OT HPG used `columns:["t","c"]`, `days:1`, `interval:"1D"`; bank calls used `columns:["c","t"]`, `days:365`, `interval:"1D"`. These satisfy C1 shapes/domains. The snapshot records symbol-only/default requests, so additional non-default projection/window does not match. All arms suffered quote/aggregation mismatches. A raw-schema validator cannot reject these; neither the 36 cases nor this smoke proves those requests are invalid in production. Matching remained correctly strict.

**Correction accounting is keyed too broadly.** Each OT aggregation trial sends five bank calls in one batch: one tool name but five distinct entity/intents. The policy aggregates their failures into that tool's attempt counter. After five failures `correctionTools()` is empty. The third actual request has `tool_choice:"none"` and only output-contract feedback, so it cannot repair financial queries. This is a concrete runtime granularity defect, not five completed correction attempts. The source is `FinancePolicyState.failures/failed()/correctionTools()`.

The coordinator additionally reproduced the actual class deterministically, without inference: five distinct entity failures produce one stored intent, attempt count5 and no correction tools. After a VCB failure, an ordinary requested BID call is also rejected as changing the original entity, even outside the extra correction phase. See [policy-counter-repro.json](policy-counter-repro.json). This is a real candidate correctness defect. The earlier focused tests and qualified native engineering gate did not cover independent multi-entity intent isolation; passing them must not be presented as proof that this case was safe.

**HPG repair was permitted but not taken.** Both HPG trials have a third request with `tool_choice:"auto"` and real error context; the model declines another tool execution and returns null. Permitting correction does not guarantee it occurs. No corrected request, restored coverage or recovered financial primary was observed.

**Output protection is not answer recovery.** Both OT aggregation trials end with `Machine-response contract failed after bounded correction: Required evidence must be an array copied from actual successful tool results.` No final answer is emitted. These are two real error/DNF trials, despite HTTP200 from the provider. Rejecting an invalid final does not provide missing data or improve accuracy by itself.

## Manual evidence and refusal adjudication

All five mismatched-evidence trials in OC/DSH contain invented placeholder receipt values, including `benchmark_evidence.call_id`, `call_id_vcb` and `call_id_from_response`, with fabricated hash labels after rejected requests. Some also use SDK aliases. These are not merely namespace differences around genuine receipts. All five fail official primary; **no fabricated evidence was accepted**. OT has no nonempty mismatched-evidence answer in this smoke.

`smoke-trap-01__opentrading__r1` is a **lexical grader false negative**. It returns null, a genuine successful resolver receipt and: “Mã tài sản XYZX không được giải mã thành symbol hợp lệ trong snapshot 2026-11-01.” This honestly reports unresolved XYZX, but falls outside the frozen refusal lexicon. Official grade stays unchanged at OT1/6. Separate adjudicated refusal sensitivity is **OT2/6**, equal to OC/DSH on smoke. It still supplies no financial quote/aggregation canary and does not remove either OT DNF. No grader was patched to reopen this certificate.

## Resume and final decision

The coordinator ran the exact original command/settings plus `--resume`, exit0. The receipt has **2216 files before/after, identical hash maps, zero changed paths**. This reviewer independently rehashed all 2216 recorded current files: zero mismatch. Manifest, trial rows, provider/MCP ledgers, native/effective captures and trial artifacts remain unchanged, proving no extra requests, captures, duplicate trials or replacements. No second resume was necessary.

Receipt: [smoke-resume-check.json](smoke-resume-check.json), SHA256 `34562b4c32591e39966cff3ece70293e16d6b617485513a8910a9c037dbaa9dc`.

**Readiness failed; pilot and rollout do not proceed.** This smoke cannot promote the candidate. The registered four-condition promotion guard is **not assessable**, because baseline and pilot were not run. Production was not installed or modified by this experiment. There is no evidence here that OT has surpassed both harnesses.

A future version should separate correction state by actual intent/entity/batch call, test parallel independent intents and make replay limits actionable without hidden-gold request selection or dropping args. Any behavior/grader change requires a new version/protocol and preserved old outcomes; do not backfill v4.1 to obtain a favorable certificate. Compute and stronger-model tracks remain separate experiments.

Detailed fresh grades, counts and manual closure: [independent-evidence.json](independent-evidence.json). Comprehensive coordinator report: [REPORT.md](REPORT.md).
