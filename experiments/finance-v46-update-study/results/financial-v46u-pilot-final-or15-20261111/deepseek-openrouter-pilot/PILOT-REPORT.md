# Pilot report — or15 merged evidence (user exception B, 2026-11-11)

Model `deepseek/deepseek-v4.1-flash-1017`; 36 pilot tasks (22 core + 8 compute + 6 native memory) × 3 arms × 2 runs = 216 trials.
Composition: or15 sealed pilot rows; ONLY the 21 semantically failed slots replaced by confirmation reruns (or15r OpenCode/DSH, or15r2 OpenTrading, latest code). Selective rerun can only raise scores and mixes code versions. User decision "A chọn b".
Audit PASS (fixed auditor), 0 accepted fabricated evidence; all-arm manual review 205/205 wins kept; judge: Nemotron Ultra batched (5/request), kappa vs manual labels 1.0 (n=211).

## Primary (judge correct ∧ numeric gate ∧ no FP/FR ∧ not removed)
| Arm | Total /72 | Core /44 | Compute /16 | Memory /12 |
|---|---:|---:|---:|---:|
| OpenTrading B0 | 72 | 44 | 16 | 12 |
| OpenCode | 66 | 44 | 16 | 6 |
| DSH | 67 | 44 | 12 | 11 |

Tiers: {"compute": {"C1": {"dsh": "4/4", "opencode": "4/4", "opentrading_baseline": "4/4"}, "C2": {"dsh": "4/4", "opencode": "4/4", "opentrading_baseline": "4/4"}, "C3": {"dsh": "2/4", "opencode": "4/4", "opentrading_baseline": "4/4"}, "C4": {"dsh": "2/4", "opencode": "4/4", "opentrading_baseline": "4/4"}}, "memory": {"M1": {"dsh": "2/2", "opencode": "2/2", "opentrading_baseline": "2/2"}, "M2": {"dsh": "2/2", "opencode": "2/2", "opentrading_baseline": "2/2"}, "M3a": {"dsh": "1/2", "opencode": "0/2", "opentrading_baseline": "2/2"}, "M3b": {"dsh": "2/2", "opencode": "0/2", "opentrading_baseline": "2/2"}, "M4": {"dsh": "2/2", "opencode": "0/2", "opentrading_baseline": "2/2"}, "M5-stale": {"dsh": "2/2", "opencode": "2/2", "opentrading_baseline": "2/2"}}}

Paired task bootstrap vs B0: {"compute": {"dsh": {"diff_vs_opentrading_baseline": -0.25, "ci95": [-0.625, 0.0]}, "opencode": {"diff_vs_opentrading_baseline": 0.0, "ci95": [0.0, 0.0]}}, "core": {"dsh": {"diff_vs_opentrading_baseline": 0.0, "ci95": [0.0, 0.0]}, "opencode": {"diff_vs_opentrading_baseline": 0.0, "ci95": [0.0, 0.0]}}, "memory": {"dsh": {"diff_vs_opentrading_baseline": -0.0833, "ci95": [-0.25, 0.0]}, "opencode": {"diff_vs_opentrading_baseline": -0.5, "ci95": [-0.8333, -0.1667]}}}

## Secondary
| Arm | Strict | Raw format | DNF | FP/traps | FR/answerable | Stable 2/2 | Requests | p50/p90 s | usage.cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| OpenTrading B0 | 72 | 72 | 0 | 0/4 | 0/68 | 36/36 | 303 | 17.8 / 43.0 | $0.492 |
| OpenCode | 66 | 72 | 0 | 0/4 | 4/68 | 33/36 | 213 | 17.4 / 53.0 | $0.300 |
| DSH | 67 | 68 | 4 | 0/4 | 0/68 | 33/36 | 211 | 17.5 / 49.2 | $0.180 |

Memory rule metrics: stale-use 0/2 every arm (no M5-revoke task in pilot). OpenCode false refusals = memory tasks it could not recall.
Findings and fixes: see analysis/or15-manual-judge-20261111.md and amendment addendum (g).
