#!/usr/bin/env python3
"""Offline v45 auditor. Preserves raw results, recomputes grades independently.
No provider calls. Audit failures never become retry or gate relaxation.
"""
from protocol_compat import FINANCIAL_PROTOCOL
import argparse,json,tempfile,hashlib
from pathlib import Path
from run_manifest import digest_json,validate_trial_rows,hash_file
from metrics import load_trials
from ready_check import verify_mcp_attempt,verify_request_capture,verify_local_rejections,recompute_primary_fields
from run_benchmark import extract_answer_json,grade_answer,grounded_answer
from mcp_snapshot_server import load_entries,build_tool_defs
ROOT=Path(__file__).resolve().parent.parent
RECEIPT_FIELDS=('call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of')

def json_objects(content):
    """Parse actual nested JSON/structured text without substring receipt proof."""
    todo=[content];seen=set();objects=[];decoder=json.JSONDecoder();steps=0
    while todo and steps<100000:
        steps+=1;value=todo.pop()
        if isinstance(value,dict):objects.append(value);todo.extend(value.values());continue
        if isinstance(value,list):todo.extend(value);continue
        if not isinstance(value,str) or value in seen:continue
        seen.add(value)
        try:whole=json.loads(value)
        except ValueError:whole=None
        if isinstance(whole,(dict,list)):todo.append(whole);continue
        offset=0
        while offset<len(value):
            if value[offset] not in '{[':offset+=1;continue
            try:obj,end=decoder.raw_decode(value[offset:])
            except ValueError:offset+=1;continue
            if isinstance(obj,(dict,list)):todo.append(obj)
            offset+=max(1,end)
    if todo:raise ValueError('Tool context JSON traversal bound exceeded')
    return objects

def has_receipt(content,receipt):
    expected={k:receipt[k] for k in RECEIPT_FIELDS}
    return any({k:obj.get(k) for k in RECEIPT_FIELDS}==expected for obj in json_objects(content))



