import collections,json,pathlib
root=pathlib.Path('/home/doanlong/extra/benchmark');out=root/'audits/2026-11-05/comprehensive-review/forensics'
trials=json.loads((out/'trials.json').read_text());calls=json.loads((out/'calls.json').read_text());caps=json.loads((out/'captures.json').read_text());pairs=json.loads((out/'matched-losses.json').read_text())
selected=[('fin-l1-quote-01','opentrading_finance',2),('fin-l1-gold-01','opentrading_finance',1),('fin-l3-top-01','opentrading_finance',1),('fin-l2-growth-01','opentrading_finance',1),('fin-l1-bctc-01','opentrading_finance',1),('fin-l5-compare-01','opentrading_finance',1),('fin-l5-compare-01','opentrading_finance',2),('fin-l1-quote-01','opentrading_baseline',2),('fin-l2-crypto-01','opentrading_finance',1),('fin-l2-tech-01','opentrading_finance',1)]
lines=['# Trace snippets: v3 smoke + pilot','', 'Trích trực tiếp artifact đã đóng băng. Không gọi model hay sửa trial. Tên source SDK khác canonical tool phải được phân biệt.','']
for task,arm,run in selected:
 t=next(t for t in trials if t['split']=='pilot' and t['task']==task and t['arm']==arm and t['run']==run)
 lines+=['## '+t['trial_id'],'',f"Stage: `{t['stage']}`, error: `{t['error_type']}`.",'']
 for c in [c for c in calls if c['trial_id']==t['trial_id']]:
  lines += ['Ledger: ['+c['ledger_source']+']('+str(root/c['ledger_source'])+')','', '```json',json.dumps({k:c[k] for k in ['tool','arguments','status','error_code','snapshot_requests','schema_errors']},ensure_ascii=False,indent=2),'```','']
 cs=next(c for c in caps if c['trial_id']==t['trial_id'] and c['kind']=='native' and c['index']==1)
 lines += ['First native request: ['+cs['path']+']('+str(root/cs['path'])+':1).','']
 log=root/t['run_log_path']
 if log.exists():
  markers=[(i,l) for i,l in enumerate(log.read_text().splitlines(),1) if '"type":"tool-end"' in l or '"type":"done"' in l]
  lines += ['Native trace: '+', '.join('['+str(i)+']('+str(log)+':'+str(i)+')' for i,l in markers[:8])+'.','']
 ans=t['answer'];lines+=['Grade: ['+t['grade_path']+']('+str(root/t['grade_path'])+'). Raw answer object below.','', '```json',json.dumps(ans,ensure_ascii=False,indent=2),'```','','Failed checks:','', '```json',json.dumps(t['failed_checks'],ensure_ascii=False,indent=2),'```','']
(out/'SNIPPETS.md').write_text('\n'.join(lines)+'\n')
# Verify facts used in prose against raw-derived data.
assert len(trials)==194 and len(calls)==305 and len(caps)==779
for s in ['smoke','pilot']:
 for arm in {t['arm'] for t in trials if t['split']==s}:
  tt=[t for t in trials if t['split']==s and t['arm']==arm]
  assert sum(t['provider_tool_call_count'] for t in tt)==sum(t['mcp_calls'] for t in tt)
  assert sum(t['rejected_tool_messages_visible_to_model'] for t in tt)==sum(t['mcp_rejected'] for t in tt)
for arm in ['opentrading_baseline','opentrading_finance']:
 pp=[p for p in pairs if p['ot']==arm and p['comparator']=='dsh']
 assert len(pp)==6 and collections.Counter(p['stage'] for p in pp)=={'rejected_no_success':3,'after_successful_tool':3}
print('Verified: 194 trials, 305 calls, 779 captures; provider/MCP count equality, all rejection messages visible; paired DSH deficit 3+3 each OT variant.')
