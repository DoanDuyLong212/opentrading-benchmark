# Independent MCP C1/v4 and protocol review

2026-11-05. Read-only source/artifact review; pure offline validation only, no provider/model calls, no edits to original OpenTrading/MCP projects. This review does not certify deployment or the financial correctness of all 174 tools.

## Gate status

**Pending implementation corrections before inference.** The advertised C1 schema and the authoritative replay validator initially disagree. Separately, the coordinator identified a gateway model-admission gap described below. Final verification will be appended, preserving the findings.

### P1 — Advertised C1 constraints were not enforced by the replay validator

At initial review, `experiments/finance-v4-study/tools/mcp_snapshot_server.py:24` loaded legacy `snapshot_tool_schemas.json`; `select_entry` at line69 validated against that legacy schema, while `build_tool_defs` at lines89–100 advertised the new `tool_contracts_v4.json` schema. Direct calls with `{symbol:"HPG",interval:"day"}`, `{symbol:"HPG",columns:["close"]}` and `{symbol:"HPG",days:0}` were invalid under C1 but returned `not_recorded`, rather than `invalid_request`. OT candidate local validation and the common MCP server therefore had different validation semantics.

The strict matcher prevented any fabricated financial result, and all recorded requests remained valid; nevertheless, this would undermine the new error taxonomy and the claim that common C1 domain guards are enforced for every condition. Required correction: validate with the same public C1 inputSchema in the authoritative server, preserving matching/default behavior, and add offline invalid-domain/error-ledger regressions. Recheck all402 recorded requests afterward. Merely calling the package metadata-only would not resolve the inconsistency.

### P1 — Config-only Bolt allowlist did not constrain the gateway entry point

The coordinator identified, and this reviewer independently confirmed, copied diagnostic Flash admission in `experiments/finance-v4-study/tools/runners/provider.py:26–29,47–53`. The driver checked `config.allowed_models`, but `normalize_model` still accepted `deepseek-ai/deepseek-v4.1-flash`. The config being Bolt-only therefore did not establish fail-closed admission across all entry points. Required correction: restrict this new study's gateway to Bolt and preserve the original external diagnostic files; verify both driver and gateway reject other models before credentials/network are used. No unauthorized inference was performed during review.

## Independently verified facts

- The source-local capture contains174 tools, and all174 outputSchemas are generic objects without typed financial properties. The C1 catalog preserves the actual generic outputSchema; it does not invent typed financial outputs. `structuredContent` in the new replay result is consistent with this object contract, and text content carries the same envelope. Production deployment remains explicitly unverified.
- C1 contains17 task tools and52 described fields. Actual source module hashes match catalog identity. Nine pure offline boundary/source tests pass independently; the corpus parity test was implemented independently in memory to avoid rewriting another worker's artifact.
- All277 original task environments load, all402 recorded request parameter objects validate under C1, and all589 existing payload/request-contract/gold files are byte-identical to their v4 copies. Each recorded request selects its original envelope through the unchanged replay matcher.
- Domains are justified by source: history/technical intervals, candle columns, statement frequency/codes, Ichimoku convention and documented valuation labels. Positive candle count rejects the production silent floor without asserting a false365 maximum. Dynamic metrics, FX symbols and distinct index/crypto endpoint columns remain open; defaults are not converted into falsely exhaustive universes. No scalar-to-list coercion or invented aliases/defaults were added.
- The valuation description/search hint correctly describes observed quotients, disclaims fair value/DCF/target bands, and warns about unverified units/bases. This is more truthful than the captured production description; it is not an implementation of a valuation engine.
- All native arms use the same `isolated.prepare`/snapshot executable and common catalog. The only expected difference is native SDK transformation and the declared OT candidate policy, which must be exposed in actual request captures. Successful calls alone receive benchmark evidence; rejected calls keep null source/as_of/response hash and have no fabricated financial payload or evidence.
- `wire_guard_proof.py` is explicitly a real SDK handler with a synthetic stub, not evidence that production was patched. Its synthetic result must remain separate from sourced financial facts.

## Protocol and external-review synthesis

The preregistered v4 protocol selects a combined OT candidate on the same C1 interface, with22 eligible pilot tasks×2 repeats×4 conditions. It keeps44 started outcomes per condition, all failures, fixed model/budgets, frozen-grader sensitivity and no retuning after inference. The promotion guard requires strictly greater primary than OT baseline, no DNF/false-refusal/FP regression, no accepted fabricated evidence and no increase in claimed evidence mismatches; equality cannot promote. No automatic production rollout is authorized by this prototype.

This is a development experiment on already inspected tasks. It cannot isolate a causal effect of description length, estimate generalization, or establish broad superiority. Common MCP/schema/grader changes also mean historicalv3→v4 deltas are not solely an OT effect. The plan states these limits accurately. The metadata-plus-enum/bound change should consistently be described as a common contract package, rather than a description-only ablation.

The external-review synthesis correctly rejects AGY's answered-only ranking denominators and wrong task labels. It also rejects OpenCode's inference that prompt length/model size alone caused the gap and its claim that model-strong selected diagnostic proves parity. Missing native validation and repair are supported by source, while most replay rejections are distinct valid-schema/non-recorded queries; this distinction must remain in the final report. The period-grader negation defect is handled as a versioned common correction plus frozen-grader sensitivity, not a favorable manual score adjustment.

Initial reviewed identities: protocol SHA256 `144a120e218d305a247107f4d1eb33ca5e34f757f2f6fe738a3a70b9d993f3f5`; catalog SHA256 `08767be3f75295f23a6a2b1b5db08fd8f55fb6287e30df6815504f38b1f714d3`; tool digest `18e79cba88470f0981ad035b1729420b798f3e68d2ed2396a21113ef91df6f35`.
