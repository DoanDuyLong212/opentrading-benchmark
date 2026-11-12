"""Versioned v4.5 fail-closed run authorization and preregistered quality gates.
A complete audit is required in addition to aggregate quality; never promotes.
"""
from protocol_compat import FINANCIAL_PROTOCOL
import argparse,json
from pathlib import Path
from run_manifest import digest_json,hash_file,freeze_state,prepare_manifest,task_eligibility
ROOT=Path(__file__).resolve().parent.parent
PROTOCOL=FINANCIAL_PROTOCOL
ARMS=['opentrading_baseline','opentrading_finance','opencode','dsh']


def quality_gate(summary, audit, split):
    data=summary.get('financial_v45',{});arms=data.get('arms',{});b=arms.get('opentrading_finance',{});why=[]
    if not data.get('complete'):why.append('incomplete schedule')
    if not data.get('manual_financial_review',{}).get('review_complete') or data.get('manual_financial_review',{}).get('accepted_financial_fabrications')!=0:why.append('independent all-arm financial claim review pending/fabrication unknown')
    if not audit.get('pass') or audit.get('fabricated_evidence_accepted')!=0:why.append('independent instrumentation/financial audit not PASS or fabrication unknown')
    if not b:why.append('missing candidate')
    expected=24 if split=='devsmoke' else 44
    if b.get('scheduled')!=expected:why.append('wrong denominator')
    minimum={'grounded_financial_correctness':20,'answerable_grounded':14,'trap_grounded':6,'raw_contract_valid':23} if split=='devsmoke' else {'strict_grounded_success':33,'grounded_financial_correctness':35,'answerable_grounded':31,'trap_grounded':4}
    for field,n in minimum.items():
        if b.get(field,-1)<n:why.append(field+' below '+str(n))
    for field,limit in [('dnf',1),('false_refusals',2),('false_positives',0),('fabricated_evidence_accepted',0)]:
        if b.get(field,limit+1)>limit:why.append(field+' exceeds '+str(limit))
    controls=['opentrading_baseline'] if split=='devsmoke' else ['opentrading_baseline','opencode','dsh']
    for control in controls:
        other=arms.get(control,{})
        for metric in ['strict_grounded_success','grounded_financial_correctness']:
            margin=0 if split=='devsmoke' else 3
            if b.get(metric,-1)<other.get(metric,10**9)+margin:why.append(metric+' margin vs '+control)
        for field in ['dnf','false_refusals','false_positives']:
            if b.get(field,10**9)>other.get(field,-1):why.append(field+' regression vs '+control)
        if b.get('evidence_grounded',-1)<other.get('evidence_grounded',10**9):why.append('evidence regression vs '+control)
    if split=='devsmoke':
        families=b.get('per_family',{})
        for family in ['growth','margin','scale','ratio','aggregate','cross-source','chain']:
            if families.get(family,{}).get('answerable_grounded',0)<1:why.append('no numeric canary win '+family)
    return {'pass':not why,'reasons':why,'split':split,'candidate':'opentrading_finance','denominator':expected}


def validate_seal(path):
    seal=json.loads(Path(path).read_text())
    if seal.get('protocol')!=PROTOCOL or not seal.get('engineering_approved'):raise ValueError('v45 engineering seal missing')
    for path,sha in seal['protected_files'].items():
        if not Path(path).is_file() or hash_file(path)!=sha:raise ValueError('Sealed file drift: '+path)
    approved=json.loads(Path(seal['approval']).read_text())
    b0=seal.get('gate')=='b0_judge_primary'
    main_ok=b0 and seal.get('main_authorized_by_user') is True and approved.get('main_authorized_by_user') is True
    if seal.get('study_version')!='v4.6-update' or (seal.get('main_authorized_by_user') is not False and not main_ok):raise ValueError('Wrong study identity or unauthorized main')
    if seal.get('diagnostic_pilot_authorized') is not (approved.get('diagnostic_pilot_authorized') is True):raise ValueError('Diagnostic pilot authorization differs from protected approval')
    for item in seal['runs']:
        holdout_ok=main_ok and seal.get('holdout_authorized_by_user') is True and approved.get('holdout_authorized_by_user') is True
        if item.get('split') not in ('devsmoke','pilot') and not (main_ok and item.get('split')=='main') and not (holdout_ok and item.get('split')=='holdout'):raise ValueError('v4.6-update authorization permits smoke/pilot only')
        cfg=json.loads(Path(item['config']).read_text())
        if digest_json(freeze_state(cfg))!=item['state_sha256']:raise ValueError('v45 frozen source/task/runtime state changed')
    return seal


