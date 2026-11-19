"""Offline authorization regression tests: a blocked CLI never reaches dispatch."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import run_benchmark as rb
from v47_dev_gate import tree_hash, validate_dev_task


@pytest.mark.parametrize('split', ['main', 'holdout', 'pilot', 'smoke'])
@pytest.mark.parametrize('resume', [False, True])
@pytest.mark.parametrize('seal', [None, 'missing-seal.json', 'pretend-seal.json'])
def test_cli_dev_rejects_before_config_or_dispatch(tmp_path, split, resume, seal):
    # Poison config/runner import proves rejection occurs before provider/native setup.
    (tmp_path/'runners').mkdir()
    (tmp_path/'runners/__init__.py').write_text("raise AssertionError('native dispatch reached')")
    pretend = tmp_path/'pretend-seal.json'
    pretend.write_text(json.dumps({'engineering_approved': True}))
    cmd = [sys.executable, str(TOOLS/'run_benchmark.py'), '--split', split,
           '--config', str(tmp_path/'missing-config'), '--out', str(tmp_path/'out'),
           '--tasks', '../holdout/forbidden', '--retry', '0']
    if resume:
        cmd.append('--resume')
    if seal:
        cmd.extend(['--v45-seal', str(tmp_path/seal)])
    result = subprocess.run(cmd, env={**os.environ, 'BENCH_V47_DEV': '1',
                                    'PYTHONPATH': str(tmp_path)}, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'permits devsmoke only' in result.stderr
    assert 'missing-config' not in result.stderr
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('resume', [False, True])
def test_cli_valid_devsmoke_listing(tmp_path, resume):
    cmd = [sys.executable, str(TOOLS/'run_benchmark.py'), '--split', 'devsmoke',
           '--tasks', 'dev-fin-m1-screen-502', '--list-only', '--out', str(tmp_path/'out')]
    if resume:
        cmd.append('--resume')
    result = subprocess.run(cmd, env={**os.environ, 'BENCH_V47_DEV': '1'}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'dev-fin-m1-screen-502'
    assert not (tmp_path/'out').exists()


@pytest.mark.parametrize('split', ['main', 'holdout', 'pilot', 'devsmoke'])
@pytest.mark.parametrize('seal', [None, 'bad.json'])
def test_dev_off_preserves_seal_requirement(tmp_path, monkeypatch, split, seal):
    monkeypatch.delenv('BENCH_V47_DEV', raising=False)
    monkeypatch.setattr(rb, 'select_tasks', lambda *args: [str(Path(rb.ROOT)/'tasks/devsmoke/v45-dev-01-quote')])
    # Permit splits in config so the seal gate itself is exercised.
    cfg = rb.load_config()
    cfg['allowed_inference_splits'] = ['main', 'holdout', 'pilot', 'devsmoke']
    config = tmp_path/'config.json'
    config.write_text(json.dumps(cfg))
    monkeypatch.setattr(rb, 'run_trial', lambda *a, **kw: pytest.fail('provider dispatch'))
    monkeypatch.setattr(rb, 'run_memory_trial', lambda *a, **kw: pytest.fail('memory dispatch'))
    args = ['run_benchmark', '--split', split, '--config', str(config), '--out', str(tmp_path/'out'), '--retry', '0']
    if seal:
        (tmp_path/seal).write_text('{}')
        args += ['--v45-seal', str(tmp_path/seal)]
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises((ValueError, FileNotFoundError)):
        rb.main()


def fixture_task(tmp_path):
    task = tmp_path/'tasks/devsmoke/copy'
    task.mkdir(parents=True)
    (task/'instruction.md').write_text('fixture')
    (task/'development-lineage.json').write_text(json.dumps(dict(origin_split='main',
        origin_task_id='original', origin_sha256='a'*64, copy_sha256=tree_hash(task), reason='offline test')))
    return task


@pytest.mark.parametrize('nested', [False, True])
def test_symlink_cannot_read_holdout(tmp_path, nested):
    task = fixture_task(tmp_path)
    holdout = tmp_path/'tasks/holdout'
    holdout.mkdir()
    (holdout/'secret').write_text('never copied')
    if nested:
        (task/'environment').symlink_to(holdout, target_is_directory=True)
    else:
        task = task.parent/'alias'
        task.symlink_to(holdout, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        validate_dev_task(tmp_path, task)


def test_copy_tamper_and_holdout_origin_rejected(tmp_path):
    task = fixture_task(tmp_path)
    validate_dev_task(tmp_path, task)
    (task/'instruction.md').write_text('changed')
    with pytest.raises(ValueError, match='lineage'):
        validate_dev_task(tmp_path, task)
    p = task/'development-lineage.json'
    meta = json.loads(p.read_text())
    meta.update(origin_split='holdout', copy_sha256=tree_hash(task))
    p.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='lineage'):
        validate_dev_task(tmp_path, task)


@pytest.mark.parametrize('task_id', ['../main/fin-c4-stagger-425', '/tmp/alias', '..'])
def test_path_ids_rejected(monkeypatch, task_id):
    monkeypatch.setenv('BENCH_V47_DEV', '1')
    with pytest.raises(ValueError, match='plain names'):
        rb.select_tasks('devsmoke', tasks_filter=[task_id])


def test_direct_memory_dispatch_rejects_main(monkeypatch):
    monkeypatch.setenv('BENCH_V47_DEV', '1')
    with pytest.raises(ValueError, match='direct devsmoke'):
        rb.run_memory_trial('opentrading', 'unused', str(Path(rb.ROOT)/'tasks/main/fin-m1-screen-502'), 'unused', 1, 'unused')


def test_legacy_memory_execute_blocked(tmp_path):
    result = subprocess.run([sys.executable, str(TOOLS/'run_memory_benchmark.py'), '--execute', '--out', str(tmp_path/'out')],
        env={**os.environ, 'BENCH_V47_DEV': '1'}, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'legacy memory execution is forbidden' in result.stderr
    assert not (tmp_path/'out').exists()


def test_devsmoke_inference_reaches_manifest_without_seal(tmp_path, monkeypatch):
    import run_manifest
    import v45_gate
    monkeypatch.setenv('BENCH_V47_DEV', '1')
    def reached(*args, **kwargs):
        raise RuntimeError('validated-devsmoke-reached-manifest')
    monkeypatch.setattr(run_manifest, 'prepare_manifest', reached)
    monkeypatch.setattr(v45_gate, 'authorize_run', lambda *a: pytest.fail('devsmoke requested seal'))
    monkeypatch.setattr(sys, 'argv', ['run_benchmark', '--split', 'devsmoke', '--retry', '0',
        '--tasks', 'dev-fin-m1-screen-502', '--out', str(tmp_path/'out')])
    with pytest.raises(RuntimeError, match='validated-devsmoke-reached-manifest'):
        rb.main()


@pytest.mark.parametrize('split', ['main', 'holdout', 'pilot', 'devsmoke'])
def test_without_dev_routes_to_seal_authorizer(tmp_path, monkeypatch, split):
    import v45_gate
    monkeypatch.delenv('BENCH_V47_DEV', raising=False)
    cfg = rb.load_config()
    cfg['allowed_inference_splits'] = ['main', 'holdout', 'pilot', 'devsmoke']
    config = tmp_path/'config.json'
    config.write_text(json.dumps(cfg))
    monkeypatch.setattr(rb, 'select_tasks', lambda *a: [str(Path(rb.ROOT)/'tasks/devsmoke/v45-dev-01-quote')])
    def authorize(path, out, config, settings, tasks, resume):
        assert path == 'approved-seal'
        assert settings['split'] == split
        assert resume is True
        raise RuntimeError('seal-authorization-reached')
    monkeypatch.setattr(v45_gate, 'authorize_run', authorize)
    monkeypatch.setattr(sys, 'argv', ['run_benchmark', '--split', split, '--retry', '0', '--resume',
        '--v45-seal', 'approved-seal', '--config', str(config), '--out', str(tmp_path/'out')])
    with pytest.raises(RuntimeError, match='seal-authorization-reached'):
        rb.main()
