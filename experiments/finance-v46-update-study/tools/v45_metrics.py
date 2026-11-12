"""v4.5 co-primary and operational metrics, identical for smoke/pilot/main.
All scheduled cells remain denominators; no model pooling, quality retries or
semantic-only substitute for source-grounded financial correctness.
"""
import json, math, random, statistics, tomllib
from pathlib import Path


def summarize(rows, manifest, root):
    plan=manifest['plan']; settings=plan['settings']; schedule=plan['schedule']
    indexed={r['trial_id']:r for r in rows}
    result={'schema':'financial-metrics-v45','complete':len(rows)==len(schedule),'models':sorted({r['model'] for r in rows}), 'arms':{}}
    if len(result['models'])>1:raise ValueError('Never pool model cohorts')
    taskmeta={}; contracts=plan.get('task_contracts',{})
    for item in schedule:
        tid=item['task']
        if tid not in taskmeta:
            paths=list((Path(root)/'tasks').glob('*/'+tid+'/task.toml'))
            taskmeta[tid]=tomllib.loads(paths[0].read_text()) if paths else {}
    def counts(cells):
        observed=[indexed[c['trial_id']] for c in cells if c['trial_id'] in indexed]
        answerable=[c for c in cells if contracts.get(c['task'],{}).get('scoring')!='refusal']
        traps=[c for c in cells if c not in answerable]
        strict=sum(bool(r.get('success')) for r in observed)
        finance=sum(bool(r.get('grounded_financial_correctness')) for r in observed)
        fr=sum(bool(indexed.get(c['trial_id'],{}).get('false_refusal')) for c in answerable)
        fp=sum(bool(indexed.get(c['trial_id'],{}).get('fp')) for c in traps)
        dnf=sum(r.get('status')!='ok' or r.get('answer_source')=='missing' for r in observed)
        numeric=sum(bool(indexed.get(c['trial_id'],{}).get('grounded_financial_correctness')) for c in answerable)
        trapwins=sum(bool(indexed.get(c['trial_id'],{}).get('grounded_financial_correctness')) for c in traps)
        usage=sum(bool((r.get('tokens') or {}).get('complete')) for r in observed)
        return {'scheduled':len(cells),'observed':len(observed),'pending':len(cells)-len(observed),
          'automatic_strict_wins':sum(bool(r.get('automatic_success',r.get('success'))) for r in observed),'automatic_financial_wins':sum(bool(r.get('automatic_grounded_financial_correctness',r.get('grounded_financial_correctness'))) for r in observed),'manual_financial_rejections':sum(bool(r.get('manual_financial_rejection')) for r in observed),'strict_grounded_success':strict,'strict_rate':strict/len(cells) if cells else None,
          'grounded_financial_correctness':finance,'grounded_financial_rate':finance/len(cells) if cells else None,
          'answerable_scheduled':len(answerable),'trap_scheduled':len(traps),'answerable_grounded':numeric,'trap_grounded':trapwins,
          'raw_contract_valid':sum(bool(r.get('public_contract_valid')) for r in observed),'dnf':dnf,
          'false_refusals':fr,'false_refusal_rate_scheduled':fr/len(answerable) if answerable else None,
          'false_positives':fp,'false_positive_rate_scheduled':fp/len(traps) if traps else None,
          'fabricated_evidence_accepted':sum(bool(r.get('success')) and not bool(r.get('evidence_grounded')) for r in observed),
          'evidence_grounded':sum(bool(r.get('evidence_grounded')) for r in observed),
          'usage_complete':usage,'usage_partial_or_missing':len(observed)-usage,
          'wall_ms_observed_all_attempts':sum(r.get('wall_ms',0) for r in observed),
          'first_attempt_completed':sum(bool(r.get('first_attempt_completed')) for r in observed),
          'native_completed':sum(bool(r.get('native_completed')) for r in observed),
          'transport_recovered':sum(bool(r.get('transport_recovered')) for r in observed),
          'latency_all_observed_trials_ms':{'p50':statistics.median([r.get('wall_ms',0) for r in observed]) if observed else None,'p90':sorted(r.get('wall_ms',0) for r in observed)[max(0,math.ceil(.9*len(observed))-1)] if observed else None}}
    for arm in settings['arms']:
        cells=[c for c in schedule if c['arm']==arm]; metrics=counts(cells)
        metrics['per_level']={level:counts([c for c in cells if taskmeta[c['task']].get('level')==level]) for level in sorted({taskmeta[c['task']].get('level','?') for c in cells})}
        metrics['per_family']={family:counts([c for c in cells if taskmeta[c['task']].get('family')==family]) for family in sorted({taskmeta[c['task']].get('family','?') for c in cells})}
        tasks=sorted({c['task'] for c in cells}); repeats=settings['runs']
        metrics['stable']={'label':f'{repeats}/{repeats}','scheduled_tasks':len(tasks),'strict_all_repeats':sum(all(indexed.get(c['trial_id'],{}).get('success',False) for c in cells if c['task']==t) for t in tasks),'grounded_all_repeats':sum(all(indexed.get(c['trial_id'],{}).get('grounded_financial_correctness',False) for c in cells if c['task']==t) for t in tasks)}
        metrics['operational']=operational([r for r in rows if r['arm']==arm], contracts)
        result['arms'][arm]=metrics
    return result