def require_audit(seal,model,split):
    selected=next(x for x in seal['runs'] if x['model']==model and x['split']==split)
    out=Path(selected['out']);audit=json.loads((out/'audit-v45.json').read_text());summary=json.loads((out/'summary.json').read_text())
    manifest=json.loads((out/'manifest.json').read_text())
    if audit.get('manifest_sha256')!=manifest['fingerprint']:raise ValueError('Audit wrong manifest')
    from v45_review import load_review
    from metrics import load_trials
    review_status,_=load_review(out,load_trials(out),manifest)
    if not review_status.get('review_complete') or summary.get('financial_v45',{}).get('manual_financial_review')!=review_status:raise ValueError('Reviewed summary missing/stale adjudication')
    gate=quality_gate(summary,audit,split)
    if not gate['pass']:raise ValueError('Quality gate blocked '+str(gate['reasons']))
    return gate


def require_diagnostic_smoke(seal,model):
    """Explicitly authorized feasibility pilot: quality gate remains unchanged FAIL."""
    item=next(x for x in seal['runs'] if x['model']==model and x['split']=='devsmoke')
    out=Path(item['out']);manifest=json.loads((out/'manifest.json').read_text())
    audit=json.loads((out/'audit-v45.json').read_text());summary=json.loads((out/'summary.json').read_text())
    from v45_review import load_review
    from metrics import load_trials
    rows=load_trials(out);review,_=load_review(out,rows,manifest)
    if not summary.get('financial_v45',{}).get('complete') or not audit.get('pass') or audit.get('manifest_sha256')!=manifest['fingerprint'] or audit.get('fabricated_evidence_accepted')!=0:raise ValueError('Diagnostic pilot requires complete independently audited same-model smoke')
    if not review.get('review_complete') or review.get('accepted_financial_fabrications')!=0 or summary.get('financial_v45',{}).get('manual_financial_review')!=review:raise ValueError('Diagnostic pilot requires current all-arm independent manual review and zero accepted fabrication')
    return True


def authorize_run(path,out,config,settings,tasks,resume):
    seal=validate_seal(path);selected=next((x for x in seal['runs'] if x['out']==str(Path(out).resolve()) and x['config']==str(Path(config).resolve())),None)
    if not selected or not resume or settings!=selected['settings'] or sorted(Path(t).name for t in tasks)!=selected['tasks']:raise ValueError('Run differs from registered v45 manifest')
    if selected['split']=='pilot':
        for model in sorted({x['model'] for x in seal['runs']}):
            # Every admitted/scheduled smoke audit must exist; blocked models have no score.
            item=next(x for x in seal['runs'] if x['model']==model and x['split']=='devsmoke')
            audit=json.loads((Path(item['out'])/'audit-v45.json').read_text())
            if not audit.get('pass'):raise ValueError('All admitted model smoke audits required before pilot')
        if seal.get('diagnostic_pilot_authorized') is True:require_diagnostic_smoke(seal,selected['model'])
        else:require_audit(seal,selected['model'],'devsmoke')
    if selected['split']=='main' and seal.get('gate')=='b0_judge_primary':
        # Main amendment 2026-11-10: B0-only judge-primary admission gate (no B1 superiority).
        from b0_gate import b0_gate
        require_diagnostic_smoke(seal,selected['model'])
        pilot=Path(next(x['out'] for x in seal['runs'] if x['model']==selected['model'] and x['split']=='pilot'))
        g=b0_gate(pilot,seal.get('judge_kappa_file'))
        if not g['pass']:raise ValueError('B0 judge-primary pilot gate blocked '+str(g['reasons']))
    elif selected['split']=='holdout':
        # Amendment 2026-11-11 (d/h): holdout once, only after a complete main cohort with audit PASS.
        main=Path(next(x['out'] for x in seal['runs'] if x['model']==selected['model'] and x['split']=='main'))
        audit=json.loads((main/'audit-v45.json').read_text()) if (main/'audit-v45.json').is_file() else {}
        summary=json.loads((main/'summary.json').read_text()) if (main/'summary.json').is_file() else {}
        if not audit.get('pass') or audit.get('fabricated_evidence_accepted')!=0 or not summary.get('financial_v45',{}).get('complete'):raise ValueError('Holdout requires the complete, audited main cohort')
        if not (Path(out)/'holdout-go.json').is_file():raise ValueError('Holdout requires the budget check receipt holdout-go.json')
    elif selected['split']=='main':
        require_audit(seal,selected['model'],'devsmoke');require_audit(seal,selected['model'],'pilot')
        pilot=Path(next(x['out'] for x in seal['runs'] if x['model']==selected['model'] and x['split']=='pilot'))
        review=json.loads((pilot/'pilot-review-approval.json').read_text())
        if review.get('approved') is not True or review.get('independent_manual_financial_audit_pass') is not True or not review.get('report_delivered_to_user') or not review.get('reviewer') or review.get('manifest_sha256')!=json.loads((pilot/'manifest.json').read_text())['fingerprint'] or review.get('report_sha256')!=hash_file(pilot/'PILOT-REPORT.md'):raise ValueError('Main awaits independent manual financial audit and delivered pilot report attestation')
    return selected


