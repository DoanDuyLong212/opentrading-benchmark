#!/usr/bin/env python3
"""Amendment 2026-11-11 (d): compute stratum C1–C4 (main 30: fin-c*-401..430, holdout 7: fin-c*-951..957).

Data: audits/snapshot-extension-2026-11-11/history-120.json (120 sessions ending 30/10/2026, verified against the
frozen snapshot). Gold is computed here with Decimal; the oracle body recomputes it independently with floats from
the task's own payloads.json. Difficulty axis = number of operands and chain length; tolerance is uniform across
tiers: percentages abs 0.05 pp, ratios abs 0.005, levels/money/volumes rel 0.001; every question asks for 2-decimal
rounding so that rounding is never the failure. Only operations OpenTrading has natively
(compute pct_change/mean/sum/ratio/relative_strength/rank/share/annualize; calculate + - * / ^ sqrt ln exp sum avg).
Idempotent: rewrites the task directories it owns.
"""
import hashlib, json, re, shutil, sys
from decimal import Decimal as D, getcontext
from pathlib import Path

getcontext().prec = 40
STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from mcp_snapshot_server import digest  # noqa: E402

EXT = STUDY / 'audits/snapshot-extension-2026-11-11'
H = json.loads((EXT / 'history-120.json').read_text())
REC = json.loads((EXT / 'RECEIPT.json').read_text())
TEMPLATE = STUDY / 'tasks/main/fin-l3-index-216'
INDEXES = {'VNINDEX', 'VN30'}
S30 = 'phiên 30/10/2026'
PERIOD_END = ['30/10', '30-10', '30.10', '2026-10-30']
PCT = {'abs': 0.05}
LVL = {'rel': 0.001}
RAT = {'abs': 0.005}
ROUNDING = ('Làm tròn kết quả tới **2 chữ số thập phân** (khối lượng và số tiền đồng: làm tròn tới số nguyên); '
            'xếp hạng/so sánh dùng số chưa làm tròn.')


def key(sym):
    return ('idx:' if sym in INDEXES else 'hist:') + sym


def tool(sym):
    return 'vn_index_ohlcv' if sym in INDEXES else 'vn_quote_history'


def envelope(sym):
    rows = H[sym]
    unit = 'điểm' if sym in INDEXES else 'nghìn đồng/cổ phiếu (64,27 = 64.270 đ)'
    return {'tool': tool(sym),
            'params': {'symbol': sym, 'count': 120} if sym in INDEXES else {'symbol': sym, 'days': 170},
            'envelope': {'data': {'symbol': sym, 'closes': [{'t': r['t'], 'c': r['c'], 'v': r['v']} for r in rows]},
                         'units': {'c': unit, 'v': 'cổ phiếu'},
                         'provenance': {'source': 'vnstock', 'as_of': REC['recorded_at'], 'timezone': 'Asia/Ho_Chi_Minh',
                                        'data_time': '2026-10-30'},
                         'availability': 'available',
                         'warnings': ['Lịch sử 120 phiên (13/05–30/10/2026) ghi lại cho snapshot 2026-11-01; '
                                      'không có phiên sau 30/10/2026.']}}


def c(sym, back=0):
    """Close `back` sessions before 30/10 (back=0 is 30/10)."""
    return D(str(H[sym][-1 - back]['c']))


def v(sym, back=0):
    return D(H[sym][-1 - back]['v'])


def t(sym, back=0):
    x = H[sym][-1 - back]['t']
    return '%s/%s/%s' % (x[8:], x[5:7], x[:4])


def mean_c(sym, n):
    return sum(c(sym, i) for i in range(n)) / n


def mean_v(sym, n):
    return sum(v(sym, i) for i in range(n)) / n


def pct(sym, n):
    return (c(sym) / c(sym, n) - 1) * 100


def r4(x):
    return float(round(D(x), 4))


def val(path, gold, tol):
    return {'type': 'value', 'path': path, 'gold': r4(gold), 'tol': tol}


def unit(path, accept):
    return {'type': 'unit', 'path': path, 'accept': accept}


def src(syms):
    tools = sorted({tool(s) for s in syms})
    if len(tools) == 1:
        return {'type': 'str', 'path': 'source', 'accept': tools}
    return {'type': 'str_all', 'path': 'source', 'accept': tools}


def period():
    return {'type': 'period', 'path': 'period', 'accept': PERIOD_END}


def tokens(path, win, others):
    return {'type': 'tokens', 'path': path, 'accept': [win], 'reject': [o for o in others if o != win]}


