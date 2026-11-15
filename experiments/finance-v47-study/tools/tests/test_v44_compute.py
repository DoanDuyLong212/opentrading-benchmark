import json,sys,hashlib
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analytics_compute import compute,traverse
from mcp_snapshot_server import load_entries,replay_call,replay_compute,build_tool_defs
from ready_check import verify_mcp_attempt
ROOT=Path(__file__).resolve().parents[2]

def bank_sources(tmp_path):
 task=ROOT/'tasks/smoke/smoke-agg-01';payload=task/'environment/payloads.json';entries,_=load_entries(payload);ledger=tmp_path/'mcp.jsonl';sources={}
 for _,entry in entries:
  env=replay_call(entries,entry['tool'],entry['params'],hashlib.sha256(payload.read_bytes()).hexdigest(),ledger);sources[env['benchmark_evidence']['call_id']]=env
 return task,ledger,sources

def args(sources,op='sum'):
 return {'operation':op,'operands':[{'call_id':key,'path':'/data/last'} for key in sources],'input_unit':'nghìn đồng/cổ phiếu','output_unit':'nghìn đồng/cổ phiếu'}

def test_bank_sum_mean_and_exact_ledger(tmp_path):
 task,ledger,sources=bank_sources(tmp_path)
 for op,value in [('sum',160.9),('mean',32.18)]:
  env=replay_compute(args(sources,op),sources,hashlib.sha256((task/'environment/payloads.json').read_bytes()).hexdigest(),ledger)
  assert env['derived_result']['value']==value
  assert len(env['source_evidence'])==5 and 'benchmark_evidence' not in env
  assert {x['period'] for x in env['derived_result']['source_scopes']}=={'2026-10-30'}
 assert len(verify_mcp_attempt(task,{'ledger_path':str(ledger)}))==7
 rows=[json.loads(x) for x in ledger.read_text().splitlines()];rows[-1]['derivation']['value']=1;ledger.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
 with pytest.raises(ValueError,match='Derived result'):verify_mcp_attempt(task,{'ledger_path':str(ledger)})

@pytest.mark.parametrize('mutation',['absent','wrong_unit','duplicate','period','metric','volume','nonfinite'])
def test_failclosed_sources(tmp_path,mutation):
 _,_,sources=bank_sources(tmp_path);a=args(sources);env=next(iter(sources.values()))
 if mutation=='absent':sources={}
 elif mutation=='wrong_unit':a['input_unit']='VND'
 elif mutation=='duplicate':a['operands'].append(a['operands'][0])
 elif mutation=='period':env['data']['last_t']='2026-10-29'
 elif mutation=='metric':env['data']['other']=1;env['units']['other']=a['input_unit'];a['operands'][0]['path']='/data/other'
 elif mutation=='volume':env['data']['volume']=1;a['operands'][0]['path']='/data/volume'
 elif mutation=='nonfinite':env['data']['last']=float('inf')
 with pytest.raises(ValueError):compute(a,sources)

@pytest.mark.parametrize('path',['/data/a/-1','/data/a/01','/data/a/+1','/data/a/-','/data/~2bad'])
def test_pointer_rejects_noncanonical(path):
 with pytest.raises((ValueError,KeyError)):traverse({'data':{'a':[1,2]}},path)

def ratio_sources(previous=100):
 sources={}
 for cid,val,period in [('now',125,'Q2/2026'),('prev',previous,'Q1/2026')]:
  sources[cid]={'data':{'symbol':'VCB','metric':{'norm_id':1,'unit':'VND','values':{period:val}}},'benchmark_evidence':{'call_id':cid,'response_sha256':'response','payload_sha256':'payload'}}
 return sources,{'operation':'growth_pct','operands':[{'call_id':'now','path':'/data/metric/values/Q2~12026'},{'call_id':'prev','path':'/data/metric/values/Q1~12026'}],'input_unit':'VND','output_unit':'%'}

def test_growth_bad_denominator():
 sources,a=ratio_sources();assert compute(a,sources)['derived_result']['value']==25
 for previous in [0,-100]:
  sources,a=ratio_sources(previous)
  with pytest.raises(ValueError):compute(a,sources)

def test_float_overflow(tmp_path):
 _,_,sources=bank_sources(tmp_path)
 for env in sources.values():env['data']['last']=1e308
 with pytest.raises(ValueError,match='finite JSON'):compute(args(sources),sources)

