## /home/doanlong/OpenTrading/src/core/agent.ts:215

```text
215: /**
216:  * Calls the SDK could not parse. A short name from <tool_hoan> (`vn_quote_history`,
217:  * `server/tool`) that matches one active tool is rewritten to its full name. A deferred tool
218:  * the model called before loading it cannot run at this step (AI SDK 7 parses a repaired
219:  * call against the step's active tools), but the call itself loads it: the error says so,
220:  * with its parameters, and the model calls it again instead of spending a tool_search step.
221:  * `null` = keep the SDK's own error.
222:  */
223: async function repairCall<T extends { toolName: string }>(
224:   registry: ToolRegistry,
225:   built: BuiltToolSet | undefined,
226:   active: string[] | undefined,
227:   loaded: readonly string[],
228:   toolCall: T,
229:   error: unknown,
230: ): Promise<T | null> {
231:   if (!built) return null
232:   const deferring = built.deferring || built.deferred.length > 0
233:   if (!NoSuchToolError.isInstance(error)) return null
234:   const names = resolveToolName(registry, toolCall.toolName).filter((n) => n in built.tools)
235:   if (names.length === 1 && (!active || active.includes(names[0]!))) return { ...toolCall, toolName: names[0]! }
236:   if (names.length === 1 && deferring) {
237:     const name = names[0]!
238:     // Loaded already yet still not active: cut by the per-request cap. Saying "loaded,
239:     // call again" here would loop.
240:     if (loaded.includes(name)) {
241:       throw new Error(
242:         `Tool ${name} đã nạp nhưng không gửi kèm được trong bước này: đã chạm trần ${MAX_TOOLS_PER_REQUEST} tool mỗi lần gọi model. Dùng các tool đang có để trả lời.`,
243:       )
244:     }
245:     const def = registry.get(name)
246:     // First line loads it (loadedTools reads it), also when the model used a short name.
247:     throw new Error(
248:       [
249:         `${LOADED_PREFIX}${name}`,
250:         `Tool ${name} chưa có trong bước này nên chưa chạy; đã nạp xong — gọi lại đúng lệnh với tên ${name}.`,
251:         ...(def ? ["", describeTool(registry, def)] : []),
252:       ].join("\n"),
253:     )
254:   }
255:   if (!deferring) return null
256:   const many = names.length > 1 ? ` Tên này khớp nhiều tool: ${names.join(", ")}.` : ""
257:   throw new Error(`Không có tool "${toolCall.toolName}".${many} Gọi tool_search (query "select:<tên>" hoặc từ khoá) để nạp tool rồi gọi lại.`)
```

## /home/doanlong/OpenTrading/src/core/agent.ts:837

```text
837:   const result = streamText({
838:     model,
839:     instructions: system,
840:     messages: request,
841:     tools,
842:     stopWhen: isStepCount(maxSteps),
843:     // Every step exposes what the conversation has loaded so far, so a tool found by
844:     // tool_search is callable at the very next step.
845:     // Last allowed step: keep tools declared (some providers reject tool history otherwise)
846:     // but forbid calling them, so the turn always ends with an answer.
847:     // Message overrides carry forward to later steps, so every step rebuilds its messages from
848:     // the request plus what the model and tools produced: a nudge stays a one-step addition.
849:     prepareStep: ({ stepNumber, initialMessages, responseMessages }) => {
850:       if (!tools) return undefined
851:       // Clean before activeFor reads them: the model never sees the SDK's raw error strings.
852:       const messages = cleanToolErrors([...initialMessages, ...responseMessages])
853:       active = activeFor(built, messages)
854:       loaded = loadedTools(messages)
855:       if (stepNumber < maxSteps - 1) {
856:         if (!nudge || messages.at(-1)?.role !== "tool") return { ...(active ? { activeTools: active } : {}), messages }
857:         return { ...(active ? { activeTools: active } : {}), messages: [...messages, { role: "user", content: toolNudge(messages) }] }
858:       }
859:       summarized = true
860:       return { toolChoice: "none", activeTools: active, messages: [...messages, { role: "user", content: SUMMARY_PROMPT }] }
861:     },
862:     experimental_repairToolCall: async ({ toolCall, error }) => repairCall(opts.registry, built, active, loaded, toolCall, error),
863:     abortSignal,
864:     // The model is wrapped with retry.ts (by kind of failure, shown to the user, Esc
865:     // cancels the wait); the SDK's blind retry would repeat a daily-quota 429.
866:     maxRetries: 0,
867:     onError: () => {}, // errors are read from the stream
```

