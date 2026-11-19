# Historical whole-study contracts

These tests are outside default v4.7 collection because they assert the original
v4.2/v4.3/v4.4 study configurations, sealed driver and full corpus byte identity.
Those study snapshots are **not distributed in this repository**. The tests are
preserved and fail if explicitly run without their prerequisites; they are not
skipped or xfailed. Restoring original, independently verified snapshots under
`experiments/finance-v42-study`, `finance-v43-study`, and `finance-v44-study`
is required before claiming these historical contracts pass.

```sh
python3 -m pytest -q experiments/finance-v47-study/tools/tests/legacy
```

The shared replay, wire schema, source binding, refusal, decimal independent
recomputation, memory consent/revocation, provider accounting, pause/resume and
current gate tests remain in the active v4.7 suite. Historical calculator execution
uses the tracked v4.6u runtime and lockfile, not the removed v4.7 calculator:

```sh
BENCH_BUN_BIN=/path/to/receipt-matching/bun python3 -m pytest -q experiments/finance-v46-update-study/tools/tests/test_v45_calculate.py experiments/finance-v46-update-study/tools/tests/test_v45_math_audit.py
```

Run the v4.6u job in a separate interpreter so cached modules cannot bind it to
v4.7. `BENCH_BUN_BIN` only chooses a location; actual bytes must match the SHA256
in the study's tracked config. Install its runtime dependencies using the pinned
Bun and `bun install --frozen-lockfile` in its `experiments/opentrading-runtime`.
The original sealed config is not rewritten by relocation.
