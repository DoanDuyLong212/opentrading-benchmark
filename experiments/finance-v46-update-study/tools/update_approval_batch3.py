#!/usr/bin/env python3
"""Cập nhật engineering approval sau batch-3 corpus + budget 1900 + fix #5:
recompute freeze states cho 3 config, cập nhật note budget OR, ghi batch3 note."""
import json, sys, hashlib
from pathlib import Path
sys.path.insert(0, '.')
from run_manifest import freeze_state, digest_json, hash_file

STUDY = Path(__file__).resolve().parents[1]
ap_path = STUDY/'audits/engineering-approval-v46-update.json'
ap = json.load(open(ap_path))

states = {}
for name in ('bench_config.json', 'bench_config_deepseek.json', 'bench_config_openrouter.json'):
    cfg = json.load(open(name))
    states[name] = digest_json(freeze_state(cfg))
ap['freeze_state_sha256'] = list(states.values())

# cập nhật note budget route OR (không đụng receipt - hash receipt giữ nguyên)
adm = ap['model_admission']['nvidia/nemotron-3.5-super-vl:free']
adm['note'] = ('OpenRouter FREE route (pricing 0/0); pilot-only; budget hard-stop 1900 '
               '(user-raised 2026-11-10, verified free_model_daily_requests limit=1000 per UTC day, '
               'reset 00:00 UTC); identity trả đúng yêu cầu; envelope provider_route wired 2026-11-10')

ap['batch3_corpus_note'] = ('Corpus batch-3 đã chốt 2026-11-10 (session OpenCode thứ hai): MAIN 230 '
                            '(200 financial + 30 memory fin-mem-320..349), holdout 60 (50 nonmemory canonical + 10 memory). '
                            'Receipts audits/financial-memory-v45-batch3/. Amendment: audits/seal/SEAL-DRIFT-AMENDMENT-20261110.json')

ap['retune'] = ('preregistered 2026-11-09: 2 policy sentences (growth both-periods + refusal concise); '
                'preregistration plans/2026-11-09-v46u-retune-preregistration.md; '
                'post-freeze instrumentation 2026-11-10: fix#5 unknown_context Error-prefix + provider_route wiring + budget 1900 — see SEAL-DRIFT-AMENDMENT-20261110.json')

ap_path.write_text(json.dumps(ap, indent=1, ensure_ascii=False))
print('approval updated | freeze states:')
for k, v in states.items():
    print(' ', k, '->', v[:16])
print('OR admission receipt sha256 unchanged:', adm.get('sha256', '')[:16])
