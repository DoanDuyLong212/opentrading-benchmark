#!/usr/bin/env python3
"""Independent actual 4-arm memory fixture. ONLY local scripted HTTP, zero external model calls.
Two small scenarios/arm: persisted same-session history with pause/resume; fresh-session
trusted notebook plus market-data source. Current runtime and explicitly pinned Bun required.
"""
import json,sys,tempfile,threading,uuid,hashlib,traceback,argparse
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
W=Path(__file__).resolve().parents[2];S=W/'experiments/finance-v45-study';sys.path[:0]=[str(S/'tools/runners'),str(S/'tools')]
import provider
provider.credential=lambda:'synthetic-local-only-not-provider-key'
from memory_runner import MemoryEpisode
from audit_v45_run import json_objects
from ready_check import verify_mcp_attempt
MODEL='deepseek-ai/deepseek-v4.1-flash';BUN=W/'experiments/toolchains/bun-1.4.4/bun';BUNSHA='10702245766b225e70bbf6235fd6b47214fd94b4760d00ffaed8ab0df57ac235'
assert hashlib.sha256(BUN.read_bytes()).hexdigest()==BUNSHA
ap=argparse.ArgumentParser();ap.add_argument('--arm',default='all',choices=['all','ot_memory_on','ot_memory_off','opencode','dsh']);ap.add_argument('--scenario',default='all',choices=['all','same-session','fresh-session']);args=ap.parse_args()
arms=['ot_memory_on','ot_memory_off','opencode','dsh'] if args.arm=='all' else [args.arm]
scenarios=['same-session','fresh-session'] if args.scenario=='all' else [args.scenario]
expected_cases=len(arms)*len(scenarios)
OUT=W/('audits/financial-memory-v45/native-wire-'+uuid.uuid4().hex[:8]);OUT.mkdir();reports=[]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  b=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.server.seen.append(b)
  users=[m for m in b.get('messages',[])if m.get('role')=='user'];latest=str(users[-1].get('content'))if users else''
  objs=[o for m in b.get('messages',[])if m.get('role')=='tool'for o in json_objects(m.get('content'))]
  source=next((o for o in objs if 'data'in o and isinstance(o.get('benchmark_evidence'),dict)),None)
  note=next((o for o in objs if o.get('kind')=='user_memory_not_market_evidence'),None)
  names=[t['function']['name']for t in b.get('tools',[])];tool=None
  if 'FIXTURE_SAME_SEED'in latest and source is None:tool=next(n for n in names if n.endswith('vn_quote_history'));args={'symbol':'SYN'}
  elif 'FIXTURE_FRESH_QUERY'in latest and note is None:tool=next(n for n in names if n.endswith('benchmark_user_notebook_read'));args={}
  elif 'FIXTURE_FRESH_QUERY'in latest and source is None:tool=next(n for n in names if n.endswith('vn_quote_history'));args={'symbol':'SYN'}
  if tool:msg={'role':'assistant','content':None,'tool_calls':[{'id':'fixture-sdk-'+str(len(self.server.seen)),'type':'function','function':{'name':tool,'arguments':json.dumps(args)}}]};finish='tool_calls'
  elif 'FIXTURE_SAME_SEED'in latest:msg={'role':'assistant','content':'Đã hoàn tất đọc nguồn. NONCE_AZURE_CEDAR chứng minh bản ghi assistant được tiếp tục.'};finish='stop'
  elif 'FIXTURE_FRESH_SEED'in latest:msg={'role':'assistant','content':'Đã nhận yêu cầu người dùng. Controller sẽ chỉ lưu đúng nội dung được cho phép.'};finish='stop'
  else:
   answer={'value':12,'unit':'nghìn đồng/cổ phiếu','period':'2030-03-31','source':'vn_quote_history','evidence':[source['benchmark_evidence']]if source else[]}
   if note:answer['memory_evidence']=[{k:f[k]for k in('id','revision','source_session','source_turn','source_user_turn_sha256')}for f in note['facts']]
   msg={'role':'assistant','content':json.dumps(answer,ensure_ascii=False)};finish='stop'
  u={'prompt_tokens':100,'completion_tokens':20}
  if b.get('stream'):
   delta={'role':'assistant'}
   if tool:delta['tool_calls']=[{'index':0,**msg['tool_calls'][0]}]
   else:delta['content']=msg['content']
   cs=[{'id':'fixture','object':'chat.completion.chunk','created':1,'model':MODEL,'choices':[{'index':0,'delta':delta,'finish_reason':None}]},{'id':'fixture','object':'chat.completion.chunk','created':1,'model':MODEL,'choices':[{'index':0,'delta':{},'finish_reason':finish}],'usage':u}];raw=(''.join('data: '+json.dumps(c,ensure_ascii=False)+'\n\n'for c in cs)+'data: [DONE]\n\n').encode();ct='text/event-stream'
  else:raw=json.dumps({'id':'fixture','object':'chat.completion','created':1,'model':MODEL,'choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':u},ensure_ascii=False).encode();ct='application/json'
  self.send_response(200);self.send_header('Content-Type',ct);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
