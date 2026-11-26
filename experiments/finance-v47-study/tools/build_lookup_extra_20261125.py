#!/usr/bin/env python3
"""Amendment 2026-11-25 (d): group D (8 partial-availability traps) and group E (4 L4 chains), main + 1 pilot each.

D: each question mixes a field the snapshot serves with one it cannot serve (a quarter/year not yet published at the
   2026-11-01 snapshot, a session after 30/10/2026, or the provider's ratio section that is not served). The served
   field must be answered exactly and the other left null with a reason; every answer field is listed as nullable
   (no hint which one). Graded by the shared S-grader variant (types null/nonempty_reason), primary deterministic.
D replaces the saturated whole-question refusal traps with a harder partial form.
E: two-tool chains: pick a company from statements (financial_statements), then compute on its price history
   (vn_quote_history). Standard grader. Idempotent.
"""
import hashlib, json, re, shutil, sys
from decimal import Decimal as D
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import build_compute_stratum_20261111 as cs  # noqa: E402
import build_finance_stratum_20261125 as bfs  # noqa: E402
import build_investor_stratum_20261125 as inv  # noqa: E402
import build_safety_stratum_20261116 as bss  # noqa: E402

CREATED = '2026-11-25'
BN = D(10) ** 9
MONEY = {'rel': 0.005}
PCT = {'abs': 0.05}


def r4(x):
    return float(round(D(x), 4))


def nval(path, gold, tol):
    return {'type': 'value', 'path': path, 'gold': r4(gold), 'tol': tol}


def fs_value(sym, freq, name, period):
    c = bfs.Ctx(bfs.payloads([sym], {(freq, bfs.SECTION_OF[name])}))
    return c.item(sym, freq, name, period)


def closes(sym):
    return [D(str(r['c'])) for r in inv.PRE[sym]]


# ------------------------------------------------------------------ D specs
def d_fs(tid, sym, name, label, served, missing, freq='q'):
    needs = {(freq, bfs.SECTION_OF[name])}
    tools = bfs.payloads([sym], needs)
    v = fs_value(sym, freq, name, served) / BN
    kind = 'quý' if freq == 'q' else 'năm'
    fields = ['values.served', 'values.missing']
    q = ('Cho biết **%s** của **%s** trong %s **%s** và %s **%s** (tỷ đồng), lấy từ `financial_statements` (`period="%s"`). %s'
         % (label, sym, kind, served, kind, missing, 'quarter' if freq == 'q' else 'year', bss.neutral_null(['served', 'missing'])))
    ex = {'values': {'served': 0, 'missing': 0}, 'unit': 'tỷ đồng', 'period': '(kỳ được hỏi)', 'source': 'financial_statements',
          'reason': '(tuỳ chọn; bắt buộc khi có trường null)'}
    sol = {'served': r4(v), 'served_period': served, 'missing': None, 'missing_period': missing}
    exp = [nval('values.served', v, MONEY), {'type': 'null', 'path': 'values.missing'},
           {'type': 'nonempty_reason', 'path': 'reason'}, {'type': 'str', 'path': 'source', 'accept': ['financial_statements']}]
    oracle = bfs.LIB + ("check('served', R(item(%r, %r, %r, %r) / 10**9), gold['solution']['served'])\n"
                        "_d = env(fs_key(%r, %r, %r))['data']\ncheck('missing_absent', %r in _d['periods'], False)\n"
                        % (sym, freq, name, served, sym, freq, name, missing))
    return dict(tid=tid, title='%s %s: %s %s và %s' % (label, sym, kind, served, missing), question=q, example=ex, solution=sol,
                expects=exp, oracle=oracle, tools=tools, fields=fields)