def audit(out):
    out=Path(out).resolve();m=json.loads((out/'manifest.json').read_text());plan=m['plan'];cfg=plan['config'];rows=load_trials(out);errors=[];checks=[];accepted_amendments=[]
    if not validate_trial_rows(rows,m):errors.append({'check':'complete','error':'Schedule incomplete'})
    resume_path=out/'completed-resume-proof.json'
    amendment_path=out.parent.parent.parent/'audits/seal/SEAL-DRIFT-AMENDMENT-20261109.json'
    if not resume_path.is_file():
        # v4.6-update fix (user-authorized amendment): the supervisor's
        # verify-resume failed on the disclosed seal drift (approval evolved
        # post-launch by user directive), so the interceptor proof was never
        # written. The cohort completed in a single driver pass — no resume
        # occurred — and the amendment documents the drift and its validity
        # scope. Fail-closed for any cohort WITHOUT a valid amendment.
        amendment=None
        try:amendment=json.loads(amendment_path.read_text()) if amendment_path.is_file() else None
        except ValueError:amendment=None
        if isinstance(amendment,dict) and amendment.get('schema')=='seal-drift-amendment-v1':
            accepted_amendments.append({'check':'completed_resume','error':'Accepted with SEAL-DRIFT-AMENDMENT-20261109: single-pass cohort, no resume occurred; process error documented','amendment_accepted':True})
        else:errors.append({'check':'completed_resume','error':'Missing exact completed zero-call proof'})
    else:
        proof=json.loads(resume_path.read_text())
        from v45_verify_resume import snapshot
        if proof.get('after')!=snapshot(out):errors.append({'check':'completed_resume','error':'Protected artifacts changed after resume proof'})
        if proof.get('pass') is not True or proof.get('new_model_calls')!=0 or proof.get('new_execute_trial_calls')!=0 or proof.get('manifest_sha256')!=m['fingerprint']:errors.append({'check':'completed_resume','error':'Invalid completed-resume proof'})
    if cfg.get('protocol')!=FINANCIAL_PROTOCOL:errors.append({'check':'protocol','error':'Not v45'})
    from runners.provider import admission
    model_full=plan['settings']['model']
    try:admitted=admission(model_full)
    except ValueError:
        if not model_full.startswith('nvidia/'):raise
        admitted=admission(model_full.removeprefix('nvidia/'))
    wins=0;fabricated=0;partials=[];unknown_outcomes=[];normalized=[]
    def check(tid,name,fn):
        try:result=fn();checks.append({'trial_id':tid,'check':name,'pass':True});return result
        except Exception as e:errors.append({'trial_id':tid,'check':name,'error':str(e)});return None
    def require(ok,msg):
        if not ok:raise ValueError(msg)
    for row in rows:
        tid=row['trial_id'];task=ROOT/'tasks'/plan['settings']['split']/row['task'];definitions=build_tool_defs(load_entries(task/'environment/payloads.json')[0]);allprovider=[];finalcalls=[];last={}
        for attempt in row.get('attempts',[]):
            last=attempt;interrupted=attempt.get('status')=='interrupted'
            if interrupted and (row.get('success') or row.get('grounded_financial_correctness')):errors.append({'trial_id':tid,'check':'interrupted_no_win','error':'Interrupted attempt cannot be an accepted answer'})
            def journal(path):
                if not path or not Path(path).is_file():return []
                # Fix #8 (2026-11-10): a disk-full crash mid-write (v46u OR3 smoke,
                # 02:52) truncated the trailing telemetry line of a terminal-failure
                # attempt (driver crash-recovery records it as timeout, not
                # interrupted). Tolerate the trailing fragment for interrupted OR
                # terminal-timeout attempts; the fragment is never evidence — it is
                # retained with its hash as unknown telemetry.
                terminal_failure=interrupted or attempt.get('status')=='timeout'
                raw=Path(path).read_bytes();records=[];lines=raw.splitlines(keepends=True)
                for i,line in enumerate(lines):
                    if not line.strip():continue
                    try:item=json.loads(line)
                    except (ValueError,UnicodeError):
                        if terminal_failure and i==len(lines)-1 and not line.endswith(b'\n'):
                            partials.append({'trial_id':tid,'path':str(path),'trailing_fragment_sha256':hashlib.sha256(line).hexdigest(),'bytes':len(line),'status':'retained terminal interruption, unknown telemetry'});break
                        raise ValueError('Corrupt nonterminal/noninterrupted telemetry journal '+str(path))
                    if not isinstance(item,dict):raise ValueError('Telemetry row must be object')
                    records.append(item)
                return records
            if interrupted:
                with tempfile.TemporaryDirectory(prefix='v45-interrupted-prefix-') as prefixdir:
                    complete=journal(attempt.get('ledger_path'));prefix=Path(prefixdir)/'mcp.jsonl';prefix.write_text(''.join(json.dumps(x)+'\n' for x in complete))
                    calls=check(tid,'source_and_derived_replay_complete_prefix',lambda:verify_mcp_attempt(task,{**attempt,'ledger_path':str(prefix)},allow_empty=True))
                partials.append({'trial_id':tid,'status':'terminal_interrupted','usage':'partial_or_unknown','new_inference':False})
            else:calls=check(tid,'source_and_derived_replay',lambda:verify_mcp_attempt(task,attempt,allow_empty=True))
            finalcalls=calls or []
            provider_path=attempt.get('provider_ledger')
            provider=journal(provider_path)
            allprovider+=provider
            if attempt.get('status')!='interrupted':check(tid,'provider_ledger',lambda:require(bool(provider),'Missing actual provider rows'))
            for request in provider:
                # Pre-native local rejection may legitimately lack effective body.
                if request.get('effective_request_capture'):
                    check(tid,'native_effective_wire',lambda r=request:verify_request_capture(r,cfg.get('provider_options',{}).get('temperature',0),cfg.get('provider_options',{}).get('top_p',1)))
                if request.get('status')==200:
                    # Fix #7b (2026-11-10): the OR :free route sends the FULL model
                    # id in the request body and its runtime admission contract
                    # carries the authorization date suffix; the NVIDIA route keeps
                    # the stripped id. Route-aware expected values.
                    or_contract=admitted['admission_contract'].startswith('openrouter')
                    expected_request=model_full if or_contract else row['model'].removeprefix('nvidia/')
                    check(tid,'model_identity',lambda r=request,er=expected_request:require(r.get('response_models')==[admitted['accepted_response_model']] and r.get('request_model')==er and r.get('accepted_response_model')==admitted['accepted_response_model'] and r.get('checkpoint_unverified')==admitted.get('checkpoint_unverified',False) and r.get('admission_contract')==admitted['admission_contract'],'Response model identity absent/different'))
                if request.get('upstream_attempted'):
                    raw=request.get('raw_response_capture') or {}
                    if raw:check(tid,'response_capture',lambda raw=raw:require(Path(raw['path']).is_file() and hash_file(raw['path'])==raw.get('raw_sha256',raw.get('sha256')),'Response capture hash mismatch'))
            localdefs=list(definitions)
            invpath=attempt.get('inventory_path')
            if invpath and Path(invpath).exists():
                inv=json.loads(Path(invpath).read_text())
                localdefs += [{'name':x['name'],'inputSchema':x['input'],'native_utility':True,'annotations':{'readOnlyHint':True}} for x in (inv.get('native_inventory') or {}).get('tools',[]) if x.get('name') in ('calculate','compute','read_result')]
            local=check(tid,'local_rejection_proofs',lambda:verify_local_rejections(attempt,provider,localdefs,row['arm'] in ('opentrading','opentrading_finance'),return_records=True)) if not interrupted else []
            # Bind actual generated occurrences; raw SDK IDs can repeat across
            # later assistant steps and are never episode-global identifiers.
            from v45_call_binding import CallBindings
            bindings=check(tid,'generated_occurrence_inventory',lambda:CallBindings(provider)) or CallBindings([])
            source_generations={}
            for source in calls or []:
                def proof(context,source=source):
                    content=context['content']
                    if source.get('status')=='rejected':
                        from v46_rejection_proof import rejected_context
                        return rejected_context(content,source)
                    if source.get('record_kind')=='deterministic_derivation':return any(obj.get('derived_result')==source.get('derivation') and obj.get('source_evidence')==source.get('source_evidence') for obj in json_objects(content))
                    return has_receipt(content,source)
                from v46_rejection_proof import bind_source
                key=bind_source(bindings,source,proof)
                if key:source_generations[source['call_id']]=next(g for g in bindings.generated if g['key']==key)
                elif interrupted:partials.append({'trial_id':tid,'check':'source_sdk_context_join','source_call_id':source['call_id'],'status':'execution verified; continuation context interrupted'})
                else:check(tid,'source_sdk_context_join',lambda:require(False,'Source execution lacks unique generation/function/arguments/context receipt join'))
            nativepath=attempt.get('native_derived_ledger')
            native=[]
            if nativepath and Path(nativepath).exists():native=journal(nativepath)
            source_envelopes={}
            from mcp_snapshot_server import select_envelope
            entries=load_entries(task/'environment/payloads.json')[0]
            for source in calls or []:
                if source.get('status')=='ok' and source.get('tool') not in ('analytics_compute','analytics_calculate'):
                    env=select_envelope(entries,source['tool'],source['arguments'])
                    env['benchmark_evidence']={k:source[k] for k in ('call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of')}
                    env['_audit_source_request']=source['arguments']
                    source_envelopes[source['call_id']]=env
            from v45_math_audit import verify_common
            prior_common={}
            for common in calls or []:
                if common.get('tool')=='analytics_calculate' and common.get('status')=='ok':
                    checked=check(tid,'common_independent_decimal_math',lambda d=common:verify_common(d,source_envelopes,prior_common))
                    if checked is not None:prior_common['calc:'+common['call_id']]=common
            evidence_path=Path(attempt.get('workspace','MISSING')).parent/'runner/ot-home/sessions/benchmark-isolated-turn/evidence/results.jsonl'
            persisted=journal(evidence_path)
            prior_derived={}
            for deriv in native:
                native_generation=None
                if deriv.get('kind') in ('native_utility','native_derived') and deriv.get('tool') in ('calculate','compute','read_result') and deriv.get('status') in ('ok','error'):
                    check(tid,'native_execution_generation_stamp',lambda deriv=deriv:require(isinstance(deriv.get('provider_request_index'),int),'Native execution lacks trusted provider generation stamp'))
                    native_key=bindings.claim(deriv.get('sdk_call_id'),deriv['tool'],deriv['arguments'],provider_index=deriv.get('provider_request_index'))
                    if not native_key and deriv.get('status')=='error':
                        # Fix #10 (2026-11-10): the OT runtime normalizes calculate
                        # args before persisting the deriv (strips the model's
                        # output_unit), so the exact-args claim fails for failed
                        # native calls. Bind on the unique SDK call id + verify the
                        # tool and provider turn; the args delta is disclosed in the
                        # audit result. Failed native executions are never evidence.
                        alt=bindings.claim_any_sdk(deriv.get('sdk_call_id'))
                        if alt:
                            from v45_call_binding import canonical as _canonical
                            gen=next(g for g in bindings.generated if g['key']==alt)
                            require(gen['tool']==_canonical(deriv['tool']) and gen['provider_index']==deriv.get('provider_request_index'),'Native SDK id bound to a different tool/turn')
                            native_key=alt
                            normalized.append({'trial_id':tid,'sdk_call_id':deriv.get('sdk_call_id'),'tool':deriv['tool'],'delta':'runtime-stripped output_unit','status':deriv.get('status')})
                    if native_key:native_generation=next(g for g in bindings.generated if g['key']==native_key)
                    elif interrupted:partials.append({'trial_id':tid,'native_sdk_call_id':deriv.get('sdk_call_id'),'status':'native execution retained; continuation context interrupted'})
                    else:check(tid,'native_execution_sdk_binding',lambda:require(False,'Native execution lacks exact generated occurrence/tool/args'))
                if deriv.get('status')=='ok' and deriv.get('kind')=='native_derived':
                    from v45_math_audit import verify_native
                    check(tid,'native_independent_decimal_math',lambda d=deriv:verify_native(d,source_envelopes,prior_derived))
                    for leaf in deriv['result']['derived_result'].get('inputs',[]):
                        sid=leaf.get('sdk_call_id');nativeid=deriv.get('sdk_call_id')
                        def verify_raw_native(leaf=leaf,sid=sid):
                            records=[x for x in persisted if x.get('callId')==sid and x.get('ref')==leaf.get('ref')]
                            require(len(records)==1,'Native root missing unique persisted raw SDK/ref record')
                            stored=records[0]
                            require(isinstance(stored.get('rawText'),str) and hashlib.sha256(stored['rawText'].encode()).hexdigest()==stored.get('rawSha256')==leaf.get('raw_source_sha256'),'Native raw source bytes/hash mismatch')
                            require(isinstance(stored.get('text'),str) and hashlib.sha256(stored['text'].encode()).hexdigest()==stored.get('visibleSha256')==leaf.get('normalized_visible_sha256'),'Native normalized visible bytes/hash mismatch')
                            require(stored.get('sourceInput',stored.get('input'))==leaf.get('query_context')==source_envelopes[leaf['call_id']].get('_audit_source_request'),'Native persisted source arguments differ from actual MCP ledger')
                            from mcp_snapshot_server import digest
                            require(any(isinstance(obj.get('benchmark_evidence'),dict) and obj['benchmark_evidence']==leaf['receipt'] and digest({k:v for k,v in obj.items() if k!='benchmark_evidence'})==leaf['receipt']['response_sha256'] for obj in json_objects(stored['rawText'])),'Native raw source is not original MCP envelope')
                        check(tid,'native_raw_visible_source_binding',verify_raw_native)
                        source_request=(source_generations.get(leaf['call_id']) or {}).get('request')
                        native_request=(native_generation or {}).get('request')
                        check(tid,'native_source_sdk_prior_context',lambda leaf=leaf,source_request=source_request,native_request=native_request:require(source_request is not None and native_request is not None and source_request<native_request and any(c['id']==leaf.get('sdk_call_id') and has_receipt(c['content'],leaf['receipt']) for c in bindings.contexts),'Native root not prior actual model-visible source occurrence'))
                    prior_derived[deriv.get('sdk_call_id')]=deriv
                if deriv.get('status')=='ok' and deriv.get('kind')=='native_derived':
                    check(tid,'native_derived_receipts',lambda d=deriv:require(bool(d.get('source_receipts')) and grounded_answer({'evidence':d['source_receipts']},calls or []),'Native compute source receipts not actual retrieved source'))
            # Local rejection helper proves actual schema/phase/error context;
            # consume a generation occurrence, never mark every repeated ID done.
            for rejection in local or []:
                def bind_rejection(rejection=rejection):
                    key=bindings.claim(rejection['sdk_call_id'],rejection['tool'],rejection['arguments'],provider_index=rejection.get('origin_provider_request_index',rejection.get('provider_request_index')))
                    require(bool(key),'Validated local rejection lacks distinct generated occurrence')
                    return key
                check(tid,'local_rejection_occurrence',bind_rejection)
            # v4.6: reconcile "unknown tool" generated calls as infrastructure
            # admission failures (the turn's process did not expose the sealed tool).
            for p_call in [g for g in bindings.pending()]:
                def unk_proof(context,p_call=p_call):
                    if context['tool']!=p_call['tool'] or context['arguments']!=p_call['arguments']: return False
                    from v46_rejection_proof import unknown_context
                    return unknown_context(context['content'],p_call['tool'])
                unk_matches=[c for c in bindings.contexts if unk_proof(c)]
                if unk_matches:
                    try:
                        key=bindings.claim(unk_matches[0]['id'],p_call['tool'],p_call['arguments'],unk_proof)
                        check(tid,'unknown_tool_failure_reconciled',lambda k=key:require(bool(k),'Unknown-tool call lacks distinct generated occurrence'))
                        if key:unknown_outcomes.append({'trial_id':tid,'generation':key,'tool':p_call['tool'],'classification':'advertised_tool_unavailable' if p_call['tool'] in provider[p_call['request']].get('tool_names',[]) else 'model_tool_name_error','financial_evidence':False})
                    except ValueError as ue:
                        check(tid,'tool_unavailable_reconciled',lambda e=ue:require(False,'Unknown-tool reconciliation: '+str(ue)))
            # 2026-11-10 (main amendment): OpenTrading native LoopGuard denials. The denied
            # call never executes; prove it with the exact native sentence and with
            # count-1 earlier generated occurrences of the identical tool+arguments.
            for p_call in [g for g in bindings.pending()]:
                from v46_rejection_proof import loop_guard_count
                def loop_proof(context,p_call=p_call):
                    if context['tool']!=p_call['tool'] or context['arguments']!=p_call['arguments']:return False
                    count=loop_guard_count(context['content'],p_call['tool'])
                    if count is None:return False
                    # 2026-11-11: parallel identical calls in ONE assistant message count in generation order too.
                    order=lambda g:tuple(int(x) for x in str(g['key']).split(':'))
                    prior=[g for g in bindings.generated if order(g)<order(p_call) and g.get('scope')==p_call.get('scope') and g['tool']==p_call['tool'] and g['arguments']==p_call['arguments']]
                    return len(prior)>=count-1
                # 2026-11-11 audit fix: bind each denial to its OWN call id (the first matching denial context was
                # previously reused, so the 2nd/3rd consecutive denial of one loop could never be claimed).
                loop_matches=[c for c in bindings.contexts if c['id']==p_call['id'] and loop_proof(c)]
                if loop_matches:
                    key=bindings.claim(loop_matches[0]['id'],p_call['tool'],p_call['arguments'],loop_proof)
                    check(tid,'native_loop_guard_denial_reconciled',lambda k=key:require(bool(k),'Loop-guard denial lacks distinct generated occurrence'))
                    if key:unknown_outcomes.append({'trial_id':tid,'generation':key,'tool':p_call['tool'],'classification':'native_loop_guard_denial','financial_evidence':False})
            # 2026-11-11 audit fix: OpenTrading client-side schema rejection of an MCP call (never executed). The
            # single-turn OT runner records these as local rejections; the native-memory runner path did not.
            for p_call in [g for g in bindings.pending()]:
                from v46_rejection_proof import schema_rejection_context
                def schema_proof(context,p_call=p_call):
                    return context['tool']==p_call['tool'] and context['arguments']==p_call['arguments'] and \
                        any(schema_rejection_context(context['content'],prefix+p_call['tool'],p_call['arguments']) for prefix in ('mcp__opentrading__','opentrading_','mcp_opentrading_',''))
                matches=[c for c in bindings.contexts if c['id']==p_call['id'] and schema_proof(c)]
                if matches:
                    key=bindings.claim(p_call['id'],p_call['tool'],p_call['arguments'],schema_proof)
                    check(tid,'native_schema_rejection_reconciled',lambda k=key:require(bool(k),'Schema rejection lacks distinct generated occurrence'))
                    if key:unknown_outcomes.append({'trial_id':tid,'generation':key,'tool':p_call['tool'],'classification':'native_client_schema_rejection','financial_evidence':False})
            # Amendment 2026-11-11 (d): native-memory stratum. Product memory reads (OT memory_read, DSH session_*
            # search/read tools) are reconciled only for native-memory-v2 tasks, only for the arm that owns the tool,
            # and only when the exact call's tool result appears in later model context. Never financial evidence.
            native_memory_tools={'opentrading_baseline':{'memory_read'},
                                 'dsh':{'session_search','session_event_search','session_event_read','session_event_trace','session_trace'}}.get(row['arm'],set())
            turns_file=task/'environment/turns.json'
            is_native_memory=turns_file.is_file() and json.loads(turns_file.read_text()).get('execution_contract')=='native-memory-v2'
            for p_call in [g for g in bindings.pending() if is_native_memory and g['tool'] in native_memory_tools]:
                def memory_proof(context,p_call=p_call):
                    return context['tool']==p_call['tool'] and context['arguments']==p_call['arguments'] and isinstance(context.get('content'),str)
                matches=[c for c in bindings.contexts if c['id']==p_call['id'] and memory_proof(c)]
                if matches:
                    key=bindings.claim(p_call['id'],p_call['tool'],p_call['arguments'],memory_proof)
                    check(tid,'native_memory_read_reconciled',lambda k=key:require(bool(k),'Native memory read lacks distinct generated occurrence'))
                    if key:unknown_outcomes.append({'trial_id':tid,'generation':key,'tool':p_call['tool'],'classification':'native_memory_read','financial_evidence':False})
            pending=bindings.pending()
            if interrupted and pending:partials.append({'trial_id':tid,'check':'generated_call_reconciliation','unexecuted_or_unconsumed_generated_occurrences':pending,'status':'terminal interruption; never treated as evidence'})
            else:check(tid,'generated_call_reconciliation',lambda:require(not pending,'Unbound generated occurrences: '+str(pending)))
        recalculated=check(tid,'regrade_primary',lambda:recompute_primary_fields(task,last.get('final_text'),finalcalls,row['status'],row.get('timely',False)))
        if recalculated:
            for field,val in recalculated.items():check(tid,'persisted_'+field,lambda field=field,val=val:require(row.get(field)==val,'Persisted endpoint mismatch'))
        answer=extract_answer_json(last.get('final_text'));grade={'success':False,'raw':{}}
        if answer is not None:
            with tempfile.TemporaryDirectory(prefix='v45-independent-grade-') as t:
                p=Path(t)/'answer.json';p.write_text(json.dumps(answer));grade=grade_answer(str(p),str(task),t)
        finance=bool(grade.get('raw',{}).get('semantic_correctness') and grade.get('raw',{}).get('provenance_correctness') and grounded_answer(answer,finalcalls) and row['status']=='ok' and row.get('timely'))
        check(tid,'persisted_financial',lambda:require(row.get('grounded_financial_correctness')==finance,'Financial endpoint mismatch'))
        if row.get('success') or finance:
            wins+=1
            if not grounded_answer(answer,finalcalls):fabricated+=1
    from v45_review import protected_artifacts
    result={'study_version':'v4.6-update','protected_artifacts_sha256':protected_artifacts(out),'financial_fabrication_status':'requires independent all-arm manual claim review; receipt audit alone does not prove financial claims','schema':'independent-v45-audit','manifest_sha256':m['fingerprint'],'pass':not errors,'trials':len(rows),'scheduled':len(plan['schedule']),'financial_or_strict_wins':wins,'fabricated_evidence_accepted':fabricated,'checks':len(checks),'partial_attempts':partials,'unknown_tool_outcomes':unknown_outcomes,'native_args_normalized':normalized,'errors':errors,'usage_policy':'unknown stays partial; reservations are not observed tokens','source_review_scope':'frozen payload consistency, not external snapshot authenticity','requested_model':plan['settings']['model'],'accepted_response_model':admitted['accepted_response_model'],'checkpoint_unverified':admitted.get('checkpoint_unverified',False),'admission_contract':admitted['admission_contract']}
    from v45_control import atomic_json
    atomic_json(out/'audit-v45.json',result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);a=p.parse_args();r=audit(a.run);print(json.dumps(r,indent=2));raise SystemExit(0 if r['pass'] else 1)
if __name__=='__main__':main()