## /home/doanlong/OpenTrading/src/core/agent.ts:888

```text
888:   // Completed, but the model said nothing: ask once more for the actual answer.
889:   if (messages && !outcome.text.trim()) {
890:     const usedTools = messages.some((m) => m.role === "tool")
891:     const kept = messages.filter((m) => !isEmptyAssistant(m))
892:     const retry = streamText({
893:       model,
894:       instructions: system,
895:       // The nudge is only for this request; it is not kept in history.
896:       messages: [...request, ...kept, { role: "user", content: NUDGE_PROMPT }],
897:       tools,
898:       activeTools: activeFor(built, [...request, ...kept]),
899:       toolChoice: tools ? "none" : undefined,
900:       abortSignal,
901:       maxRetries: 0,
902:       onError: () => {},
```

## /home/doanlong/OpenTrading/src/core/mcp/schema.ts:174

```text
174: /** Above this many characters a tool schema gets compacted. */
175: export const COMPACT_OVER_CHARS = 6000
176: 
177: export function sanitizeSchema(schema: unknown, flavor: SchemaFlavor = "default", compactOver = COMPACT_OVER_CHARS): JSONSchema7 {
178:   const root = isObj(schema) ? schema : {}
179:   let out = clean(inlineRefs(root), flavor) as Node
180:   // The root must be a plain object schema: several providers reject root
181:   // `additionalProperties` and combinators. A root union ("give path OR url") is flattened:
182:   // every variant's parameters become optional root parameters, so none is lost; `allOf`
183:   // parts all apply, so their `required` lists are kept too.
184:   delete out.additionalProperties
185:   for (const key of ["allOf", "anyOf", "oneOf"] as const) {
186:     const variants = out[key]
187:     if (!Array.isArray(variants)) continue
188:     for (const variant of variants) {
189:       if (!isObj(variant)) continue
190:       if (isObj(variant.properties)) out.properties = { ...variant.properties, ...(isObj(out.properties) ? out.properties : {}) }
191:       if (key === "allOf" && Array.isArray(variant.required)) {
192:         out.required = [...new Set([...(Array.isArray(out.required) ? out.required : []), ...variant.required])]
193:       }
194:     }
195:     delete out[key]
196:   }
197:   if (Array.isArray(out.required)) {
198:     const props = isObj(out.properties) ? out.properties : {}
199:     out.required = out.required.filter((r) => typeof r === "string" && r in props)
200:     if ((out.required as unknown[]).length === 0) delete out.required
201:   }
202:   out.type = "object"
203:   if (!isObj(out.properties)) out.properties = {}
204: 
205:   const size = () => JSON.stringify(out).length
206:   if (size() > compactOver) out = stripNested(out, ["default"])
207:   if (size() > compactOver) out = stripNested(out, ["description"])
208:   if (size() > compactOver) out = cutDepth(out, 4, flavor)
209:   return out as JSONSchema7
```

## /home/doanlong/OpenTrading/src/core/mcp/convert.ts:44

