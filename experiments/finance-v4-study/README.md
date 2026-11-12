# Finance v4 development study

Isolated native OT + common MCP C1 input-contract experiment. Original v3 tools/tasks/results are preserved. No credentials or result trees were copied into this study. Native dependency directories are reused read-only and fingerprinted. All four conditions use the same C1 metadata, input validation, exact recorded-request matcher, payload bytes, budgets and v4 grader. Native OT baseline disables finance policy; candidate enables it and selects the finance prompt.

The model is locked by driver admission to `nvidia/nvidia/nemotron-3.5-bolt-e4b`. Inference is restricted to smoke/pilot. The isolated provider gateway also rejects every other model before reading credentials or starting a request; original external diagnostic changes remain untouched.

C1 domain constraints are authoritative for every condition; server ledger separately labels failures already invalid under frozen v3 schema versus new v4 domain constraints. Native local validation failures are joined to actual generated call IDs and subsequent model-visible tool errors; they do not falsely count as MCP executions. Every parsed new answer is also graded with the frozen v3 grader; both results are persisted. Financial values, periods, units and evidence are never rescued by the adapter.

Run from this directory only, after final offline checks and source freeze:

```bash
python3 tools/ready_check.py --config tools/bench_config.json --run-tests
python3 tools/run_benchmark.py --split smoke --arms opentrading,opencode,dsh --runs 2 --seed 20261105 --out results/financial-v4-smoke-20261105 --timeout 240 --retry 0 --pause 2 --effort none --max-requests 24 --max-output-tokens 2048 --max-total-tokens 48000 --provider-timeout-s 45
python3 tools/ready_check.py --config tools/bench_config.json --live-run results/financial-v4-smoke-20261105 --certificate results/financial-v4-ready-20261105.json
python3 tools/run_benchmark.py --split pilot --arms opentrading_baseline,opentrading_finance,opencode,dsh --runs 2 --seed 20261105 --out results/financial-v4-pilot-20261105 --timeout 240 --retry 0 --pause 2 --effort none --max-requests 24 --max-output-tokens 2048 --max-total-tokens 48000 --provider-timeout-s 45
```

Pilot starts only after the smoke operational gate passes. Append `--resume` to exactly the same completed command to verify zero new calls and duplicates. Do not tune quality behavior after inference begins. This public development set does not demonstrate generalization or justify production promotion.
