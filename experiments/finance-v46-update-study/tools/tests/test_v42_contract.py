"""C2 is finite-request compliance, never financial-answer rescue."""
import copy,json,runpy,sys
from pathlib import Path
import jsonschema,pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from mcp_snapshot_server import load_entries,build_tool_defs,select_entry,replay_call,_entry_matches,SCHEMAS,finite_input_schema
V42=runpy.run_path(str(ROOT/'tasks/smoke/smoke-trap-01/tests/grader.py'))

def test_all_416_recorded_requests_and_default_case_equivalence_stay_supported():
    count=0
    for path in (ROOT/'tasks').glob('*/*/environment/payloads.json'):
        entries,_=load_entries(path)
        definitions={item['name']:item for item in build_tool_defs(entries)}
        for _,entry in entries:
            count+=1;name=entry['tool'];base=entry.get('params') or {}
            variants=[base,dict(base)]
            withdefaults=dict(base)
            for key,prop in SCHEMAS[name]['properties'].items():
                if key not in withdefaults and 'default' in prop:withdefaults[key]=prop['default']
            variants.append(withdefaults)
            # C1 remains authoritative too: some production enums are case-sensitive.
            case={k:' '+v.lower()+' ' if isinstance(v,str) and k not in {'interval','period','method'} else v for k,v in base.items()}
            if jsonschema.Draft7Validator(SCHEMAS[name]).is_valid(case):variants.append(case)
            for args in variants:
                jsonschema.Draft7Validator(definitions[name]['inputSchema']).validate(args)
                assert _entry_matches(entry,args)
                assert select_entry(entries,name,args)[1]['envelope']==entry['envelope']
    # Batch-3 memory corpus (user-authorized 2026-11-10): +34 recorded request entries (18 main + 10 holdout fin-mem, multiturn).
    # Main amendment 2026-11-10: +69 entries from the 50 migrated financial holdout tasks.
    # Amendment 2026-11-11 (d): retired 114 tasks, added 88 compute/memory tasks -> 511 recorded request entries.
    # Addendum (f): hard C3/C4 templates read more entities per task -> 534 recorded request entries.
    assert count==534

def test_joint_finite_constraints_reject_projection_window_without_arg_mutation(tmp_path):
    entries,_=load_entries(ROOT/'tasks/smoke/smoke-quote-01/environment/payloads.json')
    args={'symbol':'HPG','days':1,'columns':['t','c'],'interval':'1D'};before=copy.deepcopy(args)
    schema=finite_input_schema(entries,'vn_quote_history')
    assert jsonschema.Draft7Validator(SCHEMAS['vn_quote_history']).is_valid(args)
    assert not jsonschema.Draft7Validator(schema).is_valid(args)
    env=replay_call(entries,'vn_quote_history',args,'fixture',str(tmp_path/'ledger'))
    assert args==before
    assert env['error']['code']=='unsupported_snapshot_query'
    assert env['error']['failure_class']=='finite_snapshot_support'
    assert env['error']['retryable_with_corrected_arguments'] is True
    assert '/columns' in env['error']['argument_paths']
    assert env['error']['allowed_public_variants']==[{'symbol':'HPG'}]
    assert not ({'data','benchmark_evidence','availability'} & env.keys())

@pytest.mark.parametrize('reason',[
 'Mã tài sản XYZX không được giải mã thành symbol hợp lệ trong snapshot.',
 'Không thể phân giải symbol hợp lệ cho mã XYZX.',
 'Chưa nhận diện được symbol XYZX.',
 'Không xác định mã hợp lệ.',
 'No valid ticker was returned for XYZX.',
 'Ticker could not be resolved.',
 'Unable to resolve the symbol XYZX.',
])
def test_semantic_resolver_paraphrases_require_actual_empty_snapshot(reason):
    legacy=['không tồn tại','không có','không tìm thấy','không hợp lệ','mã không']
    assert V42['refusal_hit'](reason,legacy,True)[0]
    if 'không tìm thấy' not in reason.lower():
        # Predicate expansions are resolver-specific, not generic API outage claims.
        assert not V42['refusal_hit'](reason,[],False)[0]

