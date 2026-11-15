#!/usr/bin/env python3
"""Approval update cho DeepSeek OR paid route: thêm model_admission entry +
recompute freeze states (4 configs) + note."""
import json, sys, hashlib
from pathlib import Path
sys.path.insert(0, '.')
from run_manifest import freeze_state, digest_json, hash_file

STUDY = Path(__file__).resolve().parents[1]
ap_path = STUDY/'audits/engineering-approval-v46-update.json'
ap = json.load(open(ap_path))

states = {}
for name in ('bench_config.json','bench_config_deepseek.json','bench_config_openrouter.json','bench_config_deepseek_openrouter.json'):
    cfg = json.load(open(name))
    states[name] = digest_json(freeze_state(cfg))
ap['freeze_state_sha256'] = list(states.values())

receipt = STUDY/'audits/model-admission/deepseek__deepseek-v4.1-flash-1017-openrouter.json'
ap['model_admission']['deepseek/deepseek-v4.1-flash-1017'] = {
 'approved': True,
 'receipt': str(receipt),
 'sha256': hash_file(receipt),
 'note': 'OpenRouter PAID route (credit); canary 3/3 PASS identity exact deepseek/deepseek-v4.1-flash; '
         'budget guard 1900 requests; price entitlement prompt $0.051/M completion $0.567/M cache $0.018/M; '
         'pipeline smoke→pilot, criterion B1>=B0 (user 2026-11-10)'}

ap_path.write_text(json.dumps(ap, indent=1, ensure_ascii=False))
print('approval updated:')
for k, v in states.items(): print(' ', k, '->', v[:16])
print('DS-OR admission receipt sha256:', ap['model_admission']['deepseek/deepseek-v4.1-flash-1017']['sha256'][:16])
