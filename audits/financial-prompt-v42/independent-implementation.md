# Independent implementation review v4.2

2026-11-06. Status at initial checkpoint: **PENDING**; see final coordinator closure below for the current launch gate. This reviewer makes no inference calls and does not edit implementation owners' source.

## Scope and preregistration

Review against `plans/2026-11-06-v42-replay-repair-contract-study.md`: common finite-replay C2 input contract; per-intent native correction accounting; public success/refusal response contract; semantic refusal grading with frozen-v4.1 sensitivity; equal budgets and actual SDK/wire reconciliation. The failed v4.1 smoke and source stay preserved. No production writes, main/holdout inference or stronger model calls belong to this review.

The v4.1 independent audit was read before implementation review. Its observed failures remain relevant regression cases: five bank initial failures must not consume one tool-wide correction counter; an ordinary BID request after VCB failure must remain independent; null/refusal does not make an answerable task financially correct; schema-valid finite replay rejection does not establish absent financial data. Historical TUI full-suite failure remains disclosed rather than silently converted into a clean full-suite result.

## Required closure before inference

- C2 advertised schema and authoritative replay support agree for every recorded/default-equivalent request, array ordering, case normalization, defaults, ambiguous variants and unsupported combinations. Financial payloads/gold remain byte-identical.
- Actual OT, OpenCode and DSH wire retains finite constraints. Provider schema restrictions fail visibly; no silent stripping, hidden request selection or answer-bearing schema.
- Correction identity and phase operate through actual SDK/native tool flow, preserve entity/financial selectors, isolate concurrent calls, bound duplicate/retry behavior and preserve global request/token/step/time accounting.
- Refusal schema and grader distinguish honest unresolved/no-data results, rejected requests, contradiction/double negation, forged receipts and nonempty mixed answers. Both historical and new grades are retained.
- Numeric canary acceptance is explicit and sealed before model calls. Native policyOFF remains current upstream behavior under the same common C2 interface.
- Focused independent tests, owners' relevant full-suite evidence, source/dependency/protocol hashes and all unresolved failures are recorded before a final PASS or qualified gate.

## Early design findings

The previous exact matcher normalizes string whitespace/case and array order, and permits documented defaults to be supplied or omitted. Finite JSON-schema constraints generated directly as recorded constants can disagree with that support; overlapping `oneOf` variants can additionally reject otherwise valid default-equivalent calls. The benchmark owner has been asked to establish explicit equivalence/parity coverage, rather than testing recorded requests alone. Closure pending.

Independent early probes found three implementation issues and sent reproductions to the respective owners before inference:

1. C2 generation aborts on existing recorded ten/twelve-element batch requests (`Unreviewed long array finite variant`). The generator's claim that corpus requests contain no arrays is false across the full offline corpus. Requested exact non-factorial order-independent schema support, including normalization and duplicate multiplicity considerations.
2. The new semantic refusal function accepts explicit contradictory successful-resolution assertions in Vietnamese and English, and accepts an invalid-parameter explanation as an empty resolver. Examples: “Không được giải mã thành symbol hợp lệ. Tuy nhiên đã phân giải được XYZX thành VCB.”; “No valid symbol. However XYZX successfully resolves to VCB.” Existing double-negation detection correctly rejects “Không phải là không được giải mã thành symbol hợp lệ.” Requested generic predicate/context fixes and independent adversarial coverage.
3. Actual new `FinancePolicyState` permits a second execution for a successful default-equivalent query: `{symbol:"HPG"}` then `{symbol:"HPG",days:365}` with declared `days.default=365` create two intent IDs. Requested comparison-only default normalization without argument mutation, plus failed/corrected budget-preservation tests.

These are early source checkpoints, not final findings against a frozen candidate. All remain pending until fresh targeted verification and owners' regression evidence close them. No model calls were made by these probes.

## Closure in progress

The independent reusable probe `offline-probes.py` completed PASS: **402 recordings, 2412 query variants, 589 financial files unchanged**, with `_norm` and `_entry_matches` source byte-identical to v4.1. Query variants include recorded requests, lowercase/whitespace, explicit defaults, reversed array order and unsupported unknown arguments. Comparison uses the old C1 validator and unchanged matcher, rather than trusting the new C2 validator as its own oracle. All six independent semantic canaries pass, including the three early false positives and observed honest paraphrase. This establishes the first two early findings' targeted closure; final source hashes and SDK-wide wire proof remain required.

The default-equivalent native duplicate probe now rejects the repeated execution. The owner additionally found and fixed a serious scope defect before freezing: invalid financial selector values were previously dropped or collapsed, allowing a correction to change period/year/metric meaning. The final design retains those values, permits only comparison-level lossless type equivalence, and recognizes domain aliases only when the public schema explicitly declares them. The actual C2 profile declares no aliases and no repairable window/projection fields. Consequently a schema-valid unsupported non-default window/projection is **not** authorized for native scope-changing repair. Five repaired bank intents in the deterministic SDK fixture use a separately disclosed public days-repair fixture; they are not financial quality observations or a claim that the actual study silently relaxes C2.

The actual SDK/stdio receipt was inspected: five initial bank failures retain five distinct intent IDs; five subsequent successes retain those same IDs with correction-used exactly one. A second actual SDK receipt covers baseline/candidate C2 wire and independent VCB/BID calls. Owner full-suite and fresh independent focused closure are still pending, so this document does not yet grant GO.

## Prepared outcome audit

`audit-completed-run.py` is outside the frozen study and requires explicit `--execute --run <absolute-directory>` plus a completed manifest (18 smoke or 176 pilot) and exclusive driver lock. It has only been syntax-checked, not run against v4.2 outcomes. It freshly grades primary/frozen-v4.1/frozen-v3, checks C2 captures, ledger/evidence and required-data coverage, preserves DNF and partial usage, and calculates fixed-denominator paired comparisons and the strict guard. Manual evidence classification and the coordinator's single zero-call resume receipt remain necessary after its execution.

