# Independent v4.5 engineering review

Reviewer: /root/v45_independent_review. Date: 2026-11-08, Asia/Bangkok.

**Final engineering decision (2026-11-09): APPROVED for the exact pinned headless benchmark profiles listed in the final approval artifacts.** The initial findings below are retained historical evidence; later closure sections supersede their original OPEN labels. Exact installation safety was approved separately. This review is independent of implementation owners. No NVIDIA or other external model calls were made. Findings below come from source inspection, real local native processes, synthetic MCP records, and offline tests. The source is still changing; test counts are intermediate evidence, not approval of a later unreviewed hash.

## Material findings

### P1 — Common calculator unavailable in actual isolated MCP process (OPEN)

`study/tools/analytics_calculate.py` resolves `BUN = Path.home()/'.bun/bin/bun'`. The actual MCP process receives a fresh isolated HOME from each adapter. That home has no Bun installation. All four actual arms retrieve the synthetic source correctly but `analytics_calculate` returns `invalid_derivation: pinned native calculation runtime missing`. Direct Python unit tests run under the real user HOME and do not catch this.

Independent actual-process proof: [all-native-common-wire-2b93cb39/proof.json](all-native-common-wire-2b93cb39/proof.json). It contains separate baseline OT, finance OT, OpenCode and DSH outcomes and exact workspace/ledger paths. Every cohort failed. The first two local HTTP responses were 503; the gateway recovered to the scripted source response. Subsequent calculator failures are real tool errors, not model-quality evidence. External model calls: **0**.

Required fix: a trusted, frozen Bun locator passed internally to the MCP process or resolved from the installed pinned runtime, independent of isolated HOME. Do not accept a model-supplied executable path or weaken the replay auditor because live execution failed. Add an actual subprocess clean-HOME fixture and rerun all four actual adapters through the current common calculator. `verify-all-native-common-wire.py` is the bounded, local-only independent review fixture; its first failure artifacts remain immutable.

### P1 — Extra fabricated numeric claims inside strings passed both semantic and provenance grader checks (OPEN)

The grader's new `no_unrequested_numeric_claims` scans only typed JSON numbers. A correct `v45-dev-09-chain` answer with value 972 and required evidence, plus `note: "Doanh thu năm 2025 là 99999 tỷ đồng"`, returned `success=true`, `semantic_correctness=true`, `provenance_correctness=true`, `schema_valid=true` in an independent offline reproduction. A valid primary answer and receipts do not certify this extra claim. The reproduction uses synthetic receipt IDs solely to isolate the grader; the driver separately requires actual receipt IDs, which does not address unsupported narrative claims once actual receipts are substituted.

Required fix: an explicit bounded policy for unrequested numeric assertions, including numeric-looking strings, without rejecting required period/date disclosures; mutation fixtures; and a fail-closed independent manual source/math/extra-claim audit of **all primary wins in every arm**, including smoke, before gate advancement. A numerical fabricated-claim count must not be inferred solely from receipt membership. Root has requested the manual gate amendment before financial inference.

### P1 — Native growth and relative-strength could compare unlike unit scales (FIX APPLIED, independently reproduced closed)

Initial actual native `groundedCompute` reproduction: one source contained revenue 1 triệu đồng in 2024 and 2 tỷ đồng in 2025. `pct_change` returned 100%, although converted growth is 199900%. The initial branch checked financial alignment but not source unit scaling. The independent auditor initially also computed raw growth without conversion.

Native owner added `sameSourceUnit` checks for growth and each relative-strength window. Re-running the same native reproduction after the fix now rejects with `Published source units differ inside the window; convert explicitly with calculate...`. Benchmark owner independently converts public input units for growth verification. Final root focused/typecheck/full regression evidence remains required; no post-inference tuning occurred.

### P1/P2 — Native/common metadata and independent math semantics need final parity verification (IN PROGRESS)

At initial review, the independent arithmetic verifier did not support actual native `relative_strength`, `rank`, or `share`; valid executions could fail audit. Its metadata resolver also differed from native extraction for query-derived entity, ancestor numeric year/quarter, bool consolidated scope, price-only capture-time fallback, and metric naming. These were reported to the benchmark owner, who is adding independent Decimal vector/scalar checks and metadata fixtures.

