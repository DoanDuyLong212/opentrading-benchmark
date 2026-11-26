"""Amendment 2026-11-25 (owner: "Tôi cần gấp ... OT sẽ dùng host deepinfra để chạy nốt, còn oc và dsh lấy bản đó
gộp vào ..." + chose "1 lượt + thay 23 task"). Builds 5 sealed DeepInfra runs (key 2, NL proxy):
  a-all : current tasks with no old equivalent, all 3 arms (fin-i3-risk-725, fin-r1-call-775/778, fin-s2-times10-480)
  a-dsh / a-oc / a-ot : re-runs of single-run trials voided by the pre-registered infra rules, per arm
  b-ot  : 19 old v4.6u task versions (supp tree), OpenTrading only (OC/DSH come from v4.6u run 1)
Phase 1 (this script): receipts, configs, approvals. Phase 2: prepare-only + seals (seal.py).
"""
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path('/home/doanlong/extra/bench-v47-pin/runs/deepinfra-20261125')
MAIN = Path('/home/doanlong/extra/bench-v47-pin/runs/main-20261124')
PROXY = 'http://127.0.0.1:25360'
RUNS = {
    'a-all': dict(tree='finance-v47-study', cap='0.6', arms='opentrading_machine,opencode,dsh',
                  tasks=['fin-i3-risk-725', 'fin-r1-call-775', 'fin-r1-call-778', 'fin-s2-times10-480']),
    'a-dsh': dict(tree='finance-v47-study', cap='0.4', arms='dsh',
                  tasks=['fin-i1-pick-705', 'fin-i2-maxgain-711', 'fin-m3-update-536', 'fin-m6-conv-621', 'fin-m6-conv-624']),
    'a-oc': dict(tree='finance-v47-study', cap='0.5', arms='opencode',
                 tasks=['fin-i3-risk-724', 'fin-m3-split-532', 'fin-m3-update-536', 'fin-m4-port-526', 'fin-m6-conv-621', 'fin-m6-rev-665']),
    'a-ot': dict(tree='finance-v47-study', cap='0.4', arms='opentrading_machine',
                 tasks=['fin-c3-geo-451', 'fin-m4-rule-523', 'fin-s3-asof-485']),
    'b-ot': dict(tree='finance-v47-supp', cap='0.6', arms='opentrading_machine', tasks=None),  # all 19 tasks in supp tree
}
opener = urllib.request.build_opener(urllib.request.ProxyHandler({'https': PROXY}))


def get(url):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + os.environ['OPENROUTER_KEY_2']})
    with opener.open(req, timeout=60) as r:
        return r.read()


