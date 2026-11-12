# OpenTrading architecture facts — 05/11/2026

This is an evidence extraction report for the parent review. No production code, prompts, benchmark policy, archived run, or dependencies were changed; no model requests or tests were run. Exact source excerpts are copied in `source-excerpts.md`; selected actual native request messages and finals in `selected-traces.json`.

## Scope and integrity

- Current `/home/doanlong/OpenTrading/src`: 127 TypeScript/TSX files. All 127 match `experiments/opentrading-runtime/src` byte for byte at this audit. Full inventory and hashes: `source-inventory.json`. Another 31 generated legacy Python __pycache__ files remain in original src but are not loaded by the TypeScript entry point and are excluded from source equivalence; the inventory records them separately.
- Consequently the two installed runtime files (`src/core/agent.ts`, `src/core/prompt/assemble.ts`) match the studied runtime. Original prompts remain baseline, unlike the finance prompt files in the experimental copy. Original `test/agent.test.ts` and `test/prompt.test.ts` remain older; `test/financial-prompt.test.ts` is only in the experimental copy. These seven differences are intentional consequences of runtime-only install, not source drift.
- Reviewed runtime/control paths in detail; inventoried other source paths. This is not a claim that every TUI line was manually audited. Production skills, memory, subagents, web, multi-turn compaction and UI are mapped below, but pilot cannot measure their quality because they were disabled or bypassed.
- Actual installed versions read from package JSONs: `ai 7.0.137`, `@ai-sdk/provider-utils 5.0.58`, `@ai-sdk/provider 4.0.26`, `@ai-sdk/openai-compatible 3.0.67`, `@modelcontextprotocol/sdk 1.32.1`, `zod 4.6.5`.

## Subsystem map