ORACLE_LIB = '''
from decimal import Decimal as _D
def _rows(s):
    k = ('idx:' if s in ('VNINDEX', 'VN30') else 'hist:') + s
    return env(k)['data']['closes']
def C(s, back=0): return _D(str(_rows(s)[-1 - back]['c']))
def V(s, back=0): return _D(_rows(s)[-1 - back]['v'])
def MC(s, n): return sum(C(s, i) for i in range(n)) / n
def MV(s, n): return sum(V(s, i) for i in range(n)) / n
def P(s, n): return (C(s) / C(s, n) - 1) * 100
def R(x): return float(round(_D(x), 4))
for _s in SYMS:
    check('rows_' + _s, len(_rows(_s)), 120)
    check('last_' + _s, _rows(_s)[-1]['t'], '2026-10-30')
'''


def spec(tid, tier, title, question, example, solution, expects, oracle, syms):
    # The question fixes every window by date, so `period` is not graded in this stratum (mechanics dry-run
    # 2026-11-11: correct values failed the strict period check only because the field also named the window,
    # the A8 pattern; arm-symmetric grader-validity fix, disclosed in the amendment).
    expects = [e for e in expects if e.get('type') != 'period']
    return dict(tid=tid, tier=tier, title=title, question=question, example=example, solution=solution,
                expects=expects + [src(syms)], oracle=oracle, syms=sorted(set(syms)))


def money_unit():
    return unit('unit', ['đồng', 'VND', 'vnđ'])


def pct_unit():
    return unit('unit', ['%', 'phần trăm'])


def pct_change_task(tid, tier, sym, n, extra_title=''):
    g = pct(sym, n)
    return spec(tid, tier, '%% thay đổi %s %d phiên%s' % (sym, n, extra_title),
                ('**%s** thay đổi bao nhiêu **%%** từ giá đóng cửa phiên **%s** đến giá đóng cửa **%s** (%d phiên giao dịch)?'
                 % (sym, t(sym, n), S30, n)),
                {'value': 0, 'unit': '%', 'period': '(kỳ được hỏi)', 'source': tool(sym), 'note': '(tuỳ chọn)'},
                {'value': r4(g)}, [val('value', g, PCT), pct_unit(), period()],
                "check('value', R(P(%r, %d)), gold['solution']['value'])\n" % (sym, n), [sym])


def mean_task(tid, tier, sym, n):
    g = mean_c(sym, n); gap = (c(sym) / g - 1) * 100
    u = 'điểm' if sym in INDEXES else 'nghìn đồng/cổ phiếu'
    return spec(tid, tier, 'MA%d và độ lệch %s' % (n, sym),
                ('Tính **trung bình giá đóng cửa %d phiên** gần nhất của **%s** (MA%d, gồm cả %s), đơn vị **%s**, và '
                 'giá đóng cửa %s **cao/thấp hơn MA%d bao nhiêu %%** (giá/MA − 1)?' % (n, sym, n, S30, u, S30, n)),
                {'values': {'ma': 0, 'gap_pct': 0}, 'unit': u, 'period': '(kỳ được hỏi)', 'source': tool(sym),
                 'note': '(tuỳ chọn)'},
                {'ma': r4(g), 'gap_pct': r4(gap)},
                [val('values.ma', g, LVL), val('values.gap_pct', gap, PCT), period()],
                ("check('ma', R(MC(%r, %d)), gold['solution']['ma'])\n"
                 "check('gap', R((C(%r) / MC(%r, %d) - 1) * 100), gold['solution']['gap_pct'])\n") % (sym, n, sym, sym, n),
                [sym])


