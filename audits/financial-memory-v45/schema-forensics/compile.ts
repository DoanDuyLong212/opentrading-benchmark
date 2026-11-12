import {readFileSync,writeFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const root='/home/doanlong/extra/benchmark/experiments/finance-v45-study/experiments/opentrading-runtime'
const {FinancePolicyState}=await import(root+'/src/core/finance-policy.ts')
const {jsonSchema,safeValidateTypes}=await import(root+'/node_modules/@ai-sdk/provider-utils/dist/index.js')
const path=new URL('./all-task-schemas.json',import.meta.url).pathname
const input=JSON.parse(readFileSync(path,'utf8'));const rows:any[]=[]
function patterns(node:any,path=''):any[]{if(!node||typeof node!=='object')return[];let out:any[]=[];for(const[k,v]of Object.entries(node)){const pointer=path+'/'+k.replaceAll('~','~0').replaceAll('/','~1');if(k==='pattern'&&typeof v==='string'){try{new RegExp(v,'u')}catch(error){let loose=true;try{new RegExp(v)}catch{loose=false};out.push({path:pointer,pattern:v,unicode_error:String(error),non_unicode_compiles:loose})}}else if(v&&typeof v==='object')out.push(...patterns(v,pointer))}return out}
for(const item of input.schemas){
 const policy=new FinancePolicyState({enabled:true},'Offline public contract validation only.');const def:any={name:'mcp__opentrading__'+item.occurrences[0].tool,input:item.schema}
 let exception:any;let argumentResult:any
 try{argumentResult=policy.validate(def,item.args)}catch(error){exception=String(error)}
 const sdk=await safeValidateTypes({value:item.args,schema:jsonSchema(item.schema,{validate:(value:any)=>policy.validate(def,value)})})
 rows.push({id:item.id,occurrences:item.occurrences,bad_patterns:patterns(item.schema),native_compile_pass:!exception,native_compile_error:exception,representative_args:item.args,argument_valid:argumentResult?.success,actual_sdk_validation_success:sdk.success,actual_sdk_error:!sdk.success?{name:sdk.error.name,message:sdk.error.message,cause:sdk.error.cause?String(sdk.error.cause):null}:undefined})
}
const bad=rows.filter(r=>!r.native_compile_pass);const tasks=new Map<string,Set<string>>()
for(const row of bad)for(const occur of row.occurrences){if(!tasks.has(occur.task))tasks.set(occur.task,new Set());tasks.get(occur.task)!.add(occur.tool)}
const result={read_only:true,external_model_calls:0,bun_version:Bun.version,source_schema_json_sha256:createHash('sha256').update(readFileSync(path)).digest('hex'),unique_schemas:rows.length,bad_schemas:bad.length,affected_task_tools:bad.reduce((n,r)=>n+r.occurrences.length,0),affected_tasks:[...tasks].map(([task,tools])=>({task,tools:[...tools]})),rows}
writeFileSync(new URL('./compile-results.json',import.meta.url),JSON.stringify(result,null,2));console.log(JSON.stringify({unique_schemas:rows.length,bad_schemas:bad.length,affected_task_tools:result.affected_task_tools,affected_tasks:tasks.size}))