| Subsystem | Current source and behavior | Studied pilot exposure |
|---|---|---|
| App startup/runtime | `src/index.tsx`; `src/core/runtime.ts:59–115` builds registry, permission gate, MCP, questions, hooks, memory and subagent manager | Headless wrapper calls same initRuntime, then unregisters all non-snapshot tools |
| Prompt assembly | `src/core/prompt/assemble.ts:181–226`: identity, tools, citations, profile, memory policy, style, skills, MCP instructions. Layer budgets in `prompt/budget.ts:19–38`; estimates chars/4 | Native OT system prompt, empty isolated profile, no skills/memory. Baseline and finance differ only trusted prompt directory |
| Priority | `prompts/identity.md:12–13`: safety/system outrank direct user; `assemble.ts:141–142` marks MCP guidance below user | Active; user JSON contract competes with baseline system style |
| Tool declaration | `tools/registry.ts:160–198` native Zod or MCP dynamicTool with sanitized JSON Schema; native-first/server-priority selection | Only task-allowed snapshot MCP definitions visible; no builtin calculator or web |
| Native loop | `agent.ts:759–971`: streamText → tools → next model step; tool events and safe interrupted history | Active; wrapper uses native runAgent, not replacement loop |
| Name repair | `agent.ts:223–257`: only NoSuchToolError; unambiguous short-name rewrite or deferred-tool activation | Active but no argument-type repair |
| Tool failure feedback | `mcp/convert.ts:59` throws MCP isError; `agent.ts:423–435` emits ok:false; `tools/errors.ts:94–125` cleans SDK error strings | Active; actual complete feedback visible in next request |
| MCP connections | `mcp/manager.ts:559–641,763–835`: trust, stdio/HTTP/SSE, reconnect; `904–1024` tool sync and execution | Snapshot stdio only; production remote reconnect/auth/retry paths not exercised |
| Tool timeout/output | `tools/wrap.ts:86–140` signal + race, lock, output cap; types defaults 60s/30,000 chars; MCP manager applies per-server timeout/backstop | Active but selected small rejected results not truncated; no observed evidence this caused HPG failure |
| Loop/budget | `agent.ts:39–41,787–788,842–860`: unlimited steps unless opts/config; `tools/loop-guard.ts:8–24` stops identical consecutive calls at threshold 3 via gate | Benchmark gateway separately enforces 24 model requests, 2,048 output/request, 48,000 policy token budget, timeout240; no evidence native infinity exhausted observed failed HPG budget |
| Provider | `providers.ts:54–101,138–141` SDK selected by catalog; compatible SDK includes usage; custom OpenAI baseURL uses chat; Google merges turns | Same NVIDIA provider via controlled gateway. Native main generation supplies no explicit temperature/top_p/effort/output cap; gateway policy supplies controls |
| Nudge | `agent.ts:88–96,849–860` only verified SDK routes; openai-compatible/NVIDIA gets no per-tool nudge | Actual NVIDIA captures contain no trailing nudge. Generic TOOL_NUDGE focuses source/date/unit/table, not schema repair |
| Skills/tool search | `skills/{loader,catalog}.ts`, `tools/builtin/{load-skill,tool-search}.ts`; matching requires tools; optional deferred tools over40 or10%context (`agent.ts:515–535`) | Wrapper skills[] and removes load_skill/tool_search, so cannot cause pilot routing failures |
| Memory/hooks | `memory/file-memory.ts:18–21` approved durable user preferences, no market facts; `agent.ts:765–783` recalls/hooks; `runtime.ts:124–131` switching | No memory/hook objects passed to runAgent. Excluded |
| Subagents | `subagents/manager.ts:404–415` same runAgent with independent history/role/model/maxSteps and own child tools; model-pick/limiter/sidechain | Removed. Cannot attribute pilot gap to lack of parallel subagents |
| Context/history | `core/session/{store,transcript,export}.ts`; `compact.ts:21–52,162–180`; TUI `app.ts:115,198` triggers prune/summarize | Fresh history[] for every trial, TUI not called. No compaction occurred |
| Clock | `prompt/market-clock.ts`; `agent.ts:603`; `assemble.ts:237–243` supports snapshot suppressing live reminder | OT passes frozen midnight+07 and snapshot policy. OC/DSH internal live clock not claimed pinned |
| Output validation | `agent.ts:837–868,935–944` streams plain text and marks completed; no caller-supplied answer schema, unit/period/math validator | Benchmark downstream strict grader, not native validator, catches JSON/evidence/period/math errors |
| Math/visualization | `tools/chart/*` calculates/plots known data refs; `tools/refs.ts` records raw full MCP data; no general finance calculation tool registered by runtime.ts | All chart tools removed. LLM does arithmetic/output itself; MCP finance tools may provide precomputed values |
| TUI/session controls | `src/tui/*` app, input/images, dialogs, approvals, watchlist, transcript; `core/ask.ts`, permissions, auth | Native UI not run. Headless source quality is not an evaluation of full app usability |
| Tests | Native tests include agent, tool errors, MCP real results/schema/output, retry/image, skills/routing, subagents, memory, compact, TUI | Prior 466 native /250 benchmark reported; not rerun here. Routing eval is keyword/skill matching, not LLM finance correctness (`test/routing-eval.test.ts:11–19,37–44`). Description lint examines captured fixture (`tool-desc-lint.test.ts:23–25,75–97`) |

## Findings tied to observed failures

### A. Missing local MCP argument validation: demonstrated behavior, gap magnitude remains unisolated

`tools/registry.ts:189` constructs `jsonSchema(this.schemaFor(def, flavor))` without a validation function. Actual dependency `node_modules/@ai-sdk/provider-utils/src/schema.ts:105–128` stores `validate` as optional; `validate-types.ts:67–68` explicitly returns success for any value when it is absent. JSON is parsed, but MCP JSON Schema constraints are not enforced locally. The MCP server ultimately enforces them.

Actual `fin-l1-quote-01__opentrading_finance__r1` calls `columns:"close"` even though actual provider schema requires array-of-string or null. The call reaches MCP and is rejected. Baseline peer_compare run2 similarly sends `metrics:"P/E, P/B, ROE"` where schema type is not met. This is a real unvalidated-execution path; it does not establish that a local validator alone would make the model repair or answer correctly.

OT `repairCall` deliberately only addresses unknown names (`agent.ts:233`), so there is no argument repair policy. A valid-JSON/schema-invalid call cannot enter schema repair via SDK if the registry supplies no validator; a server replay rejection is an execution error, also outside the parse-repair hook.

