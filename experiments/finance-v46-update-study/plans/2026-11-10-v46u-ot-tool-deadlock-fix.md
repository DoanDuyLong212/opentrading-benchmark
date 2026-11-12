# Amendment 2026-11-10 (d) — OpenTrading tool-deadlock fix (user-directed), new pilot or12

Status: APPROVED by user 2026-11-10 ("điều tra … thực hiện fix đi"). Registered before or12 inference.

## Finding (or11 pilot, OT B0 arm: strict 37/44 vs OpenCode 43/44, DSH 41/44)
5 of the 7 OT failures were tool-blocked DNFs (invalid_json after 12 requests; unrecoverable in the sealed
cohort): fin-l2-crypto-01 r1, fin-l3-index-01 r1/r2, fin-l3-agg-01 r1/r2. Mechanism:
1. The OT default prompt (prompts/tools.md) forbade any self-computed figure ("Không tự tính nhẩm … chỉ ghi số
   tool trả về … không thay bằng kết quả tự nghĩ ra").
2. OT's native `calculate`/`compute` rejected every attempt: sources without published unit metadata
   (crypto_spot, vn_index_ohlcv), typed literals, literal-only expressions ("missing financial period"), and the
   equivalent label "nghìn đồng" vs published "nghìn đồng/cổ phiếu" (the model then dropped the bindings).
3. Two rescue nudges (tools off: "answer from the tool results") could not be satisfied without a computed number
   → reasoning-only empty answer → DNF.
OpenCode/DSH have no such rule: they used the source's `analytics_compute` (agg mean) or, when the shared
calculators also rejected unit-less sources, wrote the formula and inputs and computed by hand.
Other OT failures: fin-l1-gold-01 r1 = model copied a corrupted response_sha256 (model error);
fin-l4-future-01 r1 = sealed grader judged a correct refusal + latest-period info as contradictory (grader).

## Fix (OpenTrading runtime, product change; applies to B0)
- F1 prompts/tools.md: tools first (calculate/compute or the source's analytics); if a calculator still rejects
  because the source lacks unit/period metadata, do not loop — compute from exactly the tool-returned numbers,
  write the formula and inputs, never leave the answer empty.
- F2 src/core/tools/financial-source.ts: a caller unit equal in scale and differing only by the per-share
  denominator is accepted; the leaf keeps the published unit. Any other override still fails (existing test kept).
- F3 src/core/loop/stop-gate.ts: the tools-off empty-answer nudge states the same fallback.
Tests: OT full suite 1895 pass (+1 new unit-equivalence test; prompt budget guard respected); study 643 pass.

## Runs
or11 (pre-fix OT) stays diagnostic; its seal is no longer valid and it is never resumed. Its judge/review
artifacts are reported as pre-fix evidence. A fresh pilot or12 under the same B0 gate/flow precedes main.

## Addendum 2026-11-11 (e) — calculator relaxation (user: "calculator của OT quá cứng … cải thiện triệt để")
Targeted rerun of the 11 or11 failed slots with F1–F3 (or12r): 9/11 recovered, but OT still dead-ended 3/10
reruns because `calculate`/`compute` rejected unit-less sources, typed operands and literal expressions.
Change (OpenTrading runtime, grounded financial mode):
- Verified-first, never dead-end: the tools first attempt full source lineage (unchanged rules, now with
  inferred alignment: several entities → cross_entity_same_period, one entity over several periods →
  time_series). If lineage fails only for missing metadata (unit/period/entity), a typed operand, embedded
  data literals or an undeclared alignment (`relaxableDerivation`), the result is still computed in lenient
  mode, labelled `lineage: "unverified"` with the reason, and carries no derived_result/source_evidence — it is
  recorded as native_utility, never as source proof.
- Never relaxed (would produce wrong numbers): scale changes inside a series, unit/metric/scope mismatches,
  unit overrides with another scale, unused/missing variables, ambiguous selectors.
- Units: per-share-only label differences accepted on input and on output conversion; formula constants include
  small counts (≤31) and powers of ten.
Tests: OT 1899 pass (5 strict-contract tests rewritten to assert "computed but never lineage"; 3 new pilot-shape
regressions: agg-01 mean with lineage, crypto-01 unit-less BTC×FX, index-01 pct_change/typed/literal).
Rerun scope (user): only the OT failed slots of or11 are rerun (OpenCode/DSH runtimes unchanged; their or12r
reruns stand); then re-judged with the same free Ultra judge.

## Addendum 2026-11-11 (f) — no shared calculators (user: "bỏ các công cụ so sánh dùng chung … tools tính toán là năng lực của OT")
`mcp_snapshot_server.SHARED_CALCULATORS = False`: the snapshot server advertises data tools only;
`analytics_compute` / `analytics_calculate` are no longer offered and calls to them are `unknown_tool`.
Calculation is each harness's own capability (OpenTrading native calculate/compute; OpenCode/DSH compute
themselves). The OT native calculator keeps its own relaxations (e); the strict `nonFormulaLiterals` used by
the retired shared shim is unchanged. Catalog tests updated (2). This changes the condition of every arm, so the
targeted rerun of the 11 or11 failed slots is repeated for all three arms under this exact code (or13r); earlier
or11/or12r rows were produced with the shared calculators and are reported as such.

## Addendum 2026-11-11 (g) — auditor/OT consistency found by the or13r audit
or13r: all 11 failed slots passed and the judge rated OT 10/10 correct, but the OT audit failed on
fin-l3-agg-01 r1/r2: (1) the independent Decimal auditor only knew the old formula constants, while OT now
treats small counts (the `/5` of a mean) as formula constants → `v45_math_audit.formula_constant` mirrors
OT `isFormulaConstant`; (2) OT labelled a per-share mean "nghìn đồng" (true dimension nghìn đồng/cổ phiếu) →
OT keeps the true per-share dimension in the reported unit. The auditor's dimension check is unchanged.
Only the two audit-blocked OT agg-01 slots are rerun (or14r). Tests: OT 1899 pass; study 644 pass.