Common extraction had additional differences: no actual SDK query symbol/ticker fallback, no native entity index/country/series/sector metadata, bool `consolidated` became string `True` rather than `consolidated`. Native extraction did not support the common calculator's explicit `periods[]` ↔ `rows[].values[]` relation or exact JSON-pointer unit keys. Owners have been notified. These need either shared documented semantics with independently implemented verification, or explicit capability limitations. Do not claim that sharing the expression engine alone proves equivalent source extraction.

All-missing financial periods must reject. All-missing statement scope/entity must not be described as verified. Native owner added structured `alignment_verification`; final common/native parity fixtures and mutation checks are pending at this review checkpoint.

## Checks and favorable findings

- Independently ran provider/compute/calculator/Decimal targeted tests: **75 passed in 14.68s**. This ran before later owner edits. The actual-process failure above demonstrates why these passes alone do not certify engineering readiness.
- Root supplied actual OT SDK local four-step wire proof (source → native calculate → read_result → final), including preserved full financial JSON Schema constraints. That proof covers OT native utilities, not the common calculator inside the isolated MCP child.
- Both OT arms explicitly use financial-grounded tools, while only candidate uses finance prompt/policy. Baseline therefore means the same upgraded arithmetic runtime and stock prompt with finance policy off; it is not untouched default stock CLI behavior.
- Tool inventory is explicitly limited to common snapshot MCP and OT calculate/compute/read_result. The gateway retains strict schema-constraint checking. Native code now preserves raw authoritative financial MCP schemas instead of silently broadening finite anyOf/required-only oneOf/not/closed-object constraints. Actual OC/DSH current-binary wire validation is required and is being exercised by the new local fixture.
- Gateway ownership is common across arms, initial+2 eligible transport retries, immutable request payloads, total upstream-attempt cap, reservations distinct from observed usage, terminal 424 delivery and failed-payload redelivery guard. Daily quota/auth/bad input/model mismatch do not become quality retries. Final real binary proof is necessary to complement direct gateway fixtures.
- User-authorized Super route amendment is explicit: requested public VL endpoint, exact returned private response ID, checkpoint UNVERIFIED. The original exact-identity canary failure remains unchanged. Do not describe the amendment as checkpoint verification or pool the two model cohorts.
- Both co-primary endpoints require correct financial content/provenance, actual source receipts, timely status OK; raw-format validity is separate. Pilot/main use scheduled denominators and separate models. Pilot gate requires registered margins over each control; main awaits an exact-manifest manual review and user-delivered pilot report attestation. New smoke/manual review gate is still being implemented.
- Financial parser rejects duplicate keys, nonfinite values, multiple objects and surrounding prose. Sole JSON fence tolerance belongs only to the registered financial parser, not raw contract validity.
- Control code provides PAUSE, explicit continuation, PID/start-time/cmdline-verified hard stop, terminal interrupted recovery and no whole-trial quality retry. Final actual-process supervisor/driver resume and interrupted-artifact audit tests remain necessary; unguarded trailing JSONL fragments must not be silently discarded or retried.

## Preservation

Independent read-only preservation check: **PASS, 16,316 stored entries**. This covers inherited v3/v4 native source scopes, v42/v44 code/tasks/tests/protocol, inherited v42 results and v43 source/log scopes, and all 8,132 protected v44 result entries with byte/hash/mtime identity. Twelve directory symlinks were checked separately with lstat/readlink. See [independent-preservation-review.json](independent-preservation-review.json).

Production's intentional upstream merge was not incorrectly compared against the old pre-merge HEAD. Legacy v3's known shared dependency update is excluded and disclosed; this is not permission to reuse its old approval with changed dependencies.

## Remaining approval conditions

1. Resolve the common calculator isolated-HOME runtime blocker and narrative-claim acceptance.
2. Finish and freeze source extraction/unit/period/scope/derived-chain semantics; independently re-run mutation fixtures and actual common calculation through all four native adapters, with retries/captures/usage inspected.
3. Root full benchmark suite, corpus/oracle/adversarial checks, native focused/typecheck, actual CLI pause/hard-stop/crash/completed-resume and instrumentation audit checks must cover the final hashes. Preserve the original full-native performance failure and isolated repeat evidence; do not modify thresholds.
4. Pin engineering approval, both admission contracts, all sources/configs/tasks/grader/auditor/protocol/runtime dependencies and schedules before financial smoke. No financial inference is authorized by this interim review.
5. Report financial metrics and superiority only after actual scheduled smoke/pilot/main as applicable. Current engineering checks establish no advantage over OpenCode or DSH.

