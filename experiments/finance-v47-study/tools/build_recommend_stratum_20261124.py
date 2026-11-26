#!/usr/bin/env python3
"""Recommendation stratum (R), amendment 2026-11-25 (f). Specs and rule: tools/recommend_specs_20261124.py (pre-registered).

One ticker per task; the agent sees snapshot data only (120 sessions to 30/10/2026, its quarterly statements when
recorded, VN-Index) and answers MUA / GIỮ / BÁN for the holding window to END. Gold applies the pre-registered
±2 % rule to the recorded close of END (never served). Scored by code (`scoring: outcome`), pooled as stratum investor.
"""
import hashlib, json, re, shutil, sys
from decimal import Decimal as D
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import build_compute_stratum_20261111 as cs  # noqa: E402
import build_investor_stratum_20261124 as inv  # noqa: E402
import investor_specs_20261124 as ISP  # noqa: E402
import recommend_specs_20261124 as SP  # noqa: E402

END_VN = '/'.join(reversed(ISP.END.split('-')))


def call_for(ret_pct):
    t = D(SP.THRESHOLD_PCT)
    return 'MUA' if ret_pct > t else 'BÁN' if ret_pct < -t else 'GIỮ'


ORACLE = r'''
from decimal import Decimal as _D
_s = gold['solution']
_rows = env('hist:' + _s['symbol'])['data']['closes']
check('entry', _rows[-1]['c'], _s['entry'])
check('entry_date', _rows[-1]['t'], '2026-10-30')
_r = (_D(str(_s['end_close'])) / _D(str(_s['entry'])) - 1) * 100
_t = _D(_s['threshold_pct'])
check('call', 'MUA' if _r > _t else 'BÁN' if _r < -_t else 'GIỮ', _s['call'])
'''


