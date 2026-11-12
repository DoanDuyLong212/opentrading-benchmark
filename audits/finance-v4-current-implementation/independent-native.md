# Independent review: current OpenTrading native base and v4.1 port

Review date: 2026-11-06 (Asia/Bangkok). Scope: read-only original application and isolated `experiments/finance-v4-current-study/experiments/opentrading-runtime`; no provider inference or original-source edits.

**Gate status: QUALIFIED PASS for the preregistered headless smoke gate.** Source findings and independent focused checks are closed. The full suite has one preserved TUI timing failure followed by a clean focused TUI rerun; this is not an all-green full-suite claim. The archived old-base 483-test result is not certification for this base. The common MCP/benchmark review and preflight remain separate gates.

## Independently verified current base

- Original HEAD is `b6e354e76894887e31c33b1f13b44eadc02fad7e`, package version 0.3.1, with 212 TypeScript/TSX source files. `git status --short` shows no tracked edits; only untracked documentation/research. No merge conflict markers found under source/prompts.
- Native `RunOptions.promptDir`, bounded prompt-directory validation, `now`, and `clockPolicy` remain integrated. Snapshot clock policy suppresses the live session reminder and still computes a real clock snapshot from the supplied historical date. No fabricated `prevClock` is needed.
- Upstream now has a shared whole-turn step counter across native recovery runs, a stop gate with at most two recovery nudges, length continuation, empty/promise/malformed/fragment/unfetched checks, failure streak nudges, source-failure notices and a remote MCP connection circuit breaker. These must remain in both baseline and candidate.
- MCP breaker counts connection failures; successful server responses reset it even if a tool reports a data/error result. Writes are not replayed by transport retries. The candidate's output-contract validation must remain after completed execution and outside the transport retry catch.
- Upstream tool wrapper now handles abort while waiting for a lock, source-envelope notices and provenance metadata. The v4 port must not overwrite the wrapper with the older implementation.
- NVIDIA provider selection still goes through the native catalog/provider path. The study adapter must preserve the actual native main loop and public API rather than emulate a subagent or answer generator.

## Dependency compatibility finding

Original package declarations are newer than the existing installed tree: `ai` declares 7.0.159 but resolves 7.0.137; MCP SDK declares 1.32.2 but resolves 1.32.1; actual provider-utils is 5.0.58; actual Ajv is 8.20.0. This does not prove API incompatibility, but source commit/package lock alone cannot identify the executed runtime. The study must pin actual resolved versions and pass typecheck/native integration on those exact dependencies. Do not install through a reused node_modules symlink or describe the archived old-base suite as evidence for this base.

## Base source SHA-256

| File | SHA-256 |
| --- | --- |
| package.json | 8ddf90966a79375fa9ed2e4a78f52baacc6db8d83dec063f418ab4462df566ef |
| bun.lock | 8dcd6c84f277bf2e615226406d5eec76fac03aa8c00a05ad8d3bc0bc8beb042f |
| src/core/agent.ts | 2e0608ddb3ee49b425311faa394c95078efd7f44265ebb839b525b0793a13410 |
| src/core/prompt/assemble.ts | a390d852c7afa696e4aa48cb9adb231922eae71847fce86ece78382c385a3b7f |
| src/core/mcp/manager.ts | d551ea0b53a75f7cdf13a77a06b0ed81cb2f1c67c1c67c01069b8ebdd777c546 |
| src/core/loop/stop-gate.ts | fdec31c97ec429a9f484a448b0b33e166c7df220f3e1bca4dd166c3ab03272f8 |
| src/core/loop/failures.ts | 78550ef90892687257f8ddb0610e1f4af373194e1a75259888ca64cb27a3078a |
| src/core/providers.ts | 6018f2591e0a34e5960966f1d090fdd59b48e4cb3e20b80b1680b3d28d51d6e6 |

## Required port checks