@pytest.mark.parametrize('reason',[
 'Không phải là không được giải mã thành symbol hợp lệ.',
 'Không được giải mã thành symbol hợp lệ, nhưng symbol VCB hợp lệ.',
 'Không tìm thấy vì request bị từ chối.',
 'Không có dữ liệu vì not_recorded.',
 'Không tìm thấy, nhưng đã tìm thấy mã VCB.',
 'Symbol VCB hợp lệ.',
 'Tool error: không tìm thấy.',
 'Không được giải mã thành symbol hợp lệ. Tuy nhiên đã phân giải được XYZX thành VCB.',
 'No valid symbol. However XYZX successfully resolves to VCB.',
 'Không được giải mã thành symbol hợp lệ do lỗi tham số không hợp lệ.',
])
def test_semantic_resolver_contradictions_and_query_errors_fail(reason):
    assert not V42['refusal_hit'](reason,['không tồn tại','không có','không tìm thấy','không hợp lệ','mã không'],True)[0]

def test_public_contract_is_uniform_gold_free_and_allows_honest_aggregation_refusal():
    from public_response_contract import PUBLIC_RESPONSE_CONTRACT,append_public_contract
    schema=PUBLIC_RESPONSE_CONTRACT['refusalSchema']
    jsonschema.validate({'value':None,'reason':'Request rejected; no numerical claim','evidence':[]},schema)
    for bad in [{'value':'null','reason':'x','evidence':[]},{'value':None,'evidence':[]},{'value':None,'reason':'x','evidence':{}}]:
        assert not jsonschema.Draft7Validator(schema).is_valid(bad)
    text=append_public_contract('Public task example')
    assert text.startswith('Public task example') and 'PUBLIC_RESPONSE_CONTRACT_V42=' in text
    assert 'gold' not in text and 'task_id' not in text

def test_frozen_v41_is_byte_identical_and_newgrading_is_separate(tmp_path):
    from run_benchmark import grade_answer
    src=ROOT.parent/'finance-v4-current-study/tasks/smoke/smoke-trap-01/tests/grader.py'
    assert (ROOT/'tools/frozen_v41_grader.py').read_bytes()==src.read_bytes()
    task=ROOT/'tasks/smoke/smoke-trap-01'
    gold=json.loads((task/'solution/gold.json').read_text())
    row=gold['provenance_contract'][0]
    answer={'value':None,'reason':'Không được giải mã thành symbol hợp lệ.','source':'symbol_resolve','evidence':[{**row,'call_id':'actual-session-id','payload_sha256':gold['payload_sha256']}]}
    path=tmp_path/'answer.json';path.write_text(json.dumps(answer))
    assert grade_answer(str(path),str(task),str(tmp_path))['success']
    assert not grade_answer(str(path),str(task),str(tmp_path),frozen_v41=True)['success']
    assert (tmp_path/'grade-frozen-v41.json').exists()

def test_wire_contracts_fail_on_missing_joint_constraint_and_preserve_argument_names():
    from wire_contracts import verify_c2_wire_contracts,schema_constraints
    entries,_=load_entries(ROOT/'tasks/smoke/smoke-quote-01/environment/payloads.json')
    definitions=build_tool_defs(entries)
    body={'tools':[{'function':{'name':'opentrading_'+d['name'],'parameters':copy.deepcopy(d['inputSchema'])}} for d in definitions]}
    verify_c2_wire_contracts(body,definitions)
    body['tools'][0]['function']['parameters'].pop('anyOf')
    with pytest.raises(ValueError,match='constraints changed'):verify_c2_wire_contracts(body,definitions)
    schema={'type':'object','properties':{'description':{'const':{'default':3}},'x-custom':{'type':'integer'}},'description':'annotation'}
    assert schema_constraints(schema)=={'type':'object','properties':{'description':{'const':{'default':3}},'x-custom':{'type':'integer'}}}

