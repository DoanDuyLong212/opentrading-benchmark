"""In-memory real MCP SDK handler + synthetic stub, NOT production patch/deploy.
API reference: python-sdk/v1.30.0/docs/server.md, lowlevel Server.call_tool.
No provider imports, sockets, credentials, upstream or model calls.
"""
import asyncio,json,importlib.metadata
from pathlib import Path
from mcp import types
from mcp.server.lowlevel import Server
ROOT=Path(__file__).resolve().parents[3]
CAT=json.loads((ROOT/'experiments/finance-v4-study/tools/tool_contracts_v4.json').read_text())
T=next(t for t in CAT['tools']if t['name']=='vn_quote_history')
async def main():
 server=Server('c1-offline-guard-proof');executed=[]
 @server.list_tools()
 async def list_tools():return [types.Tool(**T)]
 @server.call_tool(validate_input=True)
 async def call_tool(name,args):
  executed.append(args)
  if args['symbol']=='EMPTY_STUB':
   err={'error':{'code':'no_data','retryable':False,'message':'Synthetic source returned zero candle rows; argument shape is valid.'}}
   return types.CallToolResult(isError=True,content=[types.TextContent(type='text',text=json.dumps(err))])
  row={'t':'2000-01-03','o':10,'h':12,'l':9,'c':11,'v':100}
  # C1 already validated columns: unknown fields cannot turn a full row into {}.
  fields=args.get('columns')
  if fields is not None:row={k:v for k,v in row.items()if k in fields}
  return {'source':'synthetic-offline-stub','data':{'candles':[row]}}
 handler=server.request_handlers[types.CallToolRequest]
 cases={
  'bad_interval':{'symbol':'HPG','interval':'day'},
  'wrong_columns_type':{'symbol':'HPG','columns':'close'},
  'unknown_columns':{'symbol':'HPG','columns':['close']},
  'valid_projection':{'symbol':'HPG','columns':['c','t']},
  'valid_input_no_data':{'symbol':'EMPTY_STUB'},
 }
 out={}
 for label,args in cases.items():
  result=await handler(types.CallToolRequest(method='tools/call',params=types.CallToolRequestParams(name=T['name'],arguments=args)))
  out[label]=result.model_dump(mode='json',exclude_none=True)
 for key in ['bad_interval','wrong_columns_type','unknown_columns','valid_input_no_data']:assert out[key]['isError']
 assert not out['valid_projection']['isError']
 assert out['valid_projection']['structuredContent']['data']['candles']==[{'t':'2000-01-03','c':11}]
 assert executed==[cases['valid_projection'],cases['valid_input_no_data']]
 assert 'no_data'in out['valid_input_no_data']['content'][0]['text']
 for label in ['bad_interval','wrong_columns_type','unknown_columns']:
  assert 'structuredContent'not in out[label]
 proof={'scope':'Actual installed MCP lowlevel handler validation with synthetic-only stub, not production changed/deployed; no financial data fetched.','sdk_version':importlib.metadata.version('mcp'),'catalog_digest':CAT['catalog_digest'],'cases':out,'executed_stub_calls':executed}
 (Path(__file__).parent/'wire-guard-evidence.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'cases':len(cases),'validation_rejections':3,'valid_success':1,'no_data_distinct':1,'sdk':proof['sdk_version']}))
asyncio.run(main())
