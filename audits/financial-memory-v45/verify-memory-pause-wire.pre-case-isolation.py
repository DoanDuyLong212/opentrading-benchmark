#!/usr/bin/env python3
"""Independent real native-process PAUSE proof using a held local HTTP response.
No external models. Default one arm; use --arm all only for a bounded four-arm check.
"""
import argparse,json,sys,tempfile,threading,time,uuid,hashlib,traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
W=Path(__file__).resolve().parents[2];S=W/'experiments/finance-v45-study';sys.path[:0]=[str(S/'tools/runners'),str(S/'tools')]
import provider
provider.credential=lambda:'synthetic-local-pause-fixture'
from memory_runner import MemoryEpisode,save
from audit_v45_run import json_objects
MODEL='deepseek-ai/deepseek-v4.1-flash';BUN=W/'experiments/toolchains/bun-1.4.4/bun';SHA='10702245766b225e70bbf6235fd6b47214fd94b4760d00ffaed8ab0df57ac235';assert hashlib.sha256(BUN.read_bytes()).hexdigest()==SHA
ap=argparse.ArgumentParser();ap.add_argument('--arm',default='ot_memory_off',choices=['all','ot_memory_on','ot_memory_off','opencode','dsh']);a=ap.parse_args();arms=['ot_memory_on','ot_memory_off','opencode','dsh']if a.arm=='all'else[a.arm]
OUT=W/('audits/financial-memory-v45/pause-wire-'+uuid.uuid4().hex[:8]);OUT.mkdir();reports=[]
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  b=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.server.seen.append(b)
  if len(self.server.seen)==1:self.server.first.set();self.server.release.wait(15)
  source=next((o for m in b.get('messages',[])if m.get('role')=='tool'for o in json_objects(m.get('content'))if 'benchmark_evidence'in o and 'data'in o),None)
  if source is None:
   name=next(t['function']['name']for t in b['tools']if t['function']['name'].endswith('vn_quote_history'));msg={'role':'assistant','content':None,'tool_calls':[{'id':'fixture-'+str(len(self.server.seen)),'type':'function','function':{'name':name,'arguments':'{"symbol":"SYN"}'}}]};finish='tool_calls'
  else:msg={'role':'assistant','content':json.dumps({'value':12,'unit':'nghìn đồng/cổ phiếu','period':'2030-03-31','source':'vn_quote_history','evidence':[source['benchmark_evidence']]},ensure_ascii=False)};finish='stop'
  usage={'prompt_tokens':100,'completion_tokens':20}
  if b.get('stream'):
   delta={'role':'assistant'}
   if finish=='tool_calls':delta['tool_calls']=[{'index':0,**msg['tool_calls'][0]}]
   else:delta['content']=msg['content']
   chunks=[{'id':'fixture','object':'chat.completion.chunk','created':1,'model':MODEL,'choices':[{'index':0,'delta':delta,'finish_reason':None}]},{'id':'fixture','object':'chat.completion.chunk','created':1,'model':MODEL,'choices':[{'index':0,'delta':{},'finish_reason':finish}],'usage':usage}]
   raw=(''.join('data: '+json.dumps(c,ensure_ascii=False)+'\n\n'for c in chunks)+'data: [DONE]\n\n').encode();ct='text/event-stream'
  else:raw=json.dumps({'id':'fixture','object':'chat.completion','created':1,'model':MODEL,'choices':[{'index':0,'message':msg,'finish_reason':finish}],'usage':usage}).encode();ct='application/json'
  try:self.send_response(200);self.send_header('Content-Type',ct);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  except(BrokenPipeError,ConnectionResetError):pass
  finally:self.server.responded.set()