Candidate OFF must retain native schema sanitization, stop-gate behavior, source notices, provenance and recovery accounting. Candidate ON must preserve raw schema constraints without coercion, reject unsupported schemas, bound read-only corrections, protect declared entities/currencies/financial periods, freeze actual successful provenance and validate only the public output contract. No hidden field mapping or gold/task-ID rescue is permitted. Machine-output buffering must emit only the final selected JSON, while actual invalid/rejected calls remain in audit history. All extra steps and usage must use the shared budget and cancellation signal.

Public JSON-example validation remains a limited contract parser, not a universal natural-language validator. Financial correctness, arithmetic and evidence coverage for every operand remain independently graded. Source/code review cannot establish that OT beats the other harnesses. Forecasts and assertions about an absolute small-model ceiling in opencode-review.md section 10 are not outcomes of this new experiment.

## Independent port findings and closure

Three integration defects were found before inference and closed in the reviewed implementation:

1. **Length continuation checked only the suffix.** A valid JSON object split across the upstream length recovery was rejected as invalid JSON. The candidate now validates the authoritative joined assistant message; the native two-step test proves one valid object, two requests and complete usage.
2. **Length state contaminated later finance correction.** After a completed length recovery produced a wrong-type object, finance correction inherited `continuing = true` and could join the rejected object with the corrected object. A dedicated finance-rescue flag now distinguishes those paths. The native three-request test proves only the final corrected object is emitted and all three requests contribute usage.
3. **Study wrapper concatenated discarded native finals.** The baseline could stream a promise/fragment, discard it through its native stop gate and return a clean response without another tool-start. The old adapter accumulated both strings, unfairly hurting baseline against the buffered candidate. The common OT adapter now selects text only from the last assistant message in an actual completed native `done` event, without JSON extraction, earlier-answer fallback or financial rewriting. All original events remain in the audit log. The helper is `tools/runners/native_final.ts`.

The original old-base findings (unsupported schema, temporal/entity scope, immutability, nullable fields, canonical public source and step accounting) remain closed in the current port. Unsupported root contracts fail closed; unknown schema vocabulary throws before execution; Ajv coercion/default/removal are disabled. Financial selectors are protected when correcting a failed intent, while model-authored scalar-to-array repairs and read-only retrieval supersets preserving all original targets remain possible.

The finance repair run keeps the declared catalog intact, preserving SDK history compatibility, but native execution admits only one execution of each originally failed eligible read-only tool. An unrelated call produces an explicit correlated local policy rejection and never reaches MCP. This is tested with actual SDK requests rather than a fabricated ledger entry.

## Independent focused verification

Commands run by this reviewer in the new isolated runtime on the current source/dependencies, with no model inference:

- `bun test test/finance-policy.test.ts test/agent.test.ts --test-name-pattern finance`: **14 pass, 0 fail**, 71 assertions; 92 unrelated tests filtered. Covers raw-schema local rejection and next-wire identity, correction, cancellation, exact step limits, source aliases, buffering, length interactions and the actual NVIDIA-compatible native provider route.
- `bun test test/finance-policy.test.ts`: **13 pass, 0 fail**, 46 assertions. Covers no coercion/default/removal, nested constraints, bounded attempts, side effects/auth/no-data exclusion, immutable public provenance, baseline behavior, scalar/list/superset preservation, source/nullability and unsupported schema/root contracts.

These are 27 distinct focused tests, all passing. They are local scripted integration/unit tests, not quality measurements.

Independently resolved from the **own** study dependency tree: `ai 7.0.159`, provider-utils `5.0.72`, MCP SDK `1.32.2`, `zod 4.6.7`, `ajv 8.20.0`. Actual installed types support `jsonSchema(..., { validate })` and `experimental_repairToolCall` (deprecated but supported alias). The new direct Ajv dependency belongs to the isolated package/lock; production's older dependency installation is untouched.

