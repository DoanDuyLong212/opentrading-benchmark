/** Synthetic offline source/compute fixture, no provider calls or main-task data. */
import {runTool,RwLock} from '../../experiments/opentrading-runtime/src/core/tools/wrap'
import {calculateTool} from '../../experiments/opentrading-runtime/src/core/tools/calculate'
import {computeTool} from '../../experiments/opentrading-runtime/src/core/tools/compute'
import {clearResults} from '../../experiments/opentrading-runtime/src/core/tools/refs'
clearResults()
const source={data:{symbol:'SYNTH',period:'Q1/2030',scope:'consolidated',rows:[{name:'sales',unit:'VNDbn',value:200},{name:'profit',unit:'VNDbn',value:25}]},availability:'available',provenance:{source:'synthetic fixture, not live',data_time:'2030-03-31'},benchmark_evidence:{call_id:'fixture-server-call',tool:'fixture.financial',matched_entry_id:'synthetic-not-live',payload_sha256:'1'.repeat(64),response_sha256:'2'.repeat(64),source:'synthetic-fixture',as_of:'2030-04-01'}}
const ctx={signal:new AbortController().signal,callId:'fixture-sdk-call',groundedFinancial:true}
const result=await runTool({name:'fixture_financial',canonicalName:'fixture.financial',description:'synthetic fixture',source:'mcp:fixture',readOnly:true,input:{type:'object'},execute:async()=>JSON.stringify(source)},{},ctx,new RwLock())
const ref=/^\[ref (r\d+)\]/.exec(result.output)![1]!
const args={expression:'profit/sales',values:{profit:{from_call:ref,field:'profit'},sales:{from_call:ref,field:'sales'}},unit:'%'}
const raw=String(await calculateTool().execute(args,{...ctx,callId:'fixture-sdk-calculate'}));const parsed=JSON.parse(raw.replace(/^\[ref r\d+\]\s*/,''))
console.log(JSON.stringify({fixture:true,provider_calls:0,expected_result:12.5,kind:'native_derived',status:'ok',sdk_call_id:'fixture-sdk-calculate',tool:'calculate',arguments:args,result:parsed,source_call_ids:parsed.source_evidence.map((x:any)=>x.call_id),source_receipts:parsed.source_evidence,native_ref_ids:parsed.derived_result.inputs.map((x:any)=>x.ref),raw_source:source,source_sdk_call_id:ctx.callId},null,2))