## Updated external review and endpoint fairness

The reviewer read updated `opencode-review.md` §11 and `experiments/finance-v42-study/audits/INDEPENDENT-GATE-REVIEW-opencode-20261106.md`. The external 46-test probe and C2/canary observations are useful supporting evidence at their source checkpoint. Its “TECHNICALLY READY” verdict explicitly does not replace this final gate, latest native suite, actual SDK call-path proof or the live smoke certificate. C2 does **not** make the 36 old unsupported requests succeed: unchanged arguments remain unsupported; models must choose supported public variants. Twelve shared failed tasks do not prove an absolute computational ceiling, deterministic projection is not an arithmetic endpoint, and predicted 16–20/44 or preferential OT gains remain unmeasured hypotheses.

A material endpoint fairness gap was reported before inference: smoke numeric gold does not separately check all public final fields (notably final `period`/`source`), whereas the candidate's native guard checks public example shape. The coordinator has directed a common public-contract primary conjunction for **all** arms, derived only from raw final text, public examples/refusal schema and catalog, with the historical v4.1/v3 conjunction retained for sensitivity. This is not a numeric-gold change. Fresh adversarial and integration closure for that validator is pending. Where no historical period-value check exists, actual financial-period correctness remains an explicit manual diagnostic; this review does not certify a universal financial contract compiler.

Independent native focused execution on the latest per-intent source completed **33 pass, 0 fail, 119 assertions**: `bun test test/finance-policy.test.ts`, log `independent-native-focused.log`. It includes default/type/financial selector preservation, explicit alias policy, auth/no-data ineligibility and remaining pinned eligibility across sequential correction. Actual sequential SDK execution and final owner full suite still gate final closure.

## Final checkpoints still blocking GO

The coordinator's actual SDK/stdio sequential test exposed an issue missed by this review's earlier prepare-step inspection: `stopWhen` still capped the recovery stream at two steps by tool-name count. Permitting remaining intents in `prepareStep` alone therefore did not allow five sequential corrections to complete. The proper outside-sandbox run failed in 3.27 seconds; the earlier sandbox timeout is retained separately. See `root-native-sequential-probe.json`. This is why the prior code review and 33 policy tests were not an operational PASS. A source fix, fresh actual integration and final full native suite are required.

The common public validator is now implemented. Independent `public-contract-probes.py` passed **17 raw-output cases**, including correct numbers with missing period/source/evidence, wrong top-level types, provider/SDK/unrelated canonical source names, fences, prose, multiple objects, whitespace, legitimate refusal and incompatible mixed success. An arbitrary numeric value passes the structural validator as intended, demonstrating that it supplies no hidden numerical oracle. All **277 public instructions** have supported example shape. `public-contract-probes.json` pins the tested source. The prepared outcome auditor now independently recomputes this common conjunction from raw final text and task-scoped public tool names; historical endpoints remain their historical conjunction. Remaining actual SDK/call-path, final regression and source-hash closure is pending.


## Final closure — coordinator verification, 06/11/2026

**PASS for launching the registered smoke only.** Earlier pending checkpoints above are historical and superseded by this closure. Pilot remains conditional on the exact live smoke certificate and numeric canary; no efficacy or production superiority is established by these tests.

The independent reviewer completed the source/anti-pattern checks, 33 native policy tests, 17 raw public-contract negative cases, all 277 supported public examples, 2,412 C2-versus-legacy query variants over 402 recordings, 589 unchanged financial files, and the actual four-condition negative call-path proof (13 provider-stub requests / 26 captures). No real model was used. The coordinator then independently recomputed the full final freeze state, rehashed all 343 native source/test files and the final native logs/actual SDK receipt, and inspected the final benchmark preflight. This final receipt is signed by the coordinator rather than attributed to a subagent whose turn ended at its usage limit.

- Final native: **1092 pass, 2 skip, 0 fail**, 10981 assertions across 101 files; typecheck PASS. The prior stale-fixture failure is retained and explained in the native receipt. The actual parallel/sequential five-bank test now proves 4/8 requests with five independently corrected intents in one bounded phase; the earlier coordinator-detected two-step failure remains in root-native-sequential-probe.json.
- Final benchmark/offline preflight: **354 pass**, plus all four harness/MCP/isolation/grader checks PASS. The previous 352-pass/two-failure run is retained; only the synthetic reproducibility fixture was corrected to declare its public JSON example.
- Final approved freeze_state SHA256: **eb1471507c9f314d2ada983f40f183fab7839ec85ddd2c91e73776e19dddbd69**. Full current state equals the sealed state; zero native source or final receipt hash drift. See root-final-gate.json.
- The shared raw-public-contract validator applies to every arm. Historical v4.1/v3 conjunctions remain separate sensitivity endpoints. It checks public top-level shape/source and serialization, not universal financial-period contents. Final analysis must distinguish numeric/grounded correctness from strict raw-JSON format gains.
- Supervisor was read and verified: exact smoke18 -> current certificate/full regression/numeric retrieval canary -> pilot176, fixed NVIDIA Bolt/none/seed/caps, exclusive supervisor lock, expected-state checks before each stage, safe exact resume and current-certificate validation. Original/v4.1 preservation receipts remain in the isolated study audits.

At this closure no smoke/pilot run directory existed. Root explicitly authorizes the first registered smoke using the exact approved state; no source/config/prompt/protocol changes are allowed after inference. No automatic production installation is authorized. All failed/timeout/partial trials must remain in the denominator. Financial efficacy awaits the live experiment and one independent outcome audit.