Byte comparisons against production prove preservation of `src/core/tools/wrap.ts`, `src/core/providers.ts`, `src/core/mcp/breaker.ts`, `src/core/loop/stop-gate.ts`, `src/core/loop/failures.ts` and `src/core/prompt/assemble.ts`. Thus the abort-aware lock, source notices/provenance, provider routing, circuit breaker, stop gate and snapshot/prompt hooks were retained rather than replaced by old-base implementations.

Reviewed candidate SHA-256:

| File | SHA-256 |
| --- | --- |
| src/core/agent.ts | e3a80ec7ca3cefdec47f622ce60c2778526f61fc0525b9fda4dd39e6fbeb68ca |
| src/core/finance-policy.ts | 200eb7427922d1b72cdc11794b68d85bc7a8f07322c166e3f2f22927bd910814 |
| src/core/mcp/convert.ts | fa8e4f101c7e5f46c2859714d2ab63b1f5fce581fd7e2648da2e4dfa46d1aac1 |
| src/core/mcp/manager.ts | 086f1b92dabc1f65335bd789418242e40e160e12f55ef6809200517ed0d0614b |
| src/core/tools/registry.ts | c5ea67e0a40f60e5186379049a3dccc0beaae0b3abe2bdac53d2d30d112571ef |
| package.json | 93380eeec80a701bfed071458dd7bc246dd1c76c16d6f45860724b3efcdd2d90 |
| bun.lock | 8a68c24ea5dd1239f244216766bd79840534ded415c5ae67e55278fc2c3ff5a9 |

## Final verification and qualified gate decision

The implementation owner ran `bun --no-env-file test` with a clean HOME and provider-key environment variables removed: **1069 pass, 2 skip, 1 fail**, 10,867 assertions, 1072 tests across 101 files, exit 1, 164.27 seconds of command time. The preserved failure is a TUI reply-streaming/render-wait assertion. No core/finance test failed. This reviewer independently read the actual final log and run receipt; the full suite is **not** described as green.

The authorized investigation reran the entire `test/tui.test.tsx` file on unchanged source/dependencies: **113 pass, 0 fail**, 564 assertions, exit 0, 68.02 seconds. The formerly failing case passed. This is evidence of a non-reproduced render-timing failure, not conclusive proof of an upstream flake; a pristine-base control was not run. Native typecheck also passed on the own locked dependency tree (implementation-owner evidence). Headless-critical focused coverage comprises the owner's 151 tests and this reviewer's 27 distinct checks; these are overlapping verification passes, not 178 distinct tests.

Log SHA-256:

- `test-artifacts/full-native-tests.log`: `09f1b6fbe88d596cc23d7b257f2ccc03b6fc05466dcd6ed6b77bd6905c9c625b`.
- `test-artifacts/tui-focused-rerun.log`: `0921aba42198826473be903bfd759ad66ef6ef24b3d6bbad65920db14e1cf884`.

Post-test independent hashing confirms the reviewed `agent.ts`, `finance-policy.ts` and `tools/registry.ts` hashes remain exactly those listed above. No native source changed to obtain the TUI rerun pass. All failures and logs are retained.

Actual native provider capture mocks were inspected independently. The current NVIDIA-compatible route produced three requests to `nvidia/nemotron-3.5-bolt-e4b`; each retained the same declared one-tool catalog, with tool choice auto/auto/none and no reasoning fields. A separate bounded-correction mock retained the same two-tool catalog for four requests while rejecting an unrelated execution locally. These are actual installed-SDK requests with stubbed fetch, explicitly not NVIDIA inference or financial-quality evidence. The common gateway must independently prove its declared sampling/cap rewrites and raw/effective binding.

Given the closed source findings, passing direct headless SDK integration, preserved upstream safeguards, passing typecheck and unchanged-source passing TUI investigation, this reviewer accepts a **qualified operational PASS for headless smoke**. The unresolved full-suite rendering sensitivity is disclosed rather than erased. This does not authorize original-source rollout, establish financial correctness, or claim superiority over OpenCode/DSH.
