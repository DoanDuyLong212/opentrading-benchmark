import { expect, test } from "bun:test"
import { mkdtempSync, readFileSync, symlinkSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import { assemble, promptVersion, validatePromptDir, PROMPTS_DIR, type AssembleInput } from "../src/core/prompt/assemble"

const variant = (_name: string) => PROMPTS_DIR
const base: AssembleInput = {
  tier: "C", tools: ["finance_data"], skills: [], sticky: [], input: "Trả một JSON đúng đơn vị yêu cầu.",
  now: new Date("2026-09-28T03:00:00Z"),
}

test("finance contract survives smallest tier and retains native subagent invariants", () => {
  const dir = validatePromptDir(variant("finance"))
  const out = assemble(base, dir)
  expect(out.report.every((r) => !r.truncated && !r.dropped)).toBe(true)
  expect(out.system).toContain("trả đúng một object JSON hợp lệ")
  expect(out.system).toContain("đơn vị người dùng yêu cầu")
  expect(out.system).toContain("quý riêng khác lũy kế, TTM và năm")
  expect(out.system).toContain("Request bị từ chối không chứng minh")
  expect(out.system).toContain("chép nguyên các trường provenance")
  expect(out.system).not.toContain("không dán JSON")
  const child = assemble({ ...base, role: "subagent" }, dir)
  expect(child.system).toContain("<bat_bien>")
  expect(child.system).toContain("<thu_tu_uu_tien>")
  expect(child.system).toContain("Không tự tạo nguồn")
})

test("snapshot omits only live-session reminder; default production clock stays live", () => {
  const live = assemble(base, variant("finance"))
  const historical = assemble({ ...base, clockPolicy: "snapshot" }, variant("finance"))
  expect(live.reminders.some((s) => s.includes("<phien_giao_dich>"))).toBe(true)
  expect(historical.reminders.some((s) => s.includes("<phien_giao_dich>"))).toBe(false)
  expect(historical.clock).toEqual(live.clock)
  expect(historical.system).toBe(live.system)
  expect(() => assemble({ ...base, now: new Date("invalid") })).toThrow("valid Date")
})

test("trusted prompt override rejects missing, relative, oversized and escaping files", () => {
  expect(() => validatePromptDir("prompts")).toThrow("absolute")
  const dir = mkdtempSync(path.join(tmpdir(), "ot-prompt-guard-"))
  expect(() => validatePromptDir(dir)).toThrow("missing")
  for (const name of ["identity", "tools", "citations", "style"]) writeFileSync(path.join(dir, name + ".md"), "rule")
  expect(validatePromptDir(dir)).toBe(dir)
  writeFileSync(path.join(dir, "style.md"), "  ")
  expect(() => validatePromptDir(dir)).toThrow("empty")
  writeFileSync(path.join(dir, "style.md"), "x".repeat(65_537))
  expect(() => validatePromptDir(dir)).toThrow("oversized")
  writeFileSync(path.join(dir, "style.md"), "rule")
  symlinkSync(path.join(variant("finance"), "identity.md"), path.join(dir, "escaped.md"))
  expect(() => validatePromptDir(dir)).toThrow("unsafe")
})

test("one prompt byte changes native version", () => {
  const dir = mkdtempSync(path.join(tmpdir(), "ot-prompt-hash-"))
  writeFileSync(path.join(dir, "identity.md"), readFileSync(path.join(variant("finance"), "identity.md")))
  const old = promptVersion(dir)
  writeFileSync(path.join(dir, "identity.md"), readFileSync(path.join(dir, "identity.md"), "utf8") + "\n")
  expect(promptVersion(dir)).not.toBe(old)
})
