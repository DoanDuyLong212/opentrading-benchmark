#!/usr/bin/env bun
// Native OpenTrading agent. No user/bundled skills or agent definitions are loaded.
const expectedRoot = new URL('../../experiments/opentrading-runtime/', import.meta.url).pathname.replace(/\/$/, '')
if (process.env.BENCH_OT_RUNTIME !== expectedRoot) throw new Error('Untrusted OpenTrading runtime locator')
const { runAgent } = await import(expectedRoot + '/src/core/agent')
const { initRuntime } = await import(expectedRoot + '/src/core/runtime')
const promptDir = process.env.BENCH_PROMPT_DIR
const validPrompts = ['baseline', 'finance'].map(v => new URL('../prompt_variants/' + v, import.meta.url).pathname)
if (!promptDir || !validPrompts.includes(promptDir)) throw new Error('Untrusted prompt variant locator')
const now = new Date(process.env.BENCH_AS_OF + 'T00:00:00+07:00')
if (!Number.isFinite(now.getTime())) throw new Error('Invalid frozen benchmark date')
const runtime = initRuntime({ cwd: process.cwd(), skills: () => [] })
try {
  await runtime.mcp.start()
  // Remove every builtin, including memory, skills, web, questions and subagents.
  for (const tool of runtime.registry.list()) {
    if (tool.source !== 'mcp:opentrading') runtime.registry.unregister(tool.name)
  }
  const inventory = runtime.registry.list().map((tool: any) => ({ name: tool.name, source: tool.source }))
  if (process.env.BENCH_INVENTORY) await Bun.write(process.env.BENCH_INVENTORY, JSON.stringify({skills: [], tools: inventory}, null, 2))
  if (inventory.length === 0) throw new Error('No snapshot MCP tools were registered')
  let finalText = ''
  for await (const event of runAgent({history: [], input: Bun.argv.slice(2).join(' '), skills: [],
    now, clockPolicy: 'snapshot', promptDir,
    financePolicy: process.env.BENCH_FINANCE_POLICY === 'on' ? {enabled: true, machineResponse: true} : undefined,
    registry: runtime.registry, serverInstructions: () => runtime.mcp.instructions()})) {
    process.stderr.write(JSON.stringify(event) + '\n')
    if (event.type === 'tool-start') finalText = ''
    if (event.type === 'text-delta') finalText += event.text
  }
  process.stdout.write(finalText)
} finally { await runtime.mcp.stop() }
