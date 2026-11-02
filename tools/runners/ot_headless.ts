#!/usr/bin/env bun
/**
 * opentrading_headless.ts — chạy 1 task qua core OpenTrading KHÔNG TUI (headless).
 *
 * Copy pattern từ ~/OpenTrading/src/core/chat.ts (import.meta.main) nhưng tách dòng
 * sự kiện ra STDERR (JSONL — telemetry) và chỉ text trả lời ra STDOUT (answer).
 * MCP snapshot + model cấu hình qua OPENTRADING_HOME (config.json/mcp.json/auth.json).
 */
const { runAgent } = await import("/home/doanlong/OpenTrading/src/core/agent")
const { initRuntime, setAgents } = await import("/home/doanlong/OpenTrading/src/core/runtime")
const { loadSkills } = await import("/home/doanlong/OpenTrading/src/core/skills/loader")
const { loadAgents } = await import("/home/doanlong/OpenTrading/src/core/agents/loader")

const { skills } = await loadSkills()
const runtime = initRuntime({ skills: () => skills })
setAgents(runtime, (await loadAgents()).agents)
await runtime.mcp.start()

const input = Bun.argv.slice(2).join(" ")
try {
  for await (const event of runAgent({
    history: [], input, skills, registry: runtime.registry,
    serverInstructions: () => runtime.mcp.instructions(),
  })) {
    if (event.type === "text-delta") process.stdout.write(event.text)
    else process.stderr.write(JSON.stringify(event) + "\n")
  }
} finally {
  await runtime.mcp.stop()
}
