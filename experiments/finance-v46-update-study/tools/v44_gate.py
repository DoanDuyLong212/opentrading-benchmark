#!/usr/bin/env python3
"""Predeclared v44 two-model seal and separate diagnostic quality gate; no inference."""
import argparse
import json
from pathlib import Path
from run_manifest import (ROOT, digest_json, freeze_state, prepare_manifest, task_eligibility,
                          validate_trial_rows, write_exclusive, hash_file)

ARMS = ['opentrading_baseline', 'opentrading_finance', 'opencode', 'dsh']
TASKS = ['smoke-agg-01', 'smoke-quote-01', 'smoke-trap-01']
STRATA = [('bolt', 'bench_config.json', 'financial-v44-smoke-bolt-20261107-startupfix1'),
          ('deepseek', 'bench_config_deepseek.json', 'financial-v44-smoke-deepseek-20261107-startupfix1')]
MODELS = {'bolt': 'nvidia/nvidia/nemotron-3.5-bolt-e4b',
          'deepseek': 'nvidia/deepseek-ai/deepseek-v4.1-flash'}


def registered_settings(config, split='smoke'):
    stratum = config['model_stratum']
    if config['model'] != MODELS[stratum]:
        raise ValueError('Unregistered model stratum')
    if (config['provider_timeout_s'], config['trial_timeout_s']) != ((45,240) if stratum == 'bolt' else (240,900)):
        raise ValueError('Model-specific registered timeout changed')
    from experiment_conditions import CONDITIONS
    return {'split':split,'seed':20261105,'runs':2,'retry':0,'pause':2.0,
            'retry_backoff':4.0,'timeout':float(config['trial_timeout_s']),
            'effort':'none','max_requests':24,'max_output_tokens':2048,'max_total_tokens':48000,
            'model':config['model'],'arms':ARMS,'freeze_sha256':None,
            'provider_timeout_s':float(config['provider_timeout_s']),
            'conditions':{name:CONDITIONS[name] for name in ARMS},
            'clock_policy':'snapshot_as_of; OpenTrading native now pinned; other native clocks observed in wire capture',
            'quarantined_tasks':{p.name:task_eligibility(p)['exclusion_reason'] for p in sorted((ROOT/'tasks'/split).iterdir())
                                 if p.is_dir() and not task_eligibility(p)['confirmatory_eligible']},
            'include_quarantined':False}


def configuration_states():
    return {name:freeze_state(json.loads((ROOT/'tools'/filename).read_text()))
            for name,filename,_ in STRATA}


def validate_seal(path):
    receipt = json.loads(Path(path).read_text())
    if receipt.get('kind') != 'v44-shared-two-model-preinference-seal':
        raise ValueError('Not a v44 two-model seal')
    states = configuration_states()
    if receipt.get('states') != states or receipt.get('state_sha256') != digest_json(states):
        raise ValueError('v44 sealed source/config/task/runtime/protocol drift')
    engineering = receipt['engineering_review']
    if hash_file(engineering['path']) != engineering['sha256']:
        raise ValueError('Engineering review receipt changed')
    audit=receipt['audit_script']
    if hash_file(audit['path'])!=audit['sha256']:
        raise ValueError('Sealed independent auditor source changed')
    for item in receipt['runs']:
        manifest = json.loads((Path(item['out'])/'manifest.json').read_text())
        if manifest['fingerprint'] != item['manifest_sha256'] or digest_json(manifest['plan']) != item['manifest_sha256']:
            raise ValueError('Sealed schedule manifest changed')
    return receipt


def seal(path, engineering_path):
    engineering_path = Path(engineering_path).resolve()
    review = json.loads(engineering_path.read_text())
    states = configuration_states()
    # The independent/root review explicitly signs current shared state; no stale green log can authorize inference.
    if review.get('engineering_pass') is not True or review.get('state_sha256') != digest_json(states):
        raise ValueError('Fresh independent engineering review must pass and bind current two-model state_sha256')
    audit=review.get('audit_script') or {}
    if not audit.get('path') or hash_file(audit['path'])!=audit.get('sha256'):
        raise ValueError('Engineering approval must bind the final independent auditor source')
    runs = []
    for split in ('smoke','pilot'):
      paths = ([ROOT/'tasks/smoke'/name for name in TASKS] if split=='smoke' else [p for p in sorted((ROOT/'tasks/pilot').iterdir()) if p.is_dir() and task_eligibility(p)['confirmatory_eligible']])
      for name,filename,outname in STRATA:
          out = ROOT/'results'/outname.replace('-smoke-', '-'+split+'-')
          if out.exists() and any(out.iterdir()):
              raise ValueError('Pre-inference seal needs empty output paths')
          manifest = prepare_manifest(out, registered_settings(states[name]['config'],split), paths, states[name]['config'])
          runs.append({'split':split,'key':split+'-'+name,'stratum':name,'out':str(out),'config':str(ROOT/'tools'/filename),
                       'manifest_sha256':manifest['fingerprint'],'trials':24 if split=='smoke' else 176})
    value = {'kind':'v44-shared-two-model-preinference-seal','states':states,'state_sha256':digest_json(states),
             'engineering_review':{'path':str(engineering_path),'sha256':hash_file(engineering_path)},'audit_script':audit,'runs':runs}
    write_exclusive(path,value)
    return value


