#!/usr/bin/env bun
import {appendFileSync,mkdirSync,readFileSync} from 'node:fs'
import {resolve} from 'node:path'
import {createHash} from 'node:crypto'
import {z} from '../../experiments/opentrading-runtime/node_modules/zod'
import {completedFinalText} from './native_final'
const expectedRoot=new URL('../../experiments/opentrading-runtime/',import.meta.url).pathname.replace(/\/$/,'')
if(process.env.BENCH_OT_RUNTIME!==expectedRoot)throw new Error('Untrusted runtime locator')
const {runAgent}=await import(expectedRoot+'/src/core/agent')
const {initRuntime,createMemory,closeMemory}=await import(expectedRoot+'/src/core/runtime')
const {clearResults,useResultSession}=await import(expectedRoot+'/src/core/tools/refs')
const promptDir=process.env.BENCH_PROMPT_DIR
if(!promptDir||!['baseline','finance'].map(v=>new URL('../prompt_variants/'+v,import.meta.url).pathname).includes(promptDir))throw new Error('Untrusted prompt locator')
if(process.env.BENCH_NATIVE_RETRY_MAX!=='0')throw new Error('Native retry must be explicitly disabled; gateway owns retries')
const home=process.env.OPENTRADING_HOME
if(!home||resolve(home)!==resolve(process.cwd(),'..','runner','ot-home'))throw new Error('Isolated trial home required')
const now=new Date(process.env.BENCH_AS_OF+'T00:00:00+07:00')
if(!Number.isFinite(now.getTime()))throw new Error('Invalid snapshot date')
const memoryChoice=process.env.BENCH_MEMORY_MODE??'none'
if(!['none','notebook'].includes(memoryChoice))throw new Error('Untrusted memory mode')
const memory=createMemory(memoryChoice as 'none'|'notebook',home)
const runtime=initRuntime({cwd:process.cwd(),home,skills:()=>[],memory,scratchpad:false})
const sessionId='benchmark-isolated-turn';const sessionDir=home+'/sessions/'+sessionId
mkdirSync(sessionDir,{recursive:true});clearResults();useResultSession(sessionId,undefined,sessionDir)
const hash=(v:unknown)=>createHash('sha256').update(JSON.stringify(v)).digest('hex')
const nativeAllowed=new Set(['compute','calculate','read_result'])
if(memoryChoice==='notebook')nativeAllowed.add('memory_read')
const providerRequestIndex=()=>{
 const path=process.env.BENCH_PROVIDER_LEDGER;if(!path)return undefined
 try{const lines=readFileSync(path,'utf8').trim().split('\n');for(let i=lines.length-1;i>=0;i--){let row:any;try{row=JSON.parse(lines[i]!)}catch{continue}if(Number.isInteger(row.index))return row.index}}catch{}
 return undefined
}
const ledger=process.env.BENCH_NATIVE_LEDGER
const record=(row:unknown)=>{if(ledger)appendFileSync(ledger,JSON.stringify({...row as any,provider_request_index:providerRequestIndex()})+'\n')}
const controller=new AbortController();const stop=()=>controller.abort();process.on('SIGINT',stop);process.on('SIGTERM',stop)
try{
 await runtime.mcp.start()
 for(const tool of runtime.registry.list())if(tool.source!=='mcp:opentrading'&&!nativeAllowed.has(tool.name))runtime.registry.unregister(tool.name)
 for(const tool of runtime.registry.list()){
  if(tool.source==='mcp:opentrading')continue
  const execute=tool.execute
  tool.execute=async(input:any,ctx:any)=>{
   try{const result=await execute(input,ctx);const text=typeof result==='string'?result:result.output;let data:any;try{data=JSON.parse(text.replace(/^\[ref r\d+\]\s*/,''))}catch{}
    record({kind:data?.derived_result?'native_derived':'native_utility',status:'ok',sdk_call_id:ctx.callId,tool:tool.name,arguments:input,result:data??text,derived_id:data?.derived_result?hash([ctx.callId,data]):undefined,source_call_ids:(data?.source_evidence??[]).map((x:any)=>x.call_id),source_receipts:data?.source_evidence??[],native_ref_ids:(data?.derived_result?.inputs??[]).map((x:any)=>x.ref)})
    return result
   }catch(error){record({kind:'native_utility',status:'error',sdk_call_id:ctx.callId,tool:tool.name,arguments:input,error:error instanceof Error?error.message:String(error)});throw error}
  }
 }
 const inventory=runtime.registry.list().map((tool:any)=>({name:tool.name,source:tool.source,input:tool.input instanceof z.ZodType?z.toJSONSchema(tool.input):tool.input}))
 if(process.env.BENCH_INVENTORY)await Bun.write(process.env.BENCH_INVENTORY,JSON.stringify({skills:[],memory:memoryChoice,home_isolated:true,session_id:sessionId,native_retry_max:0,tools:inventory},null,2))
 if(!inventory.some(x=>x.source==='mcp:opentrading'))throw new Error('No snapshot source tools')
 let finalText='';let completed=false
 for await(const event of runAgent({history:[],input:Bun.argv.slice(2).join(' '),skills:[],now,clockPolicy:'snapshot',promptDir,stallMs:300000,signal:controller.signal,sessionId,hooks:runtime.hooks,memory:runtime.memory,constraints:runtime.constraints,redaction:runtime.redaction,cards:false,groundedFinancial:true,toolAuditContext:()=>({provider_request_index:providerRequestIndex(),native_session_id:sessionId}),providerRetry:{maxRetries:0},financePolicy:process.env.BENCH_FINANCE_POLICY==='on'?{enabled:true,machineResponse:true,auditContext:()=>({provider_request_index:providerRequestIndex(),native_session_id:sessionId})}:undefined,registry:runtime.registry,serverInstructions:()=>runtime.mcp.instructions()})){
  process.stderr.write(JSON.stringify({...event,provider_request_index:providerRequestIndex()})+'\n')
  if(event.type==='notice'&&event.text.startsWith('{')){try{const row=JSON.parse(event.text);if(row.event?.startsWith('financial_'))record({kind:'native_contract',...row})}catch{}}
  const text=completedFinalText(event);if(text!==undefined){finalText=text;completed=true}
 }
 if(completed)process.stdout.write(finalText)
}finally{process.off('SIGINT',stop);process.off('SIGTERM',stop);await runtime.mcp.stop();closeMemory(runtime)}
