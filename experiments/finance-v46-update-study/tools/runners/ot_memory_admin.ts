#!/usr/bin/env bun
/** Trusted user-form controller, never registered as a model tool; no model suggestions are accepted. */
import {readFileSync,existsSync,writeFileSync,mkdirSync} from 'node:fs'
import {resolve} from 'node:path'
import {createHash} from 'node:crypto'
const root=new URL('../../experiments/opentrading-runtime/',import.meta.url).pathname.replace(/\/$/,'')
const {openNotebook}=await import(root+'/src/core/memory/notebook/lifecycle')
const {notebookAdmin}=await import(root+'/src/core/memory/notebook/admin')
const request=JSON.parse(await Bun.stdin.text())
const home=resolve(request.home);if(!home.endsWith('/runner/ot-home'))throw new Error('Isolated episode OT home required')
mkdirSync(home,{recursive:true})
const memory=openNotebook(home+'/memory.db');const admin=notebookAdmin(memory)!
const file=home+'/authorized-memory-map.json';const map=existsSync(file)?JSON.parse(readFileSync(file,'utf8')):{}
const events=[]
try{
 for(const op of request.operations??[]){
  if(op.consent!=='explicit_user_request'||typeof op.source_text!=='string'||!request.user_text.includes(op.source_text)||!/(nhớ|lưu|ghi nhận|cập nhật|sửa|thay|xóa|xoá|hủy|huỷ|quên|remember|save|update|revise|forget|delete|revoke)/i.test(op.source_text))throw new Error('Explicit typed user consent required')
  const old=map[op.id];if(old&&op.op==='put'&&old.group!==op.kind)throw new Error('Authorized fact kind cannot change implicitly');let result:any
  if(op.op==='delete'){
   if(!old)throw new Error('Unknown native authorized user fact')
   result=admin.remove(old.group,{id:old.id,version:old.version});if(result.ok)delete map[op.id]
  }else{
   if(typeof op.text!=='string'||!request.user_text.includes(op.text))throw new Error('Memory content must be verbatim user text')
   if(op.kind==='constraint'||op.kind==='style')result=admin.saveConstraint({kind:op.kind,text:op.text},old?{id:old.id,expected:old.version}:undefined)
   else if(op.kind==='lesson')result=admin.saveLesson({title:op.text.slice(0,80),summary:op.text,appliesTo:[],tags:[]},old?{id:old.id,expected:old.version}:undefined)
   else if(op.kind==='thesis'){
    if(!op.subject||!op.source_text.includes(op.subject.alias)||!['ticker','sector','market'].includes(op.subject.kind))throw new Error('Thesis subject must be explicitly user-authored')
    result=admin.saveThesis(old?{id:old.id}:{kind:op.subject.kind,alias:op.subject.alias,otherAliases:[],uppercaseOnly:op.subject.kind==='ticker'},old?.version??null,{text:op.text,conditions:[]})
   }else throw new Error('Unsupported authorized notebook kind')
   if(result.ok)map[op.id]={...result.saved,group:op.kind}
  }
  if(!result.ok)throw new Error('Native notebook user form failed: '+result.message)
  events.push({id:op.id,op:op.op,kind:op.kind,native_saved:map[op.id]??null,source_user_turn_sha256:createHash('sha256').update(request.user_text).digest('hex')})
 }
 if(!request.audit_only)writeFileSync(file,JSON.stringify(map,null,2));const entries=admin.entries()
 const normalized=Object.entries(map).map(([user_fact_id,m]:[string,any])=>{
  const entry=entries.find(e=>e.group===m.group&&e.id===m.id&&e.version===m.version)
  if(!entry)throw new Error('Authorized map does not join actual active notebook row')
  let text:string
  if(m.group==='constraint'||m.group==='style'){const got=admin.constraintDraft(m.id);if(!got.ok)throw new Error(got.message);text=got.value.text}
  else if(m.group==='lesson'){const got=admin.lessonDraft(m.id);if(!got.ok)throw new Error(got.message);text=got.value.summary}
  else{const got=admin.subject(m.id);if(!got.ok||!got.value.thesis)throw new Error('Missing actual thesis row');text=got.value.thesis.text}
  return {user_fact_id,native_id:m.id,version:m.version,kind:m.group,text,active:true}
 })
 process.stdout.write(JSON.stringify({ok:true,events,entries,authorized_map:map,normalized_actual_entries:normalized,native_persistence_verified:true,entry_hash:createHash('sha256').update(JSON.stringify(entries)).digest('hex')}))
}finally{memory.close()}
