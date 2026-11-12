#!/usr/bin/env bun
import {z} from '../../experiments/opentrading-runtime/node_modules/zod'
import {calculateTool} from '../../experiments/opentrading-runtime/src/core/tools/calculate'
import {computeTool} from '../../experiments/opentrading-runtime/src/core/tools/compute'
import {readResultTool} from '../../experiments/opentrading-runtime/src/core/tools/builtin/read-result'
import {memoryReadTool} from '../../experiments/opentrading-runtime/src/core/memory/notebook/read-tool'
const tools=[calculateTool(),computeTool(),readResultTool()]
if(process.argv.includes('--notebook'))tools.push(memoryReadTool({readSubject:()=>'',readLesson:()=>'',search:()=>''}) as any)
console.log(JSON.stringify(tools.map(t=>({name:t.name,inputSchema:z.toJSONSchema(t.input as z.ZodType)}))))