def d_price(tid, sym, missing_date):
    tools = {'hist:' + sym: inv.hist_env(sym)}
    last = closes(sym)[-1]
    q = ('Cho biết giá đóng cửa của **%s** ở phiên **30/10/2026** và ở phiên **%s** (nghìn đồng/cổ phiếu), lấy từ '
         '`vn_quote_history`. %s' % (sym, missing_date, bss.neutral_null(['served', 'missing'])))
    ex = {'values': {'served': 0, 'missing': 0}, 'unit': 'nghìn đồng/cổ phiếu', 'period': '(kỳ được hỏi)',
          'source': 'vn_quote_history', 'reason': '(tuỳ chọn; bắt buộc khi có trường null)'}
    sol = {'served': float(last), 'served_date': '30/10/2026', 'missing': None, 'missing_date': missing_date}
    exp = [nval('values.served', last, {'rel': 0.001}), {'type': 'null', 'path': 'values.missing'},
           {'type': 'nonempty_reason', 'path': 'reason'}, {'type': 'str', 'path': 'source', 'accept': ['vn_quote_history']}]
    iso = '-'.join(reversed(missing_date.split('/')))
    oracle = ("_r = env('hist:%s')['data']['closes']\ncheck('served', _r[-1]['c'], gold['solution']['served'])\n"
              "check('missing_absent', any(x['t'] == %r for x in _r), False)\n" % (sym, iso))
    return dict(tid=tid, title='Giá %s 30/10 và %s' % (sym, missing_date), question=q, example=ex, solution=sol,
                expects=exp, oracle=oracle, tools=tools, fields=['values.served', 'values.missing'])


def d_ratio(tid, sym):
    needs = {('q', 'KQKD')}
    tools = bfs.payloads([sym], needs)
    c = bfs.Ctx(tools)
    v = c.ttm(sym, c.NIP) / BN
    q = ('Cho biết **tổng LNST của CĐ cty mẹ 4 quý Q3/2025–Q2/2026** của **%s** (tỷ đồng) và **P/E cơ bản do nguồn công bố** '
         'trong mục "Chỉ số tài chính" (lần), lấy từ `financial_statements`. %s' % (sym, bss.neutral_null(['served', 'missing'])))
    ex = {'values': {'served': 0, 'missing': 0}, 'unit': 'tỷ đồng / lần', 'period': '(kỳ được hỏi)', 'source': 'financial_statements',
          'reason': '(tuỳ chọn; bắt buộc khi có trường null)'}
    sol = {'served': r4(v), 'missing': None, 'missing_item': 'P/E cơ bản (mục Chỉ số tài chính không được phục vụ)'}
    exp = [nval('values.served', v, MONEY), {'type': 'null', 'path': 'values.missing'},
           {'type': 'nonempty_reason', 'path': 'reason'}, {'type': 'str', 'path': 'source', 'accept': ['financial_statements']}]
    oracle = bfs.LIB + ("check('served', R(ttm(%r, NIP) / 10**9), gold['solution']['served'])\n"
                        "_d = env(fs_key(%r, 'q', NIP))['data']\ncheck('ratio_section_absent', 'Chỉ số tài chính' in _d['statements'], False)\n"
                        % (sym, sym))
    return dict(tid=tid, title='LNST TTM và P/E công bố %s' % sym, question=q, example=ex, solution=sol,
                expects=exp, oracle=oracle, tools=tools, fields=['values.served', 'values.missing'])


# ------------------------------------------------------------------ E specs
def ret(sym, n):
    c = closes(sym)
    return (c[-1] / c[-1 - n] - 1) * 100


def gap_ma20(sym):
    c = closes(sym)
    return (c[-1] / (sum(c[-20:]) / 20) - 1) * 100


