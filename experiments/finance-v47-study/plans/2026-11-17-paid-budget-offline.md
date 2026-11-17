# Paid budget checkpoint 16A (offline)

PR05 adds a run-wide USD allocation for the existing `openrouter_paid` route.
No existing paid configuration has an approved upper-bound/key-limit receipt;
therefore paid inference remains blocked. No key was created or inspected and
no provider call was made. Issue #16 still requires separately authorized live
key evidence and the Phase 6 micro-pilot, at most ten trials in total.

## Admission and immutable settings

`run_benchmark.py --budget-usd <positive finite USD>` is mandatory for paid
inference. Provider options are merged once before authorization and manifest
creation. Settings preserve the effective ordinary and memory request caps,
output/total token caps, provider timeout, per-task whole-trial timeouts, retry
count, route, and immutable dollar policy. Memory episodes use the same run
journal; retry budgets cannot reset the episode request cap. Legacy memory paid
execution is blocked; use the unified driver.

`provider_options.paid_budget_receipt` names an independently reviewed JSON
receipt. `paid_budget_receipt_sha256` in the frozen configuration must match its
exact bytes. There is deliberately no receipt-generation or self-approval CLI.
A hand-written assertion, test fixture or list-price estimate is not provider
evidence. Obtaining and approving real evidence is a later gated operation.

The local receipt format (not an OpenRouter API response schema) requires:

- `status: reviewed_provider_evidence`, UTC `verified_at` and `expires_at`, at
  most 24 hours apart, current when admitting paid work.
- Exact `model`, `route: openrouter_paid`, Chat Completions `endpoint`, and
  `provider_host`. Requests pin `provider.only` and disable fallback.
- `key_fingerprint` (SHA256 of the dedicated credential), `key_response_sha256`,
  `dedicated_key: true`, `byok_disabled: true`, and reviewed `key_limit` fields
  `limit`, `limit_remaining`, `usage`, `limit_reset: null`. Limits must be finite,
  nonnegative, consistent, and cover the allocation. No credential enters a file.
- `attempt_upper_bound_usd`, `context_tokens`, `output_tokens`,
  `bound_scope: all_billable_text_features_no_cache_discount`, `bound_evidence`,
  and `bound_evidence_sha256`. Evidence must cover the exact host/model, full
  input context, maximum output/reasoning, cache writes, fees and all other text
  charges. An uncapped output needs a documented model maximum. Published list
  prices and the historical 2.8x discrepancy are not upper-bound evidence.
- Canonical absolute `allocation_path` in an existing durable managed directory.
  The approved allocation path is shared across processes and bound to one run.
  Reusing its dedicated allocation for another run fails. Operators must preserve
  this path and its lock/checkpoint with the run journal and protect the reviewed
  receipt/configuration. A provider-side dedicated lifetime key limit is the outer
  guard across machines and against external spending; a local file cannot enforce
  money across disconnected copies. Do not approve multiple allocation paths for
  the same dedicated key. This code validates reviewed evidence; it does not
  independently authenticate an offline receipt with OpenRouter.

Text strings and validated text-only content arrays are supported. Media, plugins
and other extra billable features are rejected for paid requests. Paid requests use
a strict field allowlist, support one completion only (`n` omitted or integer 1),
and force `service_tier: default` to avoid inheriting a more expensive account
default. Other tiers, speed/preset aliases, custom reasoning budgets and
unreviewed extensions are rejected. Explicit `cache_control` is rejected,
including on text content parts; the current reviewed bound does not separately
authorize cache-write surcharges. Requested output caps must be positive
integers (or absent/null).
The UTF8 request-byte upper bound must fit the reviewed context bound. Unknown
or stale evidence rejects before runtime preparation/credential lookup; receipts
are checked again before every dispatch. Scientific approval gates still apply.

## Durable accounting and recovery

`paid-budget.jsonl` lives at the run root, outside trial workspaces. Each
transport attempt reserves the approved worst-case USD amount under the shared
allocation lock before network dispatch. Both the allocation checkpoint and
journal append are fsynced. The allocation checkpoint is advanced before append:
a crash between those writes intentionally blocks recovery pending review.
The hash chain detects interior corruption, and the separate checkpoint detects
missing journals and suffix deletion. Neither malformed data nor `--resume`
creates a replacement balance. The same allocation cannot initialize a new run.

Complete JSON/SSE `usage.cost` is parsed as Decimal and settled before answer,
finish-reason, response-model or context-bound validation. Any reported provider
identity must match the pinned host; drift records a durable cohort halt after
settling its charge. An omitted provider field is not independent host proof;
the actual live admission must still verify host routing. Charged HTTP errors
also settle before retry admission. A missing, null, boolean, string, negative,
NaN or infinite cost leaves the reservation unknown. A timeout, incomplete SSE,
response byte cap or crash does likewise. Unknown charges block the next paid
call, including retries, trials and memory turns. A measured charge above its
approved reservation is durably recorded and stops the cohort.

Settlement is idempotent for an identical attempt/cost/evidence and rejects a
conflicting second settlement. There is intentionally no automatic release or
reconciliation based on local failure. An unresolved reservation requires an
explicit reviewed provider reconciliation; this PR does not authorize provider
lookup or implement an operator recovery CLI. Never delete or rewrite the journal,
allocation checkpoint or lock to restart. A checkpoint/journal disagreement also
requires audited recovery rather than automatic repair.

`aggregate_usage` exposes measured USD coverage separately from token coverage.
`summary.json.paid_budget` reads the durable journal, retaining failed/unknown
attempts rather than relying on successful trials. Historical accounting can be
read after receipt expiry; expiry still prevents further dispatch. Existing
list-price cost metrics remain estimates. The canonical reviewed zero-price admission (including the active v4.7
Nemotron Ultra identity) is validated and its hash is frozen in effective
options; this exact identity remains exempt from paid receipts. A nonzero observed free-route
charge stops the gateway and cohort.

## Offline verification

`tools/tests/test_paid_budget.py` uses explicitly synthetic receipts and a fake
URL dispatcher. It covers reservation fsync ordering, JSON/SSE and charged error
settlement, Decimal boundaries, idempotence, unknown cost/retry blocking,
process-crash recovery, checkpoint-before-append failure, corruption/suffix
deletion, allocation ownership, process races, immutable effective CLI settings,
completed resume with no calls or journal rewrites, memory cap/journal propagation,
receipt rejection before native/credential access, and exact free exemption.
These tests are not live provider/key or scientific approval receipts.

Final focused budget suite: **68 passed in 9.03s**, using the isolated Python
environment. Final regression command covering `test_paid_budget.py`,
`test_provider_runner.py`, `test_current_wire_gateway.py`,
`test_reproducibility.py`, `test_driver.py`, `test_metrics.py`, and
`test_v45_execution.py`: **182 passed in 28.58s**. `git diff --check` and
`py_compile` on the changed Python modules also passed. All checks were offline.

An allocation is bound to exactly one run and manifest. The legacy multi-split
`v45_gate.seal_runs` builder attempts to reuse its configuration allocation for
devsmoke/pilot/main, so its second paid run fails closed. PR09 must supply
separately reviewed per-run allocation policy before a paid scientific seal can
run; this checkpoint does not claim paid seal readiness. Live receipt review and
checkpoint 16B remain pending, and issue #16 remains open.

Official API references checked during discovery:
[usage.cost](https://openrouter.ai/docs/cookbook/administration/usage-accounting),
[key limits](https://openrouter.ai/docs/api_reference/limits), and
[provider routing](https://openrouter.ai/docs/features/provider-routing).
