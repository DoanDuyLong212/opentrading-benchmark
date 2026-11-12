# pilot v4.6-update — deepseek/deepseek-v4.1-flash-1017

Same registered co-primary/secondary metrics as main. Every scheduled trial remains denominator; no model pooling.

| Arm | N | Strict grounded | Grounded financial | DNF | FR / answerable | FP / traps | Usage complete |
|---|---:|---:|---:|---:|---:|---:|---:|
| opentrading_baseline | 44 | 35 | 35 | 5 | 0/40 | 0/4 | 40/44 |
| opencode | 44 | 36 | 36 | 5 | 0/40 | 0/4 | 41/44 |
| dsh | 44 | 36 | 36 | 3 | 0/40 | 0/4 | 39/44 |

Gate: PROVISIONAL — independent all-arm manual financial review pending

{
  "pass": false,
  "reasons": [
    "independent all-arm financial claim review pending/fabrication unknown",
    "independent instrumentation/financial audit not PASS or fabrication unknown",
    "missing candidate",
    "wrong denominator",
    "strict_grounded_success below 33",
    "grounded_financial_correctness below 35",
    "answerable_grounded below 31",
    "trap_grounded below 4",
    "dnf exceeds 1",
    "false_refusals exceeds 2",
    "false_positives exceeds 0",
    "fabricated_evidence_accepted exceeds 0",
    "strict_grounded_success margin vs opentrading_baseline",
    "grounded_financial_correctness margin vs opentrading_baseline",
    "dnf regression vs opentrading_baseline",
    "false_refusals regression vs opentrading_baseline",
    "false_positives regression vs opentrading_baseline",
    "evidence regression vs opentrading_baseline",
    "strict_grounded_success margin vs opencode",
    "grounded_financial_correctness margin vs opencode",
    "dnf regression vs opencode",
    "false_refusals regression vs opencode",
    "false_positives regression vs opencode",
    "evidence regression vs opencode",
    "strict_grounded_success margin vs dsh",
    "grounded_financial_correctness margin vs dsh",
    "dnf regression vs dsh",
    "false_refusals regression vs dsh",
    "false_positives regression vs dsh",
    "evidence regression vs dsh"
  ],
  "split": "pilot",
  "candidate": "opentrading_finance",
  "denominator": 44
}

Full secondary metrics, per-level/family, stable2/2, task-cluster comparisons: summary.json. Source/capture/usage independent audit: audit-v45.json. Pilot is screening evidence, not statistical proof of broad superiority.
