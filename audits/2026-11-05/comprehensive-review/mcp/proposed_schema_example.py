"""Contract-only example for planning; registers no production tool, calls no provider."""
import asyncio, json, pathlib
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
Days=Annotated[int,Field(ge=1,le=365,strict=True,description='Số nến, không phải số ngày lịch. Từ 1 đến 365.')]
Column=Literal['t','o','h','l','c','v']
class Candle(BaseModel):
 model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
 t: str=Field(description='Ngày phiên giao dịch ISO YYYY-MM-DD; không dùng fetch time.')
 o: float
 h: float
 l: float
 c: float
 v: float
class QuoteHistoryData(BaseModel):
 model_config=ConfigDict(extra='forbid')
 symbol: str
 interval: Literal['1D','1W','1M']
 candles: list[Candle]
class Provenance(BaseModel):
 source: str
 as_of: str=Field(description='Fetch timestamp, ISO8601 có timezone; không phải ngày giao dịch.')
 data_time: str|None=Field(description='Ngày quan sát mới nhất; null khi không xác định.')
 timezone: Literal['Asia/Ho_Chi_Minh']
class QuoteHistoryResult(BaseModel):
 model_config=ConfigDict(extra='forbid')
 data: QuoteHistoryData
 provenance: Provenance
 price_unit: Literal['thousand_VND_per_share','index_points']
 volume_unit: Literal['shares']
 availability: Literal['available','partial','empty']
 warnings: list[str]
server=FastMCP('offline-contract-example')
@server.tool(annotations=ToolAnnotations(readOnlyHint=True,destructiveHint=False,idempotentHint=True,openWorldHint=True))
async def vn_quote_history_contract_example(
 symbol: Annotated[str,Field(min_length=1,max_length=32,description='Mã cổ phiếu/chỉ số; ví dụ HPG, VNINDEX.')],
 days: Days=365,
 interval: Annotated[Literal['1D','1W','1M'],Field(description='1D ngày, 1W tuần, 1M tháng. Không nhận day/1d tùy ý.')]='1D',
) -> QuoteHistoryResult:
 """Ví dụ contract đề nghị, không phải implementation. Candles là t/o/h/l/c/v."""
 raise NotImplementedError('Schema-only example: must not call this tool.')
async def main():
 tools=await server.list_tools()
 pathlib.Path(__file__).with_suffix('.json').write_text(json.dumps([t.model_dump(mode='json',exclude_none=True)for t in tools],ensure_ascii=False,indent=2))
 print('Registered illustrative typed schema; zero tool/provider/model calls.')
if __name__=='__main__':asyncio.run(main())
