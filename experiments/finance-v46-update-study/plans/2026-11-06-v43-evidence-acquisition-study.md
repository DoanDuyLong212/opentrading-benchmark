# v4.3 registered evidence-acquisition development smoke

Registration finalized before inference on 2026-11-06. Authorization covers implementation, offline engineering checks and exactly two NVIDIA smoke strata below, subject to fresh independent engineering review. No production installation, pilot, main, holdout or promotion is authorized. Earlier v4.2 source, results and certificate remain preserved.

The three existing smoke tasks are observed development/regression cases, NOT held-out evaluation. Both models and every condition/task/prompt/source/runtime/protocol/schedule are sealed together before the first provider call. No tuning between strata; retain every started trial including timeout, DNF, refusal and native failure. Model strata are reported separately; no cross-model pooled treatment estimate or superiority claim.

## Design and fixed resource limits

Each model has four conditions: opentrading_baseline (B0, native base with baseline prompt and finance policy OFF), opentrading_finance (B1, same native base with concise finance work order and acquisition/repair policy ON), opencode (OC native), dsh (DSH native). All share the exact finite C2 tool catalog/descriptions/error cues/public final contract and frozen task corpus. Live catalog is task-scoped; full17 is an offline capability probe only. Candidate is a disclosed prompt-plus-native-policy package, not an isolated single-lever ablation.

Each stratum is exactly smoke-quote-01, smoke-agg-01, smoke-trap-01 × four conditions × two repeats =24 started trials; total48. Fixed seed20261105. run_manifest.build_schedule supplies deterministic Latin-cycle arm order; six task/repeat blocks mean exact position counts cannot all be equal, so residual order imbalance is disclosed. Separate manifests are created by tools/v43_gate.py seal before inference and validated byte-for-byte on resume.

- Bolt: nvidia/nvidia/nemotron-3.5-bolt-e4b; provider wire ID nvidia/nemotron-3.5-bolt-e4b; trial240s/provider45s.
- DeepSeek: nvidia/deepseek-ai/deepseek-v4.1-flash; wire ID deepseek-ai/deepseek-v4.1-flash; trial900s/provider240s. These longer caps are registered BEFORE inference because the prior Nov5 diagnostic showed genuine slow tool continuation. Within each model all four conditions use identical caps. DeepSeek remains a separately authorized diagnostic stratum, not an unrestricted allowlist or paid fallback.

Both: temperature0, top_p1, effortnone (no explicit medium request; this does not claim reasoning disabled), max24 provider requests/trial, max2048 output tokens/request, conservative48000 token policy, retry0, pause2s, native stall300s. No hidden retries, new acquisition budget or cap increases. Unknown pricing stays N/A; missing reasoning/usage stays absent, not fabricated zero.

## Intervention and accounting

Finite support is the first common description; production metadata remains explicitly separate. Unsupported errors expose argument_paths, allowed_public_variants and retryability with same-intent action instructions. No argument mutation, gold injection, answer-bearing examples, task-ID routing or synthetic receipts. Finite matcher, recorded payloads and accepted default-equivalent variants retain v4.2 semantics.

B1 acquires evidence before final or premature clarification. Zero-call acquisition and failed-intent correction are distinct bounded phases with actual effective tools. Original entity/period/metric/scope and shared limits remain binding. Output-format correction does not substitute for acquisition. Empty resolver/no-data evidence, unsupported query, auth terminal, partial success and success remain distinct. Every accepted evidence claim must join actual immutable successful execution. Null on an answerable task remains primary failure/false refusal; DNF stays DNF.

All task gold, task graders, frozen_v41/v3 graders and public_response_contract are byte-identical to v4.2. Primary is the existing strict raw public-contract plus actual receipt-grounded task correctness on ALL started trials. Development changes only common cues, candidate prompt and native acquisition policy; explanatory failure-stage metrics are separate and cannot alter primary.

## Mandatory fresh engineering gate

Before seal/launch: native tests/typecheck, benchmark tests, independent offline case fixtures (unseen entity aliases/periods/units/multiple-source/partial/terminal cases), actual four-condition SDK+MCP+gateway stub wire/call/cap captures and independent review. Cover zero-call final acquiring actual calls; success and genuine empty resolver; unsupported then supported correction; no loop/duplicate or drift; mixed/partial intents; fabricated/mismatched receipts; raw fences; answerable refusal failure; cancellation/shared caps; completed resume zero calls. Preserve failed logs. No live model invocation is part of engineering checks. Engineering approval is a durable explicit JSON receipt bound to final source, logs and independent review; tools/v43_gate.py refuses a missing or nonpassing receipt.

The new dedicated smoke gate is predeclared because legacy ready_check operational_parity_v42 certifies only three canonical arms and one model. It remains intact and its certificate cannot be claimed or bypassed. tools/v43_gate.py reports a separate v4.3 diagnostic gate: zero identity/receipt/cap/audit violations, and at least one primary-correct numeric financial retrieval (quote or aggregate with actual successful vn_quote_history) PER condition. Trap-only success cannot pass. DNF/quality failures are retained, never rescued by grader changes. Quality failure does not prevent the second separately registered model; identity/audit/cap violations stop the supervisor for inspection. No failed diagnostic gate authorizes pilot/promotion.

## Sequential execution and endpoints

Durable tools/v43_supervisor.py validates the shared seal then runs Bolt followed by DeepSeek with exact completed-resume semantics. It records started/completed/blocked status and model-specific diagnostic results atomically. It must proceed to DeepSeek after Bolt quality failure if engineering/identity/audit controls remain valid. No source edits after seal/launch, no inference outside the two manifests.

Report all48 started denominators separately by model/condition; strict primary, frozen-v4.1/v3, DNF, false-refusal on answerable started, FP, actual required retrieval coverage, C1/C2 validity, unsupported/corrected/first-success calls, acquisition phases, raw format, semantic/unit/period/source correctness, accepted fabricated/mismatched evidence, reconciled requests/tokens/latency/cost availability. Failure-stage metrics must call missing operands retrieval failure, not arithmetic failure. CI95/task-cluster and payload-family sensitivity are exploratory on only three known regression clusters; repeats are not independent tasks. Quality is not superiority. Completion grants no production installation permission.
