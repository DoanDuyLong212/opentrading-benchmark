"""Pure/source-local repro; never accesses upstream, auth, runtime files or models."""
import asyncio, json, pathlib, sys
from collections import Counter
sys.path.insert(0, '/home/doanlong/MCP-server/src')
sys.path.insert(0, '/home/doanlong/extra/benchmark/tools')
import jsonschema
from mcp import types
from opentrading_mcp.server import create_server, register_all
from opentrading_mcp.tools import vn, compute_financial
from opentrading_mcp.providers import vietstock
from opentrading_mcp.schemas import make_envelope
from opentrading_mcp.tools.shared import project_rows
from opentrading_mcp.providers.errors import ProviderBadData
from mcp_snapshot_server import SCHEMAS, select_entry
OUT=pathlib.Path(__file__).parent
async def main():
 s=create_server(); register_all(s)
 catalog=[t.model_dump(mode='json',exclude_none=True) for t in await s.list_tools()]
 live={t['name']:t for t in catalog}
 stats={}
 for group, ts in [('all',catalog),('snapshot',[t for t in catalog if t['name'] in SCHEMAS])]:
  props=[p for t in ts for p in t['inputSchema'].get('properties',{}).values()]
  stats[group]={'tools':len(ts),'properties':len(props),'property_descriptions':sum('description'in p for p in props),'enum_properties':sum('enum'in p for p in props),'bounded_properties':sum(any(k in p for k in ['minimum','maximum','minItems','maxItems','pattern','minLength','maxLength']) for p in props),'output_schemas':sum('outputSchema'in t for t in ts),'output_schemas_with_fields':sum(bool(t.get('outputSchema',{}).get('properties'))for t in ts),'description_chars':sum(len(t.get('description',''))for t in ts)}
 cases=[]
 for args in [{'symbol':'HPG','days':1},{'symbol':'HPG','interval':'day'},{'symbol':'HPG','columns':'close'},{'symbol':'HPG','columns':['close']},{'symbol':'HPG','days':0},{'symbol':'HPG','days':366},{'symbol':'HPG','extra':True}]:
  row={'args':args}
  for name,schema in [('live_schema',live['vn_quote_history']['inputSchema']),('snapshot_schema',SCHEMAS['vn_quote_history'])]:
   try:jsonschema.validate(args,schema); row[name]='accept'
   except jsonschema.ValidationError as e:row[name]=e.message
  entries=[('example',{'tool':'vn_quote_history','params':{'symbol':'HPG'},'envelope':{'data':{}}})]
  try:select_entry(entries,'vn_quote_history',args);row['snapshot_replay']='accept'
  except Exception as e:row['snapshot_replay']=str(e)
  cases.append(row)
 async def no_cache(*a,**kw):return None
 vn.cache_lookup=no_cache
 async def reject_upstream(*a,**kw):raise ProviderBadData("unknown interval 'day' (1D|1W|1M)")
 vn.run_blocking=reject_upstream
 s.get_context=lambda: None
 handler=s._mcp_server.request_handlers[types.CallToolRequest]
 wire={}
 for name,args in [('provider_bad_data',{'symbol':'HPG','interval':'day'}),('schema_type_error',{'symbol':'HPG','columns':'close'})]:
  result=await handler(types.CallToolRequest(method='tools/call',params=types.CallToolRequestParams(name='vn_quote_history',arguments=args)))
  wire[name]=result.model_dump(mode='json',exclude_none=True)
 # Unknown columns silently project to no fields on a successful row.
 projection={'input':[{'t':'2026-10-30','o':25,'h':26,'l':24,'c':25.5,'v':1000}], 'columns':['close']}
 projection['output']=project_rows(projection['input'],projection['columns'])
 compute_financial.cache_lookup=no_cache
 async def offline_call(label, fn, *args, **kwargs):
  if label=='v':return {'EPS':5,'BVPS':50}
  if label=='q':return [{'close_price':100}]
  raise AssertionError('unexpected provider call')
 async def offline_store(tool, fingerprint, ttl, data, **kwargs):return make_envelope(data,source=kwargs.pop('source'),**kwargs)
 compute_financial._call=offline_call
 compute_financial.cache_store=offline_store
 valuations={}
 for method in ['auto','per','dcf']:
  result=await handler(types.CallToolRequest(method='tools/call',params=types.CallToolRequestParams(name='valuation_run',arguments={'symbol':'FPT','method':method})))
  valuations[method]=result.model_dump(mode='json',exclude_none=True)
 original_post=vietstock._post
 posts=[]
 def post_stub(path, args):posts.append({'path':path,'args':args}); return []
 vietstock._post=post_stub
 period_cases={}
 for period in ['quarter','year','quarterly','garbage']:
  posts.clear(); data=vietstock.financeinfo('FPT',period)
  period_cases[period]={'returned_period':data['period'],'requests':list(posts)}
 vietstock._post=original_post
 data={'scope':'Source-local registration and monkeypatched offline errors only; deployed Render version not contacted.','catalog_stats':stats,'validation_cases':cases,'wire_errors':wire,'column_projection':projection,'valuation_results':valuations,'period_typo_behavior':period_cases}
 OUT.joinpath('deterministic-contract-evidence.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 print(json.dumps(data,ensure_ascii=False,indent=2))
asyncio.run(main())
