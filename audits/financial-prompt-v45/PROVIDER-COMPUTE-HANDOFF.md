# v4.5 provider and common arithmetic implementation handoff

2026-11-08. All implementation belongs to `experiments/finance-v45-study`; no frozen v4.4 source/result or production repository was edited. Root launched the approved standalone synthetic canary. This worker performed zero NVIDIA inference and no financial smoke/pilot/main launch.

## Implemented

- `tools/runners/provider.py`: user-authorized model IDs only, current-study admission receipt required, no Bolt admission. Exact response identity is still mandatory; Super remains blocked on its private response ID pending root/user policy decision. Gateway records native/effective request captures and redacted raw responses, request/model metadata, finish reasons, observed usage, durations and origins. Durable before-dispatch/response event records make interrupted in-flight requests visible.
- One common transport-retry owner: initial + at most two retries, 4/8 s and Retry-After up to60 s, within unchanged overall trial deadline and total24 upstream attempt cap. Eligible upstream statuses429/500/502/503/504 or pre-output transport timeout. Daily-quota/auth/badrequest/local policy/metadata/format/quality failures do not retry. Partial model response bytes do not retry. First transport-success result is used, never chosen by quality.
- All failures are terminal to the native SDK through typed HTTP424 Failed Dependency, **not authentication403**. Original upstream/policy status, typed origin and raw upstream response remain in the ledger. Exact failed-payload redelivery is blocked by fingerprint, preventing another native retry layer from producing upstream attempts. Fresh semantically changed agent requests are new logical requests and share remaining caps; they are not quality retries owned by this gateway.
- Default v45 resource profile: output8192, request240 s, trial900 s, total24 upstream attempts, protocol-token cap3,600,000. Failed unknown-usage attempt reservation1,056,768 = published maximum combined context1,048,576 + output8192. Every upcoming request reserves the context+output upper policy bound before dispatch, then releases to measured usage when known. Failed reservations are separate `token_reservation` fields, **never fabricated measured usage**. Known token usage above registered context+output is fatal `observed_usage_exceeds_registered_context_bound`; supervisor must stop cohort. Profile bound is an operational token reservation, not measured charge or monetary forecast. Root verified NVIDIA cards; hosted effective window may be smaller.
- Explicit native wire allowlist only `calculate`, `compute`, `read_result`, definitions supplied by actual native schema exporter. Gateway compares their schema constraints and verifies complete MCP inventory separately. It does not enable file/shell/web/delegation tools.
- `tools/analytics_compute.py`: fully anchored nonempty numeric-leaf pointer regex; original source receipts retained. Decimal40 sum/mean/growth/margin/ratio/scale/absolute_difference/relative_difference_pct; explicit source unit/period/entity/scope guards and bounded actual-data selector hints. VNDbn, VNDk and price/currency units are distinct; scale may not silently remove per-share dimension. Ratio across entities requires explicit same-metric cross_entity policy. No task IDs/golds are read.
- `tools/analytics_calculate.py`: model arguments contain source `{name,call_id,path}` or prior `{name,derived_id}`, never typed financial values. Resolves immutable session sources and flattened original evidence, checks entity/period/scope alignment, calls the same native safe expression/unit engine through fixed Bun shim, supports arbitrary public formulas/functions, units and chained derived refs. The shim is owned by native worker. Formula constants are the same native allowlist. Subprocess receives no provider/user credentials and has no model call path.
- MCP `analytics_calculate` records a separate deterministic-derivation ledger row, top-level `derived_ref='calc:'+ledger.call_id`, original `source_evidence` only; it never mints a seven-field upstream receipt. All four arms receive this common tool, while product OT additionally retains its own native tools.
- `ready_check.verify_mcp_attempt` now replays common calculator chains using original source rows and prior derived rows, checks namespace/hash/result/proof equality, and preserves rejected calls. Benchmark worker owns the broader auditor/metrics integration and independent Decimal expression verification.

## Model admission findings

Read `CANARY-REVIEW.md`. Sealed standalone canary completed12 cases/24 chat calls; all measured usage present. DeepSeek prefix selector0/2, corrected2/2, no-pattern2/2; exact model identity and corrected/no-pattern loop admission PASS. Super function/continuation6/6 but all12 response IDs `private/nvidia/nemotron-3.5-super-120b-a12b`; original exact-identity admission FAIL, no receipt. No independent official alias attestation found. Do not silently whitelist the private name or mutate original canary artifacts.

## Files and tests

