"""Portable fixtures, byte-pinned Bun relocation, and data-only snapshot startup."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest

STUDY = Path(__file__).resolve().parents[2]


def test_bun_locator_checks_receipt_bytes_and_ignores_env_trust_override(tmp_path, monkeypatch):
    import trusted_bun
    binary = tmp_path/'relocated'/'bun'
    binary.parent.mkdir()
    binary.write_bytes(b'offline test executable fixture')
    expected = hashlib.sha256(binary.read_bytes()).hexdigest()
    tools = tmp_path/'study'/'tools'
    tools.mkdir(parents=True)
    (tools/'bench_config.json').write_text(json.dumps({'provider_options':{
        'native_bun_binary':'/unavailable/author/path', 'native_bun_sha256':expected}}))
    monkeypatch.setattr(trusted_bun, 'ROOT', tools.parent)
    monkeypatch.setenv('BENCH_BUN_BIN', str(binary))
    monkeypatch.setenv('BENCH_BUN_SHA256', 'untrusted override')
    assert trusted_bun.trusted_bun() == binary.resolve()
    binary.write_bytes(b'mutated binary')
    monkeypatch.setenv('BENCH_BUN_SHA256', hashlib.sha256(binary.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match='SHA256 mismatch'):
        trusted_bun.trusted_bun()


def test_snapshot_startup_does_not_import_historical_arithmetic_bridge():
    script = "import sys; sys.path.insert(0,sys.argv[1]); import mcp_snapshot_server; assert 'analytics_calculate' not in sys.modules; assert 'analytics_compute' not in sys.modules"
    result = subprocess.run([sys.executable,'-c',script,str(STUDY/'tools')], capture_output=True,text=True,timeout=30)
    assert result.returncode == 0, result.stderr


def test_synthetic_derived_fixture_is_exact_known_source():
    path=STUDY.parent/'finance-v46-update-study/tools/tests/fixtures/native-derived-synthetic.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == 'dcb1777e5e7b47460811a7fff347cbb15c1e805fb6313a9b8a81852783c3d695'
