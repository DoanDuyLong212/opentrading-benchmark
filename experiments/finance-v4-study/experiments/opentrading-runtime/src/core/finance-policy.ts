/** Opt-in native read-only finance safeguards. No task IDs, oracle or financial gold. */
import Ajv from "ajv"
import type { JSONSchema7 } from "@ai-sdk/provider"
import type { ToolDef } from "./tools/types"

export interface FinancePolicyOptions { enabled: true; machineResponse?: boolean }
const ajv = new Ajv({ strict: false, strictSchema: true, allErrors: true, coerceTypes: false, useDefaults: false, removeAdditional: false, validateFormats: false })
const key = (v: unknown): string => JSON.stringify(v, (_k, x) => x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.entries(x).sort(([a],[b])=>a.localeCompare(b))) : x)
const obj = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v)
const path = (v: unknown, p: string): unknown => p.split(".").reduce<unknown>((x,k)=>obj(x) ? x[k] : undefined,v)
const immutableClone = (value: unknown): unknown => {
  const copy: unknown = structuredClone(value)
  const freeze = (v: unknown): unknown => { if (v && typeof v === "object") { for (const child of Object.values(v)) freeze(child); Object.freeze(v) }; return v }
  return freeze(copy)
}
export class FinancePolicyState {
  readonly localRejections = new Map<string, {code:"invalid_tool_input"|"policy_guard_rejected";tool:string;rawInput:string;reason?:string}>()
  readonly successes: { tool: string; canonical: string; value: unknown }[] = []
  readonly failures = new Map<string, { args: Set<string>; eligible: boolean; attempts: number; message: string; intent: unknown }>()
  private validators = new WeakMap<object, ReturnType<typeof ajv.compile>>()
  constructor(readonly options: FinancePolicyOptions, readonly input: string) {}
  validate(def: ToolDef, value: unknown) {
    if (!obj(def.input)) return { success: false as const, error: new Error("unsupported_schema: MCP input contract must be an object schema; arguments were not executed.") }
    let validate = this.validators.get(def.input)
    if (!validate) { validate = ajv.compile(def.input as JSONSchema7); this.validators.set(def.input, validate) }
    if (validate(value)) return { success: true as const, value }
    const error = new Error(`invalid_argument: ${ajv.errorsText(validate.errors)}. Correct arguments to the declared schema; rejected input is not evidence of missing data.`)
    this.failed(def,value,error)
    return { success: false as const, error }
  }
  before(def: ToolDef, input: unknown) {
    const f = this.failures.get(def.name)
    if (f && obj(f.intent) && obj(input) && obj(def.input) && obj(def.input.properties)) {
      for (const [name, schema] of Object.entries(def.input.properties)) {
        if (!obj(schema) || !/symbol|ticker|currency|entity|peers/i.test(name)) continue
        const prior = f.intent[name]
        // Normalize only for comparison, never mutate model arguments or choose a
        // catalog request. Read-only batches may retain all original targets.
        const entities = (v: unknown): string[] => (Array.isArray(v) ? v : typeof v === "string" ? [v] : []).filter((x): x is string=>typeof x === "string").map(x=>x.trim().toUpperCase()).filter(Boolean)
        const original = entities(prior), corrected = new Set(entities(input[name]))
        if (original.some(v=>!corrected.has(v)) || (!def.readOnly && original.length !== corrected.size)) throw new Error("Tool correction changed the original entity/currency scope; rejected without execution.")
      }
    }
    if (f && obj(f.intent) && obj(input) && obj(def.input) && obj(def.input.properties)) {
      for (const [name, schema] of Object.entries(def.input.properties)) {
        if (!/^(year|quarter|month|date|startDate|endDate|fromDate|toDate|period|start|end|from|to|scope|consolidated)$/i.test(name)) continue
        const prior = f.intent[name]
        if (prior === undefined) continue
        // Preserve valid requested scope. Invalid declared enum/type may be repaired;
        // invalid optional presentation windows (days/interval) are not intent fields.
        if (obj(schema) && Array.isArray(schema.enum) && !schema.enum.includes(prior)) continue
        if (String(prior).trim().toUpperCase() !== String(input[name]).trim().toUpperCase()) throw new Error("Tool correction changed the original temporal/financial scope; rejected without execution.")
      }
    }
    if (f && (!f.eligible || f.attempts >= 2 || f.args.has(key(input)))) throw new Error("Tool correction exhausted or repeated rejected arguments; do not replay this request.")
  }
  failed(def: ToolDef, input: unknown, error: unknown) {
    const prior = this.failures.get(def.name)
    const message = error instanceof Error ? error.message : String(error)
    const eligible = def.readOnly && /invalid.argument|invalid.request|not.recorded|schema|parse|validation/i.test(message) && !/auth|permission|unauthorized|forbidden|no.data|not.found|unavailable/i.test(message)
    const f = prior ?? { args: new Set<string>(), eligible, attempts: 0, message, intent: immutableClone(input) }
    f.args.add(key(input)); f.attempts++; f.eligible &&= eligible; f.message = message; this.failures.set(def.name,f)
  }
  succeeded(def: ToolDef, value: unknown) {
    const text = typeof value === "string" ? value : obj(value) && typeof value.output === "string" ? value.output : undefined
    let parsed: unknown = value
    try { if (text !== undefined) parsed = JSON.parse(text.includes("<structuredContent>\n") ? text.split("<structuredContent>\n").at(-1)! : text.replace(/^\[ref r\d+\]\s*/, "")) } catch {}
    this.successes.push({tool:def.name, canonical:def.canonicalName ?? def.name, value:immutableClone(parsed)})
    this.failures.delete(def.name)
  }
  correctionTools() { return [...this.failures].filter(([,v])=>v.eligible && v.attempts < 2).map(([k])=>k) }
  /** Contract keys come from user-provided JSON examples, including appended evidence mapping. */
  issues(text: string, defs: ToolDef[]): string[] {
    if (!this.options.machineResponse) return []
    let value: unknown
    try { value = JSON.parse(text) } catch { return ["Final response must be exactly one JSON object, without markdown or surrounding prose."] }
    if (!obj(value)) return ["Final response must be a JSON object."]
    const issues: string[] = []
    const nullable = new Set([...this.input.matchAll(/["`]?([A-Za-z_]\w*)["`]?\s*(?::|=|(?:với|là|as)\s+(?:JSON\s+)?)\s*["`]?null\b/gu)].map(m=>m[1]))
    let sourceContract = /source[^\n]{0,160}(?:tên tool|tool name|catalog|namespace tool)/i.test(this.input)
    const examples = [...this.input.matchAll(/```json\s*([\s\S]*?)```/g)]
    for (const example of examples) {
      try {
        const e = JSON.parse(example[1]!)
        if (obj(e)) for (const k of Object.keys(e)) {
          const optional = typeof e[k] === "string" && /tuỳ chọn|tùy chọn|optional/i.test(e[k])
          if (!(k in value)) { if (!optional) issues.push(`Missing requested field: ${k}`); continue }
          // JSON examples declare public field shapes; null refusal remains permitted
          // only when the user explicitly discusses null in the requested contract.
          if (k === "source" && typeof e[k] === "string" && defs.some(d=>e[k] === (d.canonicalName ?? d.name))) sourceContract = true
          if (value[k] === null && nullable.has(k)) continue
          const shape = (v: unknown) => Array.isArray(v) ? "array" : v === null ? "null" : typeof v
          if (shape(e[k]) !== shape(value[k])) issues.push(`Requested field has wrong JSON type: ${k}; expected ${shape(e[k])}`)
        }
      } catch {}
    }
    const names = new Set(defs.map(d=>d.canonicalName ?? d.name))
    if (sourceContract && typeof value.source === "string" && !value.source.split(/[,;]+/).every(s=>names.has(s.trim()))) issues.push("source must use exact registered tool names, not provider names or invented aliases.")
    // Parse public evidence field mapping supplied by caller/user, never a hidden grader schema.
    const mappings = [...this.input.matchAll(/\{[^{}]*"tool"\s*:[^{}]*\}/g)].map(m=>{try{return JSON.parse(m[0])}catch{return undefined}}).filter(obj)
    const mapping = mappings.find(m=>Object.values(m).some(v=>typeof v === "string" && v.includes(".")))
    if (mapping) {
      if (!Array.isArray(value.evidence)) issues.push("Required evidence must be an array copied from actual successful tool results.")
      else for (const row of value.evidence) {
        const matched = obj(row) && this.successes.some(s=>Object.entries(mapping).every(([k,p])=> {
          const expected = k === "tool" ? s.canonical : typeof p === "string" ? path(s.value,p) : undefined
          return expected !== undefined && key(row[k]) === key(expected)
        }))
        if (!matched) issues.push("Evidence row does not exactly match any actual successful tool response; copy public mapped fields unchanged.")
      }
      if (value.value !== null && Array.isArray(value.evidence) && value.evidence.length === 0) issues.push("Non-null answer requires actual successful tool evidence.")
    }
    return [...new Set(issues)]
  }
}
