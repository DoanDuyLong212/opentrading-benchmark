import json,pathlib,sys,hashlib
W=pathlib.Path(__file__).resolve().parents[3];S=W/'experiments/finance-v45-study';sys.path.insert(0,str(S/'tools'))
from mcp_snapshot_server import load_entries,build_tool_defs
out=pathlib.Path(__file__).parent;unique={};tasks=[]
for p in sorted((S/'tasks').rglob('environment/payloads.json')):
 entries,_=load_entries(p);case=str(p.parent.parent.relative_to(S/'tasks'));tools=[]
 for d in build_tool_defs(entries):
  schema=d['inputSchema'];key=hashlib.sha256(json.dumps(schema,sort_keys=True,ensure_ascii=False).encode()).hexdigest();args=next((item['params']for _,item in entries if item['tool']==d['name']),{})
  row=unique.setdefault(key,{'id':key,'schema':schema,'args':args,'occurrences':[]});row['occurrences'].append({'task':case,'tool':d['name']});tools.append({'name':d['name'],'schema_id':key})
 tasks.append({'task':case,'tools':tools})
(out/'all-task-schemas.json').write_text(json.dumps({'tasks':tasks,'schemas':list(unique.values())},ensure_ascii=False))
run=S/'results/financial-memory-v45-mini-20261109-preflight5';episodes=[]
for p in sorted((run/'episodes').glob('*/result.json')):
 r=json.loads(p.read_text());events=[];rows=[]
 for log in sorted((p.parent/'runner').glob('turn-*.log')):
  for line in log.read_text().splitlines():
   try:e=json.loads(line)
   except ValueError:continue
   if e.get('type')=='tool-end'and'invalid escaped character for Unicode pattern'in str(e.get('output','')):events.append({'log':str(log),'call_id':e.get('callId'),'provider_request_index':e.get('provider_request_index'),'output':e['output']})
 if events:episodes.append({'trial_id':p.parent.name,'model':r['model'],'arm':r['arm'],'case':r['case'],'status':r['status'],'native_regex_tool_failures':events,'failure_count':len(events),'provider_attempts':r.get('provider_attempts_all_turns')})
(out/'observed-failures.json').write_text(json.dumps({'run':str(run),'episodes':episodes,'count':sum(e['failure_count']for e in episodes)},ensure_ascii=False,indent=2))
print(json.dumps({'tasks':len(tasks),'task_tools':sum(len(t['tools'])for t in tasks),'unique_schemas':len(unique),'observed_affected_episodes':len(episodes),'observed_regex_tool_failures':sum(e['failure_count']for e in episodes)}))
