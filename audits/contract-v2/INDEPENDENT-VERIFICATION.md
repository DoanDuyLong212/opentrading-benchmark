# Independent snapshot contract verification — 2026-11-04

The implementation is verified relative to captured MCP payloads. No network/model calls were made in this review, and no holdout model trials were executed. Original-source certification of Vietnamese financial filings is outside this scope.

## Verified results

| Check | Result |
| --- | --- |
| Explicit raw-payload financial recomputation using Decimal | 45/45 tasks pass across main, pilot and smoke |
| Independent adversarial, grader and replay tests including actual MCP stdio | 129/129 pass |
| All instruction fenced JSON examples parse | 1 additional test passes across all 277 tasks |
| Incomplete narrative answer excluded from confirmatory scoring | 1 additional regression test |
| Offline valid answer fixtures / source oracles | 227/227 fixtures and 227/227 oracles pass |
| Offline mutated/empty/source/period/non-null-refusal probes | Every tested exploit rejected |
| Financial expectation/solution disagreement and task leakage | None detected by the audit |
| Original payload bytes versus Git HEAD | 277/277 unchanged |
| Original numerical gold solutions and numerical expectations versus archived v1 | Development/main/smoke unchanged |

The independent sample covers quarterly consolidated profit versus parent-company profit, revenue growth, gross margins, GDP totals/QoQ/YoY, foreign-currency multiplication and unit scaling, averages, filtering/ranking, RSI retrieval/selection/counts, multiperiod index changes, two-source consistency, absent periods/entities and company profile synthesis. It imports no oracle/generator arithmetic or synthesized answer construction. The captured CTD fiscal Q4 is preserved.

Commands and observed output:

```text
python3 -m pytest tools/tests/test_independent_snapshot.py tools/tests/test_grader_v2.py tools/tests/test_snapshot_server.py -q
129 passed in 26.86s

python3 -m pytest tools/tests/test_independent_snapshot.py -q -k all_instruction_json_examples_parse
1 passed, 71 deselected in 7.60s

python3 -m pytest tools/tests/test_independent_snapshot.py -q -k independent_finance_calculation
45 passed, 25 deselected in 13.86s

python3 tools/audit_benchmark.py --out audits/contract-v2/independent-acceptance
227 valid fixtures pass; 227 oracles pass; no counterexamples, leakage or numerical mismatch
```

The stdio tests require execution outside the process sandbox on this host; they use only local subprocess pipes and frozen files. The audit artifact is `independent-acceptance/audit-evidence.json`. Its 227 fixture/oracle counts include diagnostic tasks for regression coverage, and do not count them as confirmatory evaluation tasks.

## Corrections validated

Evidence now identifies the exact replay entry and response hash. Required coverage follows actual source dependencies in the trusted original oracle, narrowed by explicit entity metadata for historical merged single-symbol captures. One VCB call cannot ground five-bank answers. A GDP question does not require unrelated CPI data, a global-metal quote does not require unrelated Yahoo data, and a VCB RSI question does not require six symbols. Extra catalog evidence must still join a successful authoritative call in the final attempt.

The MCP SDK previously rejected schema-invalid arguments before the server ledger saw them. Validation now runs in the authoritative replay handler; a real stdio regression confirms exactly three ledger rows for one successful call, one invented entity and one schema-invalid argument.

The grader rejects recursive duplicate JSON keys, trailing JSON, overflowing/non-finite numeric values, negated units/indicator lines, contradictory verdict clauses and short dates with the wrong year. Growth period expectations now require both captured quarters. An invalid single-quoted JSON `source` example in smoke aggregation and its legacy generator was repaired mechanically.

USD and USDT remain distinct. Fiat quote questions no longer accept stablecoin units as interchangeable aliases, and reciprocal FX dimensions are not collapsed globally. The pilot BTCUSDT quote explicitly uses USDT; its conversion exercise explicitly declares the calculation premise 1 USDT = 1 USD. Stored financial numbers were not changed.

The migration is repeatable with `python3 tools/migrate_contract_v2.py --apply --refresh-contracts` and never replaces the original v1 archive. `migration.json.contract_adjustments` transparently records 78 task-level adjustments: 49 narrowed response requirements, 20 changed period/unit alias contracts and 31 diagnostic quarantines; categories overlap.

## Confirmatory eligibility and limits

| Split | All stored tasks | Eligible | Diagnostic only |
| --- | ---: | ---: | ---: |
| Main | 200 | 178 | 22 |
| Pilot | 24 | 22 | 2 |
| Smoke | 3 | 3 | 0 |
| Holdout | 50 | 43 | 7 |

CPI rows sometimes contain 105.08 and 5.08 under identical indicator/period/unit labels. Neither the oracle threshold `value < 20` nor a successful model answer establishes which official inflation series the number represents. Tasks requiring these ambiguous captures are quarantined by a deterministic data-ambiguity rule in root TOML metadata. GDP tasks with an unused CPI catalog decoy remain eligible. The same mechanical contract/quarantine transformation applies to holdout; holdout verification is limited to byte hashes, schema formatting and eligibility metadata rather than model outcomes.

The inherited narrative evidence checks remain token/number matching with limited required hits. A direct reproduction using `fin-l4-narrative-244`, an actual ANV replay call, verdict `sai` and note `17.83` passes the diagnostic grader despite omitting nine requested closes. The original acceptance probes mutated the verdict/value rather than removing note evidence, so they did not detect this completeness defect. Twelve narrative tasks with this weak rubric are now diagnostic only, with `incomplete_narrative_evidence_rubric`; none enters confirmatory scoring. Arbitrary natural-language reasoning is not universally verified. Holdout still shares 27 payload files with main, so it measures new questions over partly shared data rather than clean unseen-document generalization.

## Final refusal paraphrase regression

The first real NVIDIA smoke artifact contained valid refusals such as `Mã XYZX không được tìm thấy trong cơ sở dữ liệu tại thời điểm snapshot 2026-11-01.` The previous literal token matcher rejected these because gold used active `không tìm thấy`. The refusal-specific normalization now recognizes passive forms only for availability predicates, rather than removing arbitrary words or matching a specific symbol. Tests cover passive missing-symbol/unpublished-report reasons, double negation, opposite availability clauses and non-null refusals. All original evidence/schema/numeric/period checks remain active.

`python3 -m pytest tools/tests/test_grader_v2.py tools/tests/test_independent_snapshot.py tools/tests/test_snapshot_server.py -q` passed **143 tests** (including 45 independent financial computations). A second `migrate_contract_v2.py --apply --refresh-contracts` changed **zero of 1,699 task files** after normalizing eligibility-block separator whitespace. The migration preserved the original archive and all stored financial payload and numerical solution values. The final development/main acceptance artifact is `final-grader-acceptance/audit-evidence.json`; no heldout model calls were made.