def snap(root):return{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and not p.is_symlink()}
for arm in arms:
 for mode in ['soft-after-turn','hard-abort']:
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.seen=[];server.first=threading.Event();server.release=threading.Event();server.responded=threading.Event();threading.Thread(target=server.serve_forever,daemon=True).start();provider.NVIDIA_URL='http://127.0.0.1:'+str(server.server_port)
  work=Path(tempfile.mkdtemp(prefix='v45-memory-pause-'));ws=work/'ws';ws.mkdir();task=work/'task';(task/'environment').mkdir(parents=True);control=work/'control.json'
  payload={'snapshot_date':'2030-04-01','tools':{'source':{'tool':'vn_quote_history','params':{'symbol':'SYN'},'envelope':{'data':{'symbol':'SYN','last':12,'last_t':'2030-03-31'},'units':{'last':'nghìn đồng/cổ phiếu'},'availability':'available','provenance':{'source':'synthetic-not-live','data_time':'2030-03-31','as_of':'2030-04-01'}}}}};(task/'environment/payloads.json').write_text(json.dumps(payload))
  options={**json.loads((S/'tools/bench_config_deepseek.json').read_text())['provider_options'],'native_bun_binary':str(BUN),'native_bun_sha256':SHA,'opentrading_runtime_root':str(S/'experiments/opentrading-runtime'),'max_requests':12,'timeout_s':60,'provider_timeout_s':20,'request_interval_s':0}
  turns=[{'session':'S1','turn':0,'final':False,'text':'Lấy quote SYN, ghi object JSON với giá và biên nhận nguồn.'},{'session':'S1','turn':1,'final':True,'text':'Không gọi lại tool. Trả đúng object JSON {"value":0,"unit":"nghìn đồng/cổ phiếu","period":"2030-03-31","source":"vn_quote_history","evidence":[]} bằng giá và biên nhận đã lấy.'}]
  state={};failures=[];report={'arm':arm,'mode':mode,'work':str(work),'external_model_calls':0}
  def run():
   try:state['value']=MemoryEpisode(ws,task,'nvidia/'+MODEL,arm,options,control).run(turns)
   except BaseException as e:failures.append(traceback.format_exc())
  thread=threading.Thread(target=run,daemon=True)
  try:
   thread.start();assert server.first.wait(35),'No first upstream request reached local fixture'
   save(control,{'pause_after_turn':True}if mode=='soft-after-turn'else{'pause':True,'hard_stop':True})
   if mode=='hard-abort':
    # Give cancellation a chance while the upstream result is deliberately unavailable.
    thread.join(2);report['returned_before_upstream_release']=not thread.is_alive()
   server.release.set();thread.join(30);assert not thread.is_alive(),'Native controller did not settle';assert not failures,failures
   done=state['value'];report['state']=done;report['requests_before_resume']=len(server.seen)
   if mode=='soft-after-turn':
    assert done['status']=='paused'and len(done['completed_turns'])==1,done
    assert len(server.seen)==2,'Soft pause failed to finish active turn or started another turn'
    control.unlink();resumed=MemoryEpisode(ws,task,'nvidia/'+MODEL,arm,options,control).run(turns)
    assert resumed['status']=='completed'and len(server.seen)==3,resumed
   else:
    assert done['status']=='interrupted',done
    assert len(server.seen)==1,'Hard pause allowed another upstream dispatch'
    control.unlink();n=len(server.seen);resumed=MemoryEpisode(ws,task,'nvidia/'+MODEL,arm,options,control).run(turns)
    assert resumed['status']=='interrupted'and len(server.seen)==n,'Interrupted active turn was retried'
   # Drain the already-dispatched response before asserting immutable terminal artifacts.
   assert server.responded.wait(3)
   time.sleep(.2);before=snap(work/'runner');n=len(server.seen);MemoryEpisode(ws,task,'nvidia/'+MODEL,arm,options,control).run(turns);time.sleep(.2)
   assert len(server.seen)==n and snap(work/'runner')==before,'Terminal resume called upstream or rewrote artifacts'
   report.update(pass_=True,terminal_resume_new_calls=0,total_local_requests=len(server.seen))
  except BaseException as e:report.update(pass_=False,error=str(e),traceback=traceback.format_exc())
  finally:server.release.set();server.shutdown();server.server_close()
  reports.append(report);(OUT/'proof.json').write_text(json.dumps({'pass':all(r['pass_']for r in reports),'complete':len(reports)==2*len(arms),'external_model_calls':0,'reports':reports},ensure_ascii=False,indent=2));print(json.dumps({'arm':arm,'mode':mode,'pass':report['pass_'],'error':report.get('error'),'proof':str(OUT/'proof.json')},ensure_ascii=False),flush=True)
raise SystemExit(0 if all(r['pass_']for r in reports)else 1)
