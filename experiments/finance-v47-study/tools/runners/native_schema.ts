#!/usr/bin/env bun
import {z} from '../../experiments/opentrading-runtime/node_modules/zod'
import {shellTool} from '../../experiments/opentrading-runtime/src/core/tools/shell/shell'
import {readResultTool} from '../../experiments/opentrading-runtime/src/core/tools/builtin/read-result'
console.log(JSON.stringify([shellTool({} as any),readResultTool()].map(tool=>({name:tool.name,inputSchema:z.toJSONSchema(tool.input as z.ZodType)}))))