def write(spec):
    sym = spec['sym']
    tools, fs = inv.payloads([sym])
    oc = inv.outcome(sym)
    call = call_for(oc['ret'])
    d = STUDY / 'tasks' / spec['split'] / spec['tid']
    if d.exists():
        shutil.rmtree(d)
    (d / 'environment').mkdir(parents=True); (d / 'solution').mkdir(); (d / 'tests').mkdir()
    shutil.copy(STUDY / 'tools/v45_grader.py', d / 'tests/grader.py')
    pl = {'snapshot_date': '2026-11-01', 'note': 'Giá 120 phiên tới 30/10/2026 (audits/snapshot-extension-2026-11-25b) và '
          'báo cáo quý tới Q2/2026 (audits/snapshot-extension-2026-11-25).', 'tools': tools}
    (d / 'environment/payloads.json').write_text(json.dumps(pl, ensure_ascii=False, indent=1) + '\n')
    q = (inv.HEADER + '\n\n' +
         'Đưa ra **khuyến nghị** cho **%s** với khung nắm giữ từ giá đóng cửa 30/10/2026 tới giá đóng cửa phiên **%s**: '
         'đúng một trong ba từ **MUA**, **GIỮ** hoặc **BÁN**. Chấm: MUA đúng khi giá %s cao hơn giá 30/10/2026 **trên 2%%**; '
         'BÁN đúng khi thấp hơn **quá 2%%**; GIỮ đúng khi thay đổi nằm trong khoảng **±2%%**.\n\n' % (sym, END_VN, END_VN)
         + inv.data_text([sym], fs))
    example = {'values': {'call': 'MUA | GIỮ | BÁN'}, 'source': 'vn_quote_history', 'reason': '(lý do ngắn: dữ liệu và lập luận đã dùng)'}
    title = 'Khuyến nghị R — MUA/GIỮ/BÁN %s' % sym
    tmpl = (cs.TEMPLATE / 'instruction.md').read_text(encoding='utf-8')
    head = '# %s\n\n%s\n\n## Yêu cầu trả lời\nTrả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n```json\n%s\n```\n\n\n' % (
        title, q, json.dumps(example, ensure_ascii=False, indent=2))
    (d / 'instruction.md').write_text(head + tmpl[tmpl.index('## Ràng buộc chung'):], encoding='utf-8')
    sol = {'symbol': sym, 'call': call, 'threshold_pct': SP.THRESHOLD_PCT, 'entry': oc['entry'], 'end_close': oc['end_close'],
           'entry_date': ISP.ENTRY, 'end_date': ISP.END, 'ret_pct': round(float(oc['ret']), 4),
           'vnindex_ret': round(float(inv.outcome(inv.INDEX)['ret']), 4), 'post_sha256': ISP.POST_SHA256}
    expects = [{'type': 'tokens', 'path': 'values.call', 'accept': [call], 'reject': [c for c in SP.CALLS if c != call]}]
    keys = ['hist:' + sym]
    gold = {'task_id': spec['tid'], 'scoring': 'outcome', 'solution': sol, 'as_of': inv.REC['recorded_at'], 'split': spec['split'],
            'expects': expects, 'contract_version': 2, 'stratum': 'investor', 'tier': 'R',
            'notes': 'Recommendation stratum (amendment 2026-11-25 f): primary = pre-registered ±2 % rule on the recorded '
                     'close of END (tools/recommend_specs_20261124.py).',
            'provenance_contract': inv.provenance(tools, keys), 'provenance_catalog': inv.provenance(tools, sorted(tools)),
            'payload_sha256': hashlib.sha256((d / 'environment/payloads.json').read_bytes()).hexdigest(),
            'required_payload_keys': keys}
    (d / 'solution/gold.json').write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n')
    o = (cs.TEMPLATE / 'solution/oracle.py').read_text(encoding='utf-8')
    pre, mark, rest = o.partition('# === thân oracle ===\n')
    _, sep, tail = rest.partition('\nif problems:')
    assert mark and sep
    (d / 'solution/oracle.py').write_text(pre + mark + ORACLE + '\n\nif problems:' + tail, encoding='utf-8')
    toml = (cs.TEMPLATE / 'task.toml').read_text(encoding='utf-8')
    toml = toml.replace('# Task benchmark harness tài chính (bộ 200+50) — sinh bởi tools/build_main.py',
                        '# Recommendation stratum — amendment 2026-11-25 (f), tools/build_recommend_stratum_20261124.py')
    for k, v in (('id', spec['tid']), ('title', title), ('created', '2026-11-25'), ('level', 'R'), ('family', 'R recommendation'),
                 ('financebench_type', 'buy/hold/sell call (outcome-scored)'), ('entity', sym), ('split', spec['split'])):
        toml = re.sub(r'^%s = ".*"$' % k, '%s = "%s"' % (k, v), toml, flags=re.M)
    toml = re.sub(r'^tools_expected = .*$', 'tools_expected = %s' % json.dumps(sorted({e['tool'] for e in tools.values()})), toml, flags=re.M)
    toml = toml.replace('confirmatory_eligible = true', 'confirmatory_eligible = true\nstratum = "investor"\ntier = "R"')
    toml = re.sub(r'^type = "value"$', 'type = "outcome"', toml, flags=re.M)
    (d / 'task.toml').write_text(toml, encoding='utf-8')
    return d, sol


def main():
    counts = {s: sum(x['split'] == s for x in SP.SPECS) for s in ('main', 'holdout', 'pilot')}
    assert counts == {'main': 16, 'holdout': 4, 'pilot': 1}, counts
    receipt = {'post_sha256': ISP.POST_SHA256, 'threshold_pct': SP.THRESHOLD_PCT, 'tasks': {}}
    for spec in SP.SPECS:
        d, sol = write(spec)
        receipt['tasks'][spec['tid']] = {'split': spec['split'], 'symbol': sol['symbol'], 'call': sol['call'],
                                         'files': {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                   for p in sorted(d.rglob('*')) if p.is_file()}}
    (STUDY / 'audits/taskset-revision-2026-11-25/RECOMMEND-BUILD.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    from collections import Counter
    for split in ('main', 'holdout', 'pilot'):
        print(split, dict(Counter(v['call'] for v in receipt['tasks'].values() if v['split'] == split)))


if __name__ == '__main__':
    main()
