#!/usr/bin/env python3
"""v4.7 taskset revision 2026-11-24 (owner-approved): fundamental compute (C5) and finance-analysis memory (M6).

Data: quarterly (Q3/2024..Q2/2026) and annual (FY2021..FY2025) financial statements recorded 2026-11-24 from the same
Vietstock `financeinfo` source as the frozen `financial_statements` payloads (audits/snapshot-extension-2026-11-24).
Periods after Q2/2026 are excluded so nothing published after the 2026-11-01 snapshot can enter a task. Each symbol
is served as two recorded variants, statement=KQKD and statement=CDKT; the provider's ratio section (CSTC) is not
served, so ratios are computed from the statements as each question defines them.

C5: multi-step, multi-period computations (TTM, average balances, DuPont, CAGR, leverage, YoY, sector aggregates).
M6: earlier sessions fix analysis conventions (how ROE is defined) and thresholds, with update and revoke variants;
the final turn asks for the screen plus the values, so forgetting a convention changes the numbers and the answer.
Gold and oracle share tools/finance_stratum_lib.py and read only the task's own payloads.
Idempotent: rewrites only the task directories it owns.
"""
import hashlib, json, math, re, shutil, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import build_compute_stratum_20261111 as cs  # noqa: E402  (shared writer conventions, template, ROUNDING)
import build_memory_stratum_20261111 as ms  # noqa: E402  (session/turn helpers)

RAW = json.loads((STUDY / 'audits/snapshot-extension-2026-11-24/raw.json').read_text(encoding='utf-8'))
LIB = (STUDY / 'tools/finance_stratum_lib.py').read_text(encoding='utf-8')
Q = ['Q3/2024', 'Q4/2024', 'Q1/2025', 'Q2/2025', 'Q3/2025', 'Q4/2025', 'Q1/2026', 'Q2/2026']
Y = ['2021', '2022', '2023', '2024', '2025']
SECTION = {'KQKD': 'Kết quả kinh doanh', 'CDKT': 'Báo cáo tình hình tài chính'}
PCT, RATIO, MONEY = {'abs': 0.05}, {'abs': 0.005}, {'rel': 0.005}
TOOL = 'financial_statements'
CREATED = '2026-11-24'


def envelope(sym, freq, statement):
    period, keep = ('quarter', Q) if freq == 'q' else ('year', Y)
    blob = RAW['symbols'][sym][period]
    rows = [{**r, 'values': {p: r['values'].get(p) for p in keep}} for r in blob['data']['statements'][SECTION[statement]]]
    return {'tool': TOOL, 'params': {'symbol': sym, 'period': period, 'statement': statement, 'periods_n': len(keep)},
            'envelope': {'data': {'symbol': sym, 'period': period, 'periods': keep, 'statements': {SECTION[statement]: rows}},
                         'provenance': {'source': 'vietstock', 'as_of': RAW['recorded_at'], 'timezone': 'Asia/Ho_Chi_Minh',
                                        'note': 'Ghi 2026-11-24 từ cùng nguồn financeinfo; chỉ giữ kỳ đã công bố trước '
                                                'snapshot 2026-11-01 (quý tới Q2/2026, năm tới 2025).'},
                         'availability': 'available'}}


def payloads(syms, needs):
    """needs: subset of {('q','KQKD'), ('q','CDKT'), ('y','KQKD'), ('y','CDKT')}."""
    return {'fs:%s:%s:%s' % (s, f, st): envelope(s, f, st) for s in syms for f, st in sorted(needs)}


class Ctx:
    """Executes the shared library against an in-memory payload set (the oracle runs the same code on disk)."""
    def __init__(self, tools):
        self.ns = {'env': lambda k: tools[k]['envelope']}
        exec(LIB, self.ns)

    def __getattr__(self, name):
        return self.ns[name]


def r4(x):
    return float(round(cs.D(x), 4))


def val(path, gold, tol):
    return {'type': 'value', 'path': path, 'gold': r4(gold), 'tol': tol}


def tokens(path, win, others):
    return {'type': 'tokens', 'path': path, 'accept': [win], 'reject': [o for o in others if o != win]}


def src():
    return {'type': 'str', 'path': 'source', 'accept': [TOOL]}


CALLS = ('Số liệu lấy từ `financial_statements` (KQKD: `statement="KQKD"`, cân đối kế toán: `statement="CDKT"`; '
         'theo quý: `period="quarter"`, theo năm: `period="year"`). ')
DEF_EQ = '"vốn chủ sở hữu" là dòng **Vốn chủ sở hữu** như nguồn công bố; "LNST" là **LNST của CĐ cty mẹ**. '
TTM_TXT = '4 quý **Q3/2025–Q2/2026**'
PRIOR_TXT = '4 quý **Q3/2024–Q2/2025**'


def c5(tid, title, question, example, solution, expects, oracle, syms, needs):
    return {'kind': 'C5', 'tid': tid, 'tier': 'C5', 'title': title, 'question': CALLS + question, 'example': example,
            'solution': solution, 'expects': expects + [src()], 'oracle': oracle, 'syms': syms, 'needs': needs}


