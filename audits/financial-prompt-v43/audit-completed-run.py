#!/usr/bin/env python3
"""Prepared offline-only auditor. Run only after coordinator completion trigger.
No inference, source writes, or resume execution. Fresh grades go to /tmp only.
"""
import argparse, collections, datetime, fcntl, hashlib, json, os, pathlib, subprocess, sys, tempfile
sys.dont_write_bytecode=True

WORK = pathlib.Path('/home/doanlong/extra/benchmark')
STUDY = WORK/'experiments/finance-v43-study'
DEST = WORK/'audits/financial-prompt-v43/independent-evidence.json'
FIELDS = ('call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of')
MODEL_CONFIGS = {'nvidia/nvidia/nemotron-3.5-bolt-e4b':('bench_config.json','bolt'), 'nvidia/deepseek-ai/deepseek-v4.1-flash':('bench_config_deepseek.json','deepseek')}
MODELS=set(MODEL_CONFIGS)

def read(path): return json.loads(pathlib.Path(path).read_text())
def lines(path): return [json.loads(x) for x in pathlib.Path(path).read_text().splitlines() if x.strip()]
def sha(path): return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def body_text(body):
    return '\n'.join(m.get('content','') if isinstance(m.get('content'),str) else json.dumps(m.get('content'),ensure_ascii=False) for m in body.get('messages',[]))
def claim_join(answer, ledger):
    evidence = answer.get('evidence') if isinstance(answer,dict) else None
    return bool(isinstance(evidence,list) and evidence and all(isinstance(e,dict) and any(r.get('status')=='ok' and all(e.get(k)==r.get(k) and e.get(k) is not None for k in FIELDS) for r in ledger) for e in evidence))
def get(answer, path):
    for key in path.split('.'):
        if not isinstance(answer,dict) or key not in answer:return object()
        answer=answer[key]
    return answer
