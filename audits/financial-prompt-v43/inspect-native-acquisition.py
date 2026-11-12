"""Independent read-only reconciliation of actual SDK development receipt; no inference."""
import collections,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCE=ROOT/'experiments/finance-v43-study/experiments/opentrading-runtime/test-artifacts/v43-independent-acquisition.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
x=json.loads(SOURCE.read_text());cases=[];errors=[]
for capture in x['captures']:
    enabled,mode=capture['enabled'],capture['mode'];events=capture['events'];bodies=capture['bodies'];ledger=capture['ledger']
    starts={e['callId']:e for e in events if e.get('type')=='tool-start'}
    ends={e['callId']:e for e in events if e.get('type')=='tool-end'}
    local=[e for e in ends.values() if e.get('localRejection')]
    executed=[e for e in ends.values() if not e.get('localRejection')]
    if len(starts)!=len(ends) or len(executed)!=len(ledger):errors.append([enabled,mode,'SDK starts/ends/actual MCP count mismatch'])
    unmatched=list(ledger)
    for end in executed:
        start=starts.get(end['callId'],{});matches=[r for r in unmatched if start.get('name','').endswith('__'+r['tool']) and start.get('input')==r['args'] and end.get('ok') is not r['isError']]
        if len(matches)!=1:errors.append([enabled,mode,'call arguments/status do not uniquely join actual MCP',end['callId']]);continue
        r=matches[0];unmatched.remove(r)
        if end.get('ok') and json.loads(end['output'])!=r['result']:errors.append([enabled,mode,'model-visible output differs from actual MCP'])
        if not r['isError']:
            receipt=r['result']['receipt']
            if receipt['request_hash']!=digest(r['args']) or receipt['response_hash']!=digest(r['result']['data']):errors.append([enabled,mode,'actual receipt hash mismatch'])
    phases=[e for e in events if e.get('type')=='finance-phase']
    enter=[e for e in phases if e.get('transition')=='enter' and e.get('phase')=='bounded_finance_acquisition']
    if not enabled and phases:errors.append([enabled,mode,'policy-off phase activation'])
    if len(enter)>1:errors.append([enabled,mode,'repeated acquisition'])
    for p in enter:
        names=set(p['availableToolNames'])
        if not names or any(name.endswith('__place_order') for name in names):errors.append([enabled,mode,'acquisition exposes side effect'])
        # At least one actual request must retain exactly the declared read-only set and auto choice.
        cancelled_before_request=any(e.get('transition')=='exit' and e.get('reason')=='cancelled' for e in phases) and len(bodies)==1
        if not cancelled_before_request and not any({t['function']['name'] for t in body.get('tools',[])}==names and body.get('tool_choice')=='auto' for body in bodies[1:]):errors.append([enabled,mode,'entered acquisition has no effective wire with tools/auto'])
    if enabled and mode=='six_sequential' and len(ledger)!=6:errors.append([enabled,mode,'six-intent acquisition lost executions'])
    if enabled and mode=='duplicate' and (len(ledger)!=1 or len(local)!=1):errors.append([enabled,mode,'duplicate not bounded'])
    if mode in ('cancel','shared_cap') and ledger:errors.append([enabled,mode,'cancel/cap produced MCP execution'])
    if enabled and mode=='cancel' and len(bodies)!=1:errors.append([enabled,mode,'cancel at phase entry scheduled another provider request'])
    if any(p['stepsUsed']>p['maxSteps'] for p in phases):errors.append([enabled,mode,'shared steps exceeded'])
    cases.append({'enabled':enabled,'mode':mode,'requests':len(bodies),'actual_mcp_executions':len(ledger),'successful_mcp':sum(not r['isError'] for r in ledger),'local_rejections':len(local),'phases':phases,'wire_tools_choices':[{'tools':[t['function']['name'] for t in b.get('tools',[])],'choice':b.get('tool_choice')} for b in bodies]})
result={'pass':not errors,'source':str(SOURCE),'source_sha256':sha(SOURCE),'cases':cases,'errors':errors,'scope':'Actual independent-development native SDK request/MCP reconciliation; benchmark gateway/all-four-adapter wire proof is separate.'}
pathlib.Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'pass':not errors,'cases':len(cases),'requests':sum(c['requests'] for c in cases),'actual_mcp':sum(c['actual_mcp_executions'] for c in cases),'errors':errors},indent=2))
raise SystemExit(bool(errors))