def roe_ttm_task(tid, syms):
    tools = payloads(syms, {('q', 'KQKD'), ('q', 'CDKT')}); c = Ctx(tools)
    v = {s: c.roe_ttm(s) for s in syms}; top = max(syms, key=v.get)
    q = ('Với **%s**: tính **ROE TTM** (%%) của từng mã = tổng LNST %s ÷ **bình quân vốn chủ sở hữu tại 5 thời điểm cuối quý '
         'Q2/2025, Q3/2025, Q4/2025, Q1/2026, Q2/2026** × 100. %sMã nào có ROE TTM cao nhất?' % (', '.join(syms), TTM_TXT, DEF_EQ))
    ex = {'values': {**{s: 0 for s in syms}, 'highest': 'MÃ'}, 'unit': '%', 'period': '(kỳ được hỏi)', 'source': TOOL, 'note': '(tuỳ chọn)'}
    exp = [val('values.' + s, v[s], PCT) for s in syms] + [tokens('values.highest', top, syms)]
    oracle = ''.join("check('roe_%s', R(roe_ttm('%s')), gold['solution']['%s'])\n" % (s, s, s) for s in syms) + \
        "check('highest', max(%r, key=roe_ttm), gold['solution']['highest'])\n" % (syms,)
    return c5(tid, 'ROE TTM %s' % '/'.join(syms), q, ex, {**{s: r4(v[s]) for s in syms}, 'highest': top}, exp, oracle, syms, {('q', 'KQKD'), ('q', 'CDKT')})


def oplev_task(tid, syms):
    tools = payloads(syms, {('q', 'KQKD')}); c = Ctx(tools)
    rg = {s: c.pct(c.ttm(s, c.REV), c.ttm(s, c.REV, c.PRIOR_TTM)) for s in syms}
    og = {s: c.pct(c.ttm(s, c.OP), c.ttm(s, c.OP, c.PRIOR_TTM)) for s in syms}
    ol = {s: og[s] / rg[s] for s in syms}; top = max(syms, key=ol.get)
    q = ('Với **%s**: so sánh %s với %s. Tính cho từng mã: **tăng trưởng doanh thu thuần TTM** (%%), **tăng trưởng LN thuần '
         'từ HĐKD TTM** (%%), và **đòn bẩy hoạt động** = tăng trưởng LN thuần từ HĐKD ÷ tăng trưởng doanh thu (lần). '
         'Mã nào có đòn bẩy hoạt động cao nhất?' % (', '.join(syms), TTM_TXT, PRIOR_TXT))
    ex = {'values': {s: {'rev_growth': 0, 'op_growth': 0, 'op_leverage': 0} for s in syms} | {'highest': 'MÃ'},
          'unit': '% / lần', 'period': '(kỳ được hỏi)', 'source': TOOL, 'note': '(tuỳ chọn)'}
    exp = []
    for s in syms:
        exp += [val('values.%s.rev_growth' % s, rg[s], PCT), val('values.%s.op_growth' % s, og[s], PCT),
                val('values.%s.op_leverage' % s, ol[s], {'abs': 0.01})]
    exp.append(tokens('values.highest', top, syms))
    oracle = "def _g(s, n): return pct(ttm(s, n), ttm(s, n, PRIOR_TTM))\n" + ''.join(
        "check('rg_%s', R(_g('%s', REV)), gold['solution']['%s']['rev_growth'])\n"
        "check('og_%s', R(_g('%s', OP)), gold['solution']['%s']['op_growth'])\n" % (s, s, s, s, s, s) for s in syms) + \
        "check('highest', max(%r, key=lambda s: _g(s, OP) / _g(s, REV)), gold['solution']['highest'])\n" % (syms,)
    sol = {s: {'rev_growth': r4(rg[s]), 'op_growth': r4(og[s]), 'op_leverage': r4(ol[s])} for s in syms} | {'highest': top}
    return c5(tid, 'Đòn bẩy hoạt động TTM %s' % '/'.join(syms), q, ex, sol, exp, oracle, syms, {('q', 'KQKD')})


