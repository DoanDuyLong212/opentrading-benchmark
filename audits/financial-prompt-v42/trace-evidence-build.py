import pathlib,json,hashlib,collections,decimal
from jsonschema import Draft202012Validator
ROOT=pathlib.Path('/home/doanlong/extra/benchmark')
RUN=ROOT/'experiments/finance-v42-study/results/financial-v42-smoke-20261106'
rows=[json.loads(l) for l in (RUN/'trials.jsonl').read_text().splitlines()]
out={'scope':'Read-only frozen smoke forensic audit; no inference. Derived evidence only.','run':str(RUN),'trials':[],'manual_payload_checks':{}}
for row in rows:
 t=RUN/'trials'/row['trial_id'];a=next((t/'attempts').iterdir());r=json.loads((a/'result.json').read_text());initial=json.loads((a/'provider-requests/0001-effective.json').read_text());calls=[json.loads(l) for l in (a/'mcp.jsonl').read_text().splitlines()] if (a/'mcp.jsonl').exists() else []
 schemas={v['function']['name']:v['function']['parameters'] for v in initial['tools']}; base={k.split('__')[-1].removeprefix('opentrading_'):v for k,v in schemas.items()}
 validated=[]
 for c in calls:
  schema=base[c['tool']];errs=list(Draft202012Validator(schema).iter_errors(c['arguments']));c1={k:v for k,v in schema.items() if k!='anyOf' and not k.startswith('x-')};c1errs=list(Draft202012Validator(c1).iter_errors(c['arguments']));validated.append({'tool':c['tool'],'arguments':c['arguments'],'c1_shape_valid':not c1errs,'c2_valid':not errs,'status':c['status'],'error_code':c.get('error_code'),'call_id':c['call_id']})
 requests=[]
 for f in sorted((a/'provider-requests').glob('*effective.json')):
  x=json.loads(f.read_text());requests.append({'path':str(f.relative_to(ROOT)),'tool_choice':x.get('tool_choice'),'tools':len(x.get('tools',[])),'max_tokens':x.get('max_tokens'),'system_chars':sum(len(str(m['content'])) for m in x['messages'] if m['role']=='system'),'system_utf8_bytes':sum(len(str(m['content']).encode()) for m in x['messages'] if m['role']=='system')})
 provider=[json.loads(l) for l in (a/'provider.jsonl').read_text().splitlines()]
 out['trials'].append({k:row[k] for k in ['trial_id','success','semantic_correctness','grounded_correctness','evidence_grounded','public_contract_valid','public_contract_errors','status','error_type','tokens','requests','wall_ms','native_completion']}|{'result_path':str((a/'result.json').relative_to(ROOT)),'final_text':r['final_text'],'calls':validated,'provider_requests':requests,'provider_statuses':[v.get('status') for v in provider],'per_request_output':[v.get('usage',{}).get('completion_tokens') for v in provider],'input_byte_estimates':[v.get('input_budget_estimate_bytes') for v in provider]})
for task in ['smoke-quote-01','smoke-agg-01','smoke-trap-01']:
 d=ROOT/'experiments/finance-v42-study/tasks/smoke'/task;payload=json.loads((d/'environment/payloads.json').read_text()); gold=json.loads((d/'solution/gold.json').read_text());check={'payload':str((d/'environment/payloads.json').relative_to(ROOT)),'payload_sha256':hashlib.sha256((d/'environment/payloads.json').read_bytes()).hexdigest(),'recorded_tools':payload['tools']}
 if task=='smoke-agg-01':
  vals={b['symbol']:decimal.Decimal(str(b['last'])) for b in payload['tools']['vn_quote_history']['data']['banks']};total=sum(vals.values());mean=total/len(vals);check.update(values={k:str(v) for k,v in vals.items()},sum=str(total),mean=str(mean),gold_agrees=all(vals[k]==decimal.Decimal(str(gold['solution'][k])) for k in vals) and mean==decimal.Decimal(str(gold['solution']['mean'])))
 elif task=='smoke-quote-01':check.update(value=payload['tools']['vn_quote_history']['data']['last'],gold_agrees=payload['tools']['vn_quote_history']['data']['last']==gold['solution']['value'])
 else:check.update(empty_resolver=payload['tools']['symbol_resolve']['data']['resolved'] is None and payload['tools']['symbol_resolve']['data']['candidates']==[])
 out['manual_payload_checks'][task]=check
out['aggregate']={'mcp_status':dict(collections.Counter(c['status'] for t in out['trials'] for c in t['calls'])),'c2_valid_calls':sum(c['c2_valid'] for t in out['trials'] for c in t['calls']),'all_calls':sum(len(t['calls']) for t in out['trials']),'provider_requests':sum(len(t['provider_requests']) for t in out['trials']),'per_request_max_output':max(n for t in out['trials'] for n in t['per_request_output']),'max_trial_ms':max(t['wall_ms'] for t in out['trials'])}
(ROOT/'audits/financial-prompt-v42/trace-evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out['aggregate']));print([(k,v.get('mean',v.get('value',v.get('empty_resolver')))) for k,v in out['manual_payload_checks'].items()])
