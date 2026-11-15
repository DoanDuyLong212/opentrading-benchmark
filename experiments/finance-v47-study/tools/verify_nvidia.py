#!/usr/bin/env python3
"""Preregistered v45 synthetic admission/schema canary. No financial task input.
Prints the manifest by default; network requires --execute and approved manifest SHA.
No retry and no response-based changes to prompts or settings.
"""
import argparse,hashlib,json,time,urllib.request,urllib.error
from pathlib import Path
import os
NVIDIA_URL='https://integrate.api.nvidia.com/v1'
DEFAULT_MODEL='nvidia/nemotron-3.5-super-vl-120b-a12b'
AUTHORIZED_MODELS={DEFAULT_MODEL,'deepseek-ai/deepseek-v4.1-flash'}
def credential():
 key=os.environ.get('NVIDIA_API_KEY')
 if key:return key
 for name in ('~/.opentrading/auth.json','~/.local/share/opencode/auth.json'):
  try:
   entry=json.loads(Path(name).expanduser().read_text()).get('nvidia',{});key=entry.get('key') or entry.get('apiKey')
   if key:return key
  except (OSError,ValueError):pass
 raise ValueError('NVIDIA credential missing')

PATTERNS={'prefix':'^/data(?:/|$)','anchored':'^/data/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$','none':None}
def manifest():
 return {'version':'v45-synthetic-canary-1','models':sorted(AUTHORIZED_MODELS),'treatments':PATTERNS,'repeats':2,'cases':12,'max_chat_requests':24,'max_catalog_requests':1,'max_tokens_per_request':4096,'request_timeout_seconds':240,'total_deadline_seconds':7200,'retries':0,'synthetic_object':{'data':{'point':17}},'expected_selector':'/data/point','sampling':{model:{'temperature':1 if model==DEFAULT_MODEL else 0,'top_p':.95 if model==DEFAULT_MODEL else 1} for model in sorted(AUTHORIZED_MODELS)},'acceptance':'Admission requires both corrected-pattern and no-pattern repeats: expected model identity, valid function selector /data/point, continuation uses synthetic17, complete usage; pattern treatments reported regardless outcome.'}
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
REQUEST_LOG=None
REQUEST_COUNT={'chat':0,'catalog':0}
def event(row):
 if REQUEST_LOG:
  with REQUEST_LOG.open('a') as fp:fp.write(json.dumps(row,sort_keys=True)+'\n');fp.flush();os.fsync(fp.fileno())
def request(path,body,deadline):
 if time.monotonic()>=deadline:raise RuntimeError('sealed canary deadline exhausted before dispatch')
 kind='catalog' if body is None else 'chat'
 if REQUEST_COUNT[kind]>=(1 if kind=='catalog' else 24):raise RuntimeError('sealed request cap exceeded')
 REQUEST_COUNT[kind]+=1
 event({'phase':'before_dispatch','kind':kind,'index':REQUEST_COUNT[kind],'body':body,'utc_unix':time.time()})
 req=urllib.request.Request(NVIDIA_URL+path,data=None if body is None else json.dumps(body).encode(),headers={'Authorization':'Bearer '+credential(),'Content-Type':'application/json'})
 started=time.time();raw=b'';status=None
 try:
  with urllib.request.urlopen(req,timeout=min(240,max(.1,deadline-time.monotonic()))) as response:status=response.status;raw=response.read(4000000)
 except urllib.error.HTTPError as exc:status=exc.code;raw=exc.read(4000000)
 except (OSError,TimeoutError,urllib.error.URLError) as exc:
  event({'phase':'transport_error','kind':kind,'index':REQUEST_COUNT[kind],'error':type(exc).__name__})
  return {'status':status,'error':type(exc).__name__,'duration_s':time.time()-started},{}
 key=credential().encode();raw=raw.replace(key,b'[REDACTED]')
 event({'phase':'response','kind':kind,'index':REQUEST_COUNT[kind],'status':status,'raw':raw.decode(errors='replace')})
 try:data=json.loads(raw)
 except ValueError:data={}
 if not isinstance(data,dict):data={}
 return {'status':status,'raw_response':raw.decode(errors='replace'),'response_sha256':hashlib.sha256(raw).hexdigest(),'response_model':data.get('model'),'usage':data.get('usage'),'finish_reasons':[x.get('finish_reason') for x in data.get('choices',[]) if isinstance(x,dict)] if isinstance(data,dict) and isinstance(data.get('choices'),list) else [],'duration_s':time.time()-started},data

def first_message(answer):
 choices=answer.get('choices') if isinstance(answer,dict) else None
 if not isinstance(choices,list) or not choices or not isinstance(choices[0],dict):return {}
 message=choices[0].get('message')
 return message if isinstance(message,dict) else {}