def margin_task(tid, syms):
    tools = payloads(syms, {('q', 'KQKD')}); c = Ctx(tools)
    now = {s: c.margin_ttm(s, c.GP) for s in syms}; prev = {s: c.margin_ttm(s, c.GP, c.PRIOR_TTM) for s in syms}
    opn = {s: c.margin_ttm(s, c.OP) for s in syms}; opp = {s: c.margin_ttm(s, c.OP, c.PRIOR_TTM) for s in syms}
    d = {s: now[s] - prev[s] for s in syms}; top = max(syms, key=d.get)
    q = ('Với **%s**: tính **biên lợi nhuận gộp TTM** (%%) = tổng lợi nhuận gộp ÷ tổng doanh thu thuần của %s, và cùng chỉ số '
         'của %s; tính **thay đổi** (điểm %%). Tính tương tự **biên LN thuần từ HĐKD** của hai kỳ. Mã nào cải thiện biên gộp '
         'nhiều nhất?' % (', '.join(syms), TTM_TXT, PRIOR_TXT))
    ex = {'values': {s: {'gross_now': 0, 'gross_prev': 0, 'gross_change_pp': 0, 'op_now': 0, 'op_prev': 0} for s in syms}
          | {'best_gross_improvement': 'MÃ'}, 'unit': '%', 'period': '(kỳ được hỏi)', 'source': TOOL, 'note': '(tuỳ chọn)'}
    exp = []
    for s in syms:
        exp += [val('values.%s.gross_now' % s, now[s], PCT), val('values.%s.gross_prev' % s, prev[s], PCT),
                val('values.%s.gross_change_pp' % s, d[s], PCT), val('values.%s.op_now' % s, opn[s], PCT),
                val('values.%s.op_prev' % s, opp[s], PCT)]
    exp.append(tokens('values.best_gross_improvement', top, syms))
    oracle = ''.join("check('gm_%s', R(margin_ttm('%s', GP)), gold['solution']['%s']['gross_now'])\n"
                     "check('om_%s', R(margin_ttm('%s', OP, PRIOR_TTM)), gold['solution']['%s']['op_prev'])\n"
                     % (s, s, s, s, s, s) for s in syms) + \
        "check('best', max(%r, key=lambda s: margin_ttm(s, GP) - margin_ttm(s, GP, PRIOR_TTM)), gold['solution']['best_gross_improvement'])\n" % (syms,)
    sol = {s: {'gross_now': r4(now[s]), 'gross_prev': r4(prev[s]), 'gross_change_pp': r4(d[s]), 'op_now': r4(opn[s]),
               'op_prev': r4(opp[s])} for s in syms} | {'best_gross_improvement': top}
    return c5(tid, 'Biên lợi nhuận TTM %s' % '/'.join(syms), q, ex, sol, exp, oracle, syms, {('q', 'KQKD')})


def dupont_task(tid, a, b):
    syms = [a, b]
    tools = payloads(syms, {('y', 'KQKD'), ('y', 'CDKT')}); c = Ctx(tools)
    dp = {s: c.dupont(s) for s in syms}; driver = c.dupont_driver(a, b)
    q = ('Phân tích **DuPont năm 2025** cho **%s** và **%s**: biên lợi nhuận ròng (%%) = LNST 2025 ÷ doanh thu thuần 2025 × 100; '
         'vòng quay tài sản (lần) = doanh thu thuần 2025 ÷ bình quân tổng tài sản cuối 2024 và cuối 2025; hệ số nhân vốn (lần) = '
         'bình quân tổng tài sản ÷ bình quân vốn chủ sở hữu (cuối 2024, cuối 2025); ROE (%%) = tích ba thành phần. %s'
         'Thành phần nào giải thích nhiều nhất chênh lệch ROE giữa hai mã, tức có |ln(giá trị %s ÷ giá trị %s)| lớn nhất? '
         'Ghi `driver` là `margin`, `turnover` hoặc `leverage`.' % (a, b, DEF_EQ, a, b))
    ex = {'values': {s: {'net_margin': 0, 'asset_turnover': 0, 'equity_multiplier': 0, 'roe': 0} for s in syms}
          | {'driver': 'margin/turnover/leverage'}, 'unit': '% / lần', 'period': '(kỳ được hỏi)', 'source': TOOL, 'note': '(tuỳ chọn)'}
    exp = []
    for s in syms:
        exp += [val('values.%s.net_margin' % s, dp[s]['margin'], PCT), val('values.%s.asset_turnover' % s, dp[s]['turnover'], RATIO),
                val('values.%s.equity_multiplier' % s, dp[s]['leverage'], RATIO), val('values.%s.roe' % s, dp[s]['roe'], PCT)]
    exp.append(tokens('values.driver', driver, ['margin', 'turnover', 'leverage']))
    oracle = ''.join("check('roe_%s', R(dupont('%s')['roe']), gold['solution']['%s']['roe'])\n" % (s, s, s) for s in syms) + \
        "check('driver', dupont_driver('%s', '%s'), gold['solution']['driver'])\n" % (a, b)
    sol = {s: {'net_margin': r4(dp[s]['margin']), 'asset_turnover': r4(dp[s]['turnover']), 'equity_multiplier': r4(dp[s]['leverage']),
               'roe': r4(dp[s]['roe'])} for s in syms} | {'driver': driver}
    return c5(tid, 'DuPont 2025 %s/%s' % (a, b), q, ex, sol, exp, oracle, syms, {('y', 'KQKD'), ('y', 'CDKT')})


