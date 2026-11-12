#!/usr/bin/env bun
import {z} from '../../experiments/opentrading-runtime/node_modules/zod'
import {calculateTool} from '../../experiments/opentrading-runtime/src/core/tools/calculate'
import {computeTool} from '../../experiments/opentrading-runtime/src/core/tools/compute'
import {readResultTool} from '../../experiments/opentrading-runtime/src/core/tools/builtin/read-result'
console.log(JSON.stringify([calculateTool(),computeTool(),readResultTool()].map(tool=>({name:tool.name,inputSchema:z.toJSONSchema(tool.input as z.ZodType)}))))
