"""Offline trust-boundary tests; never install packages or call providers."""
import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location('bootstrap_under_test', Path(__file__).resolve().parents[1] / 'bootstrap_offline.py')
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


def test_corrupt_cache_is_rejected_without_network(tmp_path, monkeypatch):
    cached = tmp_path / 'archive.zip'
    cached.write_bytes(b'changed after download')
    monkeypatch.setattr(bootstrap.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('network forbidden'))
    with pytest.raises(ValueError, match='checksum mismatch'):
        bootstrap.obtain(tmp_path, cached.name, 'https://example.invalid/archive.zip', '0' * 64, False)


def test_offline_cache_miss_never_attempts_network(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('network forbidden'))
    with pytest.raises(ValueError, match='offline cache missing'):
        bootstrap.obtain(tmp_path, 'missing', 'https://example.invalid/missing', '0' * 64, True)


def test_tree_digest_detects_dependency_mutation_and_symlink_escape(tmp_path):
    modules = tmp_path / 'modules'
    modules.mkdir()
    dependency = modules / 'dependency.js'
    dependency.write_text('trusted')
    before = bootstrap.tree_digest(modules)
    dependency.write_text('tampered')
    assert bootstrap.tree_digest(modules) != before
    (modules / 'external').symlink_to(tmp_path / 'outside')
    with pytest.raises(ValueError, match='escapes tree'):
        bootstrap.tree_digest(modules)


def test_clean_setup_environment_does_not_inherit_provider_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'synthetic-secret-do-not-forward')
    monkeypatch.setenv('NVIDIA_API_KEY', 'synthetic-secret-do-not-forward')
    env = bootstrap.clean_environment(tmp_path)
    assert not any('KEY' in name for name in env)
    assert env['HOME'] == str(tmp_path / '.home')
    assert env['NPM_CONFIG_USERCONFIG'] != env['NPM_CONFIG_GLOBALCONFIG']


def test_installation_receipt_cannot_authorize_changed_binary(tmp_path, monkeypatch):
    monkeypatch.setattr(bootstrap, 'specification', lambda: {'artifacts': {'bun': {'binary_sha256': '0' * 64}}})
    path = tmp_path / 'bun/bin/bun'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'untrusted executable')
    (tmp_path / 'toolchain-receipt.json').write_text('{"sha256":"attacker assertion"}')
    with pytest.raises(ValueError, match='differs from trusted distribution'):
        bootstrap.verify_installation(tmp_path)