def cagr_task(tid, syms):
    tools = payloads(syms, {('y', 'KQKD')}); c = Ctx(tools)
    rv = {s: c.cagr(s, c.REV) for s in syms}; ni = {s: c.cagr(s, c.NIP) for s in syms}; top = max(syms, key=ni.get)
    q = ('Với **%s**: tính **CAGR doanh thu thuần** và **CAGR LNST** (%%/năm) giai đoạn **2021→2025** (4 năm) = '
         '((giá trị 2025 ÷ giá trị 2021)^(1/4) − 1) × 100. %sMã nào có CAGR LNST cao nhất?' % (', '.join(syms), DEF_EQ))
    ex = {'values': {s: {'revenue_cagr': 0, 'profit_cagr': 0} for s in syms} | {'highest_profit_cagr': 'MÃ'},
          'unit': '%/năm', 'period': '(kỳ được hỏi)', 'source': TOOL, 'note': '(tuỳ chọn)'}
    exp = []
    for s in syms:
        exp += [val('values.%s.revenue_cagr' % s, rv[s], PCT), val('values.%s.profit_cagr' % s, ni[s], PCT)]
    exp.append(tokens('values.highest_profit_cagr', top, syms))
    oracle = ''.join("check('rv_%s', R(cagr('%s', REV)), gold['solution']['%s']['revenue_cagr'])\n"
                     "check('ni_%s', R(cagr('%s', NIP)), gold['solution']['%s']['profit_cagr'])\n" % (s, s, s, s, s, s) for s in syms)
    sol = {s: {'revenue_cagr': r4(rv[s]), 'profit_cagr': r4(ni[s])} for s in syms} | {'highest_profit_cagr': top}
    return c5(tid, 'CAGR 2021–2025 %s' % '/'.join(syms), q, ex, sol, exp, oracle, syms, {('y', 'KQKD')})


def leverage_task(tid, syms):
    tools = payloads(syms, {('q', 'CDKT')}); c = Ctx(tools)
    de = {s: c.debt_to_equity(s, 'Q2/2026') for s in syms}; dp = {s: c.debt_to_equity(s, 'Q2/2025') for s in syms}
    cr = {s: c.current_ratio(s) for s in syms}; ch = {s: de[s] - dp[s] for s in syms}; best = min(syms, key=ch.get)
    q = ('Với **%s**: tại **cuối Q2/2026** tính **nợ phải trả ÷ vốn chủ sở hữu** (lần) và **thanh toán hiện hành** = tài sản ngắn hạn '
         '÷ nợ ngắn hạn (lần); tính nợ phải trả ÷ vốn chủ sở hữu tại **cuối Q2/2025** và **thay đổi** (lần) giữa hai thời điểm. %s'
         'Mã nào giảm đòn bẩy nhiều nhất (thay đổi nhỏ nhất)?' % (', '.join(syms), DEF_EQ))
    ex = {'values': {s: {'de_now': 0, 'de_prev': 0, 'de_change': 0, 'current_ratio': 0} for s in syms} | {'most_deleveraged': 'MÃ'},
          'unit': 'lần', 'period': '(kỳ được hỏi)', 'source': TOOL, 'note': '(tuỳ chọn)'}
    exp = []
    for s in syms:
        exp += [val('values.%s.de_now' % s, de[s], RATIO), val('values.%s.de_prev' % s, dp[s], RATIO),
                val('values.%s.de_change' % s, ch[s], RATIO), val('values.%s.current_ratio' % s, cr[s], RATIO)]
    exp.append(tokens('values.most_deleveraged', best, syms))
    oracle = ''.join("check('de_%s', R(debt_to_equity('%s', 'Q2/2026')), gold['solution']['%s']['de_now'])\n"
                     "check('cr_%s', R(current_ratio('%s')), gold['solution']['%s']['current_ratio'])\n" % (s, s, s, s, s, s) for s in syms)
    sol = {s: {'de_now': r4(de[s]), 'de_prev': r4(dp[s]), 'de_change': r4(ch[s]), 'current_ratio': r4(cr[s])} for s in syms} \
        | {'most_deleveraged': best}
    return c5(tid, 'Đòn bẩy tài chính %s' % '/'.join(syms), q, ex, sol, exp, oracle, syms, {('q', 'CDKT')})


def yoy_task(tid, syms):
    tools = payloads(syms, {('q', 'KQKD')}); c = Ctx(tools)
    rg = {s: c.pct(c.q(s, c.REV, 'Q2/2026'), c.q(s, c.REV, 'Q2/2025')) for s in syms}
    ng = {s: c.pct(c.q(s, c.NIP, 'Q2/2026'), c.q(s, c.NIP, 'Q2/2025')) for s in syms}
    win = sorted(s for s in syms if ng[s] > rg[s])
    q = ('Với **%s**: tính tăng trưởng **cùng kỳ** của **Q2/2026 so với Q2/2025** (%%) cho doanh thu thuần và LNST. %s'
         'Liệt kê **các mã có tăng trưởng LNST cao hơn tăng trưởng doanh thu** vào `profit_outgrows_revenue`.' % (', '.join(syms), DEF_EQ))
    ex = {'values': {s: {'revenue_yoy': 0, 'profit_yoy': 0} for s in syms} | {'profit_outgrows_revenue': ['MÃ1', '...']},
          'unit': '%', 'period': '(kỳ được hỏi)', 'source': TOOL, 'note': '(tuỳ chọn)'}
    exp = []
    for s in syms:
        exp += [val('values.%s.revenue_yoy' % s, rg[s], PCT), val('values.%s.profit_yoy' % s, ng[s], PCT)]
    exp.append({'type': 'set', 'path': 'values.profit_outgrows_revenue', 'gold': win})
    oracle = "def _y(s, n): return pct(q(s, n, 'Q2/2026'), q(s, n, 'Q2/2025'))\n" + ''.join(
        "check('ng_%s', R(_y('%s', NIP)), gold['solution']['%s']['profit_yoy'])\n" % (s, s, s) for s in syms) + \
        "check('set', sorted(s for s in %r if _y(s, NIP) > _y(s, REV)), gold['solution']['profit_outgrows_revenue'])\n" % (syms,)
    sol = {s: {'revenue_yoy': r4(rg[s]), 'profit_yoy': r4(ng[s])} for s in syms} | {'profit_outgrows_revenue': win}
    return c5(tid, 'Tăng trưởng cùng kỳ Q2/2026 %s' % '/'.join(syms), q, ex, sol, exp, oracle, syms, {('q', 'KQKD')})


