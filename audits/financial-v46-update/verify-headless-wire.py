#!/usr/bin/env python3
"""Actual v45 OT adapter + snapshot stdio + native utilities; ONLY local scripted HTTP, no real inference."""
import json,sys,tempfile,threading,urllib.request,uuid,hashlib
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'experiments/finance-v46-update-study'
BUN=ROOT/'experiments/toolchains/bun-1.4.4/bun'
BUN_SHA256='10702245766b225e70bbf6235fd6b47214fd94b4760d00ffaed8ab0df57ac235'
assert hashlib.sha256(BUN.read_bytes()).hexdigest()==BUN_SHA256,'Pinned Bun changed'
sys.path.insert(0,str(STUDY/'tools'));sys.path.insert(0,str(STUDY/'tools/runners'))
import provider
provider.credential=lambda:'synthetic-local-fixture-not-a-provider-key'
model='deepseek-ai/deepseek-v4.1-flash'
seen=[]
def objects(body):
 for m in body.get('messages',[]):
  if m.get('role')!='tool':continue
  content=m.get('content','')
  if not isinstance(content,str):continue
  i=content.find('{')
  if i>=0:
   try:yield json.JSONDecoder().raw_decode(content[i:])[0]
   except ValueError:pass
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])));seen.append(body)
  results=list(objects(body))
  names=[t.get('function',{}).get('name') for t in body.get('tools',[])]
  phase=len(seen)-1
  if phase==0:tool=next(n for n in names if n.endswith('vn_quote_history'));args={'symbol':'SYN'}
  elif phase==1:tool='calculate';args={'expression':'x*2','values':{'x':{'from_call':'r1','field':'last'}},'unit':'đồng/cổ phiếu'}
  elif phase==2:tool='read_result';args={'id':'r1'}
  else:tool=None
  if tool:message={'role':'assistant','content':None,'tool_calls':[{'id':'fixture-sdk-'+str(phase),'type':'function','function':{'name':tool,'arguments':json.dumps(args)}}]};finish='tool_calls'
  else:
   calc=next(r for r in results if 'derived_result'in r)
   source=next(r for r in results if 'benchmark_evidence'in r)
   message={'role':'assistant','content':json.dumps({'value':calc['result'],'unit':calc['unit'],'evidence':[source['benchmark_evidence']]},ensure_ascii=False)};finish='stop'
  usage={'prompt_tokens':100,'completion_tokens':20}
  if body.get('stream'):
   delta={'role':'assistant'}
   if tool:delta['tool_calls']=[{'index':0,**message['tool_calls'][0]}]
   else:delta['content']=message['content']
   chunks=[{'id':'fixture-chat','object':'chat.completion.chunk','created':1,'model':model,'choices':[{'index':0,'delta':delta,'finish_reason':None}]},{'id':'fixture-chat','object':'chat.completion.chunk','created':1,'model':model,'choices':[{'index':0,'delta':{},'finish_reason':finish}],'usage':usage}]
   payload=(''.join('data: '+json.dumps(c,ensure_ascii=False)+'\n\n'for c in chunks)+'data: [DONE]\n\n').encode();content_type='text/event-stream'
  else:
   payload=json.dumps({'id':'fixture-chat','object':'chat.completion','created':1,'model':model,'choices':[{'index':0,'message':message,'finish_reason':finish}],'usage':usage},ensure_ascii=False).encode();content_type='application/json'
  self.send_response(200);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();provider.NVIDIA_URL='http://127.0.0.1:'+str(server.server_port)
out=ROOT/('audits/financial-v46-update/headless-wire-'+uuid.uuid4().hex[:8]);out.mkdir(parents=True,exist_ok=False)
work=Path(tempfile.mkdtemp(prefix='v45-headless-'));ws=work/'ws';ws.mkdir();task=work/'task';(task/'environment').mkdir(parents=True)
payload={'snapshot_date':'2030-04-01','tools':{'synthetic':{'tool':'vn_quote_history','params':{'symbol':'SYN'},'envelope':{'data':{'symbol':'SYN','last':12,'last_t':'2030-03-31'},'units':{'last':'nghìn đồng/cổ phiếu'},'availability':'available','provenance':{'source':'synthetic-fixture-not-live','data_time':'2030-03-31','as_of':'2030-04-01'}}}}}
(task/'environment/payloads.json').write_text(json.dumps(payload))
from run_opentrading import run
try:
 result=run(ws,'Use the synthetic quote tool, calculate twice the last price in đồng/cổ phiếu, read_result once, then return exactly a JSON object with value, unit and evidence copied from source receipts. This is a synthetic technical fixture.',task,'nvidia/'+model,60,out/'native.log',{'native_bun_binary':str(BUN),'native_bun_sha256':BUN_SHA256,'protocol':'financial_product_v45','native_arm':'opentrading','condition':'opentrading_finance','opentrading_runtime_root':str(STUDY/'experiments/opentrading-runtime'),'prompt_variant':'finance','finance_policy':True,'request_interval_s':0,'temperature':1,'top_p':.95,'max_output_tokens':8192,'max_total_tokens':3600000,'provider_timeout_s':10,'mcp_ledger':str(out/'mcp.jsonl')})
 rows=[json.loads(l)for l in Path(result['native_derived_ledger']).read_text().splitlines()] if result.get('native_derived_ledger')else[]
 derived=[r for r in rows if r.get('kind')=='native_derived']
 assert result['status']=='ok',result
 assert (out/'native.log').read_text().splitlines()[1].startswith(str(BUN)+' '),'Actual OT command used another Bun'
 answer=json.loads(result['final_text']);assert answer['value']==24000,answer
 assert len(seen)==4,len(seen)
 assert len(derived)==1 and derived[0]['result']['derived_result']['inputs'][0]['sdk_call_id']=='fixture-sdk-0',derived
 inventory=json.loads(Path(result['inventory_path']).read_text())['native_inventory']
 assert sorted(x['name']for x in inventory['tools']if x.get('source')!='mcp:opentrading')==['calculate','compute','read_result']
 assert inventory['memory']=='none' and inventory['native_retry_max']==0
 report={'pass':True,'fixture':True,'external_provider_calls':0,'local_scripted_requests':len(seen),'work':str(work),'result':result,'native_derived':derived,'expected_value':24000,'native_bun_binary':str(BUN),'native_bun_sha256':BUN_SHA256,'actual_bun_command_verified':True}
 (out/'proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({'pass':True,'external_provider_calls':0,'local_scripted_requests':len(seen),'proof':str(out/'proof.json')}))
finally:server.shutdown();server.server_close()