## Follow-up before memory-stratum implementation

The common calculator locator fix is now present: the controller supplies `BENCH_BUN_BIN`, both registered configs specify `/home/doanlong/.bun/bin/bun`, and the MCP subprocess uses the absolute locator rather than its isolated HOME. Independent fresh-Python-process clean-HOME calculation passed (24000 đồng/cổ phiếu), with no `.bun` installation in that HOME and zero external model calls: [independent-clean-home-calculator.json](independent-clean-home-calculator.json). The configured binary matches the frozen inventory's actual Bun path/hash in this environment; a future different configured path must also be fingerprinted rather than assumed. Root is running the actual four-arm wire rerun; the original all-arm failure remains retained. This closes the direct clean-HOME regression but does not replace that wire proof.

The all-arm manual adjudication mechanism is now implemented in `v45_review.py`: required decision coverage is exactly the union of automatic strict/financial wins across all arms; source/entity/period/unit/scope/arithmetic/narrative checks and evidence notes are mandatory; reviewer/independence, manifest, all trial artifacts and automatic audit hashes are bound. Decisions can only remove automatic wins. Gates stop before advancement until review is complete, and automatic rows remain unchanged. This is the registered treatment of unsupported narrative claims; neither a receipt-only score nor typed-number scanning certifies narrative correctness. No financial run has been started.

Independent math/execution rerun: **66 passed, 1 failed in45.02s**. The remaining failure was the actual subprocess graceful-pause fixture waiting10s for its first durable call boundary; the process had not created its output directory and its log was empty when the fixture killed it. Evidence remains under `/tmp/pytest-of-doanlong/pytest-46/test_real_subprocess_graceful_0/`. This is an unresolved startup/timing failure at this checkpoint, not a permission to relabel the control test PASS. The owner was notified to diagnose/recheck the unchanged behavior when source/load is stable. Final approval remains BLOCKED pending that verification, actual four-arm wire success and new memory protocol/runner checks.

The additional memory scope is reviewed separately in [financial-memory-v45/INDEPENDENT-CHECK.md](../financial-memory-v45/INDEPENDENT-CHECK.md). Existing original memory-task oracles passed10/10 independently; this is not memory effectiveness evidence.

## 2026-11-09 latest-base integration checkpoint

The clean-HOME locator and actual common-calculator integration blocker is resolved by `all-native-common-wire-9665393e/proof.json`: all4 actual native adapters pass on the latest study base with explicit workspace Bun1.4.4/SHA and only local scripted HTTP. Historical failed proofs remain unchanged. The old global-Bun helper proof is not reused as certification of the new base. The independent native-utility helper now explicitly pins Bun1.4.4, asserts the actual command binary, and preserves its prior source as `native/verify-headless-wire.pre-bun144.py`; root must execute this bounded four-response fixture before final qualification.

Current independent occurrence checks pass6/6, including identical SDK IDs and arguments across fresh sessions and successive assistant steps. Native and local-rejection reconciliation now requires exact session/turn/provider generation stamps and fails ambiguous candidates; raw response hashes are checked. Latest math/memory/controller checks pass54/54. All-arm hash-bound manual review remains mandatory before qualifying reported financial wins; this is no automatic assertion that narrative fabrication is absent.

The new native full-suite result is1881PASS/2SKIP/6FAIL/1ERROR, retained. Whole-file candidate TUI113PASS/1FAIL versus untouched latest-product baseline108PASS/6FAIL includes a shared streaming failure. This is not an all-green production qualification or performance-superiority result. Scope any eventual approval to the validated benchmark headless path. Memory continuation/control actual proofs and final frozen-source approval remain pending; see the separate memory independent check.

### Subsequent actual integration closure