def sector_task(tid, syms, sector):
    tools = payloads(syms, {('q', 'KQKD')}); c = Ctx(tools)
    agg = lambda qs: sum(c.ttm(s, c.NIP, qs) for s in syms) / sum(c.ttm(s, c.REV, qs) for s in syms) * 100
    now, prev = agg(c.TTM), agg(c.PRIOR_TTM)
    dni = {s: c.ttm(s, c.NIP) - c.ttm(s, c.NIP, c.PRIOR_TTM) for s in syms}; top = max(syms, key=lambda s: abs(dni[s]))
    total = sum(c.ttm(s, c.NIP) for s in syms) / 10 ** 9
    q = ('Gộp **%s** thành một nhóm %s. Tính **biên LNST gộp của nhóm** (%%) = tổng LNST của cả nhóm ÷ tổng doanh thu thuần của '
         'cả nhóm, cho %s và cho %s, và **thay đổi** (điểm %%); tính **tổng LNST của nhóm** trong %s (tỷ đồng). %s'
         'Mã nào có thay đổi LNST TTM (tuyệt đối, tỷ đồng) lớn nhất giữa hai kỳ?' % (', '.join(syms), sector, TTM_TXT, PRIOR_TXT, TTM_TXT, DEF_EQ))
    ex = {'values': {'group_margin_now': 0, 'group_margin_prev': 0, 'change_pp': 0, 'group_profit_ttm_bn': 0, 'largest_change': 'MÃ'},
          'unit': '% / tỷ đồng', 'period': '(kỳ được hỏi)', 'source': TOOL, 'note': '(tuỳ chọn)'}
    exp = [val('values.group_margin_now', now, PCT), val('values.group_margin_prev', prev, PCT), val('values.change_pp', now - prev, PCT),
           val('values.group_profit_ttm_bn', total, MONEY), tokens('values.largest_change', top, syms)]
    oracle = ("_S = %r\n" % (syms,) + "def _agg(qs): return sum(ttm(s, NIP, qs) for s in _S) / sum(ttm(s, REV, qs) for s in _S) * 100\n"
              "check('now', R(_agg(TTM)), gold['solution']['group_margin_now'])\n"
              "check('prev', R(_agg(PRIOR_TTM)), gold['solution']['group_margin_prev'])\n"
              "check('top', max(_S, key=lambda s: abs(ttm(s, NIP) - ttm(s, NIP, PRIOR_TTM))), gold['solution']['largest_change'])\n")
    sol = {'group_margin_now': r4(now), 'group_margin_prev': r4(prev), 'change_pp': r4(now - prev), 'group_profit_ttm_bn': r4(total),
           'largest_change': top}
    return c5(tid, 'Biên LNST nhóm %s' % sector, q, ex, sol, exp, oracle, syms, {('q', 'KQKD')})


# ------------------------------------------------------------------ M6: finance-analysis memory
CONV = {
    'ttm': ('Khi tính ROE cho tôi, luôn dùng **ROE TTM** = tổng LNST của CĐ cty mẹ 4 quý Q3/2025–Q2/2026 ÷ bình quân vốn chủ sở hữu '
            'tại 5 thời điểm cuối quý Q2/2025, Q3/2025, Q4/2025, Q1/2026, Q2/2026 × 100.'),
    'fy': ('Khi tính ROE cho tôi, luôn dùng **ROE năm 2025** = LNST của CĐ cty mẹ năm 2025 ÷ vốn chủ sở hữu cuối năm 2025 × 100 '
           '(số liệu theo năm, không dùng số quý).'),
}


def roe_by(c, conv, s):
    return c.roe_ttm(s) if conv == 'ttm' else c.roe_fy(s)


