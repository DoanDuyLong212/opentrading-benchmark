"""Locate Bun independently of HOME; trust only bytes pinned in study config."""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def trusted_bun():
    receipt = json.loads((ROOT/'tools/bench_config.json').read_text(encoding='utf-8'))['provider_options']
    # BENCH_BUN_SHA256 deliberately cannot redefine this trust anchor.
    expected = receipt['native_bun_sha256']
    candidate = Path(os.environ.get('BENCH_BUN_BIN', receipt['native_bun_binary'])).expanduser().resolve()
    if not candidate.is_file():
        raise ValueError('Pinned Bun missing; set BENCH_BUN_BIN to Bun matching the study receipt')
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected:
        raise ValueError('Pinned Bun binary content changed; trusted SHA256 mismatch')
    return candidate