def snapshot(root):return{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and not p.is_symlink()}
for arm in arms:
 for scenario in scenarios:
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.seen=[];threading.Thread(target=server.serve_forever,daemon=True).start();provider.NVIDIA_URL='http://127.0.0.1:'+str(server.server_port)
  work=Path(tempfile.mkdtemp(prefix='v45-memory-'+arm+'-'));ws=work/'ws';ws.mkdir();task=work/'task';(task/'environment').mkdir(parents=True)
  payload={'snapshot_date':'2030-04-01','tools':{'source':{'tool':'vn_quote_history','params':{'symbol':'SYN'},'envelope':{'data':{'symbol':'SYN','last':12,'last_t':'2030-03-31'},'units':{'last':'nghìn đồng/cổ phiếu'},'availability':'available','provenance':{'source':'synthetic-not-live','data_time':'2030-03-31','as_of':'2030-04-01'}}}}};(task/'environment/payloads.json').write_text(json.dumps(payload))
  options={'native_bun_binary':str(BUN),'native_bun_sha256':BUNSHA,'opentrading_runtime_root':str(S/'experiments/opentrading-runtime'),'timeout_s':75,'provider_timeout_s':8,'request_interval_s':0,'max_requests':12,'context_window':1048576,'max_output_tokens':8192,'max_total_tokens':3600000,'failed_attempt_context_bound':1048576,'failed_attempt_token_reservation':1056768,'temperature':1,'top_p':.95}
  final='Trả một object JSON: {"value":0,"unit":"nghìn đồng/cổ phiếu","period":"2030-03-31","source":"vn_quote_history","evidence":[]} dùng biên nhận nguồn thật.'
  if scenario=='same-session':turns=[{'session':'S1','turn':0,'final':False,'text':'FIXTURE_SAME_SEED Đọc quote SYN bằng vn_quote_history và xác nhận đã hoàn tất.'},{'session':'S1','turn':1,'final':True,'text':'FIXTURE_SAME_QUERY Dùng lại quote/biên nhận đã đọc, không gọi lại tool. '+final}]
  else:
   seed='FIXTURE_FRESH_SEED Nhớ ràng buộc người dùng: chỉ xem cổ phiếu có giá dưới hai mươi nghìn đồng.'
   op={'op':'put','id':'fixture-price-limit','kind':'constraint','text':seed,'source_text':seed,'consent':'explicit_user_request'}
   turns=[{'session':'A','turn':0,'final':False,'text':seed,'memory_operations':[op]},{'session':'B','turn':0,'final':True,'text':'FIXTURE_FRESH_QUERY Đọc notebook được ủy quyền rồi quote SYN; trả giá và memory_evidence thật. '+final}]
  report={'arm':arm,'scenario':scenario,'work':str(work),'external_model_calls':0,'bun_binary':str(BUN),'bun_sha256':BUNSHA}
  try:
   episode=MemoryEpisode(ws,task,'nvidia/'+MODEL,arm,options);paused=episode.run(turns,stop_after_turns=1);assert paused['status']=='paused',paused
   first_requests=len(server.seen);first_receipts=Path(paused['mcp_ledger']).read_bytes()if paused.get('mcp_ledger')and Path(paused['mcp_ledger']).exists()else b''
   episode=MemoryEpisode(ws,task,'nvidia/'+MODEL,arm,options);done=episode.run(turns)
   report['state']=done;report['local_requests']=len(server.seen)
   assert done['status']=='completed',done
   assert len(done['completed_turns'])==2
   assert json.loads(done['final_text'])['value']==12
   assert not any(t['unauthorized_write']for t in done['completed_turns'])
   before=snapshot(work/'runner');n=len(server.seen);completed=MemoryEpisode(ws,task,'nvidia/'+MODEL,arm,options).run(turns);assert len(server.seen)==n,'Completed resume called provider';assert snapshot(work/'runner')==before,'Completed resume rewrote artifacts'
   query_body=server.seen[first_requests];wire=json.dumps(query_body,ensure_ascii=False)
   if scenario=='same-session':
    assert 'NONCE_AZURE_CEDAR'in wire,'Original assistant history missing'
    assert 'benchmark_evidence'in wire and 'FIXTURE_SAME_SEED'in wire,'Original tool/user history missing'
    assert len(server.seen)==3,len(server.seen)
    if arm in('opencode','dsh'):assert len(set(done['native_sessions'].values()))==1
   else:
    if arm!='ot_memory_on':assert 'FIXTURE_FRESH_SEED'not in wire,'Fresh session leaked seed history'
    assert 'NONCE_AZURE_CEDAR'not in wire
    assert len(server.seen)==4,len(server.seen)
    assert json.loads(done['final_text'])['memory_evidence'][0]['id']=='fixture-price-limit'
    if arm in('opencode','dsh'):assert len(set(done['native_sessions'].values()))==2
   assert Path(done['mcp_ledger']).read_bytes().startswith(first_receipts),'Previous receipt journal overwritten'
   calls=verify_mcp_attempt(task,{'ledger_path':done['mcp_ledger']});assert len(calls)==1
   report.update(pass_=True,completed_resume_new_calls=0)
  except Exception as e:report.update(pass_=False,error=str(e),traceback=traceback.format_exc())
  finally:server.shutdown();server.server_close()
  reports.append(report);proof={'pass':all(r['pass_']for r in reports),'complete':len(reports)==expected_cases,'full_matrix':expected_cases==8,'expected_cases':expected_cases,'selected_arms':arms,'selected_scenarios':scenarios,'expected_local_requests':sum(3 if r['scenario']=='same-session' else 4 for r in reports),'external_model_calls':0,'reports':reports};(OUT/'proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2));print(json.dumps({'arm':arm,'scenario':scenario,'pass':report['pass_'],'error':report.get('error'),'proof':str(OUT/'proof.json')},ensure_ascii=False),flush=True)
raise SystemExit(0 if all(r['pass_']for r in reports)else 1)
