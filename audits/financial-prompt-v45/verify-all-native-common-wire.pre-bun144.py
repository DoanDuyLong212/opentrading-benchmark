#!/usr/bin/env python3
"""Independent bounded actual four-arm local wire check. NEVER calls NVIDIA.
Only synthetic source records and a local scripted HTTP endpoint. No financial inference.
"""
import json,sys,tempfile,threading,time,uuid,traceback
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[2];STUDY=ROOT/'experiments/finance-v45-study'
sys.path[:0]=[str(STUDY/'tools/runners'),str(STUDY/'tools')]
import provider
provider.credential=lambda:'synthetic-local-provider-fixture'
from audit_v45_run import json_objects
from ready_check import verify_mcp_attempt,verify_request_capture
MODEL='deepseek-ai/deepseek-v4.1-flash'
OUT=ROOT/('audits/financial-prompt-v45/all-native-common-wire-'+uuid.uuid4().hex[:8]);OUT.mkdir()
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));self.server.seen.append(body);n=len(self.server.seen)
  if n<=2:
   payload=json.dumps({'error':{'message':'temporary fixture overloaded'}}).encode();self.send_response(503);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
  names=[x['function']['name']for x in body.get('tools',[])];objects=[o for m in body.get('messages',[]) if m.get('role')=='tool' for o in json_objects(m.get('content'))]
  source=next((o for o in objects if isinstance(o.get('benchmark_evidence'),dict) and 'data'in o),None)
  calculation=next((o for o in objects if isinstance(o.get('derived_result'),dict) and 'source_evidence'in o),None)
  if source is None:tool=next(x for x in names if x.endswith('vn_quote_history'));args={'symbol':'SYN'}
  elif calculation is None and n==4:tool=next(x for x in names if x.endswith('analytics_calculate'));args={'expression':'quote*2','variables':[{'name':'quote','call_id':source['benchmark_evidence']['call_id'],'path':'/data/last'}],'output_unit':'đồng/cổ phiếu'}
  else:tool=None
  if tool:message={'role':'assistant','content':None,'tool_calls':[{'id':'fixture-sdk-'+str(n),'type':'function','function':{'name':tool,'arguments':json.dumps(args)}}]};finish='tool_calls'
  else:message={'role':'assistant','content':json.dumps({'value':calculation['derived_result']['value'],'unit':calculation['derived_result']['unit'],'evidence':[source['benchmark_evidence']]} if calculation else {'value':None,'reason':'Synthetic fixture calculator failed; inspect actual ledger','evidence':[source['benchmark_evidence']] if source else []},ensure_ascii=False)};finish='stop'
  usage={'prompt_tokens':100,'completion_tokens':20}
  if body.get('stream'):
   delta={'role':'assistant'}
   if tool:delta['tool_calls']=[{'index':0,**message['tool_calls'][0]}]
   else:delta['content']=message['content']
   chunks=[{'id':'fixture','object':'chat.completion.chunk','created':1,'model':MODEL,'choices':[{'index':0,'delta':delta,'finish_reason':None}]},{'id':'fixture','object':'chat.completion.chunk','created':1,'model':MODEL,'choices':[{'index':0,'delta':{},'finish_reason':finish}],'usage':usage}]
   payload=(''.join('data: '+json.dumps(c,ensure_ascii=False)+'\n\n' for c in chunks)+'data: [DONE]\n\n').encode();ct='text/event-stream'
  else:payload=json.dumps({'id':'fixture','object':'chat.completion','created':1,'model':MODEL,'choices':[{'index':0,'message':message,'finish_reason':finish}],'usage':usage},ensure_ascii=False).encode();ct='application/json'
  self.send_response(200);self.send_header('Content-Type',ct);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
reports=[]
for arm in ['opentrading_baseline','opentrading_finance','opencode','dsh']:
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.seen=[];threading.Thread(target=server.serve_forever,daemon=True).start();provider.NVIDIA_URL='http://127.0.0.1:'+str(server.server_port)
 work=Path(tempfile.mkdtemp(prefix='v45-independent-'+arm+'-'));ws=work/'ws';ws.mkdir();task=work/'task';(task/'environment').mkdir(parents=True)
 payload={'snapshot_date':'2030-04-01','tools':{'synthetic':{'tool':'vn_quote_history','params':{'symbol':'SYN'},'envelope':{'data':{'symbol':'SYN','last':12,'last_t':'2030-03-31'},'units':{'last':'nghìn đồng/cổ phiếu'},'availability':'available','provenance':{'source':'synthetic-not-live','data_time':'2030-03-31','as_of':'2030-04-01'}}}}};(task/'environment/payloads.json').write_text(json.dumps(payload))
 options={'protocol':'financial_product_v45','condition':arm,'native_arm':'opentrading' if arm.startswith('opentrading')else arm,'opentrading_runtime_root':str(STUDY/'experiments/opentrading-runtime'),'prompt_variant':'finance' if arm=='opentrading_finance'else'baseline','finance_policy':arm=='opentrading_finance','request_interval_s':0,'temperature':1,'top_p':.95,'context_window':1048576,'max_output_tokens':8192,'max_total_tokens':3600000,'max_requests':24,'provider_timeout_s':10,'mcp_ledger':str(work/'mcp.jsonl')}
 report={'arm':arm,'work':str(work),'external_model_calls':0}
 try:
  module=__import__('run_opentrading' if arm.startswith('opentrading')else'run_'+arm);result=module.run(ws,'Synthetic engineering fixture. Call vn_quote_history for SYN, then analytics_calculate with expression quote*2 from /data/last and output unit đồng/cổ phiếu. Return exactly one JSON object with value, unit, and original source evidence. Use only the named common calculator; this is not a live financial task.',task,'nvidia/'+MODEL,90,OUT/(arm+'.log'),options)
  report['result']=result;report['local_upstream_requests']=len(server.seen)
  ledger=[json.loads(l)for l in Path(result['provider_ledger']).read_text().splitlines()if l.strip()]
  for row in ledger:verify_request_capture(row,1,.95)
  calls=verify_mcp_attempt(task,{'ledger_path':str(work/'mcp.jsonl')})
  assert result['status']=='ok',result
  assert json.loads(result['final_text'])['value']==24000,result['final_text']
  assert len(server.seen)==5,len(server.seen)
  assert [x['status']for x in ledger]==[503,503,200,200,200],ledger
  assert result['transport_recovered'] and result['tokens']['complete'] is False
  assert sum(x.get('token_reservation',0)for x in ledger)==2*1056768
  assert len(calls)==2 and calls[1]['tool']=='analytics_calculate' and calls[1]['status']=='ok'
  assert server.seen[0]==server.seen[1]==server.seen[2],'Transport retry changed effective payload'
  report['pass']=True
 except Exception as e:report['pass']=False;report['error']=str(e);report['traceback']=traceback.format_exc()
 finally:server.shutdown();server.server_close()
 reports.append(report);(OUT/'proof.json').write_text(json.dumps({'pass':all(r['pass']for r in reports),'complete':len(reports)==4,'external_model_calls':0,'reports':reports},ensure_ascii=False,indent=2));print(json.dumps({'arm':arm,'pass':report['pass'],'error':report.get('error'),'proof':str(OUT/'proof.json')},ensure_ascii=False),flush=True)
raise SystemExit(0 if all(r['pass']for r in reports)else 1)