```text
44: /**
45:  * Flatten an MCP tool result into what the model reads: text, plus images for models that
46:  * can see them. `isError` becomes a thrown error (the AI SDK turns it into a tool-error).
47:  * Returns a plain string when there are no images, so text-only callers stay simple.
48:  */
49: export function resultToOutput(result: CallToolResultLike): string | ToolResult {
50:   const parts: string[] = []
51:   const images: ToolImage[] = []
52:   for (const block of result.content ?? []) {
53:     const { text, image } = blockToParts(block)
54:     if (text) parts.push(text)
55:     if (image) images.push(image)
56:   }
57:   if (parts.length === 0 && images.length === 0 && result.structuredContent !== undefined) parts.push(JSON.stringify(result.structuredContent, null, 2))
58:   const text = parts.join("\n\n")
59:   if (result.isError) throw new Error(text || "MCP tool báo lỗi nhưng không kèm thông điệp.")
60:   if (images.length > 0) return { output: text || `(tool trả về ${images.length} ảnh)`, images }
61:   return text || "(tool không trả về nội dung)"
62: }
```

## /home/doanlong/OpenTrading/src/core/mcp/manager.ts:935

```text
935:       this.registry.register({
936:         name: modelName,
937:         source: `mcp:${name}`,
938:         priority,
939:         ...fields,
940:         // Raw schema; the registry sanitizes it per provider when building a request.
941:         input: (tool.inputSchema ?? { type: "object", properties: {} }) as JSONSchema7,
942:         readOnly: tool.annotations?.readOnlyHint ?? false,
943:         displayName: `${name} · ${tool.annotations?.title ?? tool.name}`,
944:         annotations: {
945:           title: tool.annotations?.title,
946:           destructive: tool.annotations?.destructiveHint,
947:           openWorld: tool.annotations?.openWorldHint,
948:         },
949:         permissionScope,
950:         // The wrapper's own timer is a backstop; the SDK enforces the real per-call timeout.
951:         // Room for waiting on a reconnect and the server's queue, and for retries of a read-only call.
952:         timeoutMs: (tool.annotations?.readOnlyHint ? 2 : 1) * toolTimeoutMs + startupTimeoutMs + 5_000,
953:         maxOutputChars: config.maxOutputChars,
954:         summarize: (input) => `${name} · ${tool.name}(${compactArgs(input)})`,
955:         execute: async (input, ctx) => {
956:           const args = (input as Record<string, unknown>) ?? {}
957:           // A plain request instead of client.callTool: callTool checks structuredContent
958:           // against the tool's outputSchema and throws on a mismatch — after the tool ran.
959:           // Retrying would run a write tool twice, so we skip that check; the model reads
960:           // the content either way.
961:           const call = (live: Live) =>
962:             live.client.request({ method: "tools/call", params: { name: tool.name, arguments: args } }, CallToolResultSchema, {
963:               signal: ctx.signal,
964:               timeout: toolTimeoutMs,
965:               resetTimeoutOnProgress: true,
966:               // Without a progress handler the SDK sends no progress token, so the timeout
967:               // could never be reset by a long-running tool reporting progress.
968:               onprogress: () => {},
969:             })
```

## /home/doanlong/OpenTrading/src/core/mcp/manager.ts:1018

```text
1018:             // Outside the try: an error the tool itself reports (isError) is an answer, not a
1019:             // dead connection, even when its text says "ECONNRESET".
1020:             return resultToOutput(result)
```

## /home/doanlong/OpenTrading/src/core/tools/registry.ts:174

```text
174:     // One guard per tool set: a turn (or a subagent run) counts its own repeats.
175:     const loop = new LoopGuard()
176:     for (const def of [...declared].sort((a, b) => a.name.localeCompare(b.name))) {
177:       const execute = (input: unknown, options: { abortSignal?: AbortSignal; toolCallId: string }) =>
178:         runTool(
179:           def,
180:           input,
181:           { signal: options.abortSignal ?? new AbortController().signal, callId: options.toolCallId, agent: this.origin, loop },
182:           this.lock,
183:           this.gate,
184:         )
185:       const toModelOutput = ({ output }: { output: unknown }) => modelOutput(output as ToolResult, opts.images ?? false)
186:       set[def.name] =
187:         def.input instanceof z.ZodType
188:           ? tool({ description: def.description, inputSchema: def.input, execute, toModelOutput })
189:           : dynamicTool({ description: def.description, inputSchema: jsonSchema(this.schemaFor(def, flavor)), execute, toModelOutput })
```
