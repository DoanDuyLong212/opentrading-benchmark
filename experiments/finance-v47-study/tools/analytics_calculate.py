"""Shared native safe calculator, with session-bound financial source/derived refs.
Model callers never supply numeric values or arbitrary filesystem/code paths.
"""
import copy,json,math,subprocess,os,hashlib
from pathlib import Path
from analytics_compute import traverse,scope_for,unit_for
NAME='analytics_calculate'
VARIABLE={'type':'object','properties':{'name':{'type':'string','pattern':'^[A-Za-z_][A-Za-z0-9_]*$'},'call_id':{'type':'string','minLength':1},'path':{'type':'string','pattern':'^/data/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$'},'derived_id':{'type':'string','pattern':'^calc:[A-Za-z0-9-]+$'}},'required':['name'],'oneOf':[{'required':['call_id','path'],'not':{'required':['derived_id']}},{'required':['derived_id'],'not':{'anyOf':[{'required':['call_id']},{'required':['path']}]}}],'additionalProperties':False}
SCHEMA={'type':'object','properties':{'expression':{'type':'string','minLength':1,'maxLength':4096},'variables':{'type':'array','items':VARIABLE,'minItems':1,'maxItems':100},'output_unit':{'type':'string','maxLength':128},'precision':{'type':'integer','minimum':0,'maximum':12},'alignment':{'type':'string','enum':['same_period','time_series','cross_entity_same_period']}},'required':['expression','variables'],'additionalProperties':False,'x-opentrading-schema-profile':'grounded-calculation-v45'}
DEFINITION={'name':NAME,'description':'Read-only financial calculator using the SAME native OpenTrading expression/unit engine, never arbitrary code. Supply named variables from successful retrieved original benchmark_evidence.call_id + exact numeric JSON pointer, or a prior analytics_calculate derived_ref via derived_id. No typed financial numbers. expression supports + - * / ^ parentheses and native functions abs,min,max,sqrt,sum,avg,ln,log10,exp; formula constants only 0,1,2,3,4,12,100,252,365. All data values must be referenced. output_unit converts dimensions: a/b with output_unit % already multiplies fraction by100; do not also multiply expression by100. Use explicit alignment: same_period defaults same entity/period/scope; time_series permits distinct periods for same entity/metric; cross_entity_same_period permits named entity comparison at same period. Price per-share scale: nghìn đồng/cổ phiếu -> đồng/cổ phiếu, never strip share dimension; public final quote VND means VND per share only when task declares asset-price convention. Returned derived_ref is NOT upstream evidence; cite original source_evidence receipts. No lookup, shell, files or network.', 'inputSchema':SCHEMA,'annotations':{'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}}
ROOT=Path(__file__).resolve().parents[1]
SHIM=ROOT/'tools/runners/native_calculate.ts'
# Explicit frozen controller/config locator, never isolated HOME/PATH lookup.
_BUN_CONFIG=json.loads((ROOT/'tools/bench_config.json').read_text())['provider_options']
BUN=Path(os.environ.get('BENCH_BUN_BIN',_BUN_CONFIG['native_bun_binary'])).resolve()
BUN_SHA256=os.environ.get('BENCH_BUN_SHA256',_BUN_CONFIG['native_bun_sha256'])
if BUN!=Path(_BUN_CONFIG['native_bun_binary']).resolve() or BUN_SHA256!=_BUN_CONFIG['native_bun_sha256']:raise ValueError('Untrusted native arithmetic binary locator/receipt')

def raw_unit(env,path):
 _,ancestors=traverse(env,path);key=path.split('/')[-1].replace('~1','/').replace('~0','~');units=env.get('units',{})
 # Same public metadata specificity as native: exact pointer > row > field.
 if isinstance(units,dict) and isinstance(units.get(path),str):return units[path]
 nearest=next((row['unit'] for row in reversed(ancestors) if isinstance(row.get('unit'),str)),None)
 if nearest:return nearest
 found=[]
 if isinstance(units,dict):
  for fields,value in units.items():
   if key in [x.strip() for x in fields.replace(';',',').split(',')] and isinstance(value,str):found.append(value)
 if not found or len(set(found))!=1:raise ValueError('source numeric field requires explicit unambiguous unit metadata')
 return found[0]

def source_input(variable,sources):
 cid=variable['call_id']
 if cid not in sources:raise ValueError('call_id is not a successful retrieved source in this session')
 env=sources[cid];value,_=traverse(env,variable['path']);receipt=env['benchmark_evidence'];scope=scope_for(env,variable['path'])
 _,ancestors=traverse(env,variable['path'])
 explicit_scope=next((str(row[key]) for row in reversed(ancestors) for key in ('scope','statement_scope','consolidation','report_scope') if key in row),None)
 query=(env.get('_benchmark_request') or {}).get('arguments',{})
 scope_from_query=False
 if explicit_scope is None:
  explicit_scope=next(('consolidated' if row['consolidated'] else 'separate' for row in reversed(ancestors) if isinstance(row.get('consolidated'),bool)),None)
 if explicit_scope is None:
  if isinstance(query.get('consolidated'),bool):explicit_scope='consolidated' if query['consolidated'] else 'separate';scope_from_query=True
  elif isinstance(query.get('scope'),str):explicit_scope=query['scope'];scope_from_query=True
 if explicit_scope is not None:scope['scope']=explicit_scope
 source_only=scope_for({k:v for k,v in env.items() if k!='_benchmark_request'},variable['path'])
 if scope_from_query or scope.get('period') and not source_only.get('period'):scope['query_context']=copy.deepcopy(query)
 return {'name':variable['name'],'call_id':cid,'path':variable['path'],'value':float(value),'value_decimal':str(value),'unit':raw_unit(env,variable['path']),**scope,'source_response_sha256':receipt['response_sha256'],'source_payload_sha256':receipt['payload_sha256'],'receipt':copy.deepcopy(receipt)}

def roots_for(variables,sources,derived):
 roots=[];expression_inputs=[];names=set()
 for variable in variables:
  name=variable['name']
  if name in names:raise ValueError('variable names must be unique')
  names.add(name)
  if 'call_id' in variable:
   row=source_input(variable,sources);roots.append(row);expression_inputs.append(row)
  else:
   ref=variable['derived_id']
   if ref not in derived:raise ValueError('derived_id not produced in this session')
   env=derived[ref];result=env['derived_result'];these=[]
   for prior in result['inputs']:
    live=source_input({'name':prior['name'],'call_id':prior['call_id'],'path':prior['path']},sources)
    if any(live.get(key)!=prior.get(key) for key in ('value_decimal','unit','entity','period','scope','metric','source_response_sha256','source_payload_sha256')):raise ValueError('derived root source changed or missing')
    these.append(live)
   roots.extend(these);expression_inputs.append({'name':name,'derived_id':ref,'value':result['value'],'unit':result['unit']})
 if len(roots)>1000:raise ValueError('derived chain root count exceeds 1000')
 return roots,expression_inputs

def validate_alignment(roots,alignment):
 if any(not r.get('period') for r in roots):raise ValueError('missing financial period: source or verified SDK query metadata required, capture time is not a statement period')
 if alignment=='cross_entity_same_period' and len({r.get('metric') for r in roots})>1:raise ValueError('cross_entity_same_period requires equivalent recorded metrics')
 fields=['scope']+([] if alignment=='time_series' else ['period'])+([] if alignment=='cross_entity_same_period' else ['entity'])
 for field in fields:
  values=[r.get(field) for r in roots];declared={v for v in values if v is not None}
  if declared and (None in values or len(declared)>1):raise ValueError('source '+field+' alignment mismatch or missing metadata')
 if alignment=='time_series' and len({r.get('metric') for r in roots})>1:raise ValueError('time_series requires same recorded metric')

def calculate(args,sources,derived=None):
 import jsonschema
 jsonschema.Draft7Validator(SCHEMA).validate(args)
 roots,variables=roots_for(args['variables'],sources,derived or {})
 validate_alignment(roots,args.get('alignment','same_period'))
 request={'expression':args['expression'],'variables':[{k:r[k] for k in ('name','value','unit')} for r in variables],**{k:args[k] for k in ('output_unit','precision') if k in args}}
 if not SHIM.is_file() or not BUN.is_file():raise ValueError('pinned native calculation runtime missing')
 if hashlib.sha256(BUN.read_bytes()).hexdigest()!=BUN_SHA256:raise ValueError('Pinned native arithmetic binary content changed')
 try:result=subprocess.run([str(BUN),str(SHIM)],input=json.dumps(request),text=True,capture_output=True,timeout=15,cwd=ROOT/'experiments/opentrading-runtime',env={k:os.environ[k] for k in ('PATH','LANG','LC_ALL','TZ') if k in os.environ})
 except (OSError,subprocess.TimeoutExpired) as exc:raise ValueError('pinned native arithmetic engine unavailable: '+type(exc).__name__) from exc
 if result.returncode:
  try:message=json.loads(result.stdout).get('error',{}).get('message') or result.stderr.strip()
  except ValueError:message=result.stderr.strip()
  raise ValueError('native arithmetic rejected: '+message[:1000])
 data=json.loads(result.stdout)
 if not isinstance(data.get('result'),(int,float)) or not math.isfinite(data['result']):raise ValueError('native result must be finite numeric')
 receipts=[]
 for root in roots:
  if root['receipt'] not in receipts:receipts.append(copy.deepcopy(root['receipt']))
 verification={field:('verified' if all(r.get(field) for r in roots) else 'unverified_missing_all') for field in ('entity','period','scope')}
 if args.get('alignment')=='cross_entity_same_period':verification['entity']='explicit_cross_entity_comparison'
 return {'derived_result':{'alignment_verification':verification,'expression':args['expression'],'value':data['result'],'value_decimal':str(data['result']),'unit':data['unit'],'inputs':roots,'expression_inputs':variables,'source_scopes':[{k:r.get(k) for k in ('entity','period','scope','metric')} for r in roots],'engine':'shared-native-calculate-v45'},'source_evidence':receipts,'availability':'derived_from_retrieved_sources','note':'Derived calculation, not upstream evidence. Cite original source_evidence; derived_ref supports calculation chaining only.'}
