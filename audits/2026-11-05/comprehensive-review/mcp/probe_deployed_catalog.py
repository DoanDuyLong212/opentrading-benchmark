"""One metadata-only MCP handshake+tools/list. No tools/call, financial data or LLM."""
import asyncio,datetime,hashlib,json,logging,os,pathlib,re,sys
logging.disable(logging.CRITICAL)
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
OUT=pathlib.Path(__file__).parent
async def probe():
 config=json.loads(pathlib.Path('/home/doanlong/.opentrading/mcp.json').read_text())['mcpServers']['opentrading']
 secrets=json.loads(pathlib.Path('/home/doanlong/.opentrading/mcp-auth.json').read_text()).get('env',{})
 def replace(m):
  key=m.group(1) or m.group(2)
  if key not in os.environ and key not in secrets:raise ValueError('missing credential environment reference')
  return os.environ.get(key,secrets.get(key))
 headers={k:re.sub(r'\$\{([A-Za-z_][A-Za-z_0-9]*)\}|\$([A-Za-z_][A-Za-z_0-9]*)',replace,v) for k,v in config.get('headers',{}).items()}
 result={'endpoint':config['url'],'operations':['initialize','notifications/initialized','tools/list'],'financial_or_model_calls':0,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  async with asyncio.timeout(45):
   async with streamablehttp_client(config['url'],headers=headers,timeout=15,sse_read_timeout=20,terminate_on_close=False) as (read,write,getid):
    async with ClientSession(read,write,read_timeout_seconds=datetime.timedelta(seconds=20)) as session:
     init=await session.initialize()
     listed=await session.list_tools()
     catalog=[x.model_dump(mode='json',exclude_none=True) for x in listed.tools]
     OUT.joinpath('deployed-tool-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2))
     result.update(status='ok',serverInfo=init.serverInfo.model_dump(mode='json'),protocolVersion=init.protocolVersion,instructions=init.instructions,capabilities=init.capabilities.model_dump(mode='json',exclude_none=True),tool_count=len(catalog),nextCursor=listed.nextCursor,catalog_sha256=hashlib.sha256(json.dumps(catalog,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest())
 except BaseException as e:
  def names(x):
   if isinstance(x,BaseExceptionGroup):return {'type':type(x).__name__,'children':[names(a) for a in x.exceptions]}
   return {'type':type(x).__name__,'cause':names(x.__cause__) if x.__cause__ else None}
  result.update(status='failed',error_types=names(e))
 OUT.joinpath('deployed-metadata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k not in ('instructions','capabilities')},ensure_ascii=False,indent=2))
 if result['status']!='ok':sys.exit(2)
asyncio.run(probe())
