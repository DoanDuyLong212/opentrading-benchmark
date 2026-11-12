"""Read-only independent actual four-adapter MCP/gateway wire reconciliation."""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];STUDY=ROOT/'experiments/finance-v43-study'
sys.dont_write_bytecode=True;sys.path.insert(0,str(STUDY/'tools'))
from mcp_snapshot_server import load_entries,build_tool_defs
from wire_contracts import schema_constraints
from ready_check import verify_request_capture,verify_local_rejections
from experiment_conditions import condition
DIRECTORY=pathlib.Path(sys.argv[1]).resolve();receipt=json.loads((DIRECTORY/'receipt.json').read_text())
def read(p):return json.loads(pathlib.Path(p).read_text())
def lines(p):return [json.loads(x) for x in pathlib.Path(p).read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def canonical(name):return next((name[len(p):] for p in ('opentrading_','mcp__opentrading__','mcp_opentrading_') if name.startswith(p)),None)
def user_text(body):
    out=[]
    for m in body.get('messages',[]):
        if m.get('role')!='user':continue
        c=m.get('content')
        if isinstance(c,str):out.append(c)
        elif isinstance(c,list):out.extend(p.get('text','') for p in c if p.get('type')=='text')
    return out
errors=[];cases=[];common=None
for item in receipt['results']:
    arm=item['arm'];directory=DIRECTORY/arm;providers=lines(item['ledger']);inventory=read(item['inventory']);definitions=inventory['snapshot_tool_definitions'];expected={d['name']:d for d in definitions}
    task=next((STUDY/'tasks'/split/receipt['task'] for split in ('smoke','pilot','main','holdout') if (STUDY/'tasks'/split/receipt['task']).is_dir()),DIRECTORY/'public-mcp-fixture')
    if definitions!=build_tool_defs(load_entries(task/'environment/payloads.json')[0]):errors.append([arm,'source catalog binding differs'])
    generated=[i for r in providers for i in r.get('response_tool_call_ids',[])]
    ledger=lines(directory/'mcp.jsonl') if (directory/'mcp.jsonl').exists() else []
    try:local=verify_local_rejections({'log_path':str(directory/'native.log')},providers,definitions,condition(arm)['finance_policy'])
    except Exception as exc:errors.append([arm,'local_rejection',str(exc)]);local=[]
    if len(generated)!=len(set(generated)) or len(generated)!=len(ledger)+len(local):errors.append([arm,'generated/local/MCP reconciliation'])
    native_effective=[]
    for request in providers:
        try:verify_request_capture(request)
        except Exception as exc:errors.append([arm,'capture_binding',str(exc)])
        for stage in ('native','effective'):
            capture=request.get(stage+'_request_capture') or {}
            if not capture.get('path'):errors.append([arm,stage,'missing capture']);continue
            body=read(capture['path']);observed={canonical(t.get('function',{}).get('name','')):t.get('function',{}) for t in body.get('tools',[])}
            if set(observed)!=set(expected):errors.append([arm,stage,'catalog changed'])
            for name,definition in expected.items():
                actual=observed.get(name,{})
                if actual.get('description')!=definition['description'] or schema_constraints(actual.get('parameters'))!=schema_constraints(definition['inputSchema']):errors.append([arm,stage,'C2 constraints/common cues changed',name])
            native_effective.append({'stage':stage,'path':capture['path'],'sha256':sha(capture['path']),'tools':list(observed),'tool_choice':body.get('tool_choice')})
    first=read(providers[0]['effective_request_capture']['path']);texts=user_text(first)
    # Existing native OpenCode CLI wraps/escapes user quotes. This is comparison only, never request mutation.
    normalized=[s[1:-1].replace('\\"','"') if s.startswith('"') and s.endswith('"') else s for s in texts]
    wanted=next((s for s in normalized if 'PUBLIC_RESPONSE_CONTRACT_V42=' in s),None)
    if wanted is None:errors.append([arm,'common public contract absent'])
    if common is None:common=wanted
    elif wanted!=common:errors.append([arm,'semantic user/task/public contract content differs'])
    if cases and definitions!=cases[0]['definitions']:errors.append([arm,'source tool catalog differs across arms'])
    cases.append({'arm':arm,'definitions':definitions,'requests':len(providers),'generated_calls':len(generated),'actual_mcp':len(ledger),'local_rejections':len(local),'user_raw_lengths':[len(s) for s in texts],'user_content_after_explicit_presentation_normalization_sha256':digest(wanted),'captures':native_effective})
result={'pass':not errors,'directory':str(DIRECTORY),'receipt_sha256':sha(DIRECTORY/'receipt.json'),'errors':errors,'cases':cases,'presentation_limitation':'Full native system prompts differ by design. OpenCode outer quotation/backslash-quote presentation differs on raw wire; explicit read-only normalization yields the same public task/contract text if this check passes. No cause or efficacy inference.'}
pathlib.Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'pass':not errors,'cases':len(cases),'requests':sum(c['requests'] for c in cases),'errors':errors},indent=2));raise SystemExit(bool(errors))