def m6(tid, split, sub, title, syms, conv, roe_min, debt_max, variant=0, update=None, revoke=None):
    needs = {('q', 'KQKD'), ('q', 'CDKT')} | ({('y', 'KQKD'), ('y', 'CDKT')} if conv == 'fy' else set())
    tools = payloads(syms, needs); c = Ctx(tools)
    roe = {s: roe_by(c, conv, s) for s in syms}; dr = {s: c.debt_ratio(s) for s in syms}
    f_conv = ('conv-roe', CONV[conv])
    f_roe = ('crit-roe', 'Tôi chỉ xét doanh nghiệp có ROE (theo đúng cách tính tôi đã dặn) trên %s%%.' % roe_min)
    f_debt = ('crit-debt', 'Tôi chỉ xét doanh nghiệp có tỷ lệ nợ phải trả ÷ tổng tài sản tại cuối Q2/2026 dưới %s%%.' % debt_max)
    active_roe, active_debt = roe_min, debt_max
    if update:
        active_debt = update
    passes = sorted(s for s in syms if roe[s] > active_roe and (revoke == 'crit-debt' or dr[s] < active_debt))
    final_q = ('Trong 4 mã **%s**: mã nào thỏa **tất cả các tiêu chí tôi đã nhờ bạn ghi nhớ** (còn hiệu lực)? Ghi ROE của từng mã '
               '**theo đúng cách tính tôi đã dặn** (%%) và tỷ lệ nợ phải trả ÷ tổng tài sản tại cuối Q2/2026 (%%). '
               'Số liệu lấy từ `financial_statements` (`statement="KQKD"`/`"CDKT"`, `period="quarter"` hoặc `"year"`).'
               % ', '.join(syms))
    ex = {'values': {'pass': ['MÃ1', '...'], **{s: {'roe': 0, 'debt_ratio': 0} for s in syms}},
          'period': '(kỳ dữ liệu)', 'source': TOOL, 'note': 'chỉ số từng mã dùng để lọc'}
    final_text = final_q + '\n\n' + ms.contract_text(ex)
    facts = [f_conv, f_roe, f_debt]
    d = ms.DISTRACT[variant % len(ms.DISTRACT)]
    final = {'text': final_text, 'final': True}
    if sub == 'M6a':
        sessions = [{'id': 'S1', 'turns': [ms.remember(*f_conv)]},
                    {'id': 'S2', 'turns': [ms.remember(*f_roe), ms.remember(*f_debt), ms.chat(d)]},
                    {'id': 'S3', 'turns': [final]}]
    elif sub == 'M6b':
        new = 'Tôi chỉ xét doanh nghiệp có tỷ lệ nợ phải trả ÷ tổng tài sản tại cuối Q2/2026 dưới %s%%.' % update
        text = 'Cập nhật ghi nhớ của tôi: ' + new
        sessions = [{'id': 'S1', 'turns': [ms.remember(*f) for f in facts]},
                    {'id': 'S2', 'turns': [ms.cmd(text, [ms.put('crit-debt', new, text)]), ms.chat(d)]},
                    {'id': 'S3', 'turns': [final]}]
    elif sub == 'M6c':
        text = 'Xoá ghi nhớ: bỏ tiêu chí "%s", từ nay không áp dụng nữa.' % f_debt[1]
        sessions = [{'id': 'S1', 'turns': [ms.remember(*f) for f in facts]},
                    {'id': 'S2', 'turns': [ms.cmd(text, [ms.delete('crit-debt', text)]), ms.chat(d)]},
                    {'id': 'S3', 'turns': [final]}]
    else:
        raise ValueError(sub)
    exp = [{'type': 'set', 'path': 'values.pass', 'gold': passes}]
    for s in syms:
        exp += [val('values.%s.roe' % s, roe[s], PCT), val('values.%s.debt_ratio' % s, dr[s], PCT)]
    exp.append(src())
    fn = 'roe_ttm' if conv == 'ttm' else 'roe_fy'
    oracle = (LIB + ''.join("check('roe_%s', R(%s('%s')), gold['solution']['values']['%s']['roe'])\n" % (s, fn, s, s) for s in syms)
              + "check('pass', sorted(s for s in %r if %s(s) > %r and (%r or debt_ratio(s) < %r)), gold['solution']['pass'])\n"
              % (syms, fn, active_roe, revoke == 'crit-debt', active_debt))
    sol = {'pass': passes, 'convention': conv, 'roe_min': active_roe, 'debt_max': None if revoke else active_debt,
           'values': {s: {'roe': r4(roe[s]), 'debt_ratio': r4(dr[s])} for s in syms}}
    return {'kind': 'M6', 'tid': tid, 'split': split, 'tier': 'M6', 'subtier': sub, 'title': title, 'sessions': sessions,
            'q': {'payloads': tools, 'solution': sol, 'expects': exp, 'oracle': oracle}}


