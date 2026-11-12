# pilot v4.6-update — deepseek/deepseek-v4.1-flash-1017

Same registered co-primary/secondary metrics as main. Every scheduled trial remains denominator; no model pooling.

| Arm | N | Strict grounded | Grounded financial | DNF | FR / answerable | FP / traps | Usage complete |
|---|---:|---:|---:|---:|---:|---:|---:|
| opentrading_baseline | 72 | 66 | 66 | 1 | 0/68 | 0/4 | 72/72 |
| opencode | 72 | 65 | 65 | 0 | 4/68 | 0/4 | 72/72 |
| dsh | 72 | 64 | 64 | 6 | 0/68 | 0/4 | 72/72 |

Gate: PROVISIONAL — independent all-arm manual financial review pending

{
  "pass": false,
  "reasons": [
    "instrumentation audit not PASS or fabrication unknown",
    "manual all-arm review pending or fabrication accepted",
    "judge-primary scoring missing/stale for the reviewed schedule"
  ],
  "gate": "b0_judge_primary",
  "scheduled": 216,
  "arms_primary": {}
}

Full secondary metrics, per-level/family, stable2/2, task-cluster comparisons: summary.json. Source/capture/usage independent audit: audit-v45.json. Pilot is screening evidence, not statistical proof of broad superiority.