def diagnostic_quality(run):
    """Quality findings never change primary or substitute for independent audit controls."""
    from metrics import load_trials
    run=Path(run);manifest=json.loads((run/'manifest.json').read_text());rows=load_trials(run)
    if not validate_trial_rows(rows,manifest):
        raise ValueError('Diagnostic requires completed registered schedule')
    if len(rows)!=24 or set(manifest['plan']['tasks'])!=set(TASKS) or manifest['plan']['settings']!=registered_settings(manifest['plan']['config']):
        raise ValueError('Diagnostic schedule differs from registration')
    def numeric_receipt(row):
        for attempt in row.get('attempts',[]):
            ledger=attempt.get('ledger_path')
            if ledger and Path(ledger).is_file():
                for line in Path(ledger).read_text().splitlines():
                    call=json.loads(line)
                    if call.get('status')=='ok' and call.get('tool')=='vn_quote_history':return True
        return False
    passed=[]
    for arm in ARMS:
        if any(r['arm']==arm and r['task'] in {'smoke-quote-01','smoke-agg-01'} and r.get('success')
               and numeric_receipt(r) for r in rows):passed.append(arm)
    candidate=[r for r in rows if r['arm']=='opentrading_finance']
    from metrics import load_answer, is_false_refusal, is_answered
    for row in candidate:
        contract=manifest['plan']['task_contracts'][row['task']]
        row['_scoring']=contract['scoring'];row['_answerable_fields']=contract.get('answerable_fields',[])
        row['_answer']=load_answer(row)
    false_refusals=sum(is_false_refusal(r) for r in candidate)
    candidate_dnf=sum(not is_answered(r) for r in candidate)
    candidate_traps=sum(r.get('success') for r in candidate if r['task']=='smoke-trap-01')
    candidate_success=sum(bool(r.get('success')) for r in candidate)
    eligible=set(passed)==set(ARMS) and candidate_success>=4 and candidate_dnf==0 and candidate_traps==2 and false_refusals<=1
    return {'protocol':'v44-four-condition-numeric-diagnostic','model':manifest['plan']['settings']['model'],
            'n_started':len(rows),'numeric_canary_conditions':passed,'quality_pass':eligible,'candidate_success':candidate_success,'candidate_dnf':candidate_dnf,'candidate_false_refusals':false_refusals,'candidate_trap_correct':candidate_traps,
            'model_quality_failures':sum(not r.get('success') for r in rows),
            'dnf':sum(not is_answered(r) for r in rows),
            'note':'Independent actual receipt/control audit must also pass. Pilot requires this preregistered quality gate plus independent zero-fabrication/complete audit controls; no promotion.'}


def require_pilot_authorization(seal, item):
    from metrics import load_trials
    for prerequisite in [r for r in seal['runs'] if r['split']=='smoke']:
        prior=json.loads((Path(prerequisite['out'])/'v44-audit-controls.json').read_text())
        manifest=json.loads((Path(prerequisite['out'])/'manifest.json').read_text())
        if not validate_trial_rows(load_trials(prerequisite['out']),manifest) or prior.get('audit_controls_pass') is not True or prior.get('auditor_sha256')!=seal['audit_script']['sha256'] or prior.get('manifest_sha256')!=prerequisite['manifest_sha256'] or prior.get('trials_sha256')!=hash_file(Path(prerequisite['out'])/'trials.jsonl'):
            raise ValueError('Both registered smokes must finish independent audit before any pilot')
    smoke=next(r for r in seal['runs'] if r['split']=='smoke' and r['stratum']==item['stratum'])
    path=Path(smoke['out'])/'v44-audit-controls.json'
    receipt=json.loads(path.read_text())
    if receipt.get('manifest_sha256')!=smoke['manifest_sha256'] or receipt.get('trials_sha256')!=hash_file(Path(smoke['out'])/'trials.jsonl'):
        raise ValueError('Pilot smoke-control receipt no longer binds exact trials/manifest')
    if receipt.get('auditor_sha256')!=seal['audit_script']['sha256']:raise ValueError('Pilot receipt auditor differs from sealed source')
    if receipt.get('audit_controls_pass') is not True or receipt.get('zero_accepted_fabrication') is not True or receipt.get('smoke_financial_canary_pass') is not True:
        raise ValueError('Pilot requires independent audit, zero accepted fabrication and independent source-based financial canary')
    if not diagnostic_quality(smoke['out'])['quality_pass']:
        raise ValueError('Pilot blocked by preregistered model-specific smoke quality gate')
    return receipt


def main():
    ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
    sp=sub.add_parser('state');sp.add_argument('--output',required=True)
    sp=sub.add_parser('seal');sp.add_argument('--output',required=True);sp.add_argument('--engineering-review',required=True)
    sp=sub.add_parser('verify');sp.add_argument('--seal',required=True)
    sp=sub.add_parser('diagnostic');sp.add_argument('--run',required=True);sp.add_argument('--output',required=True)
    a=ap.parse_args()
    if a.command=='state':
        states=configuration_states();write_exclusive(a.output,{'states':states,'state_sha256':digest_json(states)})
    elif a.command=='seal':seal(a.output,a.engineering_review)
    elif a.command=='verify':validate_seal(a.seal)
    else:write_exclusive(a.output,diagnostic_quality(a.run))

if __name__=='__main__':main()
