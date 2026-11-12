# Frozen diagnostic pilot protocol v3

Registered 2026-11-05 before new inference. This is a bounded implementation of the
one-week prompt plan, not the unimplemented four-variant/264-trial proposal.

## Scope and conditions

Run 18 operational smoke trials first: all three smoke tasks × 2 runs × canonical
OpenTrading (finance candidate), OpenCode, DSH. Then run exactly 176 pilot trials:
22 confirmatory-eligible pilot tasks × 2 runs × four conditions, in one manifest.
The conditions are `opentrading_baseline`, `opentrading_finance`, `opencode`, `dsh`.
Both OT conditions use the same isolated native runtime and agent loop; only their
trusted prompt directory differs. Canonical `opentrading` selects `finance`.
All conditions use the repaired v3 snapshot server; historical v2 scores are not
concurrent controls. No main or holdout inference in this experiment.

## Fixed execution policy

NVIDIA `nvidia/nemotron-3.5-bolt-e4b`, effort none, temperature 0, top_p 1;
trial timeout 240 s, 24 upstream requests, 2048 output tokens/request, 48000 total
budget policy, retry 0, two-second minimum shared request interval. Provider
credentials stay in the parent gateway. Actual usage is captured, never fabricated.
Seed 20261105 freezes task and cyclic Latin condition order. The 44 task/run blocks
are divisible by four; each condition appears 11 times in every execution position.
Each condition sees identical task instructions plus common snapshot-as-of context.
OT's native now is pinned through its actual API and session reminders are omitted
under snapshot policy. Other native clocks are not claimed pinned; full native and
effective request captures disclose them. Schemas are captured as actually emitted;
SDK schema differences are not silently removed. Source/gold financial values and
strict replay request matching remain unchanged.

## Endpoints and decision

Primary diagnostic endpoint: grounded, schema-compliant, timely full success over
started trials, report numerator/denominator per condition and paired task changes.
Also report format/grounding, false refusal, DNF, invented evidence, tool rejection
and recovery, token coverage, requests and latency. Two runs cannot measure
stable-correct 3/3. Report all 22 tasks and failures, not a favorable subset.
Bootstrap CI95 and descriptive paired differences are exploratory in this small
pilot; the +7pp/97.5% CI main victory criterion is not implemented or tested here.
No claim of beating both harnesses based solely on this pilot. Tiny-model results
are not transferred to unverified Go/DeepSeek/medium settings.

One combined finance candidate is fixed before inference. Do not retune after pilot
and rerun for a favorable score; any later revision requires a new explicitly
labelled exploratory experiment. Stop/resume only with the exact immutable manifest;
completed trials are never replaced. Infrastructural failures remain in the report.

## Promotion guard (registered before inference)

Deploy the finance prompt as the default only if pilot primary success is at least
the concurrent OT baseline AND false-positive/started, false-refusal/started and
DNF do not regress. Require a strict primary or false-refusal improvement, or ties
on these quality endpoints plus lower total measured input+output tokens. Matched
22×2 started trials are the denominators for promotion; answered-only rates remain
secondary diagnostics and cannot hide refusals. If the guard fails, install only
the runtime/protocol correctness fixes and retain the baseline prompt by default;
keep finance as an experimental candidate with all results disclosed. This is an
engineering rollout guard, not statistical proof of superiority.