def build():
    main = [roe_ttm_task('fin-c5-roe-601', ['VNM', 'FPT', 'MWG']), roe_ttm_task('fin-c5-roe-602', ['HPG', 'GAS', 'DCM']),
            oplev_task('fin-c5-oplev-603', ['MWG', 'PNJ', 'GVR']), oplev_task('fin-c5-oplev-604', ['HPG', 'DCM', 'REE']),
            margin_task('fin-c5-margin-605', ['VNM', 'SAB', 'DHG']), margin_task('fin-c5-margin-606', ['HPG', 'DPM', 'NTP']),
            dupont_task('fin-c5-dupont-607', 'MWG', 'FPT'), dupont_task('fin-c5-dupont-608', 'VNM', 'SAB'),
            cagr_task('fin-c5-cagr-609', ['FPT', 'PNJ', 'GMD']), cagr_task('fin-c5-cagr-610', ['REE', 'HAH', 'NTP']),
            leverage_task('fin-c5-lev-611', ['FPT', 'FRT', 'VCG']), leverage_task('fin-c5-lev-612', ['GAS', 'HSG', 'KDH']),
            yoy_task('fin-c5-yoy-613', ['VNM', 'SAB', 'FPT', 'HPG']), yoy_task('fin-c5-yoy-614', ['DHG', 'GVR', 'REE', 'VHC']),
            sector_task('fin-c5-sector-615', ['HPG', 'HSG', 'NKG', 'GVR'], 'vật liệu (thép, cao su)'),
            sector_task('fin-c5-sector-616', ['VNM', 'SAB', 'MSN', 'KDC'], 'hàng tiêu dùng')]
    main += [m6('fin-m6-conv-621', 'main', 'M6a', 'Memory M6a — quy ước ROE TTM và ngưỡng (POW/MSN/HPG/GMD)', ['POW', 'MSN', 'HPG', 'GMD'], 'ttm', 15, 60, 0),
             m6('fin-m6-conv-622', 'main', 'M6a', 'Memory M6a — quy ước ROE năm 2025 và ngưỡng (DCM/NTP/FRT/MWG)', ['DCM', 'NTP', 'FRT', 'MWG'], 'fy', 20, 70, 1),
             m6('fin-m6-conv-623', 'main', 'M6a', 'Memory M6a — quy ước ROE TTM và ngưỡng (DPM/GVR/SAB/VCG)', ['DPM', 'GVR', 'SAB', 'VCG'], 'ttm', 12, 50, 2),
             m6('fin-m6-conv-624', 'main', 'M6a', 'Memory M6a — quy ước ROE năm 2025 và ngưỡng (HPG/PNJ/DHG/KDH)', ['HPG', 'PNJ', 'DHG', 'KDH'], 'fy', 15, 50, 0),
             m6('fin-m6-upd-625', 'main', 'M6b', 'Memory M6b — cập nhật ngưỡng nợ (VNM/GAS/PLX/PC1)', ['VNM', 'GAS', 'PLX', 'PC1'], 'ttm', 12, 50, 1, update=70),
             m6('fin-m6-upd-626', 'main', 'M6b', 'Memory M6b — cập nhật ngưỡng nợ (FPT/REE/HAH/PVS)', ['FPT', 'REE', 'HAH', 'PVS'], 'fy', 10.5, 50, 2, update=42),
             m6('fin-m6-upd-627', 'main', 'M6b', 'Memory M6b — cập nhật ngưỡng nợ (MWG/FRT/DCM/IMP)', ['MWG', 'FRT', 'DCM', 'IMP'], 'ttm', 15.5, 30, 0, update=70),
             m6('fin-m6-rev-628', 'main', 'M6c', 'Memory M6c — bỏ tiêu chí nợ (MSN/PLX/VJC/HPG)', ['MSN', 'PLX', 'VJC', 'HPG'], 'ttm', 11, 50, 1, revoke='crit-debt'),
             m6('fin-m6-rev-629', 'main', 'M6c', 'Memory M6c — bỏ tiêu chí nợ (FRT/MWG/VGS/PNJ)', ['FRT', 'MWG', 'VGS', 'PNJ'], 'fy', 16, 60, 2, revoke='crit-debt'),
             m6('fin-m6-rev-630', 'main', 'M6c', 'Memory M6c — bỏ tiêu chí nợ (GEX/POW/PVS/CTD)', ['GEX', 'POW', 'PVS', 'CTD'], 'ttm', 10, 55, 0, revoke='crit-debt')]
    pilot = [roe_ttm_task('fin-c5-roe-681', ['DHG', 'IMP', 'TRA']), oplev_task('fin-c5-oplev-682', ['GMD', 'NTP', 'HAH']),
             dupont_task('fin-c5-dupont-683', 'PNJ', 'DHG'), yoy_task('fin-c5-yoy-684', ['DCM', 'GAS', 'NTP', 'MWG']),
             m6('fin-m6-conv-691', 'pilot', 'M6a', 'Memory M6a — quy ước ROE TTM và ngưỡng (TRA/VHC/IMP/HAH)', ['TRA', 'VHC', 'IMP', 'HAH'], 'ttm', 15, 35, 1),
             m6('fin-m6-upd-692', 'pilot', 'M6b', 'Memory M6b — cập nhật ngưỡng nợ (GMD/GVR/REE/DGC)', ['GMD', 'GVR', 'REE', 'DGC'], 'fy', 9, 30, 2, update=40)]
    for t in main:
        t.setdefault('split', 'main')
    for t in pilot:
        t.setdefault('split', 'pilot')
    return main, pilot


