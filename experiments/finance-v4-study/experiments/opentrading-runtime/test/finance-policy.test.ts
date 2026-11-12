import { test, expect } from "bun:test"
import { FinancePolicyState } from "../src/core/finance-policy"
import { ToolRegistry } from "../src/core/tools/registry"
import type { ToolDef } from "../src/core/tools/types"
const def:ToolDef={name:"mcp_quote",canonicalName:"quote",source:"mcp:test",description:"quote",readOnly:true,input:{type:"object",properties:{symbol:{type:"string"}},required:["symbol"],additionalProperties:false},async execute(){return "{}"}}
test("raw validation does not coerce/default/remove and preserves nested constraints",()=>{
 const s=new FinancePolicyState({enabled:true},"");const args={symbol:12,extra:true};expect(s.validate(def,args).success).toBe(false);expect(args).toEqual({symbol:12,extra:true})
 expect(s.validate({...def,input:{type:"object",properties:{x:{type:"string",enum:["a"]}},required:["x"]}},{x:"b"}).success).toBe(false)
})
test("correction forbids identical arguments and more than one failed changed request",()=>{
 const s=new FinancePolicyState({enabled:true},"");s.failed(def,{symbol:"A",days:1},new Error("not_recorded"));expect(s.correctionTools()).toEqual([def.name]);expect(()=>s.before(def,{days:1,symbol:"A"})).toThrow();s.before(def,{symbol:"A"});s.failed(def,{symbol:"A"},new Error("not_recorded"));expect(s.correctionTools()).toEqual([]);expect(()=>s.before(def,{symbol:"B"})).toThrow()
})
test("side effects, auth, no-data cannot enter correction eligibility",()=>{
 for(const [d,error] of [[{...def,readOnly:false},"invalid_argument"],[def,"invalid_argument unauthorized"],[def,"no_data"],[def,"not_found"]] as const){const s=new FinancePolicyState({enabled:true},"");s.failed(d,{},new Error(error));expect(s.correctionTools()).toEqual([])}
})
test("provenance contract is derived from public user mapping and immutable successful results",()=>{
 const s=new FinancePolicyState({enabled:true,machineResponse:true},'source là tên tool trong catalog. Add evidence [{"tool":"public tool", "origin":"meta.vendor", "receipt":"audit.receipt"}]');s.succeeded(def,{output:JSON.stringify({meta:{vendor:"real"},audit:{receipt:"r1"}})})
 expect(s.issues(JSON.stringify({value:1,source:"quote",evidence:[{tool:"quote",origin:"real",receipt:"r1"}]}),[def])).toEqual([])
 expect(s.issues(JSON.stringify({value:1,source:"quote",evidence:[{tool:"quote",origin:"fake",receipt:"r1"}]}),[def])).toHaveLength(1)
 expect(s.issues(JSON.stringify({value:1,source:"provider",evidence:[]}),[def]).length).toBeGreaterThan(0)
})
test("baseline registry continues accepting raw object without schema validation",async()=>{
 let args:unknown;const r=new ToolRegistry();r.register({...def,async execute(x){args=x;return "okay"}});const built=r.toToolSet();const schema=built.tools[def.name]!.inputSchema as {validate?:unknown};expect(schema.validate).toBeUndefined()
 await built.tools[def.name]!.execute!({symbol:1},{toolCallId:"c",messages:[]} as never);expect(args).toEqual({symbol:1})
})

test("correcting query cannot silently switch requested entity/currency",()=>{
 const s=new FinancePolicyState({enabled:true},"");s.failed(def,{symbol:"ABC"},new Error("not_recorded"));expect(()=>s.before(def,{symbol:"XYZ"})).toThrow("entity/currency")
})
test("MCP output policy preserves structured data, deduplicates equivalent JSON, validates without replay",async()=>{
 const {resultToOutput}=await import("../src/core/mcp/convert")
 const schema={type:"object" as const,properties:{value:{type:"number" as const}},required:["value"]}
 expect(resultToOutput({content:[{type:"text",text:'{"value":2}'}],structuredContent:{value:2}},{outputSchema:schema})).toBe('{"value":2}')
 expect(resultToOutput({content:[{type:"text",text:"human summary"}],structuredContent:{value:2}},{outputSchema:schema})).toContain('<structuredContent>\n{"value":2}')
 expect(()=>resultToOutput({content:[{type:"text",text:"okay"}],structuredContent:{value:"bad"}},{outputSchema:schema})).toThrow("output_contract")
 expect(resultToOutput({content:[{type:"text",text:"human summary"}],structuredContent:{value:2}})).toBe("human summary")
})