def test_actual_sdk_duplicate_fixture_joins_original_intent_and_rejects_tampering():
    from intent_audit import verify_v42_local_intent
    artifact=ROOT/'tools/tests/fixtures/v42-actual-mcp-five-intents.json'
    assert __import__('hashlib').sha256(artifact.read_bytes()).hexdigest()=='a0b3de16e870429313c984bc0a323a2101b7414e85bffbf60bbffd077039a90d' # immutable historical SDK fixture; not a current-v45 wire claim
    receipt=json.loads(artifact.read_text())
    assert 'no inference' in receipt['kind'] and 'controlled C1' in receipt['kind']
    events=receipt['events'];event=next(e for e in events if e.get('localRejection'))
    schemas={event['localRejection']['tool']:receipt['publicStudySchema']}
    verify_v42_local_intent(event,events,[],schemas)
    tampered=copy.deepcopy(events);target=next(e for e in tampered if e.get('localRejection'))
    target['financeIntent']['original_sdk_call_id']='not-an-actual-sdk-id'
    with pytest.raises(ValueError,match='original SDK call absent'):
        verify_v42_local_intent(target,tampered,[],schemas)
    target['financeIntent']=copy.deepcopy(event['financeIntent']);target['localRejection']['rawInput']='{"symbol":"BID","days":1}'
    with pytest.raises(ValueError,match='arguments differ'):
        verify_v42_local_intent(target,tampered,[],schemas)

def test_refusal_mixed_values_counts_fp_and_nonempty_resolver_reference_cannot_pass(tmp_path):
    import shutil
    from run_benchmark import grade_answer
    original=ROOT/'tasks/smoke/smoke-trap-01';task=tmp_path/'task';shutil.copytree(original,task)
    gold=json.loads((task/'solution/gold.json').read_text())
    answer={'value':None,'reason':'Không tìm thấy mã hợp lệ.','source':'symbol_resolve','evidence':[{**gold['provenance_contract'][0],'call_id':'session-id','payload_sha256':gold['payload_sha256']}]}
    path=tmp_path/'answer.json';answer['values']={'VCB':123};path.write_text(json.dumps(answer))
    grade=grade_answer(str(path),str(task),str(tmp_path/'mixed'))
    assert not grade['success'] and grade['fp']==1
    answer.pop('values');path.write_text(json.dumps(answer))
    payload=json.loads((task/'environment/payloads.json').read_text());payload['tools']['symbol_resolve']['availability']='available';payload['tools']['symbol_resolve']['data']['resolved']={'symbol':'VCB'}
    (task/'environment/payloads.json').write_text(json.dumps(payload))
    grade=grade_answer(str(path),str(task),str(tmp_path/'nonempty'))
    assert not grade['success']
    assert any(c['check']=='refusal_reference_empty' and not c['pass'] for c in grade['raw']['checks'])

def test_intent_duplicate_after_lossless_type_correction_is_proven_from_actual_start(tmp_path):
    from intent_audit import verify_v42_local_intent
    name='opentrading_financial_statements';schema={'type':'object','properties':{'symbol':{'type':'string'},'year':{'type':'integer'}}}
    intent={'intent_id':'finance-intent-1','original_sdk_call_id':'original','correction_budget':1}
    events=[{'type':'tool-start','callId':'original','name':name,'input':{'symbol':'VCB','year':'2025'}},
            {'type':'tool-end','callId':'original','ok':False,'financeIntent':{**intent,'sdk_call_id':'original','phase':'initial','correction_used':0}},
            {'type':'tool-start','callId':'corrected','name':name,'input':{'symbol':'VCB','year':2025}},
            {'type':'tool-end','callId':'corrected','ok':True,'financeIntent':{**intent,'sdk_call_id':'corrected','phase':'correction','correction_used':1}}]
    reason='Repeated or already pending/successful intent; do not replay this request.'
    event={'type':'tool-end','callId':'duplicate','ok':False,'financeIntent':{**intent,'sdk_call_id':'duplicate','phase':'initial','correction_used':1,'reason':reason},'localRejection':{'code':'policy_guard_rejected','tool':name,'rawInput':'{"symbol":"VCB","year":2025}','reason':reason}}
    events.append(event)
    verify_v42_local_intent(event,events,[],{name:schema})
    event['localRejection']['rawInput']='{"symbol":"VCB","year":2024}'
    with pytest.raises(ValueError,match='arguments differ'):verify_v42_local_intent(event,events,[],{name:schema})
