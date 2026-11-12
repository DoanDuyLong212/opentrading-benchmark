# devsmoke v4.6-update — deepseek/deepseek-v4.1-flash-1017

Same registered co-primary/secondary metrics as main. Every scheduled trial remains denominator; no model pooling.

| Arm | N | Strict grounded | Grounded financial | DNF | FR / answerable | FP / traps | Usage complete |
|---|---:|---:|---:|---:|---:|---:|---:|
| opentrading_baseline | 24 | 20 | 24 | 0 | 0/18 | 0/6 | 24/24 |
| opentrading_finance | 24 | 20 | 20 | 1 | 0/18 | 0/6 | 24/24 |
| opencode | 24 | 22 | 22 | 0 | 0/18 | 0/6 | 24/24 |
| dsh | 24 | 14 | 19 | 0 | 0/18 | 0/6 | 24/24 |

Gate: FAIL

{
  "pass": false,
  "reasons": [
    "grounded_financial_correctness margin vs opentrading_baseline",
    "dnf regression vs opentrading_baseline",
    "evidence regression vs opentrading_baseline"
  ],
  "split": "devsmoke",
  "candidate": "opentrading_finance",
  "denominator": 24
}

Full secondary metrics, per-level/family, stable2/2, task-cluster comparisons: summary.json. Source/capture/usage independent audit: audit-v45.json. Pilot is screening evidence, not statistical proof of broad superiority.
