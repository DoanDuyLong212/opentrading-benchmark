#!/usr/bin/env python3
"""Snapshot MCP plus an authorized USER notebook. Notebook facts are never market receipts."""
import copy,json,os,sys,time,uuid,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
import mcp_snapshot_server as market
NAME='benchmark_user_notebook_read'
DEFINITION={'name':NAME,'description':'Read the user-authorized notebook retained ONLY within this benchmark episode. User preferences/theses/old observations are not verified market facts. An empty notebook means no saved user facts. Read-only; cannot write or activate model suggestions.','inputSchema':{'type':'object','properties':{'query':{'type':'string','description':'Optional literal search text; omit to read all current authorized entries.'}},'additionalProperties':False},'annotations':{'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True}}
def read_notebook(arguments,notebook,trace):
 if set(arguments)-{'query'} or ('query'in arguments and not isinstance(arguments['query'],str)):raise ValueError('invalid user notebook query')
 state=json.loads(Path(notebook).read_text());query=arguments.get('query','').casefold()
 facts=[x for x in state['entries'].values()if not x.get('deleted')and(query in x['text'].casefold()or query in x['id'].casefold())]
 result={'kind':'user_memory_not_market_evidence','memory_trace_id':str(uuid.uuid4()),'facts':facts,'warning':'User-authored preferences or observations; never use as verified prices/financial evidence. Missing/revoked facts must not be inferred.'}
 row={'kind':'user_memory_read','trace_id':result['memory_trace_id'],'arguments':arguments,'notebook_sha256':market.digest(state),'response_sha256':market.digest(result),'response':copy.deepcopy(result),'fact_ids':[x['id']for x in facts],'time':time.time()}
 with open(trace,'a')as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 return result

def main():
 payloadpath=Path(os.environ['BENCH_PAYLOADS']);entries,payloads=market.load_entries(payloadpath);payloadsha=hashlib.sha256(payloadpath.read_bytes()).hexdigest();sources={};derived={}
 ledger=os.environ['BENCH_MCP_LEDGER'];notebook=os.environ['BENCH_USER_NOTEBOOK'];trace=os.environ['BENCH_MEMORY_ACCESS']
 # Reconstitute only actual successful executions already journaled in THIS episode,
 # without replaying an MCP tool or minting any new receipt.
 for line in Path(ledger).read_text().splitlines()if Path(ledger).exists()else[]:
  row=json.loads(line)
  if row.get('status')=='ok'and row.get('matched_entry_id'):
   env=market.select_envelope(entries,row['tool'],row['arguments'])
   if market.digest(env)!=row['response_sha256']:raise ValueError('prior source journal/hash differs')
   env['benchmark_evidence']={k:row[k]for k in('call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of')}
   env['_benchmark_request']={'tool':row['tool'],'arguments':copy.deepcopy(row['arguments'])};sources[row['call_id']]=env
  elif row.get('status')=='ok'and row.get('derived_ref'):
   env=market.calculate(row['arguments'],sources,derived);env['derived_ref']=row['derived_ref']
   if market.digest(env)!=row['response_sha256']:raise ValueError('prior derived journal/hash differs')
   derived[row['derived_ref']]=env
 server=Server('opentrading-memory-snapshot',instructions='Controlled episode-local USER notebook is read-only and distinct from market source evidence. Snapshot data '+str(payloads['snapshot_date']))
 @server.list_tools()
 async def listing():return[types.Tool(**x)for x in market.build_tool_defs(entries)+[DEFINITION]]
 @server.call_tool(validate_input=False)
 async def calling(name,arguments):
  arguments=arguments or{}
  if name==NAME:env=read_notebook(arguments,notebook,trace)
  elif name==market.CALCULATE_NAME:env=market.replay_calculate(arguments,sources,derived,payloadsha,ledger)
  elif name==market.COMPUTE_NAME:env=market.replay_compute(arguments,sources,payloadsha,ledger)
  else:
   env=market.replay_call(entries,name,arguments,payloadsha,ledger)
   if env.get('benchmark_evidence'):
    saved=copy.deepcopy(env);saved['_benchmark_request']={'tool':name,'arguments':copy.deepcopy(arguments)};sources[env['benchmark_evidence']['call_id']]=saved
  return types.CallToolResult(content=[types.TextContent(type='text',text=json.dumps(env,ensure_ascii=False,allow_nan=False))],structuredContent=env,isError=env.get('request_rejected')is True)
 async def run():
  async with stdio_server()as(read,write):await server.run(read,write,server.create_initialization_options())
 anyio.run(run)
if __name__=='__main__':main()
