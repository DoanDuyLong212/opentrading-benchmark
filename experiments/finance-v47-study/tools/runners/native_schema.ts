#!/usr/bin/env bun
// v4.7: the native tools OpenTrading declares in a trial (shell, read_result), as the gateway pins them.
// --machine: the opentrading_machine arm's shell is the calculator (useCalculatorShell, #294).
import {z} from '../../experiments/opentrading-runtime/node_modules/zod'
import {shellTool} from '../../experiments/opentrading-runtime/src/core/tools/shell/shell'
import {readResultTool} from '../../experiments/opentrading-runtime/src/core/tools/builtin/read-result'
const full=shellTool({} as any)
const shell=process.argv.includes('--machine')?full.readOnlyVariant!:full
console.log(JSON.stringify([shell,readResultTool()].map(tool=>({name:tool.name,inputSchema:z.toJSONSchema(tool.input as z.ZodType)}))))