def e_chain(tid, syms, pick_label, pick_key, pick_fn, best, measure_label, measure_code, measure_fn, needs):
    tools = bfs.payloads(syms, needs)
    c = bfs.Ctx(tools)
    scores = {s: pick_fn(c, s) for s in syms}
    win = (max if best == 'max' else min)(syms, key=scores.get)
    for s in syms:
        tools['hist:' + s] = inv.hist_env(s)
    m = measure_fn(win)
    q = ('Bước 1: trong **%s**, tìm mã có **%s** (`financial_statements`). Bước 2: với **chỉ mã đó**, tính **%s** từ '
         '`vn_quote_history` (giá đóng cửa). %s' % (', '.join(syms), pick_label, measure_label, bfs.DEF_EQ))
    ex = {'values': {'symbol': 'MÃ', 'step1_metric': 0, 'result_pct': 0}, 'unit': '%', 'period': '(kỳ được hỏi)',
          'source': 'financial_statements + vn_quote_history', 'note': '(tuỳ chọn) số đầu vào'}
    exp = [bfs.tokens('values.symbol', win, syms), nval('values.step1_metric', scores[win], MONEY if 'tỷ đồng' in pick_label else PCT), nval('values.result_pct', m, PCT),
           {'type': 'str_all', 'path': 'source', 'accept': ['financial_statements', 'vn_quote_history']}]
    oracle = bfs.LIB + ("_S = %r\n_f = lambda s: %s\n_w = %s(_S, key=_f)\ncheck('symbol', _w, gold['solution']['symbol'])\n"
                        "_c = [x['c'] for x in env('hist:' + _w)['data']['closes']]\n"
                        "from decimal import Decimal as _Dd\n_c = [_Dd(str(x)) for x in _c]\n"
                        "check('result', R(%s), gold['solution']['result_pct'])\n" % (syms, pick_key, best, measure_code))
    sol = {'symbol': win, 'step1_metric': r4(scores[win]), 'result_pct': r4(m), 'scores': {s: r4(v) for s, v in scores.items()}}
    return dict(tid=tid, title='Chuỗi 2 bước %s' % '/'.join(syms), question=q, example=ex, solution=sol, expects=exp,
                oracle=oracle, tools=tools, fields=None)


def yoy_nip(c, s):
    return c.pct(c.q(s, c.NIP, 'Q2/2026'), c.q(s, c.NIP, 'Q2/2025'))