Owned: provider.py, verify_nvidia.py, analytics_compute.py, analytics_calculate.py, MCP calculation function/list/dispatch, ready_check common-derived dispatch only; tests `test_v45_provider_compute.py`, `test_v45_calculate.py`, `test_v45_canary.py`, updated provider/current-wire/v44-compute regression expectations plus historical SDK envelope fixture copied without editing original artifacts.

Canary script/source-pin/manifest/results were frozen before root's execution and have not been edited afterward. The historical v44 SDK envelope test migrates only the model field synthetically and explicitly does **not** certify the new actual native runtime; the native worker owns new actual SDK proof.

Command:

```sh
python3 -m pytest experiments/finance-v45-study/tools/tests/test_v45_provider_compute.py experiments/finance-v45-study/tools/tests/test_v45_calculate.py experiments/finance-v45-study/tools/tests/test_v44_compute.py experiments/finance-v45-study/tools/tests/test_provider_runner.py experiments/finance-v45-study/tools/tests/test_current_wire_gateway.py experiments/finance-v45-study/tools/tests/test_v45_canary.py -q
```

Final log: `/tmp/v45-provider-compute-checks.log` (root must inspect final exit and counts). These are offline stub/real local arithmetic tests, not financial model-quality evidence.

## Remaining root integration before seal

1. Add `grounded-calculation-v45` to wire-contract proof and recognize common calculator in all auditor/tool-coverage/compute metrics. Independent financial arithmetic checks must not rely solely on calling the same engine twice.
2. Supply actual native definitions from pinned exporter before ProviderGateway startup, verify all four arm inventories and no secondary retry layer with actual SDK/binary fixtures.
3. Set exact approved cap/reservation/retry options in driver/config/manifests; stop cohort on observed hard-bound breach, not simply mark one trial failed.
4. Keep unknown/interrupted dispatches and observed usage partial. Resume may not reset budget or restart a quality trial silently; fingerprint guard exists in one live gateway, not as an external durable resume/retry authorization.
5. Super admission identity is blocked under the original protocol. Await root/user decision for a separate versioned route-contract policy; original failure and private identifier must remain visible.
6. Freeze complete source/dependency/native-shim/corpus/metric manifests before any financial smoke. No financial inference has been authorized to this worker.

## Final amendment after explicit user authorization

Superseding operational Super-blocked status above: user approved the requested Super route with returned private ID retained and checkpoint marked UNVERIFIED. Separate `ROUTE-ADMISSION-AMENDMENT.md` and `...Super...-route-v2.json` receipt implement that permission using existing canary only. Original exact-identity FAIL is unchanged. Gateway uses only the exact approved pair, pins original canary hash and exposes checkpoint flag on every row; raw requests/responses retain their real model strings. All other mismatches still reject. Both requested routes are now schedulable under different identity contracts, not claimed verified identical checkpoints.

Common-calculator final metadata hardening: source period cannot use capture date for financial statement leaves; actual SDK year/quarter/period can supply it through internal `_benchmark_request` recorded from real MCP arguments and reconstructed offline from ledger. Capture-time fallback remains only the public price-field whitelist. Query-derived period/scope includes actual query context in lineage. Missing period rejects even when all operands omit it. Cross-entity comparison requires equivalent recorded metrics. Unknown scope/entity fields are explicitly marked in `alignment_verification`, not presented as fully verified. The native worker owns matching native semantics.

`analytics_calculate` now advertises exactly actual native functions: abs, min, max, sqrt, sum, avg, ln, log10, exp. Source versus derived namespaces and source seven-field receipts stay separate.

Local wire investigation found genuine native schema conversion losses (top additionalProperties, finite anyOf, required-only oneOf/not), not harmless annotation differences. The gateway constraint gate was preserved; native worker fixed schema conversion and root is rerunning actual SDK fixtures. Never bypass this gate or reinterpret rejected calls as executed source tools.

Final consolidated offline log: `/tmp/v45-provider-compute-final.log`; earlier pre-amendment 84-test PASS is in `/tmp/v45-provider-compute-checks.log`, new common query/alias tests separately12/12 PASS before consolidation. Root/fresh verifier must inspect the final consolidated log and complete actual native/binary proof and whole benchmark suite before financial inference.

Final consolidated result confirmed: **86 passed, 0 failed in 20.64 s**, exit0. Published log `audits/financial-prompt-v45/provider-compute-tests.log` and source fingerprints `provider-compute-verification.json`. Read-only normalize/admission checks admit DeepSeek exact-identity-v1 and Super user-authorized-route-v2 with UNVERIFIED checkpoint, without any model call. Worker-owned edits are complete for fresh independent review.
