#!/usr/bin/env bun
/**
 * v4.7 shared shell sandbox (decision 2026-11-16, 6b): replaces the math-only filter.
 *
 * Every arm's native shell tool (OpenTrading `shell`, OpenCode `shell`, DSH `bash`) resolves `bash`
 * through PATH/$SHELL and runs `bash -c <command>`; the runner puts ../mathshell/bin first in PATH
 * and points SHELL at it, so every command of every arm lands here. The command is NOT filtered: it
 * runs as written, so each harness shows what its own shell can do (Python, numpy/pandas, awk, bc,
 * scripts in the workspace). What keeps the benchmark sound is where it runs:
 *
 * - a fresh container of the pinned image (Dockerfile here: python 3.12, numpy, pandas, gawk, bc);
 * - no network (`--network none`): market data can only come from the frozen MCP snapshot;
 * - only the trial's workspace (same absolute path, read-write) and its own temp folder (as /tmp)
 *   are mounted: no task gold, grader, other trials, home directory or keys;
 * - read-only root, no capabilities, no privilege gain, memory/CPU/process limits, a time limit,
 *   the host user's uid so files in the workspace stay the trial's.
 *
 * Every command is journalled in runner/shell.jsonl (audit_v45_run.py reconciles each row with a
 * generated shell call). Computation is never financial evidence.
 */
import { appendFileSync, mkdirSync } from "node:fs"
import { spawn, spawnSync } from "node:child_process"
import { randomBytes } from "node:crypto"
import path from "node:path"

const env = process.env
const workspace = env.BENCH_SANDBOX_WORKSPACE
const tmp = env.BENCH_SANDBOX_TMP
const image = env.BENCH_SANDBOX_IMAGE
if (!workspace || !tmp || !image) {
  console.error("sandbox: BENCH_SANDBOX_WORKSPACE, BENCH_SANDBOX_TMP and BENCH_SANDBOX_IMAGE are required")
  process.exit(126)
}
const limitS = Number(env.BENCH_SANDBOX_TIMEOUT_S ?? 300)

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

const journal = (row: Record<string, unknown>) => {
  const ledger = env.BENCH_SHELL_LEDGER
  if (!ledger) return
  try {
    appendFileSync(ledger, JSON.stringify({ time: new Date().toISOString(), arm: env.BENCH_SHELL_ARM ?? null, argv: args, command: command ?? null, image, ...row }) + "\n")
  } catch {}
}

if (command === undefined) {
  journal({ verdict: "refused", reason: "no -c command" })
  console.error("Shell của bài đánh giá này chỉ nhận lệnh dạng bash -c '<lệnh>'.")
  process.exit(2)
}

mkdirSync(tmp, { recursive: true })
const inside = (dir: string) => dir === workspace || dir.startsWith(workspace + path.sep)
const cwd = inside(process.cwd()) ? process.cwd() : workspace
const name = `ot-bench-${randomBytes(6).toString("hex")}`
const uid = process.getuid?.() ?? 1000
const gid = process.getgid?.() ?? 1000
const docker = [
  "run", "--rm", "-i", "--name", name,
  "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
  "--memory", "2g", "--cpus", "2", "--pids-limit", "256",
  "-u", `${uid}:${gid}`,
  "-v", `${workspace}:${workspace}`, "-v", `${tmp}:/tmp`, "-w", cwd,
  "-e", "HOME=/tmp", "-e", "LC_ALL=C.UTF-8", "-e", "TMPDIR=/tmp",
  image, "timeout", "--signal=KILL", String(limitS), "bash", "-c", command,
]
const started = Date.now()
const child = spawn("docker", docker, { stdio: "inherit" })
const stop = () => {
  spawnSync("docker", ["rm", "-f", name], { stdio: "ignore" })
  journal({ verdict: "killed", ms: Date.now() - started })
  process.exit(143)
}
process.on("SIGTERM", stop)
process.on("SIGINT", stop)
child.on("exit", (code, signal) => {
  const exit = code ?? (signal ? 128 : 1)
  journal({ verdict: exit === 137 ? "timeout" : "run", exit, ms: Date.now() - started })
  process.exit(exit)
})