def exact_answer(content):
 try:return json.loads(content)=={'value':17}
 except (TypeError,ValueError):return False

def main():
 global REQUEST_LOG
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--approved-manifest-sha256');ap.add_argument('--out',default='audits/model-admission/canary-results.json');args=ap.parse_args();m=manifest();sha=digest(m)
 if not args.execute:print(json.dumps({'manifest':m,'sha256':sha},indent=2));return 0
 if args.approved_manifest_sha256!=sha:raise SystemExit('Approved exact manifest SHA required')
 dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():raise SystemExit('Output exists; refuse replay/retry canary')
 REQUEST_LOG=dest.with_suffix('.attempts.jsonl')
 if REQUEST_LOG.exists():raise SystemExit('Canary attempt log exists; no replay after interrupted dispatch')
 with dest.open('x') as fp:fp.write(json.dumps({'manifest':m,'manifest_sha256':sha,'status':'registered_before_catalog'},indent=2)+'\n');fp.flush();os.fsync(fp.fileno())
 deadline=time.monotonic()+m['total_deadline_seconds'];catalog,data=request('/models',None,deadline);ids={x.get('id') for x in data.get('data',[])}
 results={'manifest':m,'manifest_sha256':sha,'catalog':catalog,'cases':[],'chat_requests':0}
 for model in sorted(AUTHORIZED_MODELS):
  if model not in ids:continue
  for treatment,pattern in PATTERNS.items():
   for repeat in range(2):
    if time.monotonic()>=deadline:break
    prop={'type':'string'}
    if pattern:prop['pattern']=pattern
    function={'name':'select_numeric','description':'Select exact JSON pointer of numeric point already supplied. No lookup.','parameters':{'type':'object','properties':{'path':prop},'required':['path'],'additionalProperties':False}}
    body={'model':model,'messages':[{'role':'user','content':'Object: {"data":{"point":17}}. Call select_numeric with exact JSON pointer of point. Do not select parent object.'}],'tools':[{'type':'function','function':function}],'tool_choice':'auto','max_tokens':4096,**m['sampling'][model]}
    row={'model':model,'treatment':treatment,'repeat':repeat,'request':body,'state':'first_dispatch_registered'};results['cases'].append(row);dest.write_text(json.dumps(results,indent=2)+'\n');first,answer=request('/chat/completions',body,deadline);results['chat_requests']+=1;row['first']=first
    message=first_message(answer);calls=message.get('tool_calls',[])
    try:valid=len(calls)==1 and calls[0]['function']['name']=='select_numeric' and json.loads(calls[0]['function']['arguments'])=={'path':'/data/point'}
    except (ValueError,KeyError,TypeError):valid=False
    row['function_call_verified']=valid
    if calls and len(calls)==1 and calls[0].get('id'):
     selected=json.loads(calls[0]['function'].get('arguments','{}')) if valid else {}
     body={**body,'messages':body['messages']+[message,{'role':'tool','tool_call_id':calls[0]['id'],'content':json.dumps({'value':17} if valid else {'error':'invalid_selector','expected_numeric_leaf':'/data/point'})},{'role':'user','content':'Return only JSON {"value":17} from tool result, or {"error":"invalid_selector"} when rejected.'}]}
     row['continuation_request']=body;row['state']='continuation_dispatch_registered';dest.write_text(json.dumps(results,indent=2)+'\n');second,continuation=request('/chat/completions',body,deadline);results['chat_requests']+=1;row['tool_loop']={**second,'request':body,'message':first_message(continuation)}
    row['state']='completed';dest.write_text(json.dumps(results,indent=2)+'\n')
  eligible=[r for r in results['cases'] if r['model']==model and r['treatment'] in ('anchored','none')]
  def usage_ok(r):return isinstance(r.get('usage'),dict) and all(isinstance(r['usage'].get(k),int) and not isinstance(r['usage'][k],bool) and r['usage'][k]>=0 for k in ('prompt_tokens','completion_tokens'))
  accepted=len(eligible)==4 and all(r['function_call_verified'] and r['first'].get('status')==200 and r['first'].get('response_model')==model and r.get('tool_loop',{}).get('response_model')==model and r['tool_loop'].get('status')==200 and usage_ok(r['first']) and usage_ok(r['tool_loop']) and exact_answer(r['tool_loop'].get('message',{}).get('content','')) for r in eligible)
  if accepted:
   receipt={'model':model,'response_model':model,'function_call_verified':True,'tool_loop':{'status':200},'canary_path':str(dest.resolve()),'manifest_sha256':sha,'case_sha256s':[digest(r) for r in eligible]}
   (dest.parent/(model.replace('/','__')+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 dest.write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({'out':str(dest),'chat_requests':results['chat_requests'],'manifest_sha256':sha}));return 0
if __name__=='__main__':raise SystemExit(main())
