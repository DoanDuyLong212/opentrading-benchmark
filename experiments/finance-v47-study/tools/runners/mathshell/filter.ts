#!/usr/bin/env bun
/**
 * v4.7 shared math-only shell filter (decision 2026-11-15, option A).
 *
 * Every arm's native shell tool (OpenTrading `shell`, OpenCode `shell`, DSH `bash`) resolves
 * `bash` through PATH/$SHELL and runs `bash -c <command>`; the runner puts bin/ first in PATH and
 * points SHELL at bin/bash, so every command of every arm passes this one check. The rule is the
 * OpenTrading arithmetic grammar (`mathOnlyCommand` of the pinned runtime): one awk BEGIN block /
 * arithmetic statements, no files, pipes, network or interpreters. A command that passes runs in
 * /bin/bash; any other is refused with the same message for every arm.
 *
 * OpenTrading itself prefixes accepted arithmetic with `LC_ALL=C` and `-v OFMT=%.15g -v
 * CONVFMT=%.15g` (shell/run.ts shellArgs, math.ts awkWithPrecision) before it calls bash. Those
 * two exact harness-added forms are removed before the check; the model never writes them.
 */
import { appendFileSync } from "node:fs"
import { spawnSync } from "node:child_process"

const runtime = process.env.BENCH_OT_RUNTIME
if (!runtime) {
  console.error("mathshell: BENCH_OT_RUNTIME not set")
  process.exit(126)
}
const { mathOnlyCommand, mathHint } = await import(runtime + "/src/core/tools/shell/math")

const args = process.argv.slice(2)
let command: string | undefined
for (let i = 0; i < args.length; i++) {
  const a = args[i]!
  if (/^-[a-z]*c$/.test(a)) {
    command = args[i + 1]
    break
  }
  if (!/^-[a-z]+$/.test(a)) break
}

const normalize = (c: string) =>
  c.replace(/^LC_ALL=C /, "").replace(/^awk -v OFMT=%\.15g -v CONVFMT=%\.15g /, "awk ")

const verdict = command !== undefined && mathOnlyCommand(normalize(command), { kind: "bash" }) ? "run" : "refused"
const ledger = process.env.BENCH_SHELL_LEDGER
if (ledger) {
  try {
    appendFileSync(ledger, JSON.stringify({ time: new Date().toISOString(), arm: process.env.BENCH_SHELL_ARM ?? null, argv: args, command: command ?? null, verdict }) + "\n")
  } catch {}
}
if (verdict === "refused") {
  console.error(
    "Lệnh này không chạy: shell trong bài đánh giá này chỉ chạy phép tính số (một lệnh awk 'BEGIN{...}' hoặc biểu thức số; không file, pipe, mạng hay python). Viết lại thành phép tính. " +
      mathHint({ kind: "bash" }),
  )
  process.exit(2)
}
const res = spawnSync("/bin/bash", ["-c", command!], { stdio: "inherit", env: process.env })
process.exit(res.status ?? 1)