def paired(rows, candidate='opentrading_finance', controls=('opentrading_baseline','opencode','dsh'), draws=10000, clusters=None):
    output=[]
    by={}
    for row in rows:by.setdefault((row['task'],row['arm']),[]).append(row)
    for control in controls:
        tids=sorted({t for t,a in by if a==candidate}&{t for t,a in by if a==control})
        for endpoint in ('success','grounded_financial_correctness'):
            ds=[statistics.mean(bool(r.get(endpoint)) for r in by[t,candidate])-statistics.mean(bool(r.get(endpoint)) for r in by[t,control]) for t in tids]
            if not ds:continue
            rng=random.Random(20261108);n=len(ds); observed=statistics.mean(ds)
            bs=sorted(statistics.mean(rng.choices(ds,k=n)) for _ in range(draws))
            p=(1+sum(statistics.mean(d*rng.choice((-1,1)) for d in ds)>=observed-1e-12 for _ in range(draws)))/(draws+1)
            groups={}
            for tid,delta in zip(tids,ds):groups.setdefault((clusters or {}).get(tid,tid),[]).append(delta)
            grouped=[statistics.mean(x) for x in groups.values()];rngcluster=random.Random(20261108)
            clusterbs=sorted(statistics.mean(rngcluster.choices(grouped,k=len(grouped))) for _ in range(draws))
            output.append({'payload_sensitivity':{'clusters':len(grouped),'difference_equal_cluster_weight':statistics.mean(grouped),'ci95':[clusterbs[int(draws*.025)],clusterbs[min(draws-1,int(draws*.975))]]},'candidate':candidate,'control':control,'endpoint':endpoint,'tasks':n,'difference':observed,'ci95_task_cluster':[bs[int(draws*.025)],bs[min(draws-1,int(draws*.975))]],'p_one_sided_task_signflip':p})
    ranked=sorted(output,key=lambda x:x['p_one_sided_task_signflip']);running=0
    for i,item in enumerate(ranked):
        running=max(running,min(1,(len(ranked)-i)*item['p_one_sided_task_signflip']));item['p_holm_within_model']=running
    return output


