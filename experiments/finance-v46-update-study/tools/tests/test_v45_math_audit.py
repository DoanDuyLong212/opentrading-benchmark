import copy,json,sys
from pathlib import Path
import pytest
TOOLS=Path(__file__).resolve().parents[1];sys.path.insert(0,str(TOOLS))
from v45_math_audit import verify_native,expression,factor
ROOT=TOOLS.parents[2]
FIXTURE=ROOT/'audits/financial-prompt-v45/native/derived-fixture.json'

def fixture():
    f=json.loads(FIXTURE.read_text());return f,{'fixture-server-call':f['raw_source']}

def test_native_independent_decimal_fixture():
    f,s=fixture();assert verify_native(f,s)['computed']=='12.5'

@pytest.mark.parametrize('field,bad',[('unit','USD'),('entity','OTHER'),('period','Q4/1900'),('scope','separate'),('value',999),('source_response_sha256','bad'),('source_payload_sha256','bad')])
def test_native_root_mutations_rejected(field,bad):
    f,s=fixture();f['result']['derived_result']['inputs'][0][field]=bad
    with pytest.raises(ValueError):verify_native(f,s)

@pytest.mark.parametrize('field,bad',[('unit','USD'),('entity','OTHER'),('period','Q4/1900'),('scope','separate'),('value',999),('name','invented')])
def test_native_expression_binding_mutations_rejected(field,bad):
    f,s=fixture();f['result']['derived_result']['expression_inputs'][0][field]=bad
    with pytest.raises((ValueError,KeyError)):verify_native(f,s)

def test_extra_lineage_rejected():
    f,s=fixture();extra=copy.deepcopy(f['result']['derived_result']['inputs'][0]);extra['path']='/data/rows/0/value';extra['value']=200;f['result']['derived_result']['inputs'].append(extra)
    # This extra root aliases an existing real source; a duplicate named binding is not allowed.
    f['result']['derived_result']['expression_inputs'].append({**extra,'name':'unused'})
    with pytest.raises(ValueError):verify_native(f,s)

def test_expression_binding_named_constant_rejected():
    f,s=fixture();f['result']['derived_result']['expression_inputs'].append({'name':'constant','value':123,'unit':''})
    with pytest.raises(ValueError):verify_native(f,s)

def test_derived_chain_unit_mutation_rejected():
    first,s=fixture();f=copy.deepcopy(first);root=first['result']['derived_result'];binding={'name':'prior','sdk_call_id':'prior-sdk','ref':'r2','value':12.5,'unit':'USD','derived_inputs':copy.deepcopy(root['inputs'])};f['result']['derived_result'].update(expression='prior',expression_inputs=[binding],value=12.5,unit='%')
    with pytest.raises(ValueError,match='unit'):verify_native(f,s,{'prior-sdk':first})

@pytest.mark.parametrize('expr,value',[('sqrt(4)',2),('abs(-4)',4),('sum(1,2,3)',6),('avg(1,3)',2),('2^3',8),('min(1,4)',1),('max(1,4)',4),('ln(1)',0),('log10(100)',2),('exp(0)',1)])
def test_registered_expression_grammar(expr,value):assert expression(expr,{})==value

@pytest.mark.parametrize('expr',['__import__("os")','(1).__class__','[1,2]','37','42','open(1)','round(1)'])
def test_arbitrary_or_unregistered_formula_rejected(expr):
    with pytest.raises((ValueError,KeyError)):expression(expr,{})

def test_unknown_unit_rejected():
    with pytest.raises(ValueError):factor('invented-money-unit')


def compute_fixture(op,values,result,periods=None,entities=None):
    receipt={k:k+'-fixture' for k in ['call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of']};periods=periods or ['Q1/2030']*len(values);entities=entities or ['SYNTH']*len(values)
    rows=[{'symbol':entity,'period':period,'scope':'consolidated','name':'Revenue','value':value,'unit':'VNDbn'} for value,period,entity in zip(values,periods,entities)]
    source={'data':{'rows':rows},'benchmark_evidence':receipt}
    leaves=[{'ref':'r1','sdk_call_id':'sdk-source','call_id':receipt['call_id'],'path':f'/data/rows/{i}/value','value':value,'unit':'VNDbn','entity':entities[i],'period':periods[i],'scope':'consolidated','metric':'Revenue','source_response_sha256':receipt['response_sha256'],'source_payload_sha256':receipt['payload_sha256'],'receipt':receipt} for i,value in enumerate(values)]
    record={'kind':'native_derived','status':'ok','tool':'compute','arguments':{'op':op},'result':{'derived_result':{'expression':op,'value':result,'unit':'%' if op=='share' else 'điểm %' if op=='relative_strength' else 'VNDbn','inputs':leaves,'expression_inputs':leaves}}}
    return record,{receipt['call_id']:source}


def test_relative_strength_independent_decimal():
    r,s=compute_fixture('relative_strength',[100,120,200,220],10,['Q1/2030','Q2/2030']*2,['A','A','B','B']);assert verify_native(r,s)['computed']=='10.0'
    r['result']['derived_result']['value']=11
    with pytest.raises(ValueError,match='arithmetic'):verify_native(r,s)

@pytest.mark.parametrize('op,result',[('rank',[{'label':'B','value':30},{'label':'A','value':10}]),('share',[{'label':'A','value':25},{'label':'B','value':75}])])
def test_vector_ops_labels_order_and_values(op,result):
    r,s=compute_fixture(op,[10,30],result,entities=['A','B']);assert verify_native(r,s)['roots']==2
    r['result']['derived_result']['value'][0]['label']='OTHER'
    with pytest.raises(ValueError,match='Vector'):verify_native(r,s)


def test_output_dimensions_independent_reject_even_with_correct_number():
    f,s=fixture();f['result']['derived_result']['unit']='USD';f['result']['derived_result']['value']=.125
    with pytest.raises(ValueError,match='dimension'):verify_native(f,s)


def test_sdk_scope_period_query_fallback_and_no_statement_cachetime():
    f,s=fixture();source=s['fixture-server-call'];source['data'].pop('period');source['data'].pop('scope');source['_audit_source_request']={'symbol':'SYNTH','year':2030,'quarter':1,'consolidated':True}
    for item in f['result']['derived_result']['inputs']+f['result']['derived_result']['expression_inputs']:item['query_context']=source['_audit_source_request']
    assert verify_native(f,s)['reported']==12.5
    source['_audit_source_request']={}
    for item in f['result']['derived_result']['inputs']+f['result']['derived_result']['expression_inputs']:item['query_context']={}
    with pytest.raises(ValueError,match='scope|period'):verify_native(f,s)

@pytest.mark.parametrize('unit',['tỷ lệ','tỉ lệ','dimensionless','unitless','ratio','fraction','lần'])
def test_actual_native_dimensionless_aliases_independent_scale_and_dimension(unit):
    from v45_math_audit import dimensions
    assert factor(unit)==1
    assert dimensions(unit)=={}

def test_dimensionless_aliases_never_swallow_money_or_percent_scale():
    from v45_math_audit import dimensions
    assert factor('tỷ đồng')==10**9
    assert dimensions('tỷ đồng')=={'VND':1}
    assert factor('%')==factor('phần trăm')==__import__('decimal').Decimal('.01')
    assert dimensions('%')=={}
    with pytest.raises(ValueError):factor('tỷ lệ VND')
