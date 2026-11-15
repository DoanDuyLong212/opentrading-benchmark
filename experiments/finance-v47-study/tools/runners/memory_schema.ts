#!/usr/bin/env bun
// v4.7: calculate/compute are gone (#263); the native tools of an OpenTrading memory episode are
// shell, read_result and, with the notebook, memory_read. --machine: the calculator shell (#294).
import {z} from '../../experiments/opentrading-runtime/node_modules/zod'
import {shellTool} from '../../experiments/opentrading-runtime/src/core/tools/shell/shell'
import {readResultTool} from '../../experiments/opentrading-runtime/src/core/tools/builtin/read-result'
import {memoryReadTool} from '../../experiments/opentrading-runtime/src/core/memory/notebook/read-tool'
const full=shellTool({} as any)
const tools:any[]=[process.argv.includes('--machine')?full.readOnlyVariant!:full,readResultTool()]
if(process.argv.includes('--notebook'))tools.push(memoryReadTool({readSubject:()=>'',readLesson:()=>'',search:()=>''}) as any)
console.log(JSON.stringify(tools.map(t=>({name:t.name,inputSchema:z.toJSONSchema(t.input as z.ZodType)}))))
