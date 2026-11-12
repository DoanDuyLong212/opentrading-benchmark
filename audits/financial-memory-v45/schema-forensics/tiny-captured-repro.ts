import{readFileSync,writeFileSync}from'node:fs'
const input=JSON.parse(readFileSync(new URL('./captured-repro-input.json',import.meta.url),'utf8'));const pattern=input.offending_patterns[0].pattern;let unicodeError:any
try{new RegExp(pattern,'u')}catch(error){unicodeError=String(error)}
const runtime='/home/doanlong/extra/benchmark/experiments/finance-v45-study/experiments/opentrading-runtime'
const{FinancePolicyState}=await import(runtime+'/src/core/finance-policy.ts');const{jsonSchema,safeValidateTypes}=await import(runtime+'/node_modules/@ai-sdk/provider-utils/dist/index.js')
const policy=new FinancePolicyState({enabled:true},'offline capture validation');const def:any={name:input.tool,input:input.schema}
const sdk=await safeValidateTypes({value:input.captured_first_args,schema:jsonSchema(input.schema,{validate:(v:any)=>policy.validate(def,v)})})
const baselineSdk=await safeValidateTypes({value:input.captured_first_args,schema:jsonSchema(input.schema)})
const result={sdk_without_custom_validator:{success:baselineSdk.success,meaning:'Pinned SDK jsonSchema without validate callback passes through; this is not evidence of schema validation.'},read_only:true,external_model_calls:0,bun_version:Bun.version,tool:input.tool,source_capture:input.source_capture,source_capture_sha256:input.source_capture_sha256,pattern_path:input.offending_patterns[0].path,pattern,non_unicode_compiles:!!new RegExp(pattern),unicode_compiles:!unicodeError,unicode_error:unicodeError,actual_native_sdk_success:sdk.success,actual_native_sdk_error:!sdk.success?{name:sdk.error.name,message:sdk.error.message,cause:String(sdk.error.cause)}:null}
writeFileSync(new URL('./tiny-captured-repro.json',import.meta.url),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2))