def portfolio_task(tid, tier, pos, n):
    """pos: {sym: (qty)}; value change over n sessions, money in đồng."""
    syms = list(pos)
    now = sum(D(q) * c(s) * 1000 for s, q in pos.items())
    then = sum(D(q) * c(s, n) * 1000 for s, q in pos.items())
    pl = now - then; ret = (now / then - 1) * 100
    best = max(syms, key=lambda s: D(pos[s]) * (c(s) - c(s, n)))
    holdings = ', '.join('**%s %s cp**' % ('{:,}'.format(q).replace(',', '.'), s) for s, q in pos.items())
    return spec(tid, tier, 'Lãi/lỗ danh mục %d mã sau %d phiên' % (len(syms), n),
                ('Danh mục của tôi giữ nguyên trong %d phiên giao dịch gần nhất: %s. Định giá theo giá đóng cửa: giá trị danh '
                 'mục ở phiên **%s** và ở **%s** là bao nhiêu **đồng**, lãi/lỗ bao nhiêu **đồng** và bao nhiêu **%%**? Vị thế '
                 'nào đóng góp lãi (hoặc lỗ ít nhất) lớn nhất tính bằng đồng?' % (n, holdings, t(syms[0], n), S30)),
                {'values': {'value_start': 0, 'value_end': 0, 'pnl': 0, 'pnl_pct': 0, 'top_contributor': 'MÃ'},
                 'unit': 'đồng', 'period': '(kỳ được hỏi)', 'source': tool(syms[0]), 'note': '(tuỳ chọn)'},
                {'value_start': r4(then), 'value_end': r4(now), 'pnl': r4(pl), 'pnl_pct': r4(ret), 'top_contributor': best},
                [val('values.value_start', then, LVL), val('values.value_end', now, LVL), val('values.pnl', pl, LVL),
                 val('values.pnl_pct', ret, PCT), tokens('values.top_contributor', best, syms), money_unit(), period()],
                ("pos = %r\nnow = sum(_D(q) * C(s) * 1000 for s, q in pos.items())\n"
                 "then = sum(_D(q) * C(s, %d) * 1000 for s, q in pos.items())\n"
                 "check('start', R(then), gold['solution']['value_start'])\ncheck('end', R(now), gold['solution']['value_end'])\n"
                 "check('pnl', R(now - then), gold['solution']['pnl'])\ncheck('pct', R((now / then - 1) * 100), gold['solution']['pnl_pct'])\n"
                 "check('top', max(pos, key=lambda s: _D(pos[s]) * (C(s) - C(s, %d))), gold['solution']['top_contributor'])\n")
                % (pos, n, n), syms)


def eqw_task(tid, tier, syms, n, bench=None):
    p = {s: pct(s, n) for s in syms}; avg = sum(p.values()) / len(p)
    best = max(p, key=p.get)
    sol = {'avg_pct': r4(avg), 'best': best, 'best_pct': r4(p[best])}
    ex = {'values': {'avg_pct': 0, 'best': 'MÃ', 'best_pct': 0}, 'unit': '%', 'period': '(kỳ được hỏi)',
          'source': tool(syms[0]), 'note': '% thay đổi từng mã'}
    exp = [val('values.avg_pct', avg, PCT), tokens('values.best', best, syms), val('values.best_pct', p[best], PCT)]
    q = ('Danh mục **tỷ trọng bằng nhau** gồm %d mã **%s**: tính %% thay đổi giá đóng cửa của từng mã từ phiên **%s** đến '
         '**%s** (%d phiên), rồi **trung bình cộng** các %% đó. Mã nào tăng mạnh nhất (hoặc giảm ít nhất) và bao nhiêu %%?'
         % (len(syms), ', '.join(syms), t(syms[0], n), S30, n))
    orc = ("syms = %r\np = {s: P(s, %d) for s in syms}\navg = sum(p.values()) / len(p)\n"
           "check('avg', R(avg), gold['solution']['avg_pct'])\nb = max(p, key=p.get)\n"
           "check('best', b, gold['solution']['best'])\ncheck('best_pct', R(p[b]), gold['solution']['best_pct'])\n") % (syms, n)
    allsyms = list(syms)
    if bench:
        pb = pct(bench, n); ex['values']['excess_pp'] = 0; sol['excess_pp'] = r4(avg - pb)
        exp.append(val('values.excess_pp', avg - pb, PCT))
        q += ' So với **%s** cùng kỳ, danh mục vượt/thua bao nhiêu **điểm %%** (trung bình − %% thay đổi %s)?' % (bench, bench)
        orc += "check('excess', R(avg - P(%r, %d)), gold['solution']['excess_pp'])\n" % (bench, n)
        allsyms.append(bench); ex['source'] = '%s + %s' % (tool(syms[0]), tool(bench))
    return spec(tid, tier, 'Danh mục đều tỷ trọng %d mã %d phiên' % (len(syms), n), q, ex, sol,
                exp + [pct_unit(), period()], orc, allsyms)


