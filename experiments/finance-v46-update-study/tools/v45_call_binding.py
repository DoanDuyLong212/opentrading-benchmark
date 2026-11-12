"""Occurrence-level SDK binding. Raw call IDs are scoped by actual generation.
IDs may repeat across sessions or assistant steps; never treat them as a global key.
"""
import json,hashlib
from pathlib import Path
PREFIXES=('opentrading_','mcp__opentrading__','mcp_opentrading_')
def canonical(name):
 for prefix in PREFIXES:
  if name.startswith(prefix):return name[len(prefix):]
 return name
def arguments(value):
 if not isinstance(value,str):return value
 try:return json.loads(value)
 except(ValueError,TypeError):return ('invalid_raw_arguments',value)
def response_calls(provider):
 out=[]
 for ordinal,row in enumerate(provider):
  if row.get('status')!=200:continue
  cap=row.get('raw_response_capture')or{}
  if not cap.get('path'):
   if row.get('response_tool_call_ids'):raise ValueError('Generated calls lack actual response capture')
   continue
  rawbytes=Path(cap['path']).read_bytes()
  expected=cap.get('raw_sha256',cap.get('sha256'))
  if not expected or hashlib.sha256(rawbytes).hexdigest()!=expected:raise ValueError('Actual provider response bytes/hash missing or changed')
  from provider_response import response_chunks
  chunks=response_chunks(rawbytes)
  calls={}
  for chunk in chunks:
   for ci,choice in enumerate(chunk.get('choices',[])):
    for ti,tool in enumerate((choice.get('delta')or choice.get('message')or{}).get('tool_calls',[])):
     key=(choice.get('index',ci),tool.get('index',ti));slot=calls.setdefault(key,{'id':'','name':'','arguments':''});function=tool.get('function')or{}
     for field,value in [('id',tool.get('id')),('name',function.get('name')),('arguments',function.get('arguments'))]:
      if value is not None:slot[field]+=value if isinstance(value,str)else json.dumps(value)
  for (choice,index),call in sorted(calls.items()):out.append({'key':f'{ordinal}:{choice}:{index}','request':ordinal,'provider_index':row.get('index',ordinal+1),'id':call['id'],'tool':canonical(call['name']),'arguments':arguments(call['arguments'])})
 return out

def context_results(provider):
 out=[]
 for request,row in enumerate(provider):
  cap=row.get('native_request_capture')or{}
  if not cap.get('path'):continue
  messages=json.loads(Path(cap['path']).read_text()).get('messages',[]);previous={}
  # Scope to THIS actual message sequence. A later assistant can reuse an ID.
  for index,message in enumerate(messages):
   if message.get('role')=='assistant':
    for to,call in enumerate(message.get('tool_calls',[])):previous[call.get('id')]=(index,call.get('function')or{},to)
   if message.get('role')=='tool':
    sdk=message.get('tool_call_id');prior=previous.get(sdk)
    if prior is None:continue
    assistant,function,ordinal=prior
    out.append({'request':request,'message':index,'assistant_message':assistant,'assistant_ordinal':ordinal,'id':sdk,'tool':canonical(function.get('name','')),'arguments':arguments(function.get('arguments')),'content':message.get('content','')})
 return out

def _num(x):
 # JSON numbers are compared by value: an integral float the model generated (241.0) and the integer the
 # harness replays in history (241) are the same argument (audit 2026-11-11, amendment d dry-run).
 if isinstance(x,float)and x.is_integer():return int(x)
 if isinstance(x,dict):return{k:_num(v)for k,v in x.items()}
 if isinstance(x,list):return[_num(v)for v in x]
 return x
def _sig(args):return json.dumps(_num(args),sort_keys=True)
class CallBindings:
 def __init__(self,provider,request_scopes=None):
  self.provider=list(provider);self.generated=response_calls(provider);self.contexts=context_results(provider);self.claimed=set();self.claims=[]
  scopes=request_scopes or{}
  for g in self.generated:g['scope']=scopes.get(g['request'],'single-session')
  for c in self.contexts:c['scope']=scopes.get(c['request'],'single-session')
  # Recover each assistant occurrence from its actual message position within
  # that request. Align to actual earlier generated occurrences in THIS session.
  # A truncated ambiguous history never justifies guessing the earliest call.
  for request in sorted({c['request']for c in self.contexts}):
   contexts=[c for c in self.contexts if c['request']==request];scope=scopes.get(request,'single-session')
   prior=[g for g in self.generated if g['request']<request and g['scope']==scope]
   # v4.6 fix: bind by the assistant tool-list ordinal (actual generation order
   # within a parallel block), never by SDK-id lexical order.
   positions=sorted({(c['assistant_message'],c['assistant_ordinal'],c['id'],c['tool'],_sig(c['arguments']))for c in contexts})
   signatures=[(p[2],p[3],p[4])for p in positions]
   actual=[(g['id'],g['tool'],_sig(g['arguments']))for g in prior]
   prefix=[];cursor=-1
   for signature in signatures:
    prefix.append(cursor)
    cursor=next((j for j in range(cursor+1,len(actual))if actual[j]==signature),len(actual))
   suffix=[0]*len(signatures);cursor=len(actual)
   for i in range(len(signatures)-1,-1,-1):
    suffix[i]=cursor
    cursor=next((j for j in range(cursor-1,-1,-1)if actual[j]==signatures[i]),-1)
   for i,position in enumerate(positions):
    keys=[prior[j]['key']for j in range(len(prior))if prefix[i]<j<suffix[i]and actual[j]==signatures[i]]
    for c in contexts:
     if(c['assistant_message'],c['assistant_ordinal'],c['id'],c['tool'],_sig(c['arguments']))==position:c['generation_keys']=keys

 def claim(self,sdk_id,tool,args,proof=lambda context:True,scope=None,request_bounds=None,provider_index=None):
  contexts=[c for c in self.contexts if c['id']==sdk_id and c['tool']==canonical(tool)and c['arguments']==args and proof(c)]
  candidates=[g for g in self.generated if g['key']not in self.claimed and (scope is None or g['scope']==scope)and (request_bounds is None or request_bounds[0]<=g['request']<request_bounds[1])and (provider_index is None or g['provider_index']==provider_index)and g['id']==sdk_id and g['tool']==canonical(tool)and g['arguments']==args and any(c.get('generation_keys')==[g['key']]for c in contexts)]
  if len(candidates)!=1:return None
  # Exact message occurrence and source receipt proof select a generation;
  # identical signatures in different notebook states are never interchangeable.
  chosen=min(candidates,key=lambda g:g['request']);self.claimed.add(chosen['key']);self.claims.append({'generation':chosen,'contexts':contexts});return chosen['key']
 def claim_any_sdk(self,sdk_id):
  candidates=[g for g in self.generated if g['key']not in self.claimed and g['id']==sdk_id]
  if len(candidates)!=1:raise ValueError('Local rejection needs an unambiguous occurrence, not raw SDK ID')
  self.claimed.add(candidates[0]['key']);return candidates[0]['key']
 def pending(self):return[g for g in self.generated if g['key']not in self.claimed]
