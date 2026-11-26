# v4.7 benchmark: final 300-task report (2026-11-26)

Design: DEEPINFRA-COMPLETION-20261125.md (+ 300-task addendum). 300 tasks × 3 arms × 1 run = 900 trials, 0 missing.
Model deepseek/deepseek-v4.1-flash-1017. Judge: Claude Haiku 5.5 (judge cost $0.376); v4.6u OC/DSH rows keep their
original v4.6u judge-primary (Nemotron free judge + manual review), because only answer excerpts survive.

## Primary (judge correct AND numeric gate AND anti-fabrication)
| Scope | OpenTrading | OpenCode | DSH |
|---|---|---|---|
| Block A (200 v4.7 tasks; mixed judge on 19 old tasks) | 169/200 (84.5%) | 139/200 (69.5%) | 161/200 (80.5%) |
| Block A, Haiku-only (181 tasks) | 151/181 (83.4%) | 123/181 (68.0%) | 144/181 (79.6%) |
| Block B (100 v4.6u tasks, lookup-heavy) | 99/100 | 100/100 | 100/100 |
| All 300 | 268/300 (89.3%) | 239/300 (79.7%) | 261/300 (87.0%) |

Block A by stratum (primary): compute OT 66/69, OC 65/69, DSH 64/69; investor 19/36, 16/36, 16/36;
lookup 28/30 each; memory 43/51, 16/51, 39/51; robustness 13/14, 14/14, 14/14.

Paired (same task) OT wins/losses, exact sign test:
- Block A, Haiku-only: vs OpenCode 36/8 (p = 2.5e-5); vs DSH 19/12 (p = 0.28).
- All 300: vs OpenCode 39/10 (p = 3.8e-5); vs DSH 20/13 (p = 0.30).

Strict deterministic success (FINAL-300-report.json): All 300 OT 271, OC 240, DSH 260; Block A OT 173, OC 140, DSH 161.

## Caveats
- Host: Pearl fp8 for most block-A trials; DeepInfra for 45 block-A trials and all block-B OT trials.
- The 19 v4.6u tasks in block A and all of block B compare OT v4.7 with OC 2.1.2 / DSH 0.2.1-rc.2 (v4.6u).
- Block B is saturated (≥99% for all arms), so it adds little discrimination.
- One run per task: no 2/2 stability metric.
- Spend (journals, including upper-bound reconciles): $3.99; account balance after the judge: $3.72.
