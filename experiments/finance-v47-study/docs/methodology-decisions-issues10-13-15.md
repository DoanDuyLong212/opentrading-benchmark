# v4.7 methodology decision packet: #10, #13, #15

Prepared 2026-11-16. **Pending FinDaHuman decision.** This packet recommends
choices and implements conservative analysis defaults; it does not record an
approval, authorize inference or complete these decision issues. Machine-readable
status is `audits/methodology-2026-11-16/DECISIONS.json`. FinDaHuman must record each
choice, date and decision source (for example PR review URL), and confirm holdout
history before the later seal. Null fields and silence are not approval.

| Issue | Recommended choice | Pending recorded decision |
|---|---|---|
| #10 | (b): all S diagnostic and reported separately; L/C/M primary; no additional arm in this cohort | FinDaHuman, date, choice and source |
| #13 | Keep exactly the existing 40 dropped IDs and historical PRUNE bytes/hash | Accept post-selection limitation or require a new prospective cohort |
| #15 | Keep 58 holdout tasks for this economical cohort; no added C3 mid-cohort | Accept broad uncertainty and absent C3 or preregister a new cohort |
| #15 public gold | Disclose public history and constrain runtime access | Accept limitation or create new independently reviewed private data |

## What the S result means

S1 includes product policy prompt effects and is not an isolated harness-loop
comparison. S2 tests instruction handling in tool data; S3 tests stale-data date
reporting while native cross-arm clock parity is unverified. The current S
lexical rubric additionally needs blind review (see issue #9 amendment). This
packet makes no causal superiority claim from S. S4 remains deferred.

All S is excluded from primary overall rates, comparative strata, paired tests
and bootstrap differences. S1/S2/S3 counts and outcomes remain in diagnostic
stratum/tier tables. `metrics.build_summary` partitions LCM and S before rates,
stability, token/cost tables, operational and financial summaries; the CLI labels
both tables. Costs retain their own coverage and are not dropped from accounting.
Recorded completion of the entire scheduled cohort stays distinct from analysis
subset completeness, so an unfinished S schedule cannot certify a full cohort.
Existing L/C/M endpoint semantics are unchanged. Downstream charts must consume
the labeled primary/diagnostic tables; no new chart combines them.

Current inventory: main 100 L + 40 C + 30 M + 30 S = 200; holdout 36 L + 7 C +
7 M + 8 S = 58. Comparative primary has 170 main and 50 holdout tasks; diagnostic
S has 30 and eight. These are task counts per arm/repeat, not USD estimates.

## Frozen selection and its limitation

`PRUNE.json` is historical evidence, including its original selection wording.
Selection followed the or16 cohort (DeepSeek v4.1-flash-1017 via OpenRouter), so
its old statement about a rule fixed before looking at outcomes does not establish
prospective independence. Saturation in that one model/cohort does not imply the
same tasks are uninformative for a new model. Removing shared easy tasks changes
the denominator and difficulty distribution; it need not preserve an accuracy
difference or uncertainty in another cohort. Code/test-named protection can also
bias selection. The historical receipt remains byte-for-byte unchanged.

The old pruning entrypoint now only validates the frozen receipt SHA256, its 40
IDs, protected-ID disjointness, exact main/holdout ID inventory and stratum/family
composition. Both normal mode and `--dry-run` are read-only. It never reads local
results to reselect tasks, rewrites a receipt, or deletes a directory. A changed
selection requires a new explicit methodology version and receipt.

`audits/methodology-2026-11-16/or16-dropped40-evidence.json` preserves a minimal
source-backed extract: 240 trial identities/measurement rows, three source file
hashes and model/price provenance. Each of the three arms has 80/80 strict,
grounded and judge-primary wins on these 40 tasks in or16. These are descriptions
of the selected source cohort, not unbiased estimates for v4.7.

The source trial token counters are complete for all 240 rows. Frozen manifest
price fields can be mapped to input/output/cache rates, but that manifest does not
explicitly declare input/cache overlap semantics. Therefore no authoritative
list-price total or provider spend is claimed. The artifact gives measured raw
counter totals and two labeled **assumption-based scenario estimates**, inclusive
and exclusive cache accounting, with coverage. The actual cost total remains
unavailable with a reason; neither scenario is measured provider spend. Source
hashes and the retained rows were independently compared with available local
or16 artifacts. Active tests require only the committed extract, not local result
directories.

## Holdout limitations and owner confirmations

The recommended 58-task holdout has limited C/M counts and no new C3 long-series
coverage; report wide uncertainty and refrain from generalizing to C3. Gold and
tasks already appeared publicly. Removing or hiding them now cannot erase that
history. This is a holdout from local development selection, not evidence that
model training never included those data.

Cross-machine run/exposure history is **unknown**, not confirmed clean. Owner
confirmation must cover every machine, prior `dev-stage/holdout` runs and
`fin-mem-96x` history. Existing development exposure remains in the Phase1 ledger;
this packet does not rename exposed tasks to erase that history. Missing git
artifacts are not proof that inference never occurred. Preserve existing runtime
access controls and holdout gates; this draft does not open any split.

If a genuinely private confirmatory holdout is required, preregister a separate
cohort with new data, snapshot, seed, strata and independent reviewer, and allocate
its cost before generation/seal. Do not relabel these same public golds private or
select replacements based on model outcomes. The later main/holdout authorization
still needs explicit recorded decisions and budget allocation.
