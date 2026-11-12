#!/usr/bin/env python3
"""Independent actual four SDKs/gateway/MCP computation plumbing with fixed local upstream.
Never loads a credential or calls a model. Its scripted numeric answer is NOT a benchmark trial.
"""
import argparse,importlib,json,sys
from pathlib import Path
WORK=Path('/home/doanlong/extra/benchmark');STUDY=WORK/'experiments/finance-v44-study'
sys.path[:0]=[str(STUDY/'tools'),str(STUDY/'tools/runners'),str(Path(__file__).parent)]
import provider
from mcp_snapshot_server import load_entries,build_tool_defs
from public_response_contract import append_public_contract,validate_public_response_contract
from ready_check import verify_request_capture,verify_mcp_attempt
from wire_contracts import verify_c2_wire_contracts,verify_c2_public_cues
from experiment_conditions import condition,RUNTIME_ROOT
from derived_verifier import verify_derived
ARMS=['opentrading_baseline','opentrading_finance','opencode','dsh']

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--arms',default=','.join(ARMS));ap.add_argument('--previous-call-id');args=ap.parse_args()
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    task=STUDY/'tasks/smoke/smoke-agg-01';defs=build_tool_defs(load_entries(task/'environment/payloads.json')[0])
    config=json.loads((STUDY/'tools/bench_config.json').read_text());provider.credential=lambda:'offline-independent-no-secret'
    state={'requests':0,'visible_source_envelopes':[],'derived_visible':False,'previous_arm_call_id':args.previous_call_id,'rejection_visible':False};all_requests=[]
    def envelopes(body):
        result=[]
        def unpack(value):
            if isinstance(value,str):
                if value.startswith('Error: '):value=value[len('Error: '):]
                try:unpack(json.JSONDecoder().raw_decode(value.lstrip())[0])
                except ValueError:
                    unescaped=value.replace('\\\"','\"')
                    if unescaped!=value:
                        try:unpack(json.JSONDecoder().raw_decode(unescaped.lstrip())[0])
                        except ValueError:pass
            elif isinstance(value,list):
                for item in value:unpack(item)
            elif isinstance(value,dict):
                if isinstance(value.get('benchmark_evidence'),dict) or 'derived_result' in value or value.get('request_rejected') is True:result.append(value)
                else:
                    for k in ('content','text','structuredContent','output','error','message'):
                        if k in value:unpack(value[k])
        for m in body.get('messages',[]):
            if m.get('role')=='tool':unpack(m.get('content'))
        return result
    def tool_name(body,canonical):return next(t['function']['name'] for t in body['tools'] if t['function']['name'].endswith(canonical))
    class Response:
        status=200
        def __init__(self,body):
            self.headers={'Content-Type':'text/event-stream' if body.get('stream') else 'application/json'}
            known=envelopes(body);sources=[e for e in known if isinstance(e.get('benchmark_evidence'),dict) and e['benchmark_evidence']['tool']=='vn_quote_history']
            unique={e['benchmark_evidence']['call_id']:e for e in sources};sources=list(unique.values());derived=list({json.dumps(e,sort_keys=True):e for e in known if 'derived_result' in e}.values())
            calls=[];answer=None
            if state['requests']==1:
                calls.append({'id':'fixture-negative','type':'function','function':{'name':tool_name(body,'analytics_compute'),'arguments':json.dumps({'operation':'mean','operands':[{'call_id':state['previous_arm_call_id'] or 'not-retrieved-in-this-session','path':'/data/last'}],'input_unit':'nghìn đồng/cổ phiếu','output_unit':'nghìn đồng/cổ phiếu'})}})
            elif not sources:
                state['rejection_visible']=any(e.get('request_rejected') is True for e in known)
                assert state['rejection_visible'],'Negative compute was not visible in continuation'
                for i,symbol in enumerate(['VCB','BID','CTG','TCB','MBB']):
                    calls.append({'id':'fixture-source-'+str(i),'type':'function','function':{'name':tool_name(body,'vn_quote_history'),'arguments':json.dumps({'symbol':symbol})}})
            elif len(sources)!=5:raise AssertionError('SDK did not retain all five retrieved envelopes')
            elif not derived:
                refs=[]
                for e in sources:
                    # Public returned leaves, no task solution or gold imported.
                    def walk(node,path='/data'):
                        if isinstance(node,dict):
                            for key,value in node.items():
                                if key=='last' and isinstance(value,(int,float)):return path+'/last'
                                found=walk(value,path+'/'+key)
                                if found:return found
                        elif isinstance(node,list):
                            for i,value in enumerate(node):
                                found=walk(value,path+'/'+str(i))
                                if found:return found
                        return None
                    path=walk(e['data']);assert path
                    refs.append({'call_id':e['benchmark_evidence']['call_id'],'path':path})
                state['visible_source_envelopes']=sources
                for i,op in enumerate(['sum','mean']):
                    calls.append({'id':'fixture-derived-'+str(i),'type':'function','function':{'name':tool_name(body,'analytics_compute'),'arguments':json.dumps({'operation':op,'operands':refs,'input_unit':'nghìn đồng/cổ phiếu','output_unit':'nghìn đồng/cổ phiếu'})}})
            else:
                assert len(derived)==2 and {e['derived_result']['operation'] for e in derived}=={'sum','mean'}
                state['derived_visible']=True
                value={}
                for e in sources:
                    d=e['data']
                    if isinstance(d,dict) and 'symbol' in d:value[d['symbol']]=d.get('last')
                    elif isinstance(d,dict) and 'banks' in d:
                        for b in d['banks']:value[b['symbol']]=b['last']
                assert len(value)==5
                value['mean']=next(e['derived_result']['value'] for e in derived if e['derived_result']['operation']=='mean')
                answer={'values':value,'unit':'nghìn đồng','period':'phiên 2026-10-30','source':'vn_quote_history','evidence':[e['benchmark_evidence'] for e in sources]}
            message={'role':'assistant','content':None if calls else json.dumps(answer,ensure_ascii=False)}
            if calls:message['tool_calls']=calls
            common={'id':'independent-fixed-wire','object':'chat.completion.chunk','created':0,'model':body['model'],'usage':{'prompt_tokens':100,'completion_tokens':20}}
            if body.get('stream'):
                delta={'role':'assistant','tool_calls':[{'index':i,**c} for i,c in enumerate(calls)]} if calls else message
                first={**common,'choices':[{'index':0,'delta':delta,'finish_reason':None}]};last={**common,'choices':[{'index':0,'delta':{},'finish_reason':'tool_calls' if calls else 'stop'}]}
                self.remaining=('data: '+json.dumps(first)+'\n\ndata: '+json.dumps(last)+'\n\ndata: [DONE]\n\n').encode()
            else:self.remaining=json.dumps({**common,'object':'chat.completion','choices':[{'index':0,'message':message,'finish_reason':'tool_calls' if calls else 'stop'}]}).encode()
        def __enter__(self):return self
        def __exit__(self,*_):return False
        def read1(self,_):value=self.remaining;self.remaining=b'';return value
    def fixed_upstream(request,**_):
        body=json.loads(request.data);all_requests.append(body);state['requests']+=1
        verify_c2_wire_contracts(body,defs);verify_c2_public_cues(body,defs)
        return Response(body)
    provider.urllib.request.urlopen=fixed_upstream;results=[]
    for arm in args.arms.split(','):
        if arm not in ARMS:raise ValueError('Unregistered fixture arm')
        state.update(requests=0,visible_source_envelopes=[],derived_visible=False)
        directory=out/arm;ws=directory/'workspace';ws.mkdir(parents=True)
        cond=condition(arm);module=importlib.import_module('run_'+cond['native_arm'])
        instruction=append_public_contract('Benchmark time context: frozen snapshot 2026-11-01.\n\n'+(task/'instruction.md').read_text())
        opts={**cond,'condition':arm,'effort':'none','opentrading_runtime_root':str(RUNTIME_ROOT),'max_requests':24,'max_output_tokens':2048,'max_total_tokens':48000,'provider_timeout_s':45,'request_interval_s':0,'mcp_ledger':str(directory/'mcp.jsonl')}
        result=module.run(str(ws),instruction,str(task),config['model'],240,str(directory/'native.log'),opts)
        rows=[json.loads(x) for x in Path(result['provider_ledger']).read_text().splitlines()]
        ledger=verify_mcp_attempt(task,{'ledger_path':str(directory/'mcp.jsonl')});proofs=verify_derived(task,ledger)
        for r in rows:
            assert r['status']==200;verify_request_capture(r)
            for stage in ('native','effective'):
                body=json.loads(Path(r[stage+'_request_capture']['path']).read_text());verify_c2_wire_contracts(body,defs);verify_c2_public_cues(body,defs)
        assert result['status']=='ok' and state['derived_visible'] and len(proofs)==2
        assert len(ledger)==8 and ledger[0]['tool']=='analytics_compute' and ledger[0]['status']=='rejected' and ledger[0]['error_code']=='invalid_derivation' and all(r['status']=='ok' for r in ledger[1:])
        assert sum(r.get('tool_call_count',0) for r in rows)==8
        assert {p['value_decimal'] for p in proofs}=={'160.9','32.18'}
        raw=validate_public_response_contract(instruction,result.get('final_text'),[d['name'] for d in defs]);assert raw['valid']
        first_body=json.loads(Path(rows[0]['native_request_capture']['path']).read_text())
        system='\n'.join(m.get('content','') for m in first_body.get('messages',[]) if m.get('role')=='system' and isinstance(m.get('content'),str))
        user=[m.get('content') for m in first_body.get('messages',[]) if m.get('role')=='user']
        results.append({'system_characters':len(system),'system_utf8_bytes':len(system.encode()),'initial_user_messages':user,'arm':arm,'native_status':result['status'],'requests':len(rows),'negative_compute_rejection_visible':state['rejection_visible'],'previous_session_reference_test':state['previous_arm_call_id'] is not None,'generated_calls':8,'raw_source_calls':5,'derived_calls':2,'sum':'160.9','mean':'32.18','derived_result_visible':True,'raw_contract':raw,'independent_decimal_proofs':proofs,'provider_ledger':result['provider_ledger'],'mcp_ledger':str(directory/'mcp.jsonl')})
        state['previous_arm_call_id']=next(r['call_id'] for r in ledger if r['tool']=='vn_quote_history' and r['status']=='ok')
    receipt={'pass':True,'kind':'independent actual SDK+gateway+stdioMCP, fixed offline provider, no model inference','financial_performance_evidence':False,'results':results,'requests':len(all_requests)}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'pass':True,'arms':len(results),'requests':len(all_requests)}))
if __name__=='__main__':main()