Shared counterevidence: native OC/DSH also have many replay-rejected calls; all arms' failures must be classified into invalid-schema vs valid-schema-but-not-recorded. DSH adapter `.../@deepseek-ai/dsh-mcp-client/lib/index.js:127–147,179–187` forwards raw input schema and output schema; its immediate executor only verifies args is an object (`230`) before call, so one cannot infer full DSH input validation from this adapter alone. OC binary source was not reverse-engineered here. Actual wire schemas below establish what models saw, not a complete causal isolation.

### B. Error feedback arrived intact; model stopped instead of repairing

HPG finance run1 second native request includes the entire error JSON: invalid_request; retryable_with_corrected_arguments=true; snapshot_requests=[{"symbol":"HPG"}]; and guidance that rejection does not prove missing data. It is only ~500 chars, below both native error caps. The final nevertheless claims it cannot find data and returns null. Baseline peer_compare run2 similarly receives complete error guidance before returning nulls. No evidence of dropped MCP isError, missing feedback, truncation, request cap or timeout in these two trials.

Files are sealed in `selected-traces.json` including exact native capture paths and raw-message hashes. Example HPG native capture: `results/financial-prompt-v3-pilot-20261105/trials/fin-l1-quote-01__opentrading_finance__r1/attempts/01-cf82421ab84a/provider-requests/0002-native.json`. Error-path root cause is unsupported model repair behavior, not server asserting true absence. A bounded recovery state needs separate validation experiments.

### C. Primary loss after successful retrieval: no native financial/output postcondition

- `fin-l2-growth-01__opentrading_finance__r1`: MCP financial_statements returned Q4/2025–Q3/2026 figures with complete evidence in native request2. Final JSON value -5.63 and Q2-vs-Q1 period do not match latest Q3-vs-Q2 request/gold -2.03. Grader provenance passed. This is semantic period/math selection failure after successful data access.
- `fin-l5-compare-01__opentrading_finance__r1`: all 15 reported financial metrics and ranking match, but canonical evidence name is wrong, failing provenance. Same source data/evidence were fully available in native request2. Raw output receives no OT final validation.
- `fin-l1-quote-01__opentrading_baseline__r2`: correct 21.0 nghìn đồng and 30/10/2026 retrieved/reported but missing required evidence, so primary fails. Tool-call success and finance correctness are distinct endpoints.

The missing contract validation is a native capability gap, not proof another harness has a deterministic finance validator. OC/DSH also output invalid evidence; downstream graders are shared. Any next implementation should separate untrusted generated values, derived calculations and immutable tool provenance; never synthesize benchmark IDs.

### D. Prompt conflict and high context cost are real; prompt rewrite alone did not solve quality

Current baseline `prompts/style.md:16` says no JSON; `prompts/tools.md:4` hides tool names; `prompts/citations.md:6` converts money to đồng and percentages one decimal. System priority (`identity.md:13`) outranks user output contract. This conflicts with benchmark JSON, canonical source names, original units and precision. Native does not offer explicit machine-output contract overriding presentation only.

Actual HPG request1 system lengths: baseline7892, finance6430, OpenCode1871, DSH307 chars. Each saw one MCP tool. OTfinance removes relevant formatting conflicts yet still12/44, equal baseline; therefore neither shorter prompt nor those conflicts alone explain the gap. Token/latency claims should use full pilot metrics and partial-usage rules. No unsupported claim that long prompts universally reduce finance reasoning.

### E. Schema sanitization weakens contracts; specific HPG rejection is not caused by this weakening

`mcp/schema.ts:184` unconditionally deletes root additionalProperties, unlike actual OC/DSH native HPG captures retaining false. `NOISE` line33 drops examples; >6000chars may drop nested defaults/descriptions (`206–208`); root unions are flattened (`185–195`); booleans become open schema (`100–101`). Property-retention tests (`mcp-schema.test.ts:44–79`) do not prove equivalent accepted language.

HPG days/interval/columns are already known properties, so root additionalProperties removal does NOT explain columns wrong type or replay-only days=1. Preserve this causal distinction. Broad production schemas can lose important conditional/exclusivity constraints; no such degraded large schema was isolated as a pilot loss here.