def main():
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = now.strftime('%Y%m%dT%H%M%SZ')
    raw_key = get('https://openrouter.ai/api/v1/key')
    kd = json.loads(raw_key)['data']
    raw_ep = get('https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash-1017/endpoints')
    BASE.mkdir(exist_ok=True)
    (BASE / f'key-response-{stamp}.json').write_bytes(raw_key)
    (BASE / f'endpoints-{stamp}.json').write_bytes(raw_ep)
    di = [e for e in json.loads(raw_ep)['data']['endpoints'] if e['provider_name'] == 'DeepInfra']
    worst_p = max(float(e['pricing']['prompt']) for e in di)
    worst_c = max(float(e['pricing']['completion']) for e in di)
    ctx, out = 1048576, 393216
    computed = worst_p * ctx + worst_c * out
    bound = round(computed * 1.05, 6)   # same 5% margin as the Pearl receipt (0.170394 -> 0.178913)
    bound_ev = {'provider_name': 'DeepInfra', 'endpoints': [{k: e.get(k) for k in ('tag', 'quantization', 'pricing', 'max_completion_tokens', 'context_length', 'status')} for e in di],
                'formula': 'max prompt price over all DeepInfra endpoints x context_tokens + max completion price x output_tokens; x1.05 margin; cache not discounted',
                'computed_usd': f'{computed:.8f}', 'host_choice': 'owner decision 2026-11-25: Pearl shared pool 429-saturated; DeepInfra (fp8 variants) for the remaining trials'}
    base_receipt = json.loads((MAIN / 'paid-receipt.json').read_text())
    if hashlib.sha256(os.environ['OPENROUTER_KEY_2'].encode()).hexdigest() != base_receipt['key_fingerprint']:
        raise SystemExit('key fingerprint mismatch')
    cfg0 = json.loads((MAIN / 'bench_config_v47_main.json').read_text())
    approval0 = json.loads((MAIN / 'approval.json').read_text())
    for name, spec in RUNS.items():
        d = BASE / name
        (d / 'allocation').mkdir(parents=True, exist_ok=False)
        rec = dict(base_receipt)
        rec.update({'verified_at': now.isoformat().replace('+00:00', 'Z'),
                    'expires_at': (now + timedelta(hours=24)).isoformat().replace('+00:00', 'Z'),
                    'provider_host': 'DeepInfra',
                    'key_limit': {k: kd.get(k) for k in ('limit', 'limit_remaining', 'usage', 'limit_reset')},
                    'key_response_sha256': hashlib.sha256(raw_key).hexdigest(),
                    'attempt_upper_bound_usd': f'{bound:.6f}', 'context_tokens': ctx, 'output_tokens': out,
                    'bound_evidence': bound_ev,
                    'bound_evidence_sha256': hashlib.sha256(json.dumps(bound_ev, sort_keys=True).encode()).hexdigest(),
                    'host_check': f'endpoints listing {stamp}: DeepInfra ' + ', '.join(f"{e.get('tag')} status {e.get('status')}" for e in di),
                    'allocation_path': str(d / 'allocation/paid-allocation.json'),
                    'dedicated_key_basis': 'OPENROUTER_KEY_2, dedicated to this benchmark agent route; several sequential journals; joint spend bounded by the key limit; usage ' + str(kd.get('usage')) + ' at verification',
                    'reviewer': 'Claude (session) on owner instruction 2026-11-25 DeepInfra completion; ' + stamp,
                    'purpose': f'v4.7 single-run completion on DeepInfra: {name}'})
        (d / 'paid-receipt.json').write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        cfg = json.loads(json.dumps(cfg0))
        cfg['provider_options']['paid_budget_receipt'] = str(d / 'paid-receipt.json')
        cfg['provider_options']['paid_budget_receipt_sha256'] = hashlib.sha256((d / 'paid-receipt.json').read_bytes()).hexdigest()
        cfg['config_note'] = f'v4.7 DeepInfra completion run {name} (amendment 2026-11-25 DEEPINFRA-COMPLETION.md): main config except paid receipt (host DeepInfra) and cap {spec["cap"]}.'
        (d / 'bench_config.json').write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
        ap = dict(approval0)
        ap.update({'decision_id': f'V47-DEEPINFRA-20261125-{name.upper()}', 'approved_at': '2026-11-25',
                   'owner_words': '"Tôi cần gấp nên review lại các task hiện tại và các task cũ ... OT sẽ dùng host deepinfra để chạy nốt, còn oc và dsh lấy bản đó gộp vào ..." + choice "1 lượt + thay 23 task (Recommended)"',
                   'scope': {'split': 'main', 'runs': 1, 'arms': spec['arms'].split(','), 'tasks': spec['tasks'] or '19 v4.6u task versions (finance-v47-supp/tasks/main)',
                             'model': cfg['model'], 'provider_host': 'DeepInfra', 'budget_cap_usd': spec['cap'], 'tree': spec['tree']}})
        (d / 'approval.json').write_text(json.dumps(ap, indent=1, ensure_ascii=False))
        (d / 'spec.json').write_text(json.dumps(spec, indent=1))
    print('bound', bound, 'key remaining', kd.get('limit_remaining'), 'expires', (now + timedelta(hours=24)).isoformat())


if __name__ == '__main__':
    main()
