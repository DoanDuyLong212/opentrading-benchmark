# pilot v4.6-update — deepseek/deepseek-v4.1-flash-1017

Same registered co-primary/secondary metrics as main. Every scheduled trial remains denominator; no model pooling.

| Arm | N | Strict grounded | Grounded financial | DNF | FR / answerable | FP / traps | Usage complete |
|---|---:|---:|---:|---:|---:|---:|---:|
| opentrading_baseline | 44 | 37 | 37 | 5 | 0/40 | 0/4 | 44/44 |
| opencode | 44 | 43 | 43 | 1 | 0/40 | 0/4 | 44/44 |
| dsh | 44 | 41 | 41 | 2 | 0/40 | 0/4 | 44/44 |

Gate: PROVISIONAL — independent all-arm manual financial review pending

{
  "pass": false,
  "reasons": [
    "manual all-arm review pending or fabrication accepted",
    "judge-primary scoring missing/stale for the reviewed schedule"
  ],
  "gate": "b0_judge_primary",
  "scheduled": 132,
  "arms_primary": {}
}

Full secondary metrics, per-level/family, stable2/2, task-cluster comparisons: summary.json. Source/capture/usage independent audit: audit-v45.json. Pilot is screening evidence, not statistical proof of broad superiority.
