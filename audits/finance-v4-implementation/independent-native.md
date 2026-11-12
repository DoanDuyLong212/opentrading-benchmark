# Independent native v4 review

Scope: isolated `experiments/finance-v4-study/experiments/opentrading-runtime`, native finance policy and candidate prompts. No original application edits, provider inference, oracle access or full-suite duplication by this reviewer.

Status: **PENDING closure and final targeted verification; not approved for live inference yet.**

## Confirmed implementation properties

- Finance policy is opt-in. With the policy absent, the registry uses the prior sanitized schema, MCP conversion receives no strict contract, and streaming remains unbuffered. Native prompt/clock options remain the existing baseline behavior.
- Installed AI SDK types explicitly support `jsonSchema(raw, { validate })`, `experimental_repairToolCall`, `prepareStep`, `stopWhen` and shared `abortSignal`. The experimental repair alias is deprecated but present in installed `ai` 7.0.137.
- Model correction uses the native SDK/model, actual public error messages and registry, without hidden task identifiers, gold values or alternate answer generators. Initial invalid text remains in model history; final text is buffered and replaced rather than concatenated.
- Raw input validation disables coercion, defaults and removal. Corrected calls are executed normally; provenance comes from successful tool results. Evidence field mappings are read from the user's public contract.
- MCP output validation runs after completed execution and outside transport retry handling. An output contract error cannot trigger replay of a completed write. Actual structured content is preserved when human text differs and deduplicated when the JSON content is equal.
- Correction is bounded by failed argument history, read-only eligibility, actual native steps and the common caller/provider gateway budget. Auth/no-data errors and side effects are excluded from correction eligibility.
- Native mocked integration tests cover actual SDK request bodies and correlated tool errors, cancellation, JSON buffering/correction, request usage and max-step exhaustion. These are scripted local tests, not model-quality evidence.

## Findings sent to implementation owner before freeze

1. **Unsupported schema vocabulary was silently ignored.** `Ajv({ strict: false })` accepted undeclared constraints without a separate supported-schema guard. Required closure: reject unsupported schemas/dialects before execution for both input and output validation.
2. **Temporal scope could change during error correction.** Entity/currency comparison did not protect year/quarter/date/financial-scope fields. Required closure: protect actual declared financial temporal/scope selectors, while retaining model-authored scalar-to-array repairs and read-only batch supersets that preserve all original targets.
3. **Direct-object success provenance was mutable.** The policy retained a direct object reference. Native MCP normally returns an independently parsed string; the generic policy still requires an immutable snapshot.
4. **Empty-answer retry could bypass candidate step accounting.** Its steps/progress were not merged and its extra request was not gated by candidate maxSteps. Baseline behavior must remain unchanged when policy is off.

Previously raised root findings (canonical source namespace, field-specific nullability, batch superset comparison and correction progress/offsets) are also checked in final verification.

## Limits and rollout notes

- The machine-response checker validates the public JSON examples and explicitly supplied evidence mapping. It is not a universal natural-language contract compiler and does not independently validate financial arithmetic, period correctness or evidence coverage for every operand. Frozen benchmark grading remains necessary.
- Temporal/entity guards protect correction intent; they do not make an initially incorrect model-selected query semantically correct.
- Direct `ajv` import currently relies on the copied application's available dependency tree rather than an explicit native package declaration. The experiment must pin the actual resolved dependency; future production packaging should declare it explicitly without modifying reused dependency installations.
- No quality superiority claim follows from this source review or scripted tests. The preregistered development smoke/pilot determines measured quality.

Final closure, commands, counts and hashes will be appended after the implementation owner completes its final full native suite.
