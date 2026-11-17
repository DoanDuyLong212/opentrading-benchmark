"""Original v4.2/v4.3 corpus and configuration contracts; requires original snapshots."""
import json, sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
LEGACY=ROOT.parent/'finance-v43-study'
sys.path.insert(0,str(ROOT/'tools'))
from mcp_snapshot_server import digest
from v43_gate import registered_settings, ARMS, MODELS

def test_two_registered_model_caps_and_four_conditions_have_fixed_schedule():
    from run_manifest import build_schedule
    for filename,stratum in [('bench_config.json','bolt'),('bench_config_deepseek.json','deepseek')]:
        config=json.loads((LEGACY/'tools'/filename).read_text());s=registered_settings(config)
        assert s['model']==MODELS[stratum] and s['arms']==ARMS
        assert s['max_requests']==24 and s['max_total_tokens']==48000 and s['max_output_tokens']==2048
        assert s['retry']==0 and s['effort']=='none'
        assert config['allowed_inference_splits']==['smoke'] and config['runs_pilot']==0
        assert s['split']=='smoke'  # v4.3 was explicitly smoke-only, unlike v4.4.
        schedule=build_schedule(['smoke-quote-01','smoke-agg-01','smoke-trap-01'],ARMS,2,20261105)
        assert len(schedule)==24
        assert {a:sum(i['arm']==a for i in schedule) for a in ARMS}==dict.fromkeys(ARMS,6)
        invalid=dict(config,provider_timeout_s=46)
        with pytest.raises(ValueError,match='timeout'):registered_settings(invalid)


def test_all_corpus_gold_and_primary_graders_remain_byte_exact_v42():
    baseline=ROOT.parent/'finance-v42-study'
    for source in (baseline/'tasks').rglob('*'):
        if source.is_file() and '__pycache__' not in source.parts and source.suffix in {'.json','.py','.md','.toml'}:
            assert source.read_bytes()==(LEGACY/source.relative_to(baseline)).read_bytes(),str(source)
    for name in ['frozen_v3_grader.py','frozen_v41_grader.py','public_response_contract.py']:
        assert (baseline/'tools'/name).read_bytes()==(LEGACY/'tools'/name).read_bytes()


def test_seal_creates_both_model_manifests_before_inference_and_detects_drift(tmp_path,monkeypatch):
    import shutil,run_manifest,v43_gate
    study=tmp_path/'study';(study/'tools').mkdir(parents=True);(study/'plans').mkdir()
    for name in ['smoke-quote-01','smoke-agg-01','smoke-trap-01']:
        shutil.copytree(LEGACY/'tasks/smoke'/name,study/'tasks/smoke'/name)
    for name in ['bench_config.json','bench_config_deepseek.json']:
        fixture=json.loads((LEGACY/'tools'/name).read_text());fixture['experiment_protocol']='plans/2026-11-06-v43-evidence-acquisition-study.md'
        (study/'tools'/name).write_text(json.dumps(fixture))
    shutil.copy(LEGACY/'plans/2026-11-06-v43-evidence-acquisition-study.md',study/'plans')
    monkeypatch.setattr(v43_gate,'ROOT',study);monkeypatch.setattr(run_manifest,'ROOT',study)
    monkeypatch.setattr(run_manifest,'harness_inventory',lambda _: {'offline':'locked fixture'})
    states=v43_gate.configuration_states();review=tmp_path/'engineering.json'
    auditor=tmp_path/'auditor.py';auditor.write_text('# offline reviewer fixture\n')
    review.write_text(json.dumps({'engineering_pass':True,'state_sha256':digest(states),
                                 'audit_script':{'path':str(auditor),'sha256':__import__('hashlib').sha256(auditor.read_bytes()).hexdigest()}}))
    path=tmp_path/'seal.json';receipt=v43_gate.seal(path,review)
    assert len(receipt['runs'])==2 and v43_gate.validate_seal(path)==receipt
    for item in receipt['runs']:
        manifest=json.loads((Path(item['out'])/'manifest.json').read_text())
        assert len(manifest['plan']['schedule'])==24
        assert manifest['plan']['settings']==registered_settings(manifest['plan']['config'])
        assert not list(Path(item['out']).glob('trials*'))
    config=study/'tools/bench_config_deepseek.json';config.write_text(config.read_text()+' ')
    with pytest.raises(ValueError,match='drift'):v43_gate.validate_seal(path)

