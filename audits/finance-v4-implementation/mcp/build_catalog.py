"""Build shared C1 metadata/input contract; never imports financial providers or sends requests."""
import copy, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SOURCE=Path('/home/doanlong/MCP-server/src/opentrading_mcp')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()
frozen=json.loads((ROOT/'tools/snapshot_tool_schemas.json').read_text())
live_path=ROOT/'audits/2026-11-05/comprehensive-review/mcp/live-source-tool-catalog.json'
live={x['name']:x for x in json.loads(live_path.read_text())}
D={
'yf_commodities': {'tickers':'Yahoo Finance tickers, e.g. GC=F (gold), CL=F (oil), BTC-USD. Null uses the provider commodity universe; do not use domestic equity symbols here.','period':'Lookback using yfinance period spelling; default 2d. Not a financial statement quarter/year.','interval':'yfinance bar interval, default lowercase 1d; spelling differs from vn_quote_history.'},
'vs_overview_trading':{'symbol':'Vietnamese listed equity ticker, e.g. HPG; trading overview is not a historical statement series.'},
'symbol_resolve':{'query':'Asset ticker or human-readable asset name to resolve. May be ambiguous; inspect candidates and asset class before selecting the next tool.','limit':'Maximum resolver candidates returned; default 5.'},
'market_movers':{'top_n':'Number of rows in each gainers/losers/volume ranking, default 10.','universe':'Ranking universe: vn30 for the VN30 basket, hose for HOSE; not an arbitrary ticker list.'},
'valuation_run':{'symbol':'Vietnamese equity ticker. Output is observed price/EPS/BVPS and quotients, not a fair-value target.','btype':'Business type code: 1 ordinary, 2 broker, 3 bank, 5 insurance. Unknown codes produce a warning and auto label; this is not a sector-specific valuation model.','method':'Supported label selection: auto, per, pb, ensemble. These label the existing quotient output; no DCF, fair-value band, target price or sensitivity is implemented. Unit/basis compatibility can remain unverified.'},
'financial_statements':{'symbol':'Vietnamese listed equity ticker.','period':'Statement frequency: quarter or year. quarter means quarterly reports; year means annual reports. quarterly/yearly are not supported values and must not silently select annual data.','statement':'Requested statement section: all, KQKD (income), CDKT (balance), CSTC (ratios), or exact source statement label. Inspect returned section and warnings; unknown names may return all sections in production.','periods_n':'Number of most recent periods to display, default 15. Read each value under its explicit period label and row unit; as_of is fetch time, not fiscal period.'},
'peer_compare':{'symbol':'Main Vietnamese equity ticker, compared with peers.','peers':'Other equity tickers. Production uses at most the first five peers; excess peers are silently omitted. Supply at most five when complete coverage is required.','metrics':'Optional list of source item_id strings. Aliases pe→p_e, pb→p_b, roe→roe, roa→roa, eps→trailing_eps, bvps→book_value_per_share_bvps are normalized by production. Other actual source item_ids are allowed; this is not a closed six-item enum. Missing/unknown metrics have warnings. Values belong to the latest annual period for each symbol, and PE/PB are period-end multiples, not current-price multiples.'},
'stock_overview':{'symbol':'Vietnamese equity ticker; combines quote/company profile. Inspect price and ratio observation bases separately.'},
'crypto_spot':{'symbols':'Binance-style spot pairs, e.g. BTCUSDT or ETHUSDT; this is an array, not a comma-separated string.'},
'financial_detail':{'symbol':'Vietnamese equity ticker.','statement':'Statement code: KQKD income, CDKT balance, LCTT cash flow, TM notes, BCTT. These are source codes, not English aliases.','periods_n':'Most recent permitted source periods to display, default 4; inspect period labels, report_type and per-row unit. Tool documents financial values in billions VND; never assume other tools use the same unit.'},
'signals_technical':{'symbol':'Vietnamese equity ticker.','interval':'Candle frequency: 1D daily, 1W weekly, 1M monthly. day, daily and minute aliases are not supported here.','indicators':'Optional output field names, e.g. rsi14, macd, sma20, recommend, patterns, support, resistance, rs_vs_bench, pos_52w, sma150, ichimoku, swings, swing_trend, fib. Null returns all. This list is illustrative, not a closed source field enum. Insufficient history yields null, not fabricated 0/50.','ichimoku_convention':'offset25 uses displacement 25; classic26 uses displacement 26. No claim of full TradingView parity.'},
'vs_indicator_data':{'category_id':'Optional Vietstock indicator category ID; obtain IDs from source metadata, do not invent mappings.','term_type_id':'Vietstock term-type ID (integer or string), default 3. Retains source ID semantics; do not infer monthly/yearly solely from a prose label.','sub_term_type_id':'Optional source sub-term-type ID, integer/string or null.','from_date':'Start date string in YYYY-MM-DD spelling, default 2022-01-01.','to_date':'Optional end date string in YYYY-MM-DD spelling or null.','indicator':'Optional source indicator filter such as CPI. Inspect series definition, unit and period; CPI may refer to different comparison bases.'},
'vn_quote_history':{'symbol':'Vietnamese listed equity ticker, e.g. HPG.','days':'Requested number of candles, not calendar days; default 365. Positive integer. Provider does not enforce the old prose claim of a 365 maximum. Replay accepts only explicitly recorded requests/default-equivalent arguments.','summary':'True returns count/last/high/low summary rather than candle rows. False preserves rows; summary changes output shape.','columns':'Optional array of raw candle keys: t date, o open, h high, l low, c close, v volume. Use ["c","t"], never "close" or ["close"]. Null keeps all fields. Production currently drops unknown keys silently; this C1 contract rejects them before that loss.','interval':'Candle frequency: 1D daily, 1W weekly, 1M monthly. The provider canonicalizes case. day/daily are not accepted.'},
'vn_equity_quote_batch':{'symbols':'Vietnamese equity ticker array. Batch subset is an exact query, not permission to return another recorded symbol set.','summary':'True returns count/symbols summary rather than full quotes.','columns':'Optional array of exact raw quote field names; null keeps all fields. Quote names are source-specific (e.g. close_price), not the short c key of vn_quote_history. Unknown production fields may be omitted; inspect returned keys.'},
'vn_index_ohlcv':{'symbol':'VN index ticker, default VNINDEX. Not a stock ticker.','count':'Requested number of index bars, default 100.','summary':'True returns count/last/high/low summary rather than raw bars.','columns':'Optional array of exact upstream index-bar field names; null keeps all fields. Index bars can use close/time rather than the c/t keys of vn_quote_history. No closed field enum is asserted for this upstream frame.','interval':'Market API bar resolution, default 1D. Intraday examples 1m/15m where supported. Do not infer the quote_history 1D/1W/1M domain applies to this different endpoint.'},
'vn_crypto_ohlcv':{'symbol':'Crypto pair, default BTCUSDT.','count':'Requested number of crypto bars, default 30; this tool has count, not days.','summary':'True returns count/last/high/low summary rather than raw bars.','columns':'Optional array of exact upstream crypto-bar field names; null keeps all. This endpoint does not promise quote_history short-key names.'},
'vn_msn_fx_gold':{'symbols':'Optional array of MSN currency/gold symbols such as USDVND and XAUUSD. Null defaults to those two. This is not a closed two-symbol enum; the provider may support other symbols. Do not replace with a string or invented Yahoo ticker mapping.','days':'Calendar-day lookback for MSN history, default 35. Provider fetch span floors at five days and returns at most 35 series rows; this differs from vn_quote_history candle count.'},
}
# Constraints added only when their source domain is verified. Dynamic source
# columns/metric IDs and upstream FX symbols deliberately remain open.
ENUMS={('vn_quote_history','interval'):['1D','1W','1M','1d','1w','1m'],('signals_technical','interval'):['1D','1W','1M','1d','1w','1m'],('signals_technical','ichimoku_convention'):['offset25','classic26'],('financial_statements','period'):['quarter','year'],('financial_detail','statement'):['KQKD','CDKT','LCTT','TM','BCTT','kqkd','cdkt','lctt','tm','bctt'],('valuation_run','method'):['auto','per','pb','ensemble']}
tools=[]
for name,orig in frozen.items():
 t=copy.deepcopy(live[name]);s=copy.deepcopy(orig)
 for key in list(s):
  if key.startswith('x-'):del s[key]
 for key,prop in s['properties'].items():
  prop['description']=D[name][key]
  if (name,key) in ENUMS:prop['enum']=ENUMS[name,key]
 if name=='vn_quote_history':
  s['properties']['columns']['anyOf'][0]['items']['enum']=['t','o','h','l','c','v']
  s['properties']['days']['minimum']=1
 t['inputSchema']=s
 t['_meta']=t.pop('meta',{})
 if name=='valuation_run':
  t['description']='Observed price/EPS/BVPS and reported PER/PB quotients for a Vietnamese equity. Does not compute fair value, buy bands, target price, DCF, EV or sensitivity. method selects a label; it does not introduce a different valuation calculation. Inspect source, period, unit and adjustment-basis verification flags before comparing multiples. Unknown comparability must remain explicit.'
  t['_meta']['anthropic/searchHint']='observed PER PB price EPS BVPS quotients | boi so quan sat; no DCF or fair-value bands'
 if name=='vn_quote_history':
  t['description']=t['description'].replace('tối đa 365 nến','mặc định 365 nến; provider không enforce trần 365')
 t['_meta']['opentrading/contractProfile']='finance-c1-v4'
 t['_meta']['opentrading/schemaPolicy']='Raw types/defaults/required preserved from frozen source. Additional public domain guards added; no coercion. Frozen replay matching remains exact and separate.'
 tools.append(t)