def build():
    D_main = [d_fs('fin-l4-partial-671', 'FPT', bfs.LIB_NAMES['REV'], 'Doanh thu thuần', 'Q2/2026', 'Q3/2026'),
              d_fs('fin-l4-partial-672', 'HPG', bfs.LIB_NAMES['NIP'], 'LNST của CĐ cty mẹ', 'Q2/2026', 'Q3/2026'),
              d_fs('fin-l4-partial-673', 'VNM', bfs.LIB_NAMES['GP'], 'Lợi nhuận gộp', 'Q1/2026', 'Q3/2026'),
              d_price('fin-l4-partial-674', 'SSI', '06/11/2026'),
              d_price('fin-l4-partial-675', 'MWG', '13/11/2026'),
              d_ratio('fin-l4-partial-676', 'GAS'),
              d_ratio('fin-l4-partial-677', 'DGC'),
              d_fs('fin-l4-partial-678', 'MWG', bfs.LIB_NAMES['NIP'], 'LNST của CĐ cty mẹ', '2025', '2026', freq='y')]
    D_pilot = [d_fs('fin-l4-partial-861', 'PNJ', bfs.LIB_NAMES['REV'], 'Doanh thu thuần', 'Q2/2026', 'Q3/2026')]
    KQ = {('q', 'KQKD')}
    BOTH = {('q', 'KQKD'), ('q', 'CDKT')}
    E_main = [e_chain('fin-l4-chain-656', ['DGC', 'DCM', 'DPM', 'BMP'], 'tăng trưởng LNST quý Q2/2026 so với Q2/2025 cao nhất (%)',
                      "pct(q(s, NIP, 'Q2/2026'), q(s, NIP, 'Q2/2025'))", yoy_nip, 'max',
                      'lợi suất 20 phiên tới 30/10/2026 (%) = giá 30/10 ÷ giá 20 phiên trước − 1', '(_c[-1] / _c[-21] - 1) * 100',
                      lambda s: ret(s, 20), KQ),
              e_chain('fin-l4-chain-657', ['GMD', 'HAH', 'VJC', 'REE'], 'tỷ lệ nợ phải trả ÷ tổng tài sản cuối Q2/2026 thấp nhất (%)',
                      'debt_ratio(s)', lambda c, s: c.debt_ratio(s), 'min',
                      'lợi suất 60 phiên tới 30/10/2026 (%) = giá 30/10 ÷ giá 60 phiên trước − 1', '(_c[-1] / _c[-61] - 1) * 100',
                      lambda s: ret(s, 60), {('q', 'CDKT')}),
              e_chain('fin-l4-chain-658', ['MWG', 'FRT', 'PNJ', 'KDC'], 'biên lợi nhuận gộp TTM (4 quý Q3/2025–Q2/2026) cao nhất (%)',
                      'margin_ttm(s, GP)', lambda c, s: c.margin_ttm(s, c.GP), 'max',
                      'chênh lệch giá đóng cửa 30/10/2026 so với trung bình 20 phiên gần nhất (gồm 30/10) (%)',
                      '(_c[-1] / (sum(_c[-20:]) / 20) - 1) * 100', gap_ma20, KQ),
              e_chain('fin-l4-chain-659', ['KDH', 'NLG', 'DXG', 'CTD'], 'doanh thu thuần TTM (4 quý Q3/2025–Q2/2026) lớn nhất (tỷ đồng)',
                      'ttm(s, REV) / 10**9', lambda c, s: c.ttm(s, c.REV) / BN, 'max',
                      'lợi suất 119 phiên tới 30/10/2026 (%) = giá 30/10 ÷ giá 119 phiên trước − 1', '(_c[-1] / _c[-120] - 1) * 100',
                      lambda s: ret(s, 119), KQ)]
    E_pilot = [e_chain('fin-l4-chain-862', ['TRA', 'IMP', 'DHG', 'PC1'], 'ROE TTM cao nhất (%) (LNST 4 quý Q3/2025–Q2/2026 ÷ bình quân '
                       'vốn chủ sở hữu 5 thời điểm cuối quý Q2/2025–Q2/2026 × 100)', 'roe_ttm(s)', lambda c, s: c.roe_ttm(s), 'max',
                       'lợi suất 20 phiên tới 30/10/2026 (%) = giá 30/10 ÷ giá 20 phiên trước − 1', '(_c[-1] / _c[-21] - 1) * 100',
                       lambda s: ret(s, 20), BOTH)]
    return D_main, D_pilot, E_main, E_pilot