def operational(rows, contracts):
    """Read recorded artifacts only. No inferred missing usage or causal uptake."""
    provider=[];source=[];derived=[];native=[];events=[];coverage=[];output_matches=0
    def load(path):
        if not path or not Path(path).exists():return []
        raw=Path(path).read_bytes();lines=raw.splitlines(keepends=True);result=[]
        for index,line in enumerate(lines):
            if not line.strip():continue
            try:item=json.loads(line)
            except (ValueError,UnicodeError):
                if index==len(lines)-1 and not line.endswith(b'\n'):break # retained partial suffix, never treated as completed execution
                raise ValueError('Corrupt nonterminal telemetry journal')
            result.append(item)
        return result
    for row in rows:
        trialsource=[];trialderived=[]
        for attempt in row.get('attempts',[]):
            provider+=load(attempt.get('provider_ledger'))
            ledger=load(attempt.get('ledger_path'));source += [x for x in ledger if x.get('tool') not in ('analytics_compute','analytics_calculate')];trialsource+=ledger
            trialderived += [x for x in ledger if x.get('tool') in ('analytics_compute','analytics_calculate')]
            n=load(attempt.get('native_derived_ledger'));native+=n
            trialderived += [x for x in n if x.get('tool') in ('calculate','compute')]
            path=attempt.get('log_path')
            if path and Path(path).exists():
                for line in Path(path).read_text(errors='replace').splitlines():
                    try:item=json.loads(line)
                    except ValueError:continue
                    if isinstance(item,dict):events.append(item)
        derived+=trialderived
        required=contracts.get(row['task'],{}).get('required_payload_keys',[])
        got={x.get('matched_entry_id') for x in trialsource if x.get('status')=='ok'}
        # Legacy pilot tasks name the key by tool ("financial_statements") while the ledger records "financial_statements:0".
        hit=lambda k:k in got or any(str(g).startswith(k+':') for g in got)
        coverage.append({'task':row['task'],'arm':row.get('arm'),'required':len(required),'retrieved':sum(hit(k) for k in required),'complete':bool(required) and all(hit(k) for k in required)})
        # Uptake is numeric output agreement, not a claim about hidden reasoning.
        ans=row.get('_answer')
        if ans is None and row.get('answer_path') and Path(row['answer_path']).exists():ans=json.loads(Path(row['answer_path']).read_text())
        def numbers(v):
            if isinstance(v,dict):return [n for k,x in v.items() if k not in ('evidence','source_evidence') for n in numbers(x)]
            if isinstance(v,list):return [n for x in v for n in numbers(x)]
            return [v] if isinstance(v,(int,float)) and not isinstance(v,bool) else []
        returned=numbers(ans)
        for d in trialderived:
            v=(d.get('derivation') or (d.get('result') if isinstance(d.get('result'),dict) else {}).get('derived_result') or {}).get('value')
            output_matches+=d.get('status')=='ok' and isinstance(v,(int,float)) and any(math.isclose(v,x,rel_tol=1e-6,abs_tol=1e-6) for x in returned)
    req=sum(x['required'] for x in coverage);ret=sum(x['retrieved'] for x in coverage)
    known=[x['usage'] for x in provider if isinstance(x.get('usage'),dict) and all(isinstance(x['usage'].get(k),int) for k in ('prompt_tokens','completion_tokens'))]
    failure={}
    for x in provider:
        if x.get('status')!=200:
            key=(x.get('error_origin') or 'unknown')+':'+str(x.get('error') or x.get('status'));failure[key]=failure.get(key,0)+1
    repair=[e for e in events if 'repair' in str(e.get('phase','')) or 'correction' in str(e.get('phase',''))]
    return {'required_data_coverage':{'required_entries':req,'retrieved_entries':ret,'rate':ret/req if req else None,'complete_trials':sum(x['complete'] for x in coverage),'trial_details':coverage},
      'computation':{'attempts':len(derived),'successes':sum(x.get('status')=='ok' for x in derived),'native_attempts':sum(x.get('tool') in ('calculate','compute') for x in native),'common_attempts':sum(x.get('tool') in ('analytics_compute','analytics_calculate') for x in derived),'observed_output_value_matches':output_matches,'uptake_definition':'successful derivation numeric output matches one final numeric claim; not causal attribution'},
      'repair':{'phase_events':len(repair),'local_rejections':sum(bool(e.get('localRejection')) or e.get('type')=='local_rejection' for e in events),'execution_events':sum(e.get('type')=='tool-start' and ('repair' in str(e.get('phase','')) or 'correction' in str(e.get('phase',''))) for e in events)},
      'source_lineage':{'source_attempts':len(source),'source_successes':sum(x.get('status')=='ok' for x in source),'derived_attempts':len(derived),'native_ledger_events':len(native)},
      'provider':{'gateway_attempt_rows':len(provider),'actual_upstream_attempts':sum(bool(x.get('upstream_attempted')) for x in provider),'logical_requests':len({(str(x.get('native_request_capture',{}).get('path','')).split('/provider-captures/')[0],x.get('logical_request_id',x.get('index'))) for x in provider}),'usage_known_attempts':len(known),'upstream_usage_unknown_attempts':sum(bool(x.get('upstream_attempted')) and not (isinstance(x.get('usage'),dict) and all(isinstance(x['usage'].get(k),int) and not isinstance(x['usage'].get(k),bool) for k in ('prompt_tokens','completion_tokens'))) for x in provider),'observed_input_lower_bound':sum(x['prompt_tokens'] for x in known),'observed_output_lower_bound':sum(x['completion_tokens'] for x in known),'reserved_tokens_not_observed_usage':sum(x.get('token_reservation',0) for x in provider),'failure_stages':failure,
      # OpenRouter usage.cost (authoritative billing, config cost_reporting); attempts without it stay counted as unknown.
      'usage_cost_usd':round(sum(float(x['usage']['cost']) for x in provider if isinstance(x.get('usage'),dict) and isinstance(x['usage'].get('cost'),(int,float))),6),
      'usage_cost_unknown_attempts':sum(bool(x.get('upstream_attempted')) and not (isinstance(x.get('usage'),dict) and isinstance(x['usage'].get('cost'),(int,float))) for x in provider)}}
