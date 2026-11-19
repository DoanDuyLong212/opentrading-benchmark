# Development exposure ledger

`ledger.json` records evidence known at baseline 4bbfd38. Main tasks used in diagnostics remain main tasks with exploratory history. Explicit copies live in `tasks/devsmoke/dev-*`; their lineage preserves the source ID/hash and freezes the copied files. Existing v45 development fixtures have baseline lineage; their older history is unknown.

The design reports inference for stagger-425, chain-305 and m1-screen-502. Other listed tasks have documented development edits but inference is unknown. Dates/models and request-capture hashes are recorded separately from unknown run IDs. No cross-machine or holdout non-exposure claim is supported.

With `BENCH_V47_DEV=1`, only physical, lineage-bound devsmoke tasks can be selected or dispatched, including native memory. Pilot/main/holdout and the legacy memory driver cannot use this bypass. Run diagnostics with `--split devsmoke --retry 0 --tasks dev-fin-c4-stagger-425,dev-fin-l4-chain-305,dev-fin-m1-screen-502`. Listing with `--list-only` makes zero requests. This policy does not grant inference approval or certify the historical v4.6 seal as a v4.7 seal; seal modernization remains PR-09.
