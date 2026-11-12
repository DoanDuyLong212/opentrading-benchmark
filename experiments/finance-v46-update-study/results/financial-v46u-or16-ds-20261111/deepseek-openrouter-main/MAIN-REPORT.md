# main v4.6-update — deepseek/deepseek-v4.1-flash-1017

Same registered co-primary/secondary metrics as main. Every scheduled trial remains denominator; no model pooling.

| Arm | N | Strict grounded | Grounded financial | DNF | FR / answerable | FP / traps | Usage complete |
|---|---:|---:|---:|---:|---:|---:|---:|
| opentrading_baseline | 400 | 254 | 254 | 137 | 0/378 | 0/22 | 265/400 |
| opencode | 400 | 349 | 349 | 3 | 18/378 | 0/22 | 399/400 |
| dsh | 400 | 358 | 358 | 18 | 0/378 | 0/22 | 400/400 |

Gate: PROVISIONAL — independent all-arm manual financial review pending

{
  "pass": false,
  "reasons": []
}

Full secondary metrics, per-level/family, stable2/2, task-cluster comparisons: summary.json. Source/capture/usage independent audit: audit-v45.json. Pilot is screening evidence, not statistical proof of broad superiority.
