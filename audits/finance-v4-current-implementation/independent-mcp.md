# Independent current-study MCP and benchmark review

Date: 2026-11-06, Asia/Bangkok. Scope: `experiments/finance-v4-current-study`, common C1 replay contract, native adapters, gateway admission/captures, provenance validation, frozen grader sensitivity and runtime identity. No model/provider inference; no original OT/MCP source edits; no repeated full benchmark suite by this reviewer.

**Gate status: PASS for the reviewed common MCP/benchmark implementation and narrow offline checks.** The coordinator must also require its full benchmark regression, native qualified gate, offline preflight, frozen identity and live smoke certificate. This report does not certify production deployment or financial superiority.

## Findings and closures before inference

- **Runtime fingerprint omitted TSX (P2).** The native source inventory previously filtered `.ts`/`.json` only, leaving the upgraded 212-file TypeScript/TSX base incompletely identified. The implementation now includes `.tsx`; an adversarial test changes TSX bytes and proves identity changes. No runtime behavior was changed by this fix.
- **Completed native status could hide failure (P1, coordinator finding).** `native_result_status` now requires a completed native `done` outcome, zero exit code and no error event for `status=ok`. Failed, aborted, timed-out, missing-completion and nonzero-exit cases remain failures. Native `unanswered` and `recoveries` metadata are retained; their presence is not erased merely because a process exits successfully. Seven parametrized adversarial cases pass.
- **Dropped native output concatenation (P1, native review finding).** The common OT adapter uses the actual completed native last assistant message. It does not normalize JSON, search earlier messages, read files/tool inputs, substitute values or salvage evidence. Invalid prose/JSON remains invalid; failed runs keep their partial output and failure status. Both OT conditions use the same helper. The original full event history remains logged.
- **Parallel duplicate correction proof edge (P2).** A second identical allowed call may be rejected locally in the same SDK batch, before the first execution appears in a later model request. The checker now requires the exact generated IDs in that batch, same tool name, matching actual native input, a preceding native tool-start and a corresponding actual MCP ledger row. Missing ledger proof fails. This does not waive the global generated-call count reconciliation or later model-visible error proof. Server call IDs and SDK call IDs are distinct namespaces; this is corroborated cross-layer execution proof, not a claim that those IDs are identical.

Previously identified C1-vs-validator mismatch and copied diagnostic-model admission are closed in this current study: the server validates the same C1 schema it advertises, while both the driver and direct gateway reject non-Bolt models before credentials/network access.

## Independent corpus and source verification

An independent pure-offline traversal verified:

| Check | Result |
| --- | --- |
| Original payload/request-contract/gold files compared byte-for-byte | 589, zero mismatches |
| Task environments loaded | 277 |
| Recorded requests valid under C1 and selecting their original envelope | 402/402 |
| Generated task tool definitions preserving C1 schema/output/annotations/meta and original description prefix | 333/333 |
| Source module hashes matching current local MCP source | 14/14 |

The current local MCP HEAD remains `ed934aebd0ee6f9271512150a9bb3971089d7460`, matching the frozen source identity. C1 contains 17 task tools. Catalog file SHA-256 is `07e1a7363b31cfa053719933f777c5b5991bb5d65ec5698b7d48f567564684c3`; catalog tool digest is `18e79cba88470f0981ad035b1729420b798f3e68d2ed2396a21113ef91df6f35`. The copied native application is the new 0.3.1 base, not the archived older v4 runtime.

Strict replay matching/default equivalence remains separate from schema validity: a valid-schema unrecorded request yields `not_recorded`; a C1-invalid request yields `invalid_request`; no unknown request falls back to financial data. Rejections have `isError=true`, no financial evidence/data/availability and an append-only authoritative ledger entry. Successful evidence is joined through actual seven-field receipts. The outputSchema remains the source's generic object contract; no typed financial schema was invented or claimed to have shipped to production.

## Wire, model and identity checks

- Driver config and gateway both admit only `nvidia/nvidia/nemotron-3.5-bolt-e4b` for smoke/pilot. Diagnostic Flash admission is disabled in this isolated study; no other provider/model is used by these tests.
- Actual installed current-SDK NVIDIA-compatible request captures, generated under a fetch stub, pass through the real gateway with upstream HTTP stubbed. Native messages/tools remain unchanged in effective requests; only declared sampling/cap rewrites apply: temperature 0, top-p 1, output cap 2048. Effort/reasoning fields are absent. These are contract tests, not inference or financial evidence.
- Bounded native correction retains the full declared tool catalog; local execution restricts calls to eligible failed read-only tools. Local schema/policy rejections require a unique model-generated call ID, actual rejected arguments, public schema/intent/phase proof, actual model-visible tool error and no financial evidence. They are not relabeled MCP executions. Generated calls reconcile to authoritative MCP calls plus these proved local rejections.
- Current source, TSX, package/lock, actual own installed dependencies, prompts, calendar, C1 catalog, protocol amendment/dependency plans, config and task/grader files enter identity/freeze. Actual own dependencies are documented in the native review. Baseline prompt files are sourced from current production; no current production source/dependency writes occur.
- Native flags survive adapter and trial serialization. Primary success still requires strict contract, actual evidence grounding, timely execution and `status=ok`. The same answer is also graded with the exact frozen-v3 grader and persisted separately, preventing a common grader correction from being misrepresented as native OT improvement.
- Snapshot as-of is common context; only OT's native clock is pinned. Other native clocks remain observed in captures. No byte-identical SDK-schema or clock parity claim is made.

## Independent targeted tests

In the current study workspace:

`python3 -m pytest tools/tests/test_v4_contract.py tools/tests/test_current_wire_gateway.py -q`

**47 passed in 48.17s**, no model calls. These cover C1 boundaries/error classes, original request validity, temporal-negation sensitivity, public source/catalog metadata, direct driver/gateway model denial, actual SDK-to-gateway captures, local error/intent binding, native status/final-output handling and TSX identity.

The two narrow final edge tests were additionally rerun explicitly:

`python3 -m pytest tools/tests/test_v4_contract.py -q -k 'parallel_duplicate_guard or native_source_inventory'`

**2 passed, 42 deselected in 13.77s**. These are a repeated subset of the 47, not two additional distinct tests. No broad test-suite duplication was performed.

No remaining blocking finding was identified in this review. The full benchmark regression and live operational smoke remain coordinator-owned. Every future timeout/DNF must stay in the fixed 44-per-condition pilot denominator. The experiment remains development/exploratory with a combined candidate; no result here proves OT has already beaten OpenCode or DSH.