paths=sorted({x['x-source'] for x in frozen.values()}|{'providers/vnstock.py','providers/vietstock.py','tools/shared.py','hints.py'})
identity={'local_source_head':'ed934aebd0ee6f9271512150a9bb3971089d7460','deployed_commit':'unverified','catalog_source':str(live_path.relative_to(ROOT)),'catalog_source_sha256':sha(live_path),'source_tool_count':len(live),'source_modules':{p:sha(SOURCE/p) for p in paths},'sdk':{'mcp':'1.30.0','pydantic':'2.13.5'},'official_sources':['https://modelcontextprotocol.io/specification/2025-11-25/server/tools','https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v1.30.0/docs/server.md']}
obj={'version':4,'profile':'finance-c1-v4','description':'Shared common authoritative C1 input-contract profile and MCP metadata prototype, not a production deployment or typed financial output migration. All conditions validate requests against this same advertised input schema before exact replay matching. Tool outputSchema remains the actual generic object. Snapshot restrictions are appended independently by the replay server.','source_identity':identity,'tools':tools,'catalog_digest':digest(tools)}
out=ROOT/'experiments/finance-v4-study/tools/tool_contracts_v4.json'
out.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'file':str(out),'tools':len(tools),'catalog_digest':obj['catalog_digest'],'fields':sum(len(t['inputSchema']['properties']) for t in tools)},indent=2))
