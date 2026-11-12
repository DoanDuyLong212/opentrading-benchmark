"""Offline boundary and replay-parity checks. No providers or model calls."""
import copy, hashlib, importlib.util, json, sys, unittest
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[3]
CAT=ROOT/'experiments/finance-v4-study/tools/tool_contracts_v4.json'
C=json.loads(CAT.read_text()); TOOLS={t['name']:t for t in C['tools']}
OLD=json.loads((ROOT/'tools/snapshot_tool_schemas.json').read_text())
VALIDATORS={k:jsonschema.Draft202012Validator(v['inputSchema']) for k,v in TOOLS.items()}
sys.path.insert(0,str(ROOT/'tools'))
import mcp_snapshot_server as replay

def valid(name,args):return not list(VALIDATORS[name].iter_errors(args))
class ContractChecks(unittest.TestCase):
 def test_catalog_actual_metadata(self):
  live={t['name']:t for t in json.loads((ROOT/C['source_identity']['catalog_source']).read_text())}
  self.assertEqual(set(TOOLS),set(OLD));self.assertEqual(len(TOOLS),17)
  self.assertEqual(C['catalog_digest'],replay.digest(C['tools']))
  for n,t in TOOLS.items():
   self.assertEqual(t['outputSchema'],live[n]['outputSchema'])
   self.assertEqual(t['annotations'],live[n]['annotations'])
   self.assertEqual(t['outputSchema']['type'],'object')
   self.assertFalse(t['outputSchema'].get('properties'))
   for p in t['inputSchema']['properties'].values():self.assertTrue(p['description'])
   if n!='valuation_run':
    for k,v in live[n].get('meta',{}).items():self.assertEqual(t['_meta'][k],v)
 def test_original_types_defaults_required(self):
  for n,t in TOOLS.items():
   s=t['inputSchema'];o=OLD[n]
   self.assertEqual(s.get('required',[]),o.get('required',[]));self.assertIs(s['additionalProperties'],False)
   for k,p in o['properties'].items():
    fresh=s['properties'][k]
    self.assertEqual(fresh.get('type'),p.get('type'))
    self.assertEqual(fresh.get('default','<absent>'),p.get('default','<absent>'))
    if 'anyOf'in p:
     self.assertEqual([b.get('type') for b in fresh['anyOf']],[b.get('type')for b in p['anyOf']])
 def test_history_boundary(self):
  cases=[({'symbol':'HPG'},True),({'symbol':'HPG','interval':'day'},False),({'symbol':'HPG','interval':'1W'},True),({'symbol':'HPG','interval':'1m'},True),({'symbol':'HPG','columns':'close'},False),({'symbol':'HPG','columns':['close']},False),({'symbol':'HPG','columns':['c','t']},True),({'symbol':'HPG','columns':None},True),({'symbol':'HPG','days':0},False),({'symbol':'HPG','days':366},True),({'symbol':'HPG','days':1.5},False),({'symbol':'HPG','days':'1'},False),({'symbol':'HPG','unexpected':1},False)]
  for args,expected in cases:
   with self.subTest(args=args):self.assertEqual(valid('vn_quote_history',args),expected)
 def test_period_typo_not_annual_fallback(self):
  for p in ['quarter','year']:self.assertTrue(valid('financial_statements',{'symbol':'FPT','period':p}))
  for p in ['quarterly','yearly','garbage']:self.assertFalse(valid('financial_statements',{'symbol':'FPT','period':p}))
 def test_endpoint_domains_not_conflated(self):
  self.assertTrue(valid('vn_index_ohlcv',{'interval':'15m','columns':['close','time']}))
  self.assertTrue(valid('vn_crypto_ohlcv',{'count':10,'columns':['close']}))
  self.assertFalse(valid('vn_crypto_ohlcv',{'days':10}))
  self.assertTrue(valid('vn_equity_quote_batch',{'symbols':['HPG'],'columns':['close_price']}))
  self.assertTrue(valid('vn_msn_fx_gold',{'symbols':['USDVND','XAUUSD','EURUSD']}))
  self.assertFalse(valid('vn_msn_fx_gold',{'symbols':'USDVND'}))
 def test_metrics_open_source_identifiers(self):
  for m in [['pe','pb','eps','roe'],['net_profit_margin','arbitrary_dynamic_item_id'],None]:
   self.assertTrue(valid('peer_compare',{'symbol':'VCB','peers':['MBB'],'metrics':m}))
  self.assertFalse(valid('peer_compare',{'symbol':'VCB','peers':['MBB'],'metrics':'pe'}))
 def test_truthful_valuation(self):
  for m in ['auto','per','pb','ensemble']:self.assertTrue(valid('valuation_run',{'symbol':'FPT','method':m}))
  self.assertFalse(valid('valuation_run',{'symbol':'FPT','method':'dcf'}))
  self.assertTrue(valid('valuation_run',{'symbol':'FPT','btype':99}))
  self.assertIn('Does not compute fair value',TOOLS['valuation_run']['description'])
 def test_all_recorded_requests_and_file_bytes(self):
  count=0;requests=0;parity=[]
  for p in sorted((ROOT/'tasks').glob('*/*/environment/payloads.json')):
   entries,_=replay.load_entries(p);count+=1
   for k,item in entries:
    requests+=1;self.assertTrue(valid(item['tool'],item['params']),(str(p),k,item['params']))
    # Schema diagnostics do not change exact replay behavior or response.
    self.assertEqual(replay.select_envelope(entries,item['tool'],item['params']),item['envelope'])
   for old in [p,p.with_name('request_contracts.json'),p.parents[1]/'solution/gold.json']:
    new=ROOT/'experiments/finance-v4-study'/old.relative_to(ROOT)
    if old.exists():
     self.assertTrue(new.exists(),str(new));self.assertEqual(old.read_bytes(),new.read_bytes(),str(old))
     parity.append({'path':str(old.relative_to(ROOT)),'sha256':hashlib.sha256(old.read_bytes()).hexdigest()})
  self.assertEqual(count,277)
  (Path(__file__).parent/'recorded-parity.json').write_text(json.dumps({'tasks':count,'requests':requests,'files':parity},indent=2)+'\n')
 def test_schema_valid_request_still_not_recorded(self):
  entries=[('x',{'tool':'vn_quote_history','params':{'symbol':'HPG'},'envelope':{'data':{'c':10}}})]
  self.assertTrue(valid('vn_quote_history',{'symbol':'HPG','days':1}))
  with self.assertRaisesRegex(ValueError,'not recorded'):replay.select_entry(entries,'vn_quote_history',{'symbol':'HPG','days':1})
 def test_source_identity_not_deployment_claim(self):
  self.assertEqual(C['source_identity']['deployed_commit'],'unverified')
  for rel,sha in C['source_identity']['source_modules'].items():
   self.assertEqual(hashlib.sha256((Path('/home/doanlong/MCP-server/src/opentrading_mcp')/rel).read_bytes()).hexdigest(),sha)
if __name__=='__main__':unittest.main(verbosity=2)