def fresh_grade(grader, answer, gold, destination):
    if not answer or not pathlib.Path(answer).is_file():return {'success':False,'fp':0,'schema_valid':False,'semantic_correctness':False,'error_type':'missing_answer'}
    result=subprocess.run([sys.executable,str(grader),str(answer),'-g',str(gold),'-o',str(destination)],cwd=destination.parent,capture_output=True,text=True,timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    if not destination.is_file():raise RuntimeError('Independent grader produced no artifact: '+result.stderr[:200])
    return read(destination)

def registered_config(study,model):
    if model not in MODEL_CONFIGS:raise ValueError('Unregistered audit model')
    filename,stratum=MODEL_CONFIGS[model]
    path=study/'tools'/filename
    config=read(path)
    if config.get('model')!=model or config.get('model_stratum')!=stratum:raise ValueError('Registered config model/stratum mismatch')
    return config,path

def mechanism_receipt(row, providers):
    events=[]
    for attempt in row.get('attempts',[]):
        path=attempt.get('log_path')
        if not path or not pathlib.Path(path).is_file():continue
        for line in pathlib.Path(path).read_text(errors='replace').splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            if isinstance(event,dict) and any(k in event for k in ('financeIntent','financeAcquisition','acquisition','financePhase')) or isinstance(event,dict) and event.get('type')=='finance-phase':events.append(event)
    successful=[event for event in events if event.get('ok') is True and isinstance(event.get('financeIntent'),dict)]
    # Field-level observations remain visible; unknown runtime field shapes are not credited.
    corrected=sum(event.get('ok') is True and isinstance(event.get('financeIntent'),dict) and event['financeIntent'].get('phase') in ('correction','bounded_finance_correction') and event['financeIntent'].get('correction_used')==1 for event in events)
    first=providers[0] if providers else {}
    return {'phase_events':len(events),'same_intent_corrected_executions':corrected,
            'initial_zero_call_provider_responses':int(bool(providers) and first.get('status')==200 and first.get('tool_call_count')==0),
            'acquisition_phase_events':sum(event.get('type')=='finance-phase' and event.get('phase')=='bounded_finance_acquisition' and event.get('transition')=='enter' for event in events),
            'first_success_in_acquisition':bool(successful and successful[0]['financeIntent'].get('phase')=='bounded_finance_acquisition'),
            'observed_runtime_events':events,
            'note':'Counts reflect explicit recorded fields only. A no-call provider response may be empty; this field does not assert a valid final. Final-primary recovery requires phase/call/receipt review.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help='Coordinator final-completion trigger required')
    parser.add_argument('--run',required=True)
    parser.add_argument('--output',help='Derived audit report destination outside frozen study; default model-keyed independent-evidence.json')
    args=parser.parse_args()
    if not args.execute:raise SystemExit('Prepared only; explicit final-completion trigger required.')
    destination=pathlib.Path(args.output).resolve() if args.output else DEST
    if destination.is_relative_to(STUDY.resolve()):raise SystemExit('Audit output must remain outside frozen study')
    root=pathlib.Path(args.run).resolve()
    if root.parent != (STUDY/'results').resolve():raise SystemExit('Refusing run outside the fixed study results directory')
    # Do not audit an actively owned driver; never stop it or modify its files.
    lock=open(root/'.driver.lock','r')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    manifest=read(root/'manifest.json');plan=manifest['plan'];settings=plan['settings']
    rows=lines(root/'trials.jsonl');expected=24
    MODEL=settings['model']
    if MODEL not in MODELS or settings['split']!='smoke':raise ValueError('Unregistered model or non-smoke split')
    if len(rows)!=expected or len(plan['schedule'])!=expected:raise SystemExit('Cohort incomplete: final audit not run')
    sys.path.insert(0,str(STUDY/'tools'))
    import run_manifest as identity, ready_check as ready
    from experiment_conditions import condition,prompt_directory
    if manifest['fingerprint']!=digest(plan):raise ValueError('Manifest fingerprint mismatch')
    if [r['trial_id'] for r in rows]!=[r['trial_id'] for r in plan['schedule']]:raise ValueError('Observed cohort order/identity differs from exact manifest')
    identity.validate_trial_rows(rows,manifest)
    config,config_path=registered_config(STUDY,MODEL)
    if plan['code']!=identity.code_fingerprint() or plan['harnesses']!=identity.harness_inventory(config) or plan['protocol']!=identity.protocol_fingerprint(config) or plan['config']!=config:raise ValueError('Frozen runtime/code/protocol/config drift')
    for name,fp in plan['tasks'].items():
        if fp!=identity.task_fingerprint(STUDY/'tasks'/settings['split']/name):raise ValueError('Task identity drift: '+name)
    if settings['effort']!='none' or settings['retry']!=0 or settings['runs']!=2:raise ValueError('Unregistered model/retry/repetition')
    provider_timeout,trial_timeout=(45,240) if MODEL=='nvidia/nvidia/nemotron-3.5-bolt-e4b' else (240,900)
    if (settings['seed'],settings['pause'],settings['provider_timeout_s'])!=(20261105,2,provider_timeout):raise ValueError('Unregistered seed/pause/provider deadline')
    if (settings['max_requests'],settings['max_output_tokens'],settings['max_total_tokens'],settings['timeout'])!=(24,2048,48000,trial_timeout):raise ValueError('Behavioral caps differ')
    expected_arms={'opentrading_baseline','opentrading_finance','opencode','dsh'}
    if set(settings['arms'])!=expected_arms:raise ValueError('Unexpected conditions')
    if set(plan['tasks'])!={'smoke-quote-01','smoke-agg-01','smoke-trap-01'}:raise ValueError('Unregistered task cohort')
    counts={arm:collections.Counter() for arm in expected_arms};errors=[];details=[];newrows=[];allproviders=[]
    with tempfile.TemporaryDirectory(prefix='v43-independent-regrade-') as temporary:
      temporary=pathlib.Path(temporary)
      for row in rows:
        c=counts[row['arm']];c['started']+=1;tid=row['trial_id'];task=STUDY/'tasks'/settings['split']/row['task']
        contract=plan['task_contracts'][row['task']]
        from mcp_snapshot_server import load_entries,build_tool_defs
        definitions=build_tool_defs(load_entries(task/'environment/payloads.json')[0]);providers=[];final_ledger=[];local=[]
        for attempt in row['attempts']:
          provider=lines(attempt['provider_ledger']);providers+=provider
          try:final_ledger=ready.verify_mcp_attempt(task,attempt,allow_empty=True)
          except Exception as exc:errors.append({'trial':tid,'stage':'mcp_ledger','error':str(exc)});final_ledger=[]
          c['mcp_calls']+=len(final_ledger);c['mcp_rejected']+=sum(r.get('status')=='rejected' for r in final_ledger)
          c['mcp_successful']+=sum(r.get('status')=='ok' for r in final_ledger)
          for execution in final_ledger:
            if execution.get('status')=='rejected':c['mcp_error_'+str(execution.get('error_code','unknown'))]+=1
          inventory=read(attempt['inventory_path']);cond=condition(row['arm'])
          if any(inventory.get(k)!=v for k,v in {'condition':row['arm'],'native_arm':cond['native_arm'],'prompt_variant':cond['prompt_variant'],'finance_policy':cond['finance_policy']}.items()):errors.append({'trial':tid,'stage':'condition_binding'})
          expected_as_of=read(task/'environment/payloads.json')['snapshot_date'];clock=inventory.get('clock_policy') or {}
          if clock.get('answer_as_of')!=expected_as_of or clock.get('native_now_pinned') is not (cond['native_arm']=='opentrading'):errors.append({'trial':tid,'stage':'clock_binding'})
          if cond['native_arm']=='opentrading':
            directory=prompt_directory(cond['prompt_variant'])
            if inventory.get('prompt_directory')!=str(directory) or inventory.get('prompt_files')!={p.name:sha(p) for p in sorted(directory.glob('*.md'))}:errors.append({'trial':tid,'stage':'prompt_binding'})
          complete_sets=[{prefix+d['name'] for d in definitions} for prefix in ('opentrading_','mcp__opentrading__','mcp_opentrading_')]
          try:proved=ready.verify_local_rejections(attempt,provider,definitions,cond['finance_policy']);local+=proved
          except Exception as exc:errors.append({'trial':tid,'stage':'local_rejection','error':str(exc)});proved=[]
          if sum(r.get('tool_call_count',0) for r in provider)!=len(final_ledger)+len(proved):errors.append({'trial':tid,'stage':'tool_call_reconciliation'})
          used=0
          for request in provider:
            c['gateway_requests']+=1;c['upstream_attempted']+=bool(request.get('upstream_attempted'))
            usage=request.get('usage');complete=isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k]>=0 for k in ('prompt_tokens','completion_tokens'))
            if request.get('upstream_attempted') and used+request.get('input_budget_estimate_bytes',0)+request.get('effective_max_tokens',2048)>48000:errors.append({'trial':tid,'stage':'token_policy_cap'})
            if complete:c['usage_requests']+=1;c['known_input_tokens']+=usage['prompt_tokens'];c['known_output_tokens']+=usage['completion_tokens']
            else:c['partial_or_missing_usage_requests']+=1
            if isinstance(usage,dict):
              for family,field in [('completion_tokens_details','reasoning_tokens'),('prompt_tokens_details','cached_tokens')]:
                value=(usage.get(family) or {}).get(field)
                if type(value) is int and value>=0:c['reported_'+field+'_requests']+=1;c['known_'+field]+=value
                else:c['unreported_'+field+'_requests']+=1
            if complete:used+=usage['prompt_tokens']+usage['completion_tokens']
            if request.get('request_model') not in (None,MODEL.removeprefix('nvidia/')):errors.append({'trial':tid,'stage':'request_model'})
            names=request.get('tool_names')
            if names is not None and (len(names)!=len(set(names)) or set(names) not in complete_sets):errors.append({'trial':tid,'stage':'common_catalog_tools'})
            bodies={}
            for stage in ('native','effective'):
              capture=request.get(stage+'_request_capture')
              if capture and capture.get('path'):
                p=pathlib.Path(capture['path']);b=read(p);bodies[stage]=b;c['capture_files']+=1
                if sha(p)!=capture['raw_sha256'] or digest(b)!=capture['canonical_sha256']:errors.append({'trial':tid,'stage':'capture_hash'})
            if len(bodies)==2:
              try:ready.verify_request_capture(request)
              except Exception as exc:errors.append({'trial':tid,'stage':'capture_binding','error':str(exc)})
              from wire_contracts import verify_c2_wire_contracts
              for stage,body in bodies.items():
                try:verify_c2_wire_contracts(body,definitions)
                except Exception as exc:errors.append({'trial':tid,'stage':'C2_'+stage+'_constraints','error':str(exc)})
                for tool in body.get('tools',[]):
                  function=tool.get('function',{});name=function.get('name','')
                  canonical=next((name[len(prefix):] for prefix in ('opentrading_','mcp__opentrading__','mcp_opentrading_') if name.startswith(prefix)),None)
                  definition=next((d for d in definitions if d['name']==canonical),None)
                  if definition and definition['description']!=function.get('description'):errors.append({'trial':tid,'stage':'common_description_cues_'+stage,'tool':canonical})
              effective=bodies['effective']
              if ((effective.get('model'),effective.get('temperature'),effective.get('top_p'))!=(MODEL.removeprefix('nvidia/'),0,1)
                      or type(effective.get('max_tokens')) is not int or not 1<=effective['max_tokens']<=2048):errors.append({'trial':tid,'stage':'effective_policy'})
            else:c['partial_capture_requests']+=1
            if request.get('status')==200 and (len(bodies)!=2 or request.get('response_models')!=[MODEL.removeprefix('nvidia/')]):errors.append({'trial':tid,'stage':'successful_provider_missing_identity'})
            if request.get('effort') not in (None,'none','off'):errors.append({'trial':tid,'stage':'effort'})
          if sum(bool(r.get('upstream_attempted')) for r in provider)>24:errors.append({'trial':tid,'stage':'request_cap'})
        allproviders+=providers;c['local_rejections']+=len(local)
        generated_ids=[call for request in providers for call in request.get('response_tool_call_ids',[])]
        if len(generated_ids)!=len(set(generated_ids)):errors.append({'trial':tid,'stage':'duplicate_generated_call_ids'})
        c['generated_tool_calls']+=len(generated_ids)
        c['zero_generated_call_trials']+=not generated_ids
        mechanism=mechanism_receipt(row,providers)
        for name in ('same_intent_corrected_executions','phase_events','initial_zero_call_provider_responses','acquisition_phase_events'):
            c[name]+=mechanism[name]
        answer_path=row.get('answer_path');answer=read(answer_path) if answer_path and pathlib.Path(answer_path).is_file() else None
        grades=[]
        for label,grader in [('primary',task/'tests/grader.py'),('frozen_v41',STUDY/'tools/frozen_v41_grader.py'),('frozen_v3',STUDY/'tools/frozen_v3_grader.py')]:
          directory=temporary/tid/label;directory.mkdir(parents=True);grades.append(fresh_grade(grader,answer_path,task/'solution/gold.json',directory/'grade.json'))
        from public_response_contract import append_public_contract,validate_public_response_contract
        instruction=append_public_contract('Benchmark time context: answer relative to the frozen data snapshot as of '+read(task/'environment/payloads.json')['snapshot_date']+
                   '. Execution wall-clock does not advance the financial reporting period. Use response provenance.as_of for evidence.\n\n'+(task/'instruction.md').read_text())
        raw_final=row['attempts'][-1].get('final_text') if row['attempts'] else None
        public_contract=validate_public_response_contract(instruction,raw_final,[d['name'] for d in definitions])
        if any(row.get('public_contract_'+field)!=public_contract[field] for field in ('valid','errors','branch')):
            errors.append({'trial':tid,'stage':'independent_public_contract_regrade'})
        grade,frozen_v41,frozen=grades;grounded=claim_join(answer,final_ledger);timely=bool(row.get('timely'));answered=row['status']=='ok' and timely and answer is not None
        primary=bool(grade.get('success') and public_contract['valid'] and grounded and row['status']=='ok' and timely);frozen_primary=bool(frozen.get('success') and grounded and row['status']=='ok' and timely)
        c['public_contract_valid_trials']+=public_contract['valid'];c['public_contract_invalid_trials']+=not public_contract['valid']
        frozen_v41_primary=bool(frozen_v41.get('success') and grounded and row['status']=='ok' and timely)
        if primary!=bool(row.get('success')) or frozen_primary!=bool(row.get('frozen_v3_success')) or frozen_v41_primary!=bool(row.get('frozen_v41_success')):errors.append({'trial':tid,'stage':'independent_primary_regrade'})
        c['frozen_v41_primary']+=frozen_v41_primary;c['v41_grader_delta_trials']+=primary!=frozen_v41_primary
        c['primary']+=primary;c['frozen_v3_primary']+=frozen_primary;c['semantic']+=bool(grade.get('semantic_correctness',grade.get('success')));c['schema']+=bool(grade.get('schema_valid'));c['answered']+=answered;c['dnf']+=not answered;c['fp']+=bool(grade.get('fp'));c['native_unanswered']+=bool((row.get('native_completion') or {}).get('unanswered'));c['native_recovery_trials']+=bool((row.get('native_completion') or {}).get('recoveries'))
        c['zero_call_completed_finals']+=bool(answered and not generated_ids)
        c['first_success_in_acquisition_trials']+=mechanism['first_success_in_acquisition']
        c['primary_with_acquisition_phase']+=bool(primary and mechanism['acquisition_phase_events'])
        c['usage_complete_trials']+=bool(providers and all(isinstance(r.get('usage'),dict) and all(type(r['usage'].get(k)) is int and r['usage'][k]>=0 for k in ('prompt_tokens','completion_tokens')) for r in providers))
        c['wall_ms']+=row.get('wall_ms') or 0
        c['native_status_'+str(row.get('status'))]+=1
        c['native_failed_trials']+=row.get('status')!='ok'
        c['untimely_trials']+=not timely
        answerable=contract.get('scoring')!='refusal' and bool(contract.get('answerable_fields'))
        c['answerable_started']+=answerable;c['unanswerable_started']+=contract.get('scoring')=='refusal'
        refusal=bool(answerable and answered and isinstance(answer,dict) and (('value' in answer and answer['value'] is None and bool(str(answer.get('reason') or answer.get('note') or '').strip())) or any(get(answer,p) is None or (get(answer,p)==[] and bool(str(answer.get('reason') or answer.get('note') or '').strip())) for p in contract.get('answerable_fields',[]))))
        c['false_refusal']+=refusal
        claims=answer.get('evidence') if isinstance(answer,dict) else None
        mismatched=bool(isinstance(claims,list) and claims and not grounded);c['claimed_evidence_mismatch']+=mismatched
        gold=read(task/'solution/gold.json');identity_fields=('tool','source','as_of','matched_entry_id','response_sha256')
        expectation_types={item.get('type') for item in gold.get('expects',[])}
        financial_check_coverage={'period_scored':'period' in expectation_types,'unit_scored':'unit' in expectation_types,
                                  'answer_period':answer.get('period') if isinstance(answer,dict) else None}
        if isinstance(answer,dict) and 'period' in answer and not financial_check_coverage['period_scored']:
            c['answer_period_without_numeric_gold_period_check']+=1
        required={tuple(r.get(k) for k in identity_fields) for r in gold.get('provenance_contract',[])}
        retrieved={tuple(r.get(k) for k in identity_fields) for r in final_ledger if r.get('status')=='ok'}
        coverage=bool(required) and required<=retrieved;c['required_data_complete_trials']+=coverage
        for claim in claims or []:
          if isinstance(claim,dict) and any(all(claim.get(k)==r.get(k) for k in FIELDS) for r in final_ledger if r.get('status')=='ok'):
            visible=any(str(claim['call_id']) in str(m.get('content')) and str(claim['response_sha256']) in str(m.get('content')) for req in providers if req.get('native_request_capture') for m in read(req['native_request_capture']['path']).get('messages',[]) if m.get('role')=='tool')
            if not visible:errors.append({'trial':tid,'stage':'successful_claim_not_in_model_context'})
        if primary:stage='primary_correct'
        elif not answered:stage='dnf'
        elif not coverage:stage='required_retrieval_incomplete'
        elif refusal:stage='false_refusal_after_tool_success'
        elif not public_contract['valid']:stage='public_contract_invalid'
        elif not grounded:stage='evidence_missing_or_mismatch'
        else:stage='post_tool_contract_or_financial_error'
        c['stage_'+stage]+=1
        details.append({'trial_id':tid,'native_status':row.get('status'),'timely':timely,'has_extracted_answer':answer is not None,'provider_statuses':[r.get('status') for r in providers],'primary':primary,'frozen_v41_primary':frozen_v41_primary,'frozen_v3_primary':frozen_primary,'grounded':grounded,'answered':answered,'false_refusal':refusal,'public_contract':public_contract,'required_data_complete':coverage,'required_responses':len(required),'retrieved_required_responses':len(required&retrieved),'failure_stage':stage,'financial_check_coverage':financial_check_coverage,'mechanism':mechanism,'fresh_grade':grade,'fresh_frozen_v41_grade':frozen_v41,'fresh_frozen_grade':frozen})
        newrows.append({**row,'success':primary})
    from metrics import paired_statistics
    comparisons=paired_statistics(newrows,expected_runs=2,clusters={k:v['payload_family_sha256'] for k,v in plan['task_contracts'].items()})
    cells={(r['arm'],r['task'],r['run']):r['success'] for r in newrows}
    direct_pairs=[]
    if True:
      for other in sorted(expected_arms-{'opentrading_finance'}):
        pairs=[(cells['opentrading_finance',task,run],cells[other,task,run]) for task in plan['tasks'] for run in (1,2)]
        direct_pairs.append({'candidate':'opentrading_finance','other':other,'pairs':len(pairs),'candidate_only':sum(a and not b for a,b in pairs),'other_only':sum(b and not a for a,b in pairs),'both_correct':sum(a and b for a,b in pairs),'both_wrong':sum(not a and not b for a,b in pairs)})
    totals={k:dict(v) for k,v in counts.items()}
    for value in totals.values():
      for field in ('reasoning_tokens','cached_tokens'):
        if not value.get('reported_'+field+'_requests'):value['known_'+field]=None
    if any(v['started']!=6 for v in totals.values()):errors.append({'stage':'fixed_denominators'})
    positions={a:collections.Counter() for a in expected_arms}
    narm=len(expected_arms)
    for index,item in enumerate(plan['schedule']):positions[item['arm']][index%narm]+=1
    # Exact schedule is frozen by manifest; 3 task clusters cannot evenly cover 4 positions.
    if len(cells)!=24 or set((task,run) for arm,task,run in cells)!={(task,run) for task in plan['tasks'] for run in (1,2)}:errors.append({'stage':'complete_task_arm_repeat_cells'})
    guard=None
    if True:
      candidate=counts['opentrading_finance'];baseline=counts['opentrading_baseline']
      guard={'scope':'descriptive smoke only, no promotion or superiority conclusion','primary_strictly_better':candidate['primary']>baseline['primary'],'no_dnf_regression':candidate['dnf']<=baseline['dnf'],'no_false_refusal_regression':candidate['false_refusal']<=baseline['false_refusal'],'no_fp_regression':candidate['fp']<=baseline['fp'],'no_evidence_mismatch_regression':candidate['claimed_evidence_mismatch']<=baseline['claimed_evidence_mismatch'],'no_audit_errors':not errors,'accepted_fabricated_evidence':'manual classification required before final decision'}
    evidence=read(destination) if destination.exists() else {}
    evidence.setdefault('completed_runs',{})[MODEL]={'model':MODEL,'split':settings['split'],'registered_config_path':str(config_path),'registered_config_sha256':sha(config_path),'audited_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'directory':str(root),'manifest_sha256':manifest['fingerprint'],'scheduled':expected,'observed':len(rows),'audit_controls_pass':not errors,'counts':totals,'positions':{a:dict(v) for a,v in positions.items()},'errors':errors,'usage_semantics':'Known reasoning tokens are a subset of completion tokens and are not added again; absent reasoning/cache fields remain unreported, not zero.','fresh_grades':details,'direct_paired_outcomes':direct_pairs,'paired_comparisons_exploratory_95':comparisons,'descriptive_candidate_guard_no_promotion_authority':guard,'resume_zero_call_check':'not executed by this offline auditor'}
    evidence['status']='completed model-stratified offline audit; manual evidence classification and resume receipt still required; no cross-model pooling'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'directory':str(root),'counts':totals,'errors':errors},ensure_ascii=False,indent=2))
    return bool(errors)

if __name__=='__main__':sys.exit(main())
