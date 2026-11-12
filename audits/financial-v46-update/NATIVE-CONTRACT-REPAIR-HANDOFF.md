# v4.6-update native + primary contract repair handoff

Candidate source only: `/home/doanlong/extra/benchmark/experiments/finance-v46-update-study`. Original v4.6/v4.5 runtime, tasks, outcomes and approvals unchanged. No NVIDIA/model inference by this worker.

## Repairs implemented

1. **Actual native evidence binding.** `src/core/finance-policy.ts::succeeded` previously called `parseResult` on runTool-visible text beginning `[ref rN]`; JSON parse failed and successful source remained a plain ToolResult. Every later seven-field row therefore failed native exact-match. New parser resolves that known anchored prefix only through retained ref owned by the exact registered tool and SDK call, verifies raw SHA256, reads intact raw source, then retains immutable parsed result. Unprefixed JSON/empty-source envelopes remain supported. Fresh policy, altered receipt fields and mismatched SDK owner fail closed; no fuzzy receipt matching.
2. **Schema parity.** Shared `validateAuthoritativeInput` uses same strict Ajv settings/authoritative MCP JSON Schema for B0 and B1 in grounded benchmark mode. Invalid compile returns explicit invalid_tool_schema; actual constraints/additionalProperties/oneOf/finite queries preserved. Finance safety/repair gates still B1 treatment. B0 has no FinancePolicyState or policy guard, only ordinary common schema validation.
3. **Original generation audit.** Finance options accept controller-supplied auditContext. Before/validation/local-rejection capture immutable `origin_provider_request_index`, `origin_sdk_call_id`, optional `origin_memory_session`, `origin_memory_turn`, `origin_native_session_id`. Native notices re-emitted in later bounded recovery carry explicit `replay_of` original tuple. B0 genuine SDK argument rejection emits one `financial_local_rejection` with same origin fields; `invalid_tool_input` only, never a B1 policy-guard event. Current provider_request_index remains separate emission capture metadata.
4. **Dimensionless unit semantics.** Native calculator recognizes ratio/tỷ lệ/dimensionless/lần with factor1 and no currency dimensions; % still factor0.01. Source-unit override remains rejected; error now explains source vs conversion direction. No automatic inferred per-share dimension and no typed financial-value allowance.
5. **Prospective primary unit normalizer.** Exact dimensionless aliases before broad currency matching. Bare `ty` is exact-only, so `tỷ lệ` cannot canonicalize as tỷđồng. Empty unit remains empty/invalid where required. Gold amounts, tolerance1e-6, frozen v3/v4.1 implementations unchanged.
6. **Generic refusal availability predicates.** Deterministic bounded negative-data/period/report predicates VN/English plus negation/contradiction/rejected-query guards. A tool error or unsupported query does not establish missing financial data. No observed-string-only rescue and no numeric-null success conflict allowance.
7. **Common public instructions.** All239 financial task instructions prospectively clarify precision1e-6 absent user rounding, explicit dimensionless unit labels, complete true source chain incl requested resolver and canonical no-harness-prefix names. Same text every arm, no golden outputs or case-specific templates. B1 tools/citations prompt adds generic precision/source-ref/publicUUID distinction only.
8. **Task grader families preserved.** 239 financial copies share new primary;15 memory copies retain their existing memory_evidence numeric-namespace exemption as their sole difference. All15 memory instructions untouched. Generator reads primary and appends the same common prospective guidance; embedded historical template stays historical, explicit LEGACY_GRADER_TMPL remains sensitivity artifact.

## Files owned/modified

Native src: `finance-policy.ts`, `agent.ts`, `tools/registry.ts`, `tools/financial-source.ts`, `tools/calculate/units.ts`.
Native runners: `tools/runners/ot_headless.ts`, `ot_memory_headless.ts`.
Prompt: finance `tools.md`, `citations.md`; stock baseline unchanged.
Primary/corpus: `tools/v45_grader.py`, generator common rules,239financial+15memory task graders,239financial instructions. No gold numerical values or payload edits.
Tests: new `test/finance-v46-update.test.ts`, appended actual B0/B1 SDK regression in `test/agent.test.ts`, new `tools/tests/test_v46_update_contract.py`.

## Verification status (root must finalize exact closed source)

Before final source close: native23PASS (new4+existingfinancialsource19), typecheckPASS; Python26PASS newcontract tests. Final small changes afterward added actual B0/B1 SDK test, intact-rawref SHA/SDK owner requirement + mutation assertion, and restored15memory namespace variants. Do **not** present preliminary passes as qualification of final source. Root runs final typecheck/native/actual loopback wire/fullPython independently.

No source/prompt/corpus/grader edits after final CLOSE message to root unless review reveals a defect; documentation/proofs may be added. Root controls freeze, approvals and inference. Any old answers evaluated under new rubric are diagnostic, never overwrite old scores or mix into prospective metrics. v4.7 architecture improvements remain proposal only awaiting user approval.

## Required terminal-output correction after root review

Native previously emitted financial_contract_invalid then still accepted that assistant response via general stop-gate. Root authorized correction before freeze: terminal invalid contract after existing bounded repair now records unchanged raw_final in telemetry, marks unanswered, drops invalid final text from accepted history, and closes with a nonfinancial explanatory marker. No third model/quality retry. This applies to native source, not only Python benchmark status. Actual SDK tests covering repaired-valid final, exhausted-invalid final and common B0/B1 schema rejection passed6/6. Root verifies remaining final exactsource checks.

## SDK occurrence identity correction (independent-review blocker resolved)

Finance callAudit/localRejections and active executions are keyed by the explicit origin tuple (provider request index, real SDK call ID, memory session/turn, native session), not bare SDK ID. All prior occurrences remain separate; true repeated notices retain replay_of original identity. ToolRegistry captures the before-reservation origin and forwards it through async execution completion, so later callback state cannot restamp an earlier execution. The emitter always uses the real origin_sdk_call_id, never the internal map key. Non-instrumented callers retain their prior SDK-key convenience behavior. Actual SDK fixture now generates same-sdk twice in distinct model requests with different args, then bounded format repair; assertions prove two original notices and separate truthful replays.

Final affected exact-source verification:14 native/actual SDK tests PASS,26 financial contract tests PASS,typecheck exit0. `NATIVE-OCCURRENCE-VERIFICATION.json` binds files/hashes and proof logs. Root still owns independent audit/fullsuite/pre-inference approval. Primary-copy test classifies memory only by authoritative `environment/turns.json`, preserving all15 memory grader namespace variants.