Independent inspection of `native/headless-wire-31e832f2/proof.json` verifies latest-base pinned-Bun native source→calculate→read_result→final, four local responses, result24000, and native calculate provider index2 joined to captured generation occurrence1:0:0. `native-wire-f78d427d/proof.json` verifies actual OC same-session continuation using the installed **`session.message.list`** operation: persisted history has4messages, adopted turn2 input contains the prior assistant nonce and original source receipt, native session ID remains unchanged, and completed resume adds0calls. Earlier guessed operation failures remain preserved; the previous proposed `v2.session.messages` was also not the installed operation. This bounded OC subset complements the other7 healthy cases in49bb3d66; it is not represented as a fresh single-run8/8 matrix. Evidence/source hashes are bound in `financial-memory-v45/independent-latest-integration-check.json`. Final suite/control/source-pin gates remain outstanding.

### Separate installation safety approval

`native/INDEPENDENT-INSTALL-APPROVAL.json` approves only exact21 reviewed product paths under dry-run SHA02db928a9faea2c30e27937a80e60e2b0502ecf0d06e3c79eb49a5225d625ea1. All current before/after hashes and1136 unlisted inventory entries were independently checked. Installer source is hash-bound; internal symlink ancestors are rejected (independent synthetic mutation), staged bytes/source/destination hashes are checked before replace, and backups/partial-failure receipts are preserved. This is not financial inference approval, automatic promotion, or whole-production UI certification. No production files were written by the reviewer.

### Post-install runtime/source parity review

Root's guarded installation is complete. Independent recheck confirms all21 installed source hashes equal the approved candidate manifest and package.json/bun.lock plus actual critical AJV/AI SDK/OpenAI-compatible SDK/Zod files are byte-identical between product and study. AJV is8.17.1. Reviewed parity receipts report234packages and all15011runtime files equal, with1136unlisted inventory entries unchanged. No whole-production all-tests-green claim follows. Legacy v3 node_modules is a symlink to current production dependencies: its effective rerun environment has migrated even though its stored trial/capture bytes are preserved. Historical identical-rerun-environment claims are expressly excluded. Full-host benchmark tests and final exact inference pin remain pending.

### Final host-test fixture review

The full host suite initially produced510PASS/27FAIL; the original log remains retained. Independent source review of seven test migrations finds preserved assertions and no new skip/xfail or production/grader quality rescue. Historical v43/v44 fixtures use immutable registered inputs and fresh-interpreter original CLI interception. Current tests supply required scoring metadata/common-calculator inventory and reach unit dimensions without an unrelated unused binding. Original archive values/hashes and registered migration/payload hashes remain required. The temporary alternative stdio bridge was removed: the final test retains actual SDK stdio_client and ClientSession, original three-call/evidence assertions, and a25second request deadline. Cleanup separately captures only its real SDK child and bounds EOF/terminate/kill; this does not certify natural unassisted SDK shutdown. Exact reviewed hashes/provenance/limitations are in `financial-memory-v45/INDEPENDENT-FIXTURE-MIGRATION-REVIEW.json`. Final full-suite pass and exact source pin remain required before inference approval.

## Final exact engineering approval — 2026-11-09

The final host suite passes537/537. Independent recomputation matches both current stateless freeze states: Super516aceede2b546b5ba6d8f178e70b265eebc3012d2780ea826d09c984f9406ba; DeepSeek08cdd1216e2408ab47696ca2139a2968a2104db4fee8370db1ad11f7f545e764. Final MINIpreflight5 SHA4439ae833534f1e685c9bd0f67f6780fb4dfda9779d7de4e8b94dd2338e54bf6 matches current source/protocol/admissions and the same actual runtime inventory. Source/metric/grader/protocol/corpus/runtime changes after pin are prohibited; failed and superseded plans remain retained.

Distinct FINAL-INDEPENDENT-ENGINEERING-APPROVAL-20261109.json artifacts authorize only the preregistered headless paths and bounded24episode MINI. Stateless main remains conditional on its own model's pilot gates, independent all-arm financial review and delivered pilot report. Memory MAIN and holdout are not authorized by the MINI. Super checkpoint remains UNVERIFIED; common memory sampling differs from stateless DeepSeek. No financial superiority, natural unassisted SDK shutdown, or100%whole-production/UI correctness is asserted. No external model calls were made by this reviewer.