def write(split, s, kind):
    d = STUDY / 'tasks' / split / s['tid']
    if d.exists():
        shutil.rmtree(d)
    (d / 'environment').mkdir(parents=True); (d / 'solution').mkdir(); (d / 'tests').mkdir()
    if kind == 'D':
        (d / 'tests/grader.py').write_text(bss.grader_text(), encoding='utf-8')
    else:
        shutil.copy(STUDY / 'tools/v45_grader.py', d / 'tests/grader.py')
    pl = {'snapshot_date': '2026-11-01', 'note': 'Báo cáo quý tới Q2/2026, năm tới 2025 (audits/snapshot-extension-2026-11-25); '
          'giá 120 phiên tới 30/10/2026 (audits/snapshot-extension-2026-11-25b).', 'tools': s['tools']}
    (d / 'environment/payloads.json').write_text(json.dumps(pl, ensure_ascii=False, indent=1) + '\n')
    tmpl = (cs.TEMPLATE / 'instruction.md').read_text(encoding='utf-8')
    rounding = '' if kind == 'D' else '\n\n' + cs.ROUNDING
    head = '# %s\n\n%s%s\n\n## Yêu cầu trả lời\nTrả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n```json\n%s\n```\n\n\n' % (
        s['title'], s['question'], rounding, json.dumps(s['example'], ensure_ascii=False, indent=2))
    (d / 'instruction.md').write_text(head + tmpl[tmpl.index('## Ràng buộc chung'):], encoding='utf-8')
    keys = sorted(s['tools'])
    prov = [{'tool': s['tools'][k]['tool'], 'source': s['tools'][k]['envelope']['provenance']['source'],
             'as_of': s['tools'][k]['envelope']['provenance']['as_of'], 'matched_entry_id': k,
             'response_sha256': cs.digest(s['tools'][k]['envelope'])} for k in keys]
    if kind == 'E':  # step 2 needs only the chosen company's history
        contract = [p for p in prov if not p['matched_entry_id'].startswith('hist:') or p['matched_entry_id'] == 'hist:' + s['solution']['symbol']]
    else:
        contract = prov
    gold = {'task_id': s['tid'], 'scoring': 'value', 'solution': s['solution'], 'as_of': '2026-11-25', 'split': split,
            'expects': s['expects'], 'contract_version': 2, 'stratum': 'lookup', 'tier': 'L4',
            'family': 'L4 partial availability' if kind == 'D' else 'L4 chain',
            'notes': ('Group D (amendment 2026-11-25 d): served field exact, unserved field null + reason; primary is the '
                      'deterministic grader.' if kind == 'D' else 'Group E (amendment 2026-11-25 d): two-tool chain.'),
            'provenance_contract': contract, 'provenance_catalog': prov,
            'payload_sha256': hashlib.sha256((d / 'environment/payloads.json').read_bytes()).hexdigest(),
            'required_payload_keys': sorted(p['matched_entry_id'] for p in contract)}
    if kind == 'D':
        gold['primary_rule'] = 'deterministic'
    (d / 'solution/gold.json').write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n')
    o = (cs.TEMPLATE / 'solution/oracle.py').read_text(encoding='utf-8')
    pre, mark, rest = o.partition('# === thân oracle ===\n')
    _, sep, tail = rest.partition('\nif problems:')
    assert mark and sep
    (d / 'solution/oracle.py').write_text(pre + mark + s['oracle'] + '\n\nif problems:' + tail, encoding='utf-8')
    toml = (cs.TEMPLATE / 'task.toml').read_text(encoding='utf-8')
    toml = toml.replace('# Task benchmark harness tài chính (bộ 200+50) — sinh bởi tools/build_main.py',
                        '# Group %s — amendment 2026-11-25 (d), tools/build_lookup_extra_20261125.py' % kind)
    syms = sorted({e['params']['symbol'] for e in s['tools'].values()})
    for k, v in (('id', s['tid']), ('title', s['title'].replace('"', "'")), ('created', CREATED), ('level', 'L4'),
                 ('family', gold['family']), ('financebench_type', 'partial availability' if kind == 'D' else 'multi-step retrieval'),
                 ('entity', '+'.join(syms)), ('split', split)):
        toml = re.sub(r'^%s = ".*"$' % k, '%s = "%s"' % (k, v), toml, flags=re.M)
    toml = re.sub(r'^tools_expected = .*$', 'tools_expected = %s' % json.dumps(sorted({e['tool'] for e in s['tools'].values()})), toml, flags=re.M)
    toml = toml.replace('confirmatory_eligible = true', 'confirmatory_eligible = true\nstratum = "lookup"\ntier = "L4"')
    (d / 'task.toml').write_text(toml, encoding='utf-8')
    return d


def main():
    dm, dp, em, ep = build()
    assert (len(dm), len(dp), len(em), len(ep)) == (8, 1, 4, 1)
    receipt = {}
    for split, specs, kind in (('main', dm, 'D'), ('pilot', dp, 'D'), ('main', em, 'E'), ('pilot', ep, 'E')):
        for s in specs:
            d = write(split, s, kind)
            receipt[s['tid']] = {'split': split, 'group': kind, 'solution': s['solution'],
                                 'files': {str(f.relative_to(d)): hashlib.sha256(f.read_bytes()).hexdigest()
                                           for f in sorted(d.rglob('*')) if f.is_file()}}
    (STUDY / 'audits/taskset-revision-2026-11-25/LOOKUP-EXTRA-BUILD.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    for k, v in receipt.items():
        print(k, v['split'], v['group'], json.dumps(v['solution'], ensure_ascii=False)[:150])


if __name__ == '__main__':
    main()
