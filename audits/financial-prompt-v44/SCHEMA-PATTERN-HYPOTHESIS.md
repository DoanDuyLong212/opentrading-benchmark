# Supplemental offline proof: compute pointer pattern and full-string matching hypothesis

Read-only evidence addition; original17-rejected-compute count, original audit FAIL and no-pilot decision remain unchanged. Only Python standard-library regex evaluation, JSON parsing and byte hashing were used. No model calls, source changes, runtime compute calls, package installation or new financial trial occurred. Companion `pattern-summary.json` contains17 ledger→SDK-generation→native/effective-request joins,57 operand-path occurrences, actual source-leaf controls and50 capture hashes.

## Proven from the frozen artifacts

Every one of17 actual MCP compute attempts joins by exact parsed arguments to its generated SDK call ID in a subsequent native message, then to the provider ledger's generating request. Local duplicates are excluded. Every generating native request and effective upstream request carries the same path schema:

```json
{"type":"string","pattern":"^/data(?:/|$)"}
```

No joined request contains an explicit `strict`, `guided_json`, `guided_regex`, `guided_grammar`, `guided_decoding_backend` or `response_format` field, including nested tool definitions. This establishes the visible wire configuration. It does not exclude server-side defaults, an internally selected decoder or provider tool-call constraints.

| Path | Actual attempts using this path | Operand occurrences | Regex search | Regex fullmatch | Actual quote-envelope meaning |
|---|---:|---:|---|---|---|
| `/data/` | 7 | 7 | accepts | accepts | Empty-key lookup under data; absent key, KeyError `''` |
| `/data` | 10 | 50 | accepts | accepts | Data object, not a numeric leaf; runtime rejects missing trailing slash |
| `/data/last` | 0 | 0 | accepts | rejects | Actually retrieved numeric field; valid source unit and date |

Each of57 operand call IDs joins to an actual successful quote source envelope in the same trial. Those envelopes expose `/data/last`, `units.last="nghìn đồng/cổ phiếu"` and `last_t="2026-10-30"`. Search semantics admit that real leaf; full-string matching excludes it. `/data/last_t` is also admitted by search but is text, illustrating why this prefix schema alone does not guarantee a numeric leaf. Runtime must retain the actual numeric-value and source-metadata checks.

The pattern's exact full-string language is only two strings: `/data` (the `$` branch) and `/data/` (the slash branch). There is no token after that branch in the pattern. Both strings appear in the17 rejected calls, and no other path appears. Thus the *observed distinct path set exactly equals the fullmatch language*. Standard search semantics permit arbitrary suffixes after `/data/`; fullmatch semantics prevent every nonempty leaf suffix. This is a proven mathematical compatibility signature and a concrete schema/runtime acceptance mismatch. It is not proof that the provider used fullmatch.

The semantic distinction is documented by [JSON Schema's string reference](https://json-schema.org/understanding-json-schema/reference/string): `pattern` uses matching within the string rather than an implicit whole-string requirement. Python `re.search` versus `re.fullmatch` is a transparent local comparison for this simple ASCII expression; no claim is made about reproducing an unknown provider compiler.

## External evidence makes this a priority hypothesis, not a confirmed incident cause

[XGrammar issue838](https://github.com/mlc-ai/xgrammar/issues/838), opened August14,2026, reports that its schema converter applies full-string matching to pattern and patternProperties despite JSON Schema search semantics. The issue's offline examples demonstrate rejection of valid suffix/prefix strings. That report establishes a known failure class in a named project; this study did not inspect or reproduce the deployed provider backend.

[NVIDIA NIM1.15 structured-generation documentation](https://docs.nvidia.com/nim/large-language-models/1.15.0/structured-generation.html) describes guided_json using XGrammar and potential fallback to Outlines. It does not identify this hosted model endpoint's backend/version or establish that ordinary function-tool schemas in these captures activate guided_json. [Outlines issue1083](https://github.com/dottxt-ai/outlines/issues/1083) is an older closed report of an analogous pattern anchoring disagreement, useful as historical context rather than evidence about a current service.

These primary project sources plus the exact two-string signature justify elevating decoder/schema interoperability ahead of a model-incapacity interpretation. They do not establish that constrained decoding was active, which library/version ran, whether its reported bug persists in that version, or whether model behavior independently preferred parent pointers. The study records no provider backend metadata, raw response grammar or controlled API canary. No causal fraction or forecast of recovered answers can be assigned.

## P0 for a separately authorized and preregistered study

Before interpreting another compute failure as model capability, compare four public contract treatments against the same source shapes and budgets:

1. Current prefix pattern, retained as the diagnostic control.
2. Explicit complete anchored pointer pattern that allows nonempty leaf suffixes, with JSON-pointer escapes handled and runtime numeric/source validation retained.
3. Path string without pattern, with the same runtime pointer validation.
4. Stable source field references designed from public successful responses, with an explicit mapping and no hidden task/gold lookup or silent operand inference.

Start with offline schema-language acceptance checks against independent JSON Schema search semantics and, where already available in an explicitly identified environment, the actual deployed decoder. A future API canary requires separate authorization and must record backend/version or mark them unknown, actual outgoing strict/guided flags, raw response metadata and chosen paths. Then run a fresh sealed cohort or a randomized schema treatment, never mutate/retry the current smoke cohort. Measure leaf selection, source joins, corrected original intents versus new intents, runtime rejections, continuation budget and final strict/numeric outcomes separately. A successful pointer intervention would still need complete source coverage, correct period/unit and a valid final answer to satisfy financial success.