def build_settings(cfg,split):
    # v4.6-update (B1 retired 2026-11-10): a split-level arms override in the
    # config ('arms_<split>') replaces the default pilot arm set; main keeps
    # its registered 3-arm set. Every override is disclosed in the amendment.
    default_arms=['opentrading','opencode','dsh'] if split=='main' else ARMS
    arms=cfg.get('arms_'+split) or default_arms
    return {'split':split,'seed':20261108,'runs':2,'retry':0,'pause':float(cfg.get('request_interval_s',2)),'retry_backoff':4.0,'timeout':float(cfg['trial_timeout_s']),'effort':'none','max_requests':cfg['max_requests'],'max_output_tokens':cfg['max_output_tokens'],'max_total_tokens':cfg['max_total_tokens'],'model':cfg['model'],'arms':arms,'freeze_sha256':None,'provider_timeout_s':float(cfg['provider_timeout_s']),'conditions':{k:__import__('experiment_conditions').CONDITIONS[k] for k in arms},'clock_policy':'snapshot_as_of; OpenTrading native now pinned; other native clocks observed in wire capture','quarantined_tasks':{p.name:task_eligibility(p)['exclusion_reason'] for p in sorted((ROOT/'tasks'/split).iterdir()) if p.is_dir() and not task_eligibility(p)['confirmatory_eligible']},'include_quarantined':False}


def seal_runs(configs,out,approval,destination):
    approval=Path(approval).resolve();approved=json.loads(approval.read_text())
    if approved.get('approved') is not True:raise ValueError('Independent engineering approval required')
    runs=[];protected={str(approval):hash_file(approval)}
    for config in configs:
        config=Path(config).resolve();cfg=json.loads(config.read_text());state=digest_json(freeze_state(cfg))
        admission=approved.get('model_admission',{}).get(cfg['model'],{})
        if admission.get('approved') is not True or not admission.get('receipt'):raise ValueError('Exact model admission missing from engineering approval')
        receipt=Path(admission['receipt']).resolve()
        if not receipt.is_file() or hash_file(receipt)!=admission.get('sha256'):raise ValueError('Admission evidence changed')
        protected[str(receipt)]=hash_file(receipt)
        if state not in approved.get('freeze_state_sha256',[]):raise ValueError('Approval does not cover exact freeze state')
        splits=['devsmoke','pilot']+(['main'] if cfg.get('gate')=='b0_judge_primary' and approved.get('main_authorized_by_user') is True else [])
        for split in splits:
            settings=build_settings(cfg,split);tasks=[p for p in sorted((ROOT/'tasks'/split).iterdir()) if p.is_dir() and task_eligibility(p)['confirmatory_eligible']];runout=Path(out).resolve()/(cfg['model_stratum']+'-'+split)
            prepare_manifest(runout,settings,tasks,cfg,False)
            runs.append({'out':str(runout),'config':str(config),'model':cfg['model'],'split':split,'settings':settings,'tasks':[p.name for p in tasks],'state_sha256':state})
    gate=json.loads(Path(configs[0]).read_text()).get('gate') if configs else None
    if approved.get('judge_kappa_file'):protected[str(Path(approved['judge_kappa_file']).resolve())]=hash_file(approved['judge_kappa_file'])
    receipt={'study_version':'v4.6-update','main_authorized_by_user':bool(gate=='b0_judge_primary' and approved.get('main_authorized_by_user') is True),'gate':gate,'judge_kappa_file':approved.get('judge_kappa_file'),'diagnostic_pilot_authorized':approved.get('diagnostic_pilot_authorized') is True,'blocked_models':approved.get('blocked_models',{}),'protocol':PROTOCOL,'engineering_approved':True,'approval':str(approval),'protected_files':protected,'runs':runs}
    from run_manifest import write_exclusive
    write_exclusive(destination,receipt);return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',action='append',required=True);p.add_argument('--out',required=True);p.add_argument('--approval',required=True);p.add_argument('--seal',required=True);a=p.parse_args();print(json.dumps(seal_runs(a.config,a.out,a.approval,a.seal),indent=2))
if __name__=='__main__':main()
