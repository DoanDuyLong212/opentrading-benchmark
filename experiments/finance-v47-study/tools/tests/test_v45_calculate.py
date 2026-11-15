import json,sys,copy,hashlib
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analytics_calculate import calculate
from mcp_snapshot_server import replay_calculate
from test_v44_compute import bank_sources
from ready_check import verify_mcp_attempt

def args(sources,expression='(a+b)/2',unit='nghìn đồng/cổ phiếu'):
 return {'expression':expression,'variables':[{'name':name,'call_id':cid,'path':'/data/last'} for name,cid in zip(['a','b'],sources)],'output_unit':unit,'alignment':'cross_entity_same_period'}

def test_real_native_engine_mean_and_chain_ledger(tmp_path):
 task,ledger,sources=bank_sources(tmp_path);a=args(sources);payload=hashlib.sha256((task/'environment/payloads.json').read_bytes()).hexdigest();derived={}
 env=replay_calculate(a,sources,derived,payload,ledger)
 assert env['derived_result']['value']==44.85 and len(env['source_evidence'])==2 and env['derived_ref'] in derived and 'benchmark_evidence' not in env
 chain={'expression':'avg / quote','variables':[{'name':'avg','derived_id':env['derived_ref']},{'name':'quote','call_id':next(iter(sources)),'path':'/data/last'}],'output_unit':'%','alignment':'cross_entity_same_period'}
 second=replay_calculate(chain,sources,derived,payload,ledger)
 assert second['derived_result']['value']==pytest.approx(79.662522) and second['source_evidence']==env['source_evidence']
 assert len(verify_mcp_attempt(task,{'ledger_path':str(ledger)}))==7
 rows=[json.loads(x) for x in ledger.read_text().splitlines()];rows[-1]['derivation']['value']=123;ledger.write_text('\n'.join(map(json.dumps,rows))+'\n')
 with pytest.raises(ValueError,match='Derived result'):verify_mcp_attempt(task,{'ledger_path':str(ledger)})

@pytest.mark.parametrize('mutation',['literal','period','entity','scope','unknown','typed','reparent'])
def test_reject_broken_proof_and_metadata(tmp_path,mutation):
 _,_,sources=bank_sources(tmp_path);a=args(sources);source=next(iter(sources.values()))
 if mutation=='literal':a['expression']='a+12345'
 elif mutation=='period':source['data']['last_t']='2026-01-01'
 elif mutation=='entity':a['alignment']='same_period'
 elif mutation=='scope':source['data']['scope']='consolidated'
 elif mutation=='unknown':a['variables'][0]['call_id']='made-up'
 elif mutation=='typed':a['variables'][0]={'name':'a','value':21}
 else:a['variables'][0]['path']='/data/'
 with pytest.raises((ValueError,__import__('jsonschema').ValidationError)):calculate(a,sources)

def test_changed_derived_root_rejected(tmp_path):
 _,_,sources=bank_sources(tmp_path);first=calculate(args(sources),sources);derived={'calc:abc':first};next(iter(sources.values()))['data']['last']=100
 with pytest.raises(ValueError,match='source changed'):calculate({'expression':'x*2','variables':[{'name':'x','derived_id':'calc:abc'}]},sources,derived)

def test_dimensional_units_preserved(tmp_path):
 _,_,sources=bank_sources(tmp_path);a=args(sources,expression='a',unit='VND');a['variables']=a['variables'][:1] # exercise dimensions, not unused-variable validation
 with pytest.raises(ValueError,match='lệch đơn vị'):calculate(a,sources)
 a['output_unit']='đồng/cổ phiếu';assert calculate(a,sources)['derived_result']['value']==56300

def test_missing_statement_period_not_replaced_by_capture_time():
 source={'data':{'symbol':'AAA','metric':{'unit':'VND','value':10}},'provenance':{'data_time':'2026-10-30'},'benchmark_evidence':{'call_id':'a','response_sha256':'r','payload_sha256':'p'}}
 a={'expression':'x*2','variables':[{'name':'x','call_id':'a','path':'/data/metric/value'}],'output_unit':'VND'}
 with pytest.raises(ValueError,match='missing financial period'):calculate(a,{'a':source})
 source['_benchmark_request']={'tool':'financial_detail','arguments':{'year':2025,'quarter':4,'consolidated':True}}
 result=calculate(a,{'a':source})['derived_result'];assert result['inputs'][0]['period']=='Q4/2025' and result['inputs'][0]['scope']=='consolidated'
 assert result['inputs'][0]['query_context']==source['_benchmark_request']['arguments']
 assert result['alignment_verification']['period']=='verified'

def test_only_documented_super_route_alias_accepted(tmp_path):
 from test_v45_provider_compute import setup,success
 from runners.provider import DEFAULT_MODEL,normalize_model
 from unittest.mock import patch
 g,h=setup(tmp_path);g.accepted_response_model='private/nvidia/nemotron-3.5-super-120b-a12b';g.admission={'checkpoint_unverified':True,'admission_contract':'user-authorized-requested-route-v2'}
 with patch('urllib.request.urlopen',return_value=success(g.accepted_response_model)):g.handle(h)
 assert h.status==200 and g.rows[0]['checkpoint_unverified'] is True and g.rows[0]['requested_model']==DEFAULT_MODEL
 (tmp_path/'second').mkdir();g,h=setup(tmp_path/'second')
 g.accepted_response_model='private/nvidia/nemotron-3.5-super-120b-a12b'
 with patch('urllib.request.urlopen',return_value=success('other-private-model')):g.handle(h)
 assert h.status==424 and g.rows[0]['error']=='provider_response_model_mismatch'