def test_catalog_has_no_shared_calculators():
 # User 2026-11-11: data tools only; the analytics calculators are not advertised to any arm.
 entries,_=load_entries(ROOT/'tasks/smoke/smoke-quote-01/environment/payloads.json')
 assert [d['name'] for d in build_tool_defs(entries)]==['vn_quote_history']

def test_actual_vnm_statement_growth_without_norm_id(tmp_path):
 from decimal import Decimal,localcontext
 task=ROOT/'tasks/pilot/fin-l2-growth-01';payload=task/'environment/payloads.json';entries,_=load_entries(payload)
 entry=next(entry for _,entry in entries if entry['tool']=='financial_statements')
 response=replay_call(entries,'financial_statements',entry['params'],hashlib.sha256(payload.read_bytes()).hexdigest())
 row=response['data']['statements']['Kết quả kinh doanh'][0]
 assert 'norm_id' not in row and row['name']=='Doanh thu thuần'
 call=response['benchmark_evidence']['call_id'];base='/data/statements/Kết quả kinh doanh/0/values/'
 a={'operation':'growth_pct','operands':[{'call_id':call,'path':base+'Q3~12026'},{'call_id':call,'path':base+'Q2~12026'}],'input_unit':'VND','output_unit':'%'}
 result=compute(a,{call:response})
 with localcontext() as context:
  context.prec=40
  expected=(Decimal(str(row['values']['Q3/2026']))/Decimal(str(row['values']['Q2/2026']))-1)*100
 assert Decimal(result['derived_result']['value_decimal'])==expected
 assert result['derived_result']['value']==float(expected)
 assert result['derived_result']['source_scopes']==[{'entity':'VNM','period':'Q3/2026','metric':'name:Doanh thu thuần'},{'entity':'VNM','period':'Q2/2026','metric':'name:Doanh thu thuần'}]
 assert result['source_evidence']==[response['benchmark_evidence']]
 # Prefer authoritative norm_id if both explicit identity forms are present.
 row['norm_id']=123
 assert compute(a,{call:response})['derived_result']['source_scopes'][0]['metric']=='norm_id:123'

def actual_response(task_name,tool):
 task=ROOT/'tasks/pilot'/task_name;payload=task/'environment/payloads.json';entries,_=load_entries(payload)
 entry=next(entry for _,entry in entries if entry['tool']==tool)
 return replay_call(entries,tool,entry['params'],hashlib.sha256(payload.read_bytes()).hexdigest())

def test_actual_mwg_aligned_table_margin_and_bad_alignment():
 from decimal import Decimal,localcontext
 env=actual_response('fin-l2-margin-01','financial_detail');call=env['benchmark_evidence']['call_id']
 a={'operation':'margin_pct','operands':[{'call_id':call,'path':'/data/rows/2/values/3'},{'call_id':call,'path':'/data/rows/0/values/3'}],'input_unit':'tỷ đồng','output_unit':'%'}
 result=compute(a,{call:env})['derived_result']
 with localcontext() as context:
  context.prec=40;expected=Decimal(11421)/Decimal(52614)*100
 assert Decimal(result['value_decimal'])==expected and result['value']==float(expected)
 assert {x['entity'] for x in result['source_scopes']}=={'MWG'}
 assert {x['period'] for x in result['source_scopes']}=={'Q3/2026'}
 a['operands'][1]['path']='/data/rows/0/values/2'
 with pytest.raises(ValueError,match='identical explicit recorded period'):compute(a,{call:env})
 a['operands'][1]['path']='/data/rows/0/values/3';env['data']['periods'].pop()
 with pytest.raises(ValueError,match='align exactly'):compute(a,{call:env})

def test_actual_vcb_scale_vnd_to_billion():
 from decimal import Decimal
 env=actual_response('fin-l1-bctc-01','financial_statements');call=env['benchmark_evidence']['call_id']
 a={'operation':'scale','operands':[{'call_id':call,'path':'/data/statements/Kết quả kinh doanh/0/values/Q2~12026'}],'input_unit':'VND','output_unit':'tỷ đồng'}
 result=compute(a,{call:env})
 assert Decimal(result['derived_result']['value_decimal'])==Decimal('14550.959')
 assert result['derived_result']['value']==14550.959
 assert result['source_evidence']==[env['benchmark_evidence']]