def rel_strength_task(tid, tier, sym, bench, n):
    g = pct(sym, n) - pct(bench, n)
    return spec(tid, tier, 'Sức mạnh tương đối %s vs %s %d phiên' % (sym, bench, n),
                ('Từ phiên **%s** đến **%s** (%d phiên): **%s** tăng/giảm bao nhiêu %%, **%s** bao nhiêu %%, và %s **vượt/thua** '
                 '%s bao nhiêu **điểm %%** (%% của %s − %% của %s)?' % (t(sym, n), S30, n, sym, bench, sym, bench, sym, bench)),
                {'values': {'stock_pct': 0, 'bench_pct': 0, 'relative_pp': 0}, 'unit': 'điểm %', 'period': '(kỳ được hỏi)',
                 'source': '%s + %s' % (tool(sym), tool(bench)), 'note': '(tuỳ chọn)'},
                {'stock_pct': r4(pct(sym, n)), 'bench_pct': r4(pct(bench, n)), 'relative_pp': r4(g)},
                [val('values.stock_pct', pct(sym, n), PCT), val('values.bench_pct', pct(bench, n), PCT),
                 val('values.relative_pp', g, PCT), unit('unit', ['điểm %', 'điểm phần trăm', 'pp', '%']), period()],
                ("check('s', R(P(%r, %d)), gold['solution']['stock_pct'])\ncheck('b', R(P(%r, %d)), gold['solution']['bench_pct'])\n"
                 "check('rel', R(P(%r, %d) - P(%r, %d)), gold['solution']['relative_pp'])\n") % (sym, n, bench, n, sym, n, bench, n),
                [sym, bench])


import compute_hard_templates_20261111 as HT  # noqa: E402


def _get(obj, path):
    for k in path.split('.'):
        obj = obj[k]
    return obj


def hard(tid, tier, made):
    title, question, example, code, fields, syms = made
    syms = list(dict.fromkeys(syms))
    question = re.sub(r'\{T(\w+):(\d+)\}', lambda m: HT.d(H[m.group(1)][-1 - int(m.group(2))]['t']), question)
    envs = {key(x): envelope(x)['envelope'] for x in syms}
    ns = {'env': lambda k: envs[k]}
    exec(HT.LIB + code, ns)
    out = ns['out']
    expects = []
    for path, tol in fields:
        g = _get({'values': out, 'ranking': out.get('ranking')}, path) if path != 'ranking' else out['ranking']
        if tol == 'token':
            expects.append({'type': 'tokens', 'path': path, 'accept': [g], 'reject': [x for x in syms if x != g]})
        elif tol == 'set':
            expects.append({'type': 'set', 'path': path, 'gold': g})
        elif tol == 'order':
            expects.append({'type': 'list_order', 'path': path, 'gold': g})
        else:
            expects.append({'type': 'value', 'path': path, 'gold': g, 'tol': tol})
    ex = dict(example, period='(kỳ được hỏi)', source=' + '.join(sorted({tool(x) for x in syms})), note='(tuỳ chọn) công thức và số đầu vào')
    if 'ranking' in ex:
        ex = {k: ex[k] for k in ('values', 'ranking', 'unit', 'period', 'source', 'note')}
    oracle = HT.LIB + code + "check('out', out, gold['solution'])\n"
    return spec(tid, tier, title, question, ex, out, expects, oracle, syms)


def hard_main():
    return [hard('fin-c3-geo-417', 'C3', HT.geo_ann(['VCB', 'HPG', 'FPT'])),
            hard('fin-c3-logann-418', 'C3', HT.log_ann_vs_bench(['STB', 'MWG', 'VNM', 'SAB'], 'VNINDEX')),
            hard('fin-c3-maladder-419', 'C3', HT.ma_ladder(['VIC', 'VHM', 'MSN', 'GAS'])),
            hard('fin-c3-volregime-420', 'C3', HT.vol_regime(['HPG', 'SSI', 'FPT', 'MWG', 'VNM'])),
            hard('fin-c3-volshare-421', 'C3', HT.vol_share(['ACB', 'STB', 'VPB', 'HDB', 'TPB'])),
            hard('fin-c3-doubling-422', 'C3', HT.doubling('VIC')),
            hard('fin-c3-rschain-423', 'C3', HT.rs_chain(['TCB', 'MBB', 'CTG', 'BID', 'VCB'], 'VN30')),
            hard('fin-c3-geo-424', 'C3', HT.geo_ann(['GVR', 'POW', 'PLX'])),
            hard('fin-c4-stagger-425', 'C4', HT.staggered({'HPG': (3000, 119), 'FPT': (500, 90), 'VCB': (800, 70), 'MWG': (1200, 45),
                                                           'GAS': (400, 30), 'SSI': (2500, 15)})),
            hard('fin-c4-rebal-426', 'C4', HT.rebalanced(['VCB', 'BID', 'CTG', 'MBB', 'TCB', 'ACB'])),
            hard('fin-c4-logann-427', 'C4', HT.log_ann_vs_bench(['VCB', 'BID', 'CTG', 'MBB', 'TCB', 'HPG', 'FPT', 'MWG', 'VNM', 'GAS'], 'VNINDEX')),
            hard('fin-c4-dca-428', 'C4', HT.dca(['FPT', 'MWG', 'VNM'])),
            hard('fin-c4-signal-429', 'C4', HT.signal_portfolio(['ACB', 'STB', 'VPB', 'HDB', 'TPB', 'MBB', 'TCB', 'CTG'])),
            hard('fin-c4-stagger-430', 'C4', HT.staggered({'VIC': (100, 110), 'VHM': (400, 95), 'MSN': (500, 75), 'SAB': (600, 60),
                                                           'VJC': (200, 50), 'PLX': (1500, 35), 'POW': (6000, 20)}))]


