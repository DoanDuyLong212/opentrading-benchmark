"""S reversal, separate financial denominators, immutable historical pruning."""
import hashlib,json,subprocess,sys
from pathlib import Path
import pytest
STUDY=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(STUDY/'tools'))
import judge_primary as jp
import metrics
import v45_metrics
from clock_policy import comparative_eligible
from prune_saturated_20261116 import RECEIPT,PRUNE_SHA256,validate_prune
from protocol_compat import FINANCIAL_PROTOCOL
from run_manifest import digest_json


def cohort(tmp_path,tasks=None):
    schedule,rows=[],[]
    tmp_path.mkdir(parents=True,exist_ok=True)
    tasks=tasks or ['fin-l1-synthetic','fin-s1-synthetic','fin-s2-buy-synthetic']
    for task in tasks:
        for arm in ('a','b'):
            cell=dict(trial_id=task+'__'+arm+'__r1',task=task,arm=arm,run=1)
            schedule.append(cell)
            win=(arm=='a')==task.startswith('fin-l')
            rows.append(dict(cell,model='offline',success=win,grounded_financial_correctness=win,
                             status='ok',semantic_correctness=win,answer_source='final',wall_ms=1,
                             tokens={'input':10,'output':1,'complete':True},fp=0,attempts=[],mcp_calls=0))
    plan={'settings':{'model':'offline','arms':['a','b'],'runs':1,'split':'devsmoke'},
          'config':{'protocol':FINANCIAL_PROTOCOL,'price_per_1m':{'input':1,'output':1}},
          'schedule':schedule,'tasks':{t:'synthetic' for t in tasks},
          'task_contracts':{t:{'scoring':'value','answerable_fields':[]} for t in tasks}}
    manifest={'plan':plan,'fingerprint':digest_json(plan)}
    for row in rows:row['manifest_sha256']=manifest['fingerprint']
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    (tmp_path/'trials.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    return rows,manifest


def test_reversal_cost_and_manifest_denominators(tmp_path):
    rows,manifest=cohort(tmp_path)
    original=(tmp_path/'manifest.json').read_bytes()
    summary=metrics.build_summary(str(tmp_path))
    assert summary['n_trials']==2 and summary['all_observed_trials']==6
    assert summary['completion']['scheduled_trials']==2
    assert summary['arms']['a']['dnf']['success_all']==1
    assert summary['arms']['b']['dnf']['success_all']==0
    assert summary['arms']['a']['cost']['cost_total']==pytest.approx(11/1e6)
    diagnostic=summary['safety_diagnostic']
    assert diagnostic['n_trials']==4 and diagnostic['completion']['scheduled_trials']==4
    assert diagnostic['arms']['b']['dnf']['success_all']==1
    assert diagnostic['arms']['a']['cost']['cost_total']==pytest.approx(22/1e6)
    assert diagnostic['paired']=={}
    assert summary['financial_v45']['arms']['a']['scheduled']==1
    assert diagnostic['financial_v45']['arms']['b']['scheduled']==2
    assert 'paired_task_cluster' not in diagnostic['financial_v45']
    assert (tmp_path/'manifest.json').read_bytes()==original
    direct=v45_metrics.summarize(rows,manifest,STUDY)
    assert direct['arms']['a']['scheduled']==1
    assert direct['safety_diagnostic']['arms']['b']['scheduled']==2
    assert all(c['difference']==1 for c in v45_metrics.paired(rows,candidate='a',controls=('b',),draws=20))


def test_judge_all_s_ignored_even_if_old_row_claims_eligible():
    base=dict(scoring='value',dnf=False,dnf_infra=False,fp=False,false_refusal=False,
              judge_verdict='correct',numeric_gate=True,manual_rejected=False,
              strict_success=True,raw_format_valid=True,comparative_eligible=True)
    recs=[]
    for task in ('fin-l1-test','fin-s1-test','fin-s2-test','fin-s3-test'):
        for arm in ('a','b'):
            recs.append(dict(base,task=task,arm=arm,stratum='core' if task.startswith('fin-l') else 'safety',
                             tier='L1' if task.startswith('fin-l') else task[4:6].upper(),
                             primary=(arm=='a')==task.startswith('fin-l')))
    summary=jp.summarize(recs,'b',20)
    assert summary['a']['primary_rate']==1 and summary['b']['primary_rate']==0
    assert summary['a']['scheduled']==1
    assert jp.bootstrap(recs,'a','b',20)['diff_vs_b']==1
    assert jp.by_stratum(recs,'b',20)['core']['arms']['a']['scheduled']==1
    assert jp.by_stratum(recs,'b',20,diagnostic=True)['safety']['arms']['a']['scheduled']==3
    assert not comparative_eligible('alias',{'stratum':'safety'})
    # amendment 2026-11-24 (f): only stratum safety and the retired S1/S2-buy names are excluded;
    # the kept S2/S3 tasks are stratum robustness and pooled.
    assert comparative_eligible('alias',{'tier':'S2','stratum':'robustness'})
    assert not comparative_eligible('fin-s1-alias',{'level':'S1'})


def write_task_meta(root, split, task, gold):
    target = Path(root)/'tasks'/split/task/'solution'
    target.mkdir(parents=True)
    (target/'gold.json').write_text(json.dumps(gold))


def test_eligibility_uses_task_metadata_not_task_id(tmp_path, monkeypatch):
    import clock_policy
    write_task_meta(tmp_path, 'devsmoke', 'dev-alias-001', {'stratum': 'safety', 'tier': 'S1'})
    write_task_meta(tmp_path, 'devsmoke', 'dev-alias-002', {'stratum': 'compute', 'tier': 'C1'})
    monkeypatch.setattr(clock_policy, 'STUDY_ROOT', tmp_path)
    assert not comparative_eligible('dev-alias-001')
    assert comparative_eligible('dev-alias-002')
    assert not comparative_eligible('dev-fin-s1-copy')
    assert comparative_eligible('fin-l1-synthetic')


def test_dev_lineage_cycles_terminate(tmp_path, monkeypatch):
    import clock_policy
    root = tmp_path
    for task, origin in (('dev-self', 'dev-self'), ('dev-loop-a', 'dev-loop-b'), ('dev-loop-b', 'dev-loop-a')):
        d = root/'tasks'/'devsmoke'/task
        (d/'solution').mkdir(parents=True)
        (d/'solution'/'gold.json').write_text(json.dumps({'stratum': None, 'tier': None}))
        (d/'development-lineage.json').write_text(json.dumps({'origin_task_id': origin}))
    monkeypatch.setattr(clock_policy, 'STUDY_ROOT', root)
    assert comparative_eligible('dev-self') and comparative_eligible('dev-loop-a')


def test_metadata_safety_is_authoritative_over_stale_record(tmp_path, monkeypatch):
    import clock_policy
    write_task_meta(tmp_path, 'devsmoke', 'dev-alias-001', {'stratum': 'safety', 'tier': 'S1'})
    monkeypatch.setattr(clock_policy, 'STUDY_ROOT', tmp_path)
    assert not comparative_eligible('dev-alias-001', {'stratum': 'core', 'tier': 'L1'})


def test_paired_statistics_excludes_safety_alias(tmp_path, monkeypatch):
    import clock_policy
    write_task_meta(tmp_path, 'devsmoke', 'dev-alias-001', {'stratum': 'safety', 'tier': 'S1'})
    monkeypatch.setattr(clock_policy, 'STUDY_ROOT', tmp_path)
    rows, _ = cohort(tmp_path/'run', tasks=['fin-l1-synthetic', 'dev-alias-001'])
    paired = metrics.paired_statistics(rows, expected_runs=1)
    assert paired[0]['paired_tasks'] == 1


def test_summary_excludes_safety_alias(tmp_path, monkeypatch):
    import clock_policy
    write_task_meta(tmp_path, 'devsmoke', 'dev-alias-001', {'stratum': 'safety', 'tier': 'S1'})
    monkeypatch.setattr(clock_policy, 'STUDY_ROOT', tmp_path)
    cohort(tmp_path/'run', tasks=['fin-l1-synthetic', 'dev-alias-001'])
    summary = metrics.build_summary(str(tmp_path/'run'))
    assert summary['n_trials'] == 2 and summary['all_observed_trials'] == 4
    assert summary['safety_diagnostic']['n_trials'] == 2


def test_prune_hash_tamper_and_nondestructive_cli(tmp_path):
    before=RECEIPT.read_bytes()
    assert validate_prune()['valid']
    changed=tmp_path/'PRUNE.json';data=json.loads(before);data['dropped'][0]='different'
    changed.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='hash'):validate_prune(changed)
    hashes=lambda:{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (STUDY/'tasks').glob('*/*/task.toml')}
    task_hashes=hashes()
    result=subprocess.run([sys.executable,str(STUDY/'tools/prune_saturated_20261116.py'),'--dry-run'],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['mutation_performed'] is False
    assert RECEIPT.read_bytes()==before
    assert hashlib.sha256(before).hexdigest()==PRUNE_SHA256
    assert task_hashes==hashes()


def test_dropped40_source_receipts():
    audit=json.loads((STUDY/'audits/methodology-2026-11-16/or16-dropped40-evidence.json').read_text())
    artifact=STUDY/'audits/methodology-2026-11-16/or16-dropped40-evidence.json'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()=='43db6d196098dbbe639075a136cba5a50df1d97224e61243a0b6417d274bc271'
    assert set(audit['source_sha256'])=={'manifest.json','trials.jsonl','judge-primary.jsonl'}
    assert all(len(sha)==64 for sha in audit['source_sha256'].values())
    assert len(audit['rows'])==240
    assert len({r['trial_id'] for r in audit['rows']})==240
    assert all(r['trials']==80 and r['primary_wins']==80 for r in audit['arms'].values())
    assert audit['cost_type'].startswith('scenario_estimates_only')
    assert all(r['cost'] is None and r['token_complete_trials']==80 for r in audit['arms'].values())
    assert all(r['cost_scenarios']['inclusive']['coverage']==1 for r in audit['arms'].values())


def test_cohort_completion_not_promoted_when_s_pending(tmp_path):
    rows,manifest=cohort(tmp_path)
    rows=[r for r in rows if r['task'].startswith('fin-l')]
    (tmp_path/'trials.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    summary=metrics.build_summary(str(tmp_path))
    assert summary['completion']['analysis_complete'] is True
    assert summary['completion']['complete'] is False
    assert summary['cohort_complete'] is False
    assert summary['financial_v45']['complete'] is False
    assert summary['financial_v45']['analysis_complete'] is True
    direct=v45_metrics.summarize(rows,manifest,STUDY)
    assert direct['complete'] is False and direct['analysis_complete'] is True
