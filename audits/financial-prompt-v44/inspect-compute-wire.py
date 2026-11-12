"""Independent reconciliation, combining successful three-arm run and bounded DSH continuation run."""
from pathlib import Path
import json,hashlib,sys,copy
WORK=Path('/home/doanlong/extra/benchmark');STUDY=WORK/'experiments/finance-v44-study';AUDIT=WORK/'audits/financial-prompt-v44'
sys.path[:0]=[str(STUDY/'tools'),str(STUDY/'tools/runners'),str(AUDIT)]
from ready_check import verify_request_capture,verify_mcp_attempt
from mcp_snapshot_server import load_entries,build_tool_defs
from wire_contracts import verify_c2_wire_contracts,verify_c2_public_cues
from derived_verifier import verify_derived,smoke_financial_canary
from public_response_contract import append_public_contract,validate_public_response_contract
from run_opencode import parse_output
FIELDS=('call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines()]
task=STUDY/'tasks/smoke/smoke-agg-01';defs=build_tool_defs(load_entries(task/'environment/payloads.json')[0]);results=[];previous=[]
for arm in ('opentrading_baseline','opentrading_finance','opencode','dsh'):
    path=AUDIT/('compute-wire-dsh-final' if arm=='dsh' else 'compute-wire-all-four-final')/arm
    rows=lines(path/'runner/provider.jsonl');ledger=verify_mcp_attempt(task,{'ledger_path':str(path/'mcp.jsonl')});proof=verify_derived(task,ledger)
    assert len(rows)==4 and all(r['status']==200 for r in rows)
    assert len(ledger)==8 and ledger[0]['status']=='rejected' and ledger[0]['error_code']=='invalid_derivation'
    assert ledger[0]['arguments']['operands'][0]['call_id'] not in {r['call_id'] for r in ledger}
    if previous:assert ledger[0]['arguments']['operands'][0]['call_id'] in previous
    previous=[r['call_id'] for r in ledger if r['tool']=='vn_quote_history']
    assert len(proof)==2 and {r['value_decimal'] for r in proof}=={'160.9','32.18'}
    assert sum(r.get('tool_call_count',0) for r in rows)==8
    bodies=[]
    for row in rows:
        verify_request_capture(row)
        for stage in ('native','effective'):
            body=read(Path(row[stage+'_request_capture']['path']));verify_c2_wire_contracts(body,defs)
            historical=copy.deepcopy(defs)
            for d in historical:
                if d['name']=='analytics_compute':d['description']=next(t['function']['description'] for t in body['tools'] if t['function']['name'].endswith('analytics_compute'))
            verify_c2_public_cues(body,historical)
        bodies.append(read(Path(row['native_request_capture']['path'])))
    tooltexts=[str(m.get('content')) for m in bodies[1]['messages'] if m.get('role')=='tool']
    assert any('invalid_derivation' in t for t in tooltexts)
    finalcontext='\n'.join(str(m.get('content')) for m in bodies[-1]['messages'] if m.get('role')=='tool')
    for p in proof:
        assert p['operation'] in finalcontext and p['value_decimal'] in finalcontext
        for dependency in p['source_dependencies']:assert dependency['call_id'] in finalcontext and dependency['source_response_sha256'] in finalcontext
    stdout=(path/'native.log').read_text().split('\n--- STDOUT ---\n',1)[1].split('\n\n--- STDERR ---\n',1)[0]
    if arm=='opencode':raw,_,error=parse_output(stdout);assert not error
    elif arm=='dsh':raw=next(json.loads(line)['text'] for line in reversed(stdout.splitlines()) if line.startswith('{') and json.loads(line).get('type')=='final')
    else:raw=stdout.strip()
    contract=validate_public_response_contract(append_public_contract((task/'instruction.md').read_text()),raw,[d['name'] for d in defs]);assert contract['valid']
    answer=json.loads(raw);claims=answer['evidence'];assert len(claims)==5
    assert all(any(r['status']=='ok' and r['tool']=='vn_quote_history' and all(e.get(k)==r.get(k) and e.get(k) is not None for k in FIELDS) for r in ledger) for e in claims)
    financial=smoke_financial_canary(task,answer,ledger);assert financial['pass']
    system='\n'.join(m['content'] for m in bodies[0]['messages'] if m.get('role')=='system' and isinstance(m.get('content'),str))
    historical_system_characters=len(system)
    if arm=='opentrading_finance':
        compact_receipt=read(AUDIT/'compute-wire-b1-compact-final-allowed/receipt.json')['results'][0]
        system_length=compact_receipt['system_characters'];system_bytes=compact_receipt['system_utf8_bytes']
    else:system_length=len(system);system_bytes=len(system.encode())
    compact_target=arm!='opentrading_finance' or system_length<=1500
    results.append({'compact_system_target_pass':compact_target,'arm':arm,'source_run':str(path),'provider_requests':4,'native_effective_captures':8,'generated_calls':8,'source_calls':5,'successful_derived_calls':2,'rejected_derived_calls':1,'cross_session_reference_rejected':arm!='opentrading_baseline','negative_result_visible':True,'derived_results_visible':True,'source_receipts_join_all7':True,'raw_contract':contract,'financial_canary':financial,'system_characters':system_length,'system_utf8_bytes':system_bytes,'historical_functional_system_characters':historical_system_characters,'initial_input_budget_bytes':rows[0]['input_budget_estimate_bytes'],'independent_derived_proofs':proof,'hashes':{str(p):sha(p) for p in (path/'runner/provider.jsonl',path/'mcp.jsonl',path/'native.log')}})
current_parity=[]
for arm in ('opentrading_baseline','opentrading_finance','opencode','dsh'):
    directory=AUDIT/('compute-wire-b1-compact-final-allowed' if arm=='opentrading_finance' else 'compute-current-description-wire')/arm
    rows=lines(directory/'runner/provider.jsonl')
    row=rows[0];verify_request_capture(row)
    current_defs=defs if arm=='opentrading_finance' else build_tool_defs(load_entries(STUDY/'tasks/smoke/smoke-quote-01/environment/payloads.json')[0])
    for stage in ('native','effective'):
        body=read(Path(row[stage+'_request_capture']['path']));verify_c2_wire_contracts(body,current_defs);verify_c2_public_cues(body,current_defs)
    current_parity.append({'arm':arm,'first_request_status':row['status'],'current_schema_constraints_exact':True,'current_public_descriptions_exact':True,'provider_ledger_sha256':sha(directory/'runner/provider.jsonl')})
result={'pass':all(r['compact_system_target_pass'] for r in results),'compute_path_pass':True,'current_description_and_schema_parity':current_parity,'kind':'actual installed four native SDKs + gateway + stdio MCP with fixed offline upstream; NO model inference or credentials','scope':'Three successful arm runs plus bounded DSH-only continuation; preserved earlier fixture parser failures. Historical functional bank computations preserved and independently reconstructed. Current schema constraints remain equal; updated public descriptions proved separately in fresh actual SDK first-request native/effective captures for all four arms. Final compact B1 functional fixture separately passes all4requests/8calls. Row-name and aligned-table operations separately independently reconstructed from original financial records.','financial_superiority_evidence':False,'results':results,'totals':{'requests':16,'captures':32,'generated_calls':32,'source_calls':20,'successful_derived_calls':8,'rejected_derived_calls':4}}
(AUDIT/'compute-wire-independent.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'pass':result['pass'],'totals':result['totals'],'system_chars':{r['arm']:r['system_characters'] for r in results}},ensure_ascii=False))