def hard_holdout():
    return [hard('fin-c3-logann-955', 'C3', HT.log_ann_vs_bench(['HDB', 'TPB', 'VJC', 'POW'], 'VN30')),
            hard('fin-c3-volregime-956', 'C3', HT.vol_regime(['VCB', 'BID', 'CTG', 'MBB', 'TCB'])),
            hard('fin-c4-dca-957', 'C4', HT.dca(['HPG', 'SSI']))]


def hard_pilot():
    return [hard('fin-c3-geo-805', 'C3', HT.geo_ann(['ACB', 'VPB', 'HDB'])),
            hard('fin-c3-maladder-806', 'C3', HT.ma_ladder(['SSI', 'PLX', 'GVR', 'POW'])),
            hard('fin-c4-rebal-807', 'C4', HT.rebalanced(['HPG', 'FPT', 'MWG', 'VNM', 'VIC', 'GAS'])),
            hard('fin-c4-signal-808', 'C4', HT.signal_portfolio(['VCB', 'BID', 'MSN', 'SAB', 'VJC', 'VHM', 'GVR', 'POW']))]


def build():
    S = []
    # ---------------- C1: one step, <= 3 operands ----------------
    S.append(pct_change_task('fin-c1-pct-401', 'C1', 'VCB', 5))
    d = (c('FPT') - c('FPT', 10)) * 1000
    S.append(spec('fin-c1-chg-402', 'C1', 'Thay đổi giá FPT 10 phiên (đồng)',
                  'Giá đóng cửa **FPT** ở **%s** cao/thấp hơn giá đóng cửa phiên **%s** bao nhiêu **đồng/cổ phiếu**?' % (S30, t('FPT', 10)),
                  {'value': 0, 'unit': 'đồng/cổ phiếu', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                  {'value': r4(d)}, [val('value', d, LVL), unit('unit', ['đồng/cổ phiếu', 'đồng', 'VND/cổ phiếu', 'VND']), period()],
                  "check('value', R((C('FPT') - C('FPT', 10)) * 1000), gold['solution']['value'])\n", ['FPT']))
    rr = c('FPT') / c('VNM')
    S.append(spec('fin-c1-ratio-403', 'C1', 'Tỷ lệ giá FPT/VNM',
                  'Ở **%s**, giá đóng cửa **FPT** gấp bao nhiêu **lần** giá đóng cửa **VNM**?' % S30,
                  {'value': 0, 'unit': 'lần', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                  {'value': r4(rr)}, [val('value', rr, RAT), unit('unit', ['lần', 'x']), period()],
                  "check('value', R(C('FPT') / C('VNM')), gold['solution']['value'])\n", ['FPT', 'VNM']))
    pts = c('VNINDEX') - c('VNINDEX', 5)
    S.append(spec('fin-c1-idx-404', 'C1', 'VNINDEX 5 phiên: điểm và %',
                  '**VNINDEX** thay đổi bao nhiêu **điểm** và bao nhiêu **%%** từ đóng cửa phiên **%s** đến **%s**?' % (t('VNINDEX', 5), S30),
                  {'values': {'points': 0, 'pct': 0}, 'period': '(kỳ được hỏi)', 'source': 'vn_index_ohlcv', 'note': '(tuỳ chọn)'},
                  {'points': r4(pts), 'pct': r4(pct('VNINDEX', 5))},
                  [val('values.points', pts, LVL), val('values.pct', pct('VNINDEX', 5), PCT), period()],
                  "check('pts', R(C('VNINDEX') - C('VNINDEX', 5)), gold['solution']['points'])\ncheck('pct', R(P('VNINDEX', 5)), gold['solution']['pct'])\n",
                  ['VNINDEX']))
    pl = (c('HPG') - D('20.5')) * 1000 * 1000
    S.append(spec('fin-c1-pnl-405', 'C1', 'Lãi/lỗ 1.000 cp HPG',
                  'Tôi mua **1.000 cổ phiếu HPG** giá vốn **20,5 nghìn đồng/cp**. Định giá theo giá đóng cửa **%s**, tôi lãi/lỗ bao nhiêu **đồng** (lỗ ghi số âm)?' % S30,
                  {'value': 0, 'unit': 'đồng', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                  {'value': r4(pl)}, [val('value', pl, LVL), money_unit(), period()],
                  "check('value', R((C('HPG') - _D('20.5')) * 1000 * 1000), gold['solution']['value'])\n", ['HPG']))
    rr = c('VN30') / c('VNINDEX')
    S.append(spec('fin-c1-ratio-406', 'C1', 'Tỷ lệ VN30/VNINDEX',
                  'Ở **%s**, chỉ số **VN30** bằng bao nhiêu **lần** **VNINDEX** (VN30 / VNINDEX, giá đóng cửa)?' % S30,
                  {'value': 0, 'unit': 'lần', 'period': '(kỳ được hỏi)', 'source': 'vn_index_ohlcv', 'note': '(tuỳ chọn)'},
                  {'value': r4(rr)}, [val('value', rr, RAT), unit('unit', ['lần', 'x']), period()],
                  "check('value', R(C('VN30') / C('VNINDEX')), gold['solution']['value'])\n", ['VN30', 'VNINDEX']))
    S.append(pct_change_task('fin-c1-pct-407', 'C1', 'MWG', 10))
    pg, pp_ = pct('GAS', 5), pct('PLX', 5); win = 'GAS' if pg > pp_ else 'PLX'
    S.append(spec('fin-c1-cmp-408', 'C1', 'GAS vs PLX 5 phiên',
                  ('Từ phiên **%s** đến **%s**: **GAS** và **PLX** mỗi mã thay đổi bao nhiêu %%? Mã nào tốt hơn và hơn bao nhiêu **điểm %%**?'
                   % (t('GAS', 5), S30)),
                  {'values': {'GAS': 0, 'PLX': 0, 'better': 'MÃ', 'diff_pp': 0}, 'unit': '%', 'period': '(kỳ được hỏi)',
                   'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                  {'GAS': r4(pg), 'PLX': r4(pp_), 'better': win, 'diff_pp': r4(abs(pg - pp_))},
                  [val('values.GAS', pg, PCT), val('values.PLX', pp_, PCT), tokens('values.better', win, ['GAS', 'PLX']),
                   val('values.diff_pp', abs(pg - pp_), PCT), period()],
                  ("a, b = P('GAS', 5), P('PLX', 5)\ncheck('gas', R(a), gold['solution']['GAS'])\ncheck('plx', R(b), gold['solution']['PLX'])\n"
                   "check('better', 'GAS' if a > b else 'PLX', gold['solution']['better'])\ncheck('diff', R(abs(a - b)), gold['solution']['diff_pp'])\n"),
                  ['GAS', 'PLX']))
    # ---------------- C2: 10-20 operands or two steps ----------------
    S.append(mean_task('fin-c2-ma-409', 'C2', 'TCB', 20))
    sv = sum(v('SSI', i) for i in range(10))
    S.append(spec('fin-c2-vol-410', 'C2', 'Tổng khối lượng SSI 10 phiên',
                  '**Tổng khối lượng khớp** của **SSI** trong **10 phiên** gần nhất (từ %s đến %s) là bao nhiêu **cổ phiếu**?' % (t('SSI', 9), S30),
                  {'value': 0, 'unit': 'cổ phiếu', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                  {'value': r4(sv)}, [val('value', sv, LVL), unit('unit', ['cổ phiếu', 'cp']), period()],
                  "check('value', R(sum(V('SSI', i) for i in range(10))), gold['solution']['value'])\n", ['SSI']))
    S.append(pct_change_task('fin-c2-pct-411', 'C2', 'MBB', 40))
    S.append(rel_strength_task('fin-c2-rs-412', 'C2', 'HPG', 'VNINDEX', 20))
    mv = mean_v('VIC', 20)
    S.append(spec('fin-c2-vol-413', 'C2', 'Khối lượng bình quân 20 phiên VIC',
                  '**Khối lượng khớp bình quân 20 phiên** gần nhất (gồm %s) của **VIC** là bao nhiêu **cổ phiếu/phiên**?' % S30,
                  {'value': 0, 'unit': 'cổ phiếu/phiên', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                  {'value': r4(mv)}, [val('value', mv, LVL), unit('unit', ['cổ phiếu/phiên', 'cổ phiếu', 'cp']), period()],
                  "check('value', R(MV('VIC', 20)), gold['solution']['value'])\n", ['VIC']))
    r60 = c('VHM') / c('VHM', 60); ann = (D(float(r60) ** (250 / 60)) - 1) * 100
    S.append(spec('fin-c2-ann-414', 'C2', 'Lợi suất 60 phiên VHM quy năm',
                  ('**VHM**: tính %% thay đổi giá đóng cửa từ phiên **%s** đến **%s** (60 phiên), rồi **quy đổi ra lợi suất năm kép** '
                   'với giả định 250 phiên/năm: (giá cuối/giá đầu)^(250/60) − 1.' % (t('VHM', 60), S30)),
                  {'values': {'pct_60': 0, 'annualized_pct': 0}, 'unit': '%', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                  {'pct_60': r4(pct('VHM', 60)), 'annualized_pct': r4(ann)},
                  [val('values.pct_60', pct('VHM', 60), PCT), val('values.annualized_pct', ann, {'abs': 0.1}), pct_unit(), period()],
                  ("check('p60', R(P('VHM', 60)), gold['solution']['pct_60'])\n"
                   "check('ann', R((_D(float(C('VHM') / C('VHM', 60)) ** (250 / 60)) - 1) * 100), gold['solution']['annualized_pct'])\n"),
                  ['VHM']))
    S.append(eqw_task('fin-c2-eqw-415', 'C2', ['ACB', 'VCB', 'BID'], 20))
    S.append(mean_task('fin-c2-ma-416', 'C2', 'SAB', 10))
    # ---------------- C3/C4: structural hard rule, addendum (f) (tools/compute_hard_templates_20261111.py)
    S += hard_main()
    main = S
    # ---------------- holdout ----------------
    S = []
    S.append(pct_change_task('fin-c1-pct-951', 'C1', 'TCB', 5))
    pl = (c('SSI') - D('30')) * 1000 * 2000
    S.append(spec('fin-c1-pnl-952', 'C1', 'Lãi/lỗ 2.000 cp SSI',
                  'Tôi mua **2.000 cổ phiếu SSI** giá vốn **30 nghìn đồng/cp**. Định giá theo giá đóng cửa **%s**, tôi lãi/lỗ bao nhiêu **đồng** (lỗ ghi số âm)?' % S30,
                  {'value': 0, 'unit': 'đồng', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                  {'value': r4(pl)}, [val('value', pl, LVL), money_unit(), period()],
                  "check('value', R((C('SSI') - _D('30')) * 1000 * 2000), gold['solution']['value'])\n", ['SSI']))
    S.append(mean_task('fin-c2-ma-953', 'C2', 'VPB', 20))
    S.append(rel_strength_task('fin-c2-rs-954', 'C2', 'FPT', 'VNINDEX', 20))
    S += hard_holdout()
    hold = S
    # ---------------- pilot (8; pipeline validation only, symbols/windows not used by main or holdout questions)
    P = [pct_change_task('fin-c1-pct-801', 'C1', 'CTG', 5),
         rel_strength_task('fin-c1-rs-802', 'C1', 'VJC', 'VNINDEX', 5),
         mean_task('fin-c2-ma-803', 'C2', 'BID', 20),
         eqw_task('fin-c2-eqw-804', 'C2', ['SAB', 'VNM', 'MSN'], 20),
         ] + hard_pilot()
    return main, hold, P


def write(split, s):
    d = STUDY / 'tasks' / split / s['tid']
    if d.exists():
        shutil.rmtree(d)
    (d / 'environment').mkdir(parents=True); (d / 'solution').mkdir(); (d / 'tests').mkdir()
    shutil.copy(TEMPLATE / 'tests/grader.py', d / 'tests/grader.py')
    payloads = {'snapshot_date': '2026-11-01',
                'note': 'Envelope MCP. Lịch sử 120 phiên ghi bằng thư viện nhà cung cấp vnstock (MCP history lỗi phiên bản lúc ghi); '
                        'xem audits/snapshot-extension-2026-11-11/RECEIPT.json.',
                'tools': {key(x): envelope(x) for x in s['syms']}}
    (d / 'environment/payloads.json').write_text(json.dumps(payloads, ensure_ascii=False, indent=1) + '\n')
    tmpl = (TEMPLATE / 'instruction.md').read_text(encoding='utf-8')
    contract = tmpl[tmpl.index('## Ràng buộc chung'):]
    head = '# %s\n\n%s\n\n## Yêu cầu trả lời\nTrả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n```json\n%s\n```\n\n\n' % (
        s['title'], s['question'] + '\n\n' + ROUNDING, json.dumps(s['example'], ensure_ascii=False, indent=2))
    (d / 'instruction.md').write_text(head + contract, encoding='utf-8')
    prov = [{'tool': tool(x), 'source': 'vnstock', 'as_of': REC['recorded_at'], 'matched_entry_id': key(x),
             'response_sha256': digest(envelope(x)['envelope'])} for x in s['syms']]
    gold = {'task_id': s['tid'], 'scoring': 'value', 'solution': s['solution'], 'as_of': REC['recorded_at'], 'split': split,
            'expects': s['expects'], 'contract_version': 2, 'stratum': 'compute', 'tier': s['tier'],
            'notes': 'Compute stratum (amendment 2026-11-11 d). Gold computed with Decimal from payloads; uniform tolerance.',
            'provenance_contract': prov, 'provenance_catalog': prov,
            'payload_sha256': hashlib.sha256((d / 'environment/payloads.json').read_bytes()).hexdigest(),
            'required_payload_keys': sorted(key(x) for x in s['syms'])}
    (d / 'solution/gold.json').write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n')
    o = (TEMPLATE / 'solution/oracle.py').read_text(encoding='utf-8')
    pre, mark, rest = o.partition('# === thân oracle ===\n')
    _, sep, tail = rest.partition('\nif problems:')
    assert mark and sep
    body = 'SYMS = %r\n' % s['syms'] + ORACLE_LIB.lstrip('\n') + s['oracle']
    (d / 'solution/oracle.py').write_text(pre + mark + body + '\n\nif problems:' + tail, encoding='utf-8')
    tools = sorted({tool(x) for x in s['syms']})
    toml = (TEMPLATE / 'task.toml').read_text(encoding='utf-8')
    toml = toml.replace('# Task benchmark harness tài chính (bộ 200+50) — sinh bởi tools/build_main.py',
                        '# Compute stratum — amendment 2026-11-11 (d), tools/build_compute_stratum_20261111.py')
    for k, val_ in (('id', s['tid']), ('title', s['title'].replace('"', "'")), ('created', '2026-11-11'), ('level', s['tier']),
                    ('family', '%s compute' % s['tier']), ('financebench_type', 'numeric computation'),
                    ('entity', '+'.join(s['syms'])), ('split', split)):
        toml = re.sub(r'^%s = ".*"$' % k, '%s = "%s"' % (k, val_), toml, flags=re.M)
    toml = re.sub(r'^tools_expected = .*$', 'tools_expected = %s' % json.dumps(tools), toml, flags=re.M)
    toml = toml.replace('confirmatory_eligible = true', 'confirmatory_eligible = true\nstratum = "compute"\ntier = "%s"' % s['tier'])
    (d / 'task.toml').write_text(toml, encoding='utf-8')
    return d


def main():
    main_specs, hold_specs, pilot_specs = build()
    wanted = {s['tid'] for s in main_specs + hold_specs + pilot_specs}
    for split in ('main', 'holdout', 'pilot'):
        for old in (STUDY / 'tasks' / split).glob('fin-c[34]-*'):
            if old.name not in wanted:
                shutil.rmtree(old)  # superseded by addendum (f) hard templates (never run except disclosed dry-run)
    assert len(main_specs) == 30 and len(hold_specs) == 7 and len(pilot_specs) == 8
    receipt = {}
    for split, specs in (('main', main_specs), ('holdout', hold_specs), ('pilot', pilot_specs)):
        for s in specs:
            d = write(split, s)
            receipt[s['tid']] = {'split': split, 'tier': s['tier'], 'solution': s['solution'],
                                 'files': {f: hashlib.sha256((d / f).read_bytes()).hexdigest()
                                           for f in ('instruction.md', 'solution/gold.json', 'solution/oracle.py', 'task.toml', 'environment/payloads.json')}}
    out = STUDY / 'audits/taskset-revision-2026-11-11/COMPUTE-BUILD.json'
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    print('built', len(receipt))


if __name__ == '__main__':
    main()
