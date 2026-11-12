#!/usr/bin/env python3
"""Actual installed OT/OC/DSH + MCP + gateway; upstream is a fixed local stub.

This never loads a credential and never opens an upstream network connection.
It measures schema plumbing only, not model or financial capability.
"""
import argparse,importlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/runners')]
import provider
from mcp_snapshot_server import load_entries,build_tool_defs
from public_response_contract import append_public_contract
from wire_contracts import verify_c2_wire_contracts,verify_c2_public_cues
from ready_check import verify_request_capture
from experiment_conditions import condition,RUNTIME_ROOT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--scripted-calls',action='store_true');ap.add_argument('--catalog',choices=['full17','smoke_quote','max_study'],default='full17');ap.add_argument('--arms',default='opentrading_baseline,opentrading_finance,opencode,dsh');ap.add_argument('--model',choices=['bolt','deepseek'],default='bolt');args=ap.parse_args()
    config=json.loads((ROOT/'tools'/('bench_config.json' if args.model=='bolt' else 'bench_config_deepseek.json')).read_text())
    if args.scripted_calls and args.catalog!='smoke_quote':ap.error('scripted calls require smoke_quote public fixture')
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    entries={}
    for path in (ROOT/'tasks').glob('*/*/environment/payloads.json'):
        for key,entry in load_entries(path)[0]:entries.setdefault(entry['tool'],(key,entry))
    task=out/'public-mcp-fixture';(task/'environment').mkdir(parents=True,exist_ok=True)
    (task/'environment/payloads.json').write_text(json.dumps({'snapshot_date':'2026-11-01','tools':{name:entry for name,(_key,entry) in entries.items()}},ensure_ascii=False))
    if args.catalog=='smoke_quote':
        task=ROOT/'tasks/smoke/smoke-quote-01'
    candidates=[]
    if args.catalog=='max_study':
        from run_manifest import task_eligibility
        for split in ('smoke','pilot'):
            for candidate in (ROOT/'tasks'/split).iterdir():
                if not candidate.is_dir() or not task_eligibility(candidate)['confirmatory_eligible']:continue
                defs=build_tool_defs(load_entries(candidate/'environment/payloads.json')[0])
                cost=len(json.dumps(defs,ensure_ascii=False).encode())+len((candidate/'instruction.md').read_bytes())
                candidates.append((cost,candidate))
        task=max(candidates,key=lambda x:x[0])[1]
    definitions=build_tool_defs(load_entries(task/'environment/payloads.json')[0])
    if args.catalog=='full17':assert len(definitions)==18  # 17 frozen source tools + one common deterministic compute
    provider.credential=lambda:'offline-fixture-placeholder'
    stub_calls=[]
    arm_state={'calls':0}
    class Response:
        status=200
        def __init__(self,body):
            self.headers={'Content-Type':'text/event-stream' if body.get('stream') else 'application/json'}
            content=json.dumps({'value':None,'reason':'Offline scripted schema capture; no financial assertion.','evidence':[]})
            common={'id':'offline-fixed-response','object':'chat.completion.chunk','created':0,'model':body['model'],'usage':{'prompt_tokens':100,'completion_tokens':20}}
            call=None
            if args.scripted_calls and arm_state['calls']<=2:
                tool=next(t['function']['name'] for t in body['tools'] if t['function']['name'].endswith('vn_quote_history'))
                parameters={'symbol':'HPG','days':1} if arm_state['calls']==1 else {'symbol':'HPG'}
                call={'id':'offline-unsupported' if arm_state['calls']==1 else 'offline-supported','type':'function','function':{'name':tool,'arguments':json.dumps(parameters)}}
            message={'role':'assistant','content':None if call else content}
            if call:message['tool_calls']=[call]
            if body.get('stream'):
                delta={'role':'assistant','tool_calls':[{'index':0,**call}]} if call else message
                first={**common,'choices':[{'index':0,'delta':delta,'finish_reason':None}]}
                last={**common,'choices':[{'index':0,'delta':{},'finish_reason':'tool_calls' if call else 'stop'}]}
                self.remaining=('data: '+json.dumps(first)+'\n\ndata: '+json.dumps(last)+'\n\ndata: [DONE]\n\n').encode()
            else:self.remaining=json.dumps({**common,'object':'chat.completion','choices':[{'index':0,'message':message,'finish_reason':'tool_calls' if call else 'stop'}]}).encode()
        def __enter__(self):return self
        def __exit__(self,*_):return False
        def read1(self,_):value=self.remaining;self.remaining=b'';return value
    def stub_urlopen(request,**_):
        body=json.loads(request.data);stub_calls.append(body);arm_state['calls']+=1
        verify_c2_wire_contracts(body,definitions)
        verify_c2_public_cues(body,definitions)
        return Response(body)
    provider.urllib.request.urlopen=stub_urlopen
    results=[]
    for arm in args.arms.split(','):
        arm_state['calls']=0
        directory=out/arm;ws=directory/'workspace';ws.mkdir(parents=True,exist_ok=True)
        selected=condition(arm)
        module=importlib.import_module('run_'+selected['native_arm'])
        instruction=append_public_contract((('Benchmark time context: answer relative to the frozen data snapshot as of 2026-11-01. Execution wall-clock does not advance the financial reporting period. Use response provenance.as_of for evidence.\n\n'+(task/'instruction.md').read_text()) if (task/'instruction.md').exists() else 'Offline schema plumbing probe. Do not call tools or assert financial facts. Return exactly {"value":null,"reason":"Offline scripted schema capture; no financial assertion.","evidence":[]}.'))
        options={**selected,'condition':arm,'effort':'none','opentrading_runtime_root':str(RUNTIME_ROOT),'max_requests':24,'max_output_tokens':2048,'max_total_tokens':48000,'provider_timeout_s':config['provider_timeout_s'],'request_interval_s':0,'mcp_ledger':str(directory/'mcp.jsonl')}
        result=module.run(str(ws),instruction,str(task),config['model'],config['trial_timeout_s'],str(directory/'native.log'),options)
        rows=[json.loads(line) for line in Path(result['provider_ledger']).read_text().splitlines()]
        if len(rows)>24:raise AssertionError('Shared request cap exceeded')
        if sum(r.get('usage',{}).get('prompt_tokens',0)+r.get('usage',{}).get('completion_tokens',0) for r in rows)>48000:raise AssertionError('Shared recorded token cap exceeded')
        for row in rows:
            if row.get('status')==200 and (row.get('effective_max_tokens',0)>2048 or row.get('effective_temperature')!=0 or row.get('effective_top_p')!=1):
                raise AssertionError('Shared output/sampling cap changed')
        budget_blocked=bool(rows) and all(row.get('error')=='token budget exhausted before request' and not row.get('upstream_attempted') for row in rows)
        if not rows or (any(row.get('status')!=200 for row in rows) and not (args.catalog=='full17' and budget_blocked)):
            raise AssertionError({'arm':arm,'result':result,'errors':[r.get('error') for r in rows]})
        for row in rows:
            if row.get('status')==200:verify_request_capture(row)
            native=json.loads(Path(row['native_request_capture']['path']).read_text())
            verify_c2_wire_contracts(native,definitions)
            verify_c2_public_cues(native,definitions)
            assert len(native['tools'])==len(definitions)
        call_path=None
        if args.scripted_calls:
            from run_benchmark import load_ledger
            ledger=directory/'mcp.jsonl';calls=load_ledger(str(ledger)) if ledger.exists() else []
            generated=sum(row.get('tool_call_count',0) for row in rows)
            errors_seen=[]
            for row in rows:
                capture=json.loads(Path(row['native_request_capture']['path']).read_text())
                errors_seen.extend(m for m in capture.get('messages',[]) if m.get('role')=='tool' and m.get('tool_call_id')=='offline-unsupported')
            if not errors_seen:raise AssertionError('Unsupported query error did not reach next actual model context: '+arm)
            if not any(c.get('status')=='ok' and c.get('arguments')=={'symbol':'HPG'} for c in calls):raise AssertionError('Supported continuation did not execute: '+arm)
            call_path={'generated_calls':generated,'mcp_executions':len(calls),'mcp_statuses':[c.get('status') for c in calls],'mcp_error_codes':[c.get('error_code') for c in calls if c.get('status')=='rejected'],'unsupported_error_visible':True,'unexecuted_generated_count':generated-len(calls),'context':'normal native SDK continuation, NOT proof of same-intent bounded finance correction or financial primary'}
        results.append({'arm':arm,'scripted_call_path':call_path,'status':result['status'],'budget_blocked_before_upstream':budget_blocked,'requests':len(rows),'caps_checked':True,'initial_input_estimate_bytes':rows[0].get('input_budget_estimate_bytes'),'inventory':result['inventory_path'],'ledger':result['provider_ledger']})
    receipt={'kind':'actual installed native SDK + actual MCP + actual gateway; upstream fixed in-process stub; no credential/no model inference','model':config['model'],'registered_caps':{'trial_timeout_s':config['trial_timeout_s'],'provider_timeout_s':config['provider_timeout_s'],'max_requests':24,'max_output_tokens':2048,'max_total_tokens':48000,'effort':'none'},'tools':len(definitions),'scripted_calls':args.scripted_calls,'catalog':args.catalog,'task':task.name,'eligible_catalog_costs':[{'task':p.name,'schema_plus_instruction_bytes':cost} for cost,p in sorted(candidates,key=lambda x:x[0],reverse=True)],'limit_note':'Full17wire capture can preserve constraints while budget policy blocks request before stub; this is not operational fullcatalog certification. Financial study uses per-task catalog.','stub_calls':len(stub_calls),'results':results}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
