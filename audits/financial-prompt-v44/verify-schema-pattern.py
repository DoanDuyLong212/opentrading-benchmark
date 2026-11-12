import json,pathlib,re,hashlib,collections
ROOT=pathlib.Path('/home/doanlong/extra/benchmark');p=ROOT/'experiments/finance-v44-study/results/financial-v44-smoke-deepseek-20261107-startupfix1';out=pathlib.Path('/tmp/v44-final-forensics');e={'scope':'offline regex evaluation and read-only joins only; no model calls, package installs, source edits or gate changes','pattern':'^/data(?:/|$)','observed_compute_rows':[],'capture_hashes':{},'source_links':['https://json-schema.org/understanding-json-schema/reference/string','https://github.com/mlc-ai/xgrammar/issues/838','https://docs.nvidia.com/nim/large-language-models/1.15.0/structured-generation.html','https://github.com/dottxt-ai/outlines/issues/1083']};pattern=e['pattern']
def load(f):
 b=f.read_bytes();e['capture_hashes'][str(f)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)};return json.loads(b)
def jl(f):return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
def findflags(v,path='$'):
 found=[]
 if isinstance(v,dict):
  for k,x in v.items():
   if k in ['strict','guided_json','guided_regex','guided_grammar','guided_decoding_backend','response_format']:found.append({'path':path+'.'+k,'value':x})
   found+=findflags(x,path+'.'+k)
 elif isinstance(v,list):
  for i,x in enumerate(v):found+=findflags(x,f'{path}[{i}]')
 return found
for ledger in sorted(p.glob('trials/*/attempts/*/mcp.jsonl')):
 rows=jl(ledger);comps=[r for r in rows if r['tool']=='analytics_compute']
 if not comps:continue
 a=ledger.parent;provider=jl(a/'provider.jsonl');caps={};calls={};sources={};local=[]
 for line in (a/'run.log').read_text().splitlines():
  try:v=json.loads(line)
  except:continue
  if v.get('localRejection'):local.append(v['callId'])
 for r in provider:
  cap=r.get('native_request_capture',{}).get('path')
  if not cap or not pathlib.Path(cap).is_file():continue
  body=load(pathlib.Path(cap));caps[r['index']]=body
  for m in body.get('messages',[]):
   for c in m.get('tool_calls',[]):
    if c.get('function',{}).get('name','').endswith('analytics_compute'):calls[c['id']]=json.loads(c['function']['arguments'])
   if m.get('role')=='tool' and isinstance(m.get('content'),str):
    try:env,end=json.JSONDecoder().raw_decode(m['content'].lstrip())
    except:continue
    if isinstance(env,dict) and env.get('benchmark_evidence'):sources[env['benchmark_evidence']['call_id']]=env
 # Pair exact args with generated nonlocal SDK IDs in chronological provider order.
 used=set()
 for row in comps:
  candidates=[(r['index'],cid) for r in provider for cid in r.get('response_tool_call_ids',[]) if cid not in local and cid not in used and calls.get(cid)==row['arguments']]
  assert candidates,(ledger,row['call_id']);index,cid=min(candidates);used.add(cid);r=next(r for r in provider if r['index']==index);wire=[]
  for kind in ['native_request_capture','effective_request_capture']:
   f=pathlib.Path(r[kind]['path']);body=load(f);tool=next(t for t in body['tools'] if t.get('function',{}).get('name','').endswith('analytics_compute'));actual=tool['function']['parameters']['properties']['operands']['items']['properties']['path']['pattern'];assert actual==pattern
   wire.append({'kind':kind,'path':str(f),'pattern':actual,'explicit_mode_flags_anywhere_in_request':findflags(body),'tool_choice':body.get('tool_choice')})
  refs=[]
  for ref in row['arguments']['operands']:
   s=ref['path'];env=sources[ref['call_id']];assert isinstance(env['data']['last'],(int,float));assert env['benchmark_evidence']['call_id']==ref['call_id']
   refs.append({**ref,'regex_search':bool(re.search(pattern,s)),'regex_fullmatch':bool(re.fullmatch(pattern,s)),'actual_source_numeric_leaf':{'path':'/data/last','value':env['data']['last'],'unit':env.get('units',{}).get('last'),'date':env['data'].get('last_t'),'regex_search':bool(re.search(pattern,'/data/last')),'regex_fullmatch':bool(re.fullmatch(pattern,'/data/last'))}})
  e['observed_compute_rows'].append({'trial_id':ledger.parts[-4],'mcp_call_id':row['call_id'],'sdk_call_id':cid,'generating_provider_index':index,'generating_upstream_attempted':r.get('upstream_attempted'),'generating_status':r.get('status'),'ledger_path':str(ledger),'error':row.get('error'),'wire':wire,'operands':refs})
assert len(e['observed_compute_rows'])==17
paths=collections.Counter(ref['path'] for row in e['observed_compute_rows'] for ref in row['operands']);e['summary']={'mcp_attempts':17,'path_occurrences':dict(paths),'attempts_by_uniform_path':dict(collections.Counter(row['operands'][0]['path'] for row in e['observed_compute_rows'])),'every_recorded_path_search_and_fullmatch':all(ref['regex_search'] and ref['regex_fullmatch'] for row in e['observed_compute_rows'] for ref in row['operands']),'every_actual_source_leaf_search_but_not_fullmatch':all(ref['actual_source_numeric_leaf']['regex_search'] and not ref['actual_source_numeric_leaf']['regex_fullmatch'] for row in e['observed_compute_rows'] for ref in row['operands']),'every_generating_request_native_and_effective_exact_prefix_pattern':True,'any_explicit_strict_guided_or_response_format_flags':any(w['explicit_mode_flags_anywhere_in_request'] for row in e['observed_compute_rows'] for w in row['wire'])}
e['control_paths']=[{'path':s,'regex_search':bool(re.search(pattern,s)),'regex_fullmatch':bool(re.fullmatch(pattern,s))} for s in ['', '/', '/data','/data/','/data/last','/data/last_t','/data/rows/0/values/0','data/last','/metadata/last']]
e['deduction']='For this ASCII pattern, whole-string language is exactly {/data,/data/}; both are nonnumeric containers/absent-empty-key references for the actual quote envelopes. The observed set equals that two-string language. This proves compatibility with the full-match hypothesis, not provider implementation or causality.'
(out/'pattern-summary.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n');print(json.dumps(e['summary'],indent=2));print('hashes',len(e['capture_hashes']))
