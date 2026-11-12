import assert from 'node:assert/strict'
import { mkdtemp, mkdir, writeFile, rm, symlink } from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
const temp = await mkdtemp(path.join(os.tmpdir(), 'ot-v45-merge-'))
process.env.OPENTRADING_HOME = path.join(temp, 'state')
const fetches: string[] = []
globalThis.fetch = (async (input: any) => {
  const url = String(input instanceof Request ? input.url : input)
  fetches.push(url)
  if (url.endsWith('/api.json')) return Response.json({})
  throw new Error('No external/model request permitted: ' + url)
}) as typeof fetch
try {
  const { previewContext } = await import('/home/doanlong/OpenTrading/src/core/agent.ts')
  const { assemble, validatePromptDir } = await import('/home/doanlong/OpenTrading/src/core/prompt/assemble.ts')
  const { ToolRegistry } = await import('/home/doanlong/OpenTrading/src/core/tools/registry.ts')
  const prompts = path.join(temp, 'prompts')
  await mkdir(prompts)
  for (const name of ['identity', 'tools', 'citations', 'style']) await writeFile(path.join(prompts, name + '.md'), 'Public fixture ' + name)
  assert.equal(validatePromptDir(prompts), prompts)
  assert.throws(() => validatePromptDir('relative/path'))
  const outside = path.join(temp, 'external.md')
  await writeFile(outside, 'external fixture')
  await symlink(outside, path.join(prompts, 'escape.md'))
  assert.throws(() => validatePromptDir(prompts))
  await rm(path.join(prompts, 'escape.md'))
  let indexCalls = 0
  let indexTier: unknown
  const opts = {history: [], input: 'Public integration fixture', skills: [], registry: new ToolRegistry(), promptDir: prompts,
    now: new Date('2026-11-01T00:00:00+07:00'), clockPolicy: 'snapshot' as const,
    memory: {id:'notebook', instructions:()=> 'NOTEBOOK_FIXTURE_POLICY', index:async (ctx: any) => { indexCalls++; indexTier=ctx.tier; return 'NOTEBOOK_FIXTURE_INDEX' }}}
  const snapshot = await previewContext(opts)
  assert.equal(indexCalls, 1)
  assert.equal(indexTier, snapshot.tier)
  assert(snapshot.report.some(x=>x.id==='memory_policy' && !x.dropped))
  assert(snapshot.report.some(x=>x.id==='memory' && !x.dropped))
  assert(!snapshot.report.some(x=>x.id==='phien_giao_dich' && !x.dropped))
  const live = await previewContext({...opts, clockPolicy:'live'})
  assert(live.report.some(x=>x.id==='phien_giao_dich' && !x.dropped))
  const direct = assemble({tier:'B',tools:[],skills:[],sticky:[],input:'fixture',now:opts.now,clockPolicy:'snapshot',
    memoryInstructions:'NOTEBOOK_FIXTURE_POLICY', memoryIndex:'NOTEBOOK_FIXTURE_INDEX', constraints:'CONSTRAINT_FIXTURE'}, prompts)
  assert(direct.system.includes('Public fixture identity'))
  assert(direct.system.includes('NOTEBOOK_FIXTURE_POLICY'))
  assert(direct.context?.includes('NOTEBOOK_FIXTURE_INDEX'))
  assert(direct.system.includes('CONSTRAINT_FIXTURE'))
  assert.throws(()=>assemble({...opts,tier:'B',tools:[],sticky:[],now:new Date('invalid')},prompts))
  assert(fetches.every(x=>x.endsWith('/api.json')))
  console.log(JSON.stringify({pass:true,checked:['trusted_prompt_directory','symlink_escape_rejected','memory_index_new_tier_signature','memory_policy_and_index_preserved','snapshot_clock_suppressed','live_clock_preserved','new_constraints_layer_preserved','invalid_clock_rejected'], model_calls:0, catalog_fetches_stubbed:fetches.length}))
} finally { await rm(temp, {recursive:true, force:true}) }