def write_c5(split, s):
    d = STUDY / 'tasks' / split / s['tid']
    if d.exists():
        shutil.rmtree(d)
    (d / 'environment').mkdir(parents=True); (d / 'solution').mkdir(); (d / 'tests').mkdir()
    shutil.copy(cs.TEMPLATE / 'tests/grader.py', d / 'tests/grader.py')
    tools = payloads(s['syms'], s['needs'])
    pl = {'snapshot_date': '2026-11-01', 'note': 'Envelope MCP financial_statements ghi 2026-11-24 (kỳ ≤ Q2/2026, năm ≤ 2025); '
          'xem audits/snapshot-extension-2026-11-24/RECEIPT.json.', 'tools': tools}
    (d / 'environment/payloads.json').write_text(json.dumps(pl, ensure_ascii=False, indent=1) + '\n')
    tmpl = (cs.TEMPLATE / 'instruction.md').read_text(encoding='utf-8')
    contract = tmpl[tmpl.index('## Ràng buộc chung'):]
    head = '# %s\n\n%s\n\n## Yêu cầu trả lời\nTrả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n```json\n%s\n```\n\n\n' % (
        s['title'], s['question'] + '\n\n' + cs.ROUNDING, json.dumps(s['example'], ensure_ascii=False, indent=2))
    (d / 'instruction.md').write_text(head + contract, encoding='utf-8')
    prov = [{'tool': TOOL, 'source': 'vietstock', 'as_of': RAW['recorded_at'], 'matched_entry_id': k,
             'response_sha256': cs.digest(e['envelope'])} for k, e in tools.items()]
    gold = {'task_id': s['tid'], 'scoring': 'value', 'solution': s['solution'], 'as_of': RAW['recorded_at'], 'split': split,
            'expects': s['expects'], 'contract_version': 2, 'stratum': 'compute', 'tier': 'C5',
            'notes': 'Fundamental compute stratum (amendment 2026-11-24). Gold from tools/finance_stratum_lib.py on the task payloads.',
            'provenance_contract': prov, 'provenance_catalog': prov,
            'payload_sha256': hashlib.sha256((d / 'environment/payloads.json').read_bytes()).hexdigest(),
            'required_payload_keys': sorted(tools)}
    (d / 'solution/gold.json').write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n')
    o = (cs.TEMPLATE / 'solution/oracle.py').read_text(encoding='utf-8')
    pre, mark, rest = o.partition('# === thân oracle ===\n')
    _, sep, tail = rest.partition('\nif problems:')
    assert mark and sep
    (d / 'solution/oracle.py').write_text(pre + mark + LIB + '\n' + s['oracle'] + '\n\nif problems:' + tail, encoding='utf-8')
    toml = (cs.TEMPLATE / 'task.toml').read_text(encoding='utf-8')
    toml = toml.replace('# Task benchmark harness tài chính (bộ 200+50) — sinh bởi tools/build_main.py',
                        '# Fundamental compute stratum — amendment 2026-11-24, tools/build_finance_stratum_20261124.py')
    for k, v in (('id', s['tid']), ('title', s['title'].replace('"', "'")), ('created', CREATED), ('level', 'C5'),
                 ('family', 'C5 fundamental compute'), ('financebench_type', 'financial statement analysis'),
                 ('entity', '+'.join(s['syms'])), ('split', split)):
        toml = re.sub(r'^%s = ".*"$' % k, '%s = "%s"' % (k, v), toml, flags=re.M)
    toml = re.sub(r'^tools_expected = .*$', 'tools_expected = ["%s"]' % TOOL, toml, flags=re.M)
    toml = toml.replace('confirmatory_eligible = true', 'confirmatory_eligible = true\nstratum = "compute"\ntier = "C5"')
    (d / 'task.toml').write_text(toml, encoding='utf-8')
    return d


def write_m6(t):
    d = ms.write(t)
    toml = (d / 'task.toml').read_text(encoding='utf-8')
    toml = toml.replace('# Native-memory stratum — amendment 2026-11-11 (d), tools/build_memory_stratum_20261111.py',
                        '# Finance-analysis memory stratum — amendment 2026-11-24, tools/build_finance_stratum_20261124.py')
    toml = re.sub(r'^created = ".*"$', 'created = "%s"' % CREATED, toml, flags=re.M)
    toml = re.sub(r'^family = ".*"$', 'family = "M6 finance memory"', toml, flags=re.M)
    (d / 'task.toml').write_text(toml, encoding='utf-8')
    gold = json.loads((d / 'solution/gold.json').read_text())
    gold['notes'] = 'Finance-analysis memory stratum (amendment 2026-11-24): remembered ROE convention + thresholds.'
    (d / 'solution/gold.json').write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n')
    turns = json.loads((d / 'environment/turns.json').read_text())
    turns['note'] = 'Finance-analysis memory (amendment 2026-11-24). Same sessions for every arm; memory_command = OT /nho form, chat for others.'
    (d / 'environment/turns.json').write_text(json.dumps(turns, ensure_ascii=False, indent=1) + '\n')
    return d


def main():
    main_specs, pilot_specs = build()
    assert len(main_specs) == 26 and len(pilot_specs) == 6 and len({t['tid'] for t in main_specs + pilot_specs}) == 32
    receipt = {}
    for t in main_specs + pilot_specs:
        d = write_c5(t['split'], t) if t['kind'] == 'C5' else write_m6(t)
        sol = t['solution'] if t['kind'] == 'C5' else t['q']['solution']
        receipt[t['tid']] = {'split': t['split'], 'tier': t.get('subtier', t['tier']), 'solution': sol,
                             'files': {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(d.rglob('*')) if p.is_file()}}
    out = STUDY / 'audits/taskset-revision-2026-11-24'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'FINANCE-BUILD.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    for k, v in receipt.items():
        print(k, v['split'], v['tier'], json.dumps(v['solution'], ensure_ascii=False)[:160])


if __name__ == '__main__':
    main()