test("null permitted for requested value does not make source or other fields nullable",()=>{
 const s=new FinancePolicyState({enabled:true,machineResponse:true},'value: null when unavailable. source là tên tool catalog. ```json\n{"value":0,"source":"quote"}\n```')
 expect(s.issues('{"value":null,"source":null}',[def])).toContain("Requested field has wrong JSON type: source; expected string")
 expect(s.issues('{"value":null,"source":"mcp_quote"}',[def])).toHaveLength(1)
 expect(s.issues('{"value":null,"source":"quote"}',[def])).toEqual([])
 const provider=new FinancePolicyState({enabled:true,machineResponse:true},'Return JSON with source as the provider. ```json\n{"source":"provider"}\n```')
 expect(provider.issues('{"source":"provider"}',[def])).toEqual([])
})

test("scope comparison allows model scalar-to-list repair, batch reorder and readonly supersets without mutating args",()=>{
 const batch={...def,input:{type:"object" as const,properties:{symbols:{type:"array" as const,items:{type:"string" as const}},peers:{type:"array" as const,items:{type:"string" as const}}}}}
 const cases:[unknown,unknown,boolean][]=[[{symbols:"USDVND"},{symbols:["USDVND"]},true],[{symbols:["ABC","XYZ"]},{symbols:["xyz","abc"]},true],[{symbols:["XAU"]},{symbols:["USDVND","XAU"]},true],[{symbols:["ABC"]},{symbols:["XYZ"]},false],[{peers:["ABC","XYZ"]},{peers:["ABC"]},false]]
 for(const [original,corrected,allowed] of cases){const state=new FinancePolicyState({enabled:true},"");state.failed(batch,original,new Error("invalid_argument"));const before=JSON.stringify(corrected);if(allowed)expect(()=>state.before(batch,corrected)).not.toThrow();else expect(()=>state.before(batch,corrected)).toThrow("entity/currency");expect(JSON.stringify(corrected)).toBe(before)}
})

test("unsupported schema keyword fails closed rather than silently weakening validation",()=>{
 const s=new FinancePolicyState({enabled:true},"")
 expect(()=>s.validate({...def,input:{type:"object",properties:{symbol:{type:"string",madeUpConstraint:true} as never}}},{symbol:"ABC"})).toThrow("unknown keyword")
})
test("successful provenance is an immutable clone of actual structured result",()=>{
 const s=new FinancePolicyState({enabled:true,machineResponse:true},'Add evidence [{"tool":"public tool", "receipt":"audit.receipt"}]');const actual={audit:{receipt:"r1"}};s.succeeded(def,actual);actual.audit.receipt="mutated"
 expect(s.issues('{"value":1,"evidence":[{"tool":"quote","receipt":"r1"}]}',[def])).toEqual([])
 expect(Object.isFrozen(s.successes[0]!.value)).toBe(true)
})
test("corrected request preserves declared temporal and financial scope",()=>{
 const d={...def,input:{type:"object" as const,properties:{symbol:{type:"string" as const},year:{type:"integer" as const},quarter:{type:"integer" as const},days:{type:"integer" as const}}}}
 const s=new FinancePolicyState({enabled:true},"");s.failed(d,{symbol:"ABC",year:2025,quarter:1,days:1},new Error("not_recorded"))
 expect(()=>s.before(d,{symbol:"ABC",year:2024,quarter:1})).toThrow("temporal")
 expect(()=>s.before(d,{symbol:"ABC",year:2025,quarter:2})).toThrow("temporal")
 expect(()=>s.before(d,{symbol:"ABC",year:2025,quarter:1})).not.toThrow()
})

test("malformed and non-object MCP root contracts fail closed",()=>{
 const s=new FinancePolicyState({enabled:true},"")
 for(const input of [false,true,null,[],"object"]) expect(s.validate({...def,input:input as never},{symbol:"ABC"}).success).toBe(false)
})
