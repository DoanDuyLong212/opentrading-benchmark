# v4.6-update: independent measurement repair and diagnostic comparison

Registered 2026-11-09 before this candidate's financial inference. This is a NEW study and NEW schedule. Original v4.5 and v4.6 artifacts, including failed/superseded cohorts, remain immutable. Old-output overlays are diagnostic only and never replace recorded primary scores.

## Scope and authority

The latest user asks for review/repair of v4.6, smoke and pilot, comparative assessment, and a detailed v4.7 plan for approval. This registration authorizes ONLY devsmoke and diagnostic pilot. MAIN, holdout, memory inference, additional canaries/models, and v4.7 implementation are forbidden. Earlier conditional-main authority is not exercised in this study. Source, prompts, corpus, graders, auditors, runtime packages, protocol and configuration freeze before first financial request. No tuning/retry for quality after inference begins.

## Repairs declared before inference

- Correct dimensional unit canonicalization: ratio/dimensionless labels must not match the currency prefix `ty`. A required meaningful unit label remains required; empty labels are not silently converted to ratio.
- Refusal matching recognizes bounded Vietnamese statements of unavailable period/entity/data without accepting unsupported-query/transport failures as proof of missing financial data. Apply the same semantics to every arm; mutation tests must reject conflicting numeric answers and false unavailability.
- Common public instructions disclose numeric precision sufficient for the unchanged absolute tolerance 1e-6, including arithmetic results. Do not round the benchmark's primary numeric field to a display-only currency precision. No tolerance relaxation and no deterministic repair/rescue of model outputs.
- Common public instructions describe full source lineage for resolver and cross-source operations. Evidence remains authenticated seven-field source receipts, not guessed labels or derived receipts substituted for source data.
- Native accepted final output is primary. Raw rejected output, local repair events, invalid JSON, formatting failures and all provider costs remain visible separately. No post hoc answer normalization to manufacture strict wins.
- Repair fail-closed generated occurrence binding, malformed/parallel/replayed calls and native rejection tracing using actual native/effective captures. A failed auditor is a measurement blocker, never silently converted into PASS.

## Schedule, models, sampling and budgets

Use the exact two previously admitted NVIDIA routes, with receipt hashes pinned in the independent engineering approval. No admission call is repeated. Super requested endpoint `nvidia/nemotron-3.5-super-vl-120b-a12b` returns `private/nvidia/nemotron-3.5-super-120b-a12b`; checkpoint equivalence remains UNVERIFIED and user-authorized. DeepSeek route is `deepseek-ai/deepseek-v4.1-flash`.

Per model, devsmoke = 12 development tasks x 2 repeats x 4 arms = 96 trials, denominator 24/arm; pilot = 22 eligible financial pilot tasks x 2 repeats x 4 arms = 176 trials, denominator 44/arm. Four arms: OT baseline B0, OT finance B1, OpenCode, DSH. Do not pool models, repeats, development and pilot tracks, or memory results. Registered schedule uses seed 20261108 and fixed interleaved arm order. Serial model cohorts avoid uncontrolled cross-model rate contention.

Super temperature 1/top_p .95; DeepSeek temperature 0/top_p 1, identical across all arms within model. Max output 8192 tokens, 24 actual upstream attempts/trial, total token budget 3,600,000/trial, 240s/provider request, 900s/trial, 2s common provider spacing. Common gateway exclusively owns eligible transport retries: initial request plus at most two retries, backoff 4/8s and bounded Retry-After, within ALL original caps; native/driver quality retries are zero. Context 1,048,576; unknown failed usage is reserved conservatively and is never presented as measured usage. Preserve every timeout/DNF, failed request and partial/unknown usage.

Only the approved pinned candidate runtime and Bun 1.4.4 binary may execute. Native prompt/tool inventories may differ as product behavior, but source tools, finite snapshot semantics, common calculator capability, model/sampling/caps/clock disclosures and isolation controls must be equal in actual captures. Memory remains none and fresh isolated home/store/session per stateless trial.

## Measurement and guards

Co-primary metrics are unchanged: strict grounded success and grounded financial correctness, with the exact same primary and secondary definitions used by the registered financial MAIN. Report raw-format validity separately from numerical/grounded correctness, source and derived evidence separately, per-family results, stable 2/2, DNF, FR, FP, required-data coverage, computation uptake, repair/failure stages, requests, all-attempt latency and measured/partial usage. Independent all-arm content review may REMOVE automatic wins only; it cannot rescue failed rows. All reviewed primaries remain provisional until source/entity/period/unit/math/narrative and capture joins have been checked.

Unchanged QUALITY qualification thresholds from v45_gate.py:
- Smoke: B1 grounded >=20/24, answerable >=14/18, traps 6/6, raw-format valid >=23/24, at least one grounded win in each growth/margin/scale/ratio/aggregate/cross-source/chain canary; strict and financial scores >=B0; no DNF/FR/FP/evidence regression vs B0; DNF<=1, FR<=2, FP=0, zero accepted fabrication.
- Pilot: B1 strict>=33/44, grounded>=35/44, answerable>=31/40, traps4/4; both co-primary scores >=each B0/OpenCode/DSH +3/44; no DNF/FR/FP/evidence regression against each; DNF<=1, FR<=2, FP=0, zero accepted fabrication.

Diagnostic pilot admission is DISTINCT from quality qualification. User explicitly requests pilot measurement even if the revised harness is not yet superior. Once both admitted model smoke cohorts are complete and independently audited, a given model may run its already registered pilot when its instrumentation audit, all-arm manual content review and zero-accepted-fabrication guard PASS and pins/caps remain valid. If its smoke QUALITY gate fails, preserve and prominently report that failure; pilot remains DIAGNOSTIC and grants no promotion, main run or superiority claim. A source/capture/instrumentation failure, accepted fabrication, invalid state/pins, or unknown review status BLOCKS pilot for that model until a separate future study is reviewed; do not patch and continue this frozen run.

## Controls and completion

Driver resume must use the exact saved manifest/settings. Graceful pause preserves completed work and stops before the next trial; hard interruption retains the active trial as interrupted/DNF and never quality-replays it. A completed resume must be intercepted and prove zero new execute/model calls plus unchanged trial/capture SHA256, sizes and mtimes. Do not infer death from sandbox PID namespace alone.

Stop at root review barriers after smoke and pilot; no automatic transition to MAIN. Deliver pilot metrics and comparative strengths/weaknesses per model, identify unresolved confounds, and prepare v4.7 plan only. Independent engineering approval must be issued by a reviewer other than implementation owners, bind exact freeze states and admission receipts, and cover actual native-wire/mutation/controls evidence before launch.
