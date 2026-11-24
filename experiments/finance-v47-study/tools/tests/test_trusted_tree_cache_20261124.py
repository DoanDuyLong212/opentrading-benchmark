"""DSH/node tree digest is verified once per process; any later change in the tree forces a full re-check."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bootstrap_offline  # noqa: E402
import trusted_toolchain as tt  # noqa: E402


def test_tree_verified_once_then_rechecked_on_change(tmp_path, monkeypatch):
    root = tmp_path / 'node'; (root / 'bin').mkdir(parents=True)
    binary = root / 'bin' / 'node'; binary.write_bytes(b'node-bin')
    (root / 'lib.js').write_text('a')
    digest = bootstrap_offline.tree_digest(root)
    spec = {'artifacts': {'node': {'binary_sha256': tt.sha256(binary), 'tree_sha256': digest}}, 'dsh': {}}
    monkeypatch.setattr(tt, 'spec', lambda: spec)
    monkeypatch.setenv('BENCH_NODE_BIN', str(binary))
    monkeypatch.setattr(tt, '_VERIFIED_TREES', {})
    calls = []
    real = bootstrap_offline.tree_digest
    monkeypatch.setattr(bootstrap_offline, 'tree_digest', lambda r: calls.append(1) or real(r))
    tt.trusted_tool('node'); tt.trusted_tool('node')
    assert len(calls) == 1
    (root / 'lib.js').write_text('tampered')
    with pytest.raises(ValueError, match='tree SHA256 mismatch'):
        tt.trusted_tool('node')
    assert len(calls) == 2