### F. MCP result handling ignores outputSchema, structuredContent can disappear behind text

`mcp/manager.ts:957–969` deliberately calls low-level client.request, skipping SDK client.callTool outputSchema validation to avoid duplicate effects if a completed write returns malformed data. This is a documented tradeoff, not an accidental retry bug. `mcp/convert.ts:57` includes structuredContent only when no text/images were present. If text is a short human summary while authoritative financial structure lives in structuredContent, OT model will receive only summary. Native tool definition does not preserve outputSchema in ToolDef.

DSH adapter uses client.callTool and preserves outputSchema (`index.js:138,140,186`). Snapshot pilot payloads are JSON text, so this particular OT structuredContent risk is not demonstrated in pilot. A future strict read-only finance mode can validate output and report contract failure without replaying writes. Do not add blind retries of completed side effects.

### G. Native operational controls are not the observed short-call failure

Native default maxSteps infinity and no turn-wide token/cost limit are static production risks. Tools have timeout and output cap, read/write lock, identical-call loop guard, and retry policy already. Claims that OT has no timeouts/loop guard would be incorrect. Benchmark external controls enforce same cap. HPG stops after one failed tool and next model final; no budget exhaustion caused these rejections. NVIDIA route excludes generic tool nudge; enabling it is not a proven fix and requires API/behavior tests.

## Exact API facts usable by a later implementation plan

- Local validator seam exists: `jsonSchema<OBJECT>(schema, { validate?: (value: unknown) => ValidationResult<OBJECT> | PromiseLike<ValidationResult<OBJECT>> })`, provider-utils5.0.58 `src/schema.ts:105–128`. Must validate against authoritative raw schema as well as account for model-visible dialect. No validator dependency chosen in this audit.
- AI7.0.137 `streamText` accepts `repairToolCall?: ToolCallRepairFunction` at `src/generate-text/stream-text.ts:577`; existing OT uses `experimental_repairToolCall`, a deprecated but supported alias (`584`). Callback source `tool-call-repair-function.ts:22–34` receives instructions/system/messages/toolCall/tools/inputSchema({toolName})/error(NoSuchToolError|InvalidToolInputError)/abortSignal, returns Promise<LanguageModelV4ToolCall|null>. It handles parse/validation failures, not general server execution/replay errors.
- `streamText` accepts `output?: OUTPUT` (`540`); `Output.object({schema,name?,description?})` is implemented in `src/generate-text/output.ts:94–110`, with schema-derived responseFormat (`116–121`) and final parse/validation. OT does not currently expose it in RunOptions. Provider support must be tested; never assume NVIDIA supports every strict output mode.
- Native runtime has no general financial calculator/typed financial-answer object or evidence serializer. Chart refs preserve full data for chart computations (`tools/wrap.ts:12–19`), but that does not validate generated final finance JSON.

## Boundaries and confidence

High confidence: source equality, active headless boundary, exact SDK signatures, argument-validation omission, actual MCP errors and final messages, prompt conflicts, output contract absence. Medium confidence causal contribution: each separate change's effect on primary success; current study is not a factorial ablation. Untested static risks: production remote MCP output schema/structured-only payloads, broad catalog retrieval under128 tool cap, active finance skills, multi-agent research, memory, long conversation compaction, live clock/provider behavior outside frozen NVIDIA run.

Parent should combine these facts with whole-cohort failure extraction and production MCP-server inspection before prioritizing or claiming superiority. Frozen benchmark deliberately substitutes per-task snapshot descriptions for production MCP tool descriptions, so pilot cannot directly measure whether live MCP descriptions are good.

## Native OpenCode input preprocessing confound (parent extraction)

Parent identified installed OpenCode source `packages/opencode/src/cli/cmd/run.ts:288–290` wraps/escapes multiline CLI input before `parts.text:message` at869. Benchmark `tools/runners/run_opencode.py:76–78` passes literal argv normally; actual OC capture contains quoting/escaping whereas OT/DSH messages are plain. Direction of quality effect is unknown. It invalidates any claim of byte-identical user messages across native adapters, not the fact that conditions receive the same logical task. Preserve historical runs and verify a native API prompt path in a new preregistered study.
