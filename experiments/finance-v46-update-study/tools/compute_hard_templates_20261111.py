"""Amendment 2026-11-11 (d), addendum (f): structural rule for the hard compute tiers, fixed before any data.

C3 (hard): >=3 entities, each over a >=60-session series read by reference, AND at least one non-linear operation
    (fractional power, ln/exp) or >=10 long-series sums of 8-digit volumes; 3-4 chained steps.
C4 (very hard): >=6 entities or staggered/rebalanced holdings, >=4 chained steps, at least one fractional power or
    ln/exp per entity, money in đồng (9-11 digit magnitudes) or per-entity distinct windows.
Every operation exists natively in OpenTrading (compute pct_change/mean/sum/relative_strength over refs; calculate
with + - * / ^ ln exp sqrt). Tolerances unchanged and uniform: % abs 0.05 pp, annualized % abs 0.1 pp,
ratios abs 0.005, money/levels/volumes rel 0.1%. Tasks are never dry-run per arm nor edited on arm outcomes.

Each template returns (question, example, code, fields) where `code` computes dict `out` from the task payloads
through the oracle library (C, V, MC, MV, P, G, ANN, LN). The builder executes it to obtain gold; the oracle
re-executes it on the written payloads.
"""

LIB = '''
import math
from decimal import Decimal as _D
def _rows(s):
    k = ('idx:' if s in ('VNINDEX', 'VN30') else 'hist:') + s
    return env(k)['data']['closes']
def C(s, back=0): return _D(str(_rows(s)[-1 - back]['c']))
def V(s, back=0): return _D(_rows(s)[-1 - back]['v'])
def MC(s, n, back=0): return sum(C(s, i) for i in range(back, back + n)) / n
def MV(s, n): return sum(V(s, i) for i in range(n)) / n
def P(s, n, back=0): return (C(s, back) / C(s, back + n) - 1) * 100
def G(s, n, back=0): return float(C(s, back) / C(s, back + n))
def ANN(gross, n): return (gross ** (250.0 / n) - 1) * 100
def LN(x): return math.log(x)
def T(s, back): return _rows(s)[-1 - back]['t']
def R(x): return round(float(x), 4)
'''

PCT, ANNT, RAT, LVL = {'abs': 0.05}, {'abs': 0.1}, {'abs': 0.005}, {'rel': 0.001}


def d(t):
    return '%s/%s/%s' % (t[8:], t[5:7], t[:4])


def val(path, tol):
    return (path, tol)


# ---------------------------------------------------------------- C3

def geo_ann(syms, n=119):
    code = ('syms = %r; n = %d\nout = {}\ng = {s: G(s, n) for s in syms}\n'
            'for s in syms: out["ann_" + s] = R(ANN(g[s], n))\n'
            'geo = 1.0\nfor s in syms: geo *= g[s]\ngeo = geo ** (1.0 / len(syms))\n'
            'out["geo_period_pct"] = R((geo - 1) * 100)\nout["geo_ann_pct"] = R(ANN(geo, n))\n'
            'out["best"] = max(syms, key=lambda s: g[s])\n') % (syms, n)
    q = ('Với **%s**, xét %d khoảng phiên từ giá đóng cửa phiên **{T%s:%d}** đến **phiên 30/10/2026**: (1) lợi suất **năm kép** của từng mã '
         '= (giá cuối/giá đầu)^(250/%d) − 1; (2) **trung bình nhân** của hệ số tăng trưởng 3 mã = (g₁·g₂·g₃)^(1/3) với g = giá cuối/giá đầu, '
         'quy ra %% cả kỳ; (3) quy trung bình nhân đó ra lợi suất năm kép; (4) mã có g lớn nhất.') % (', '.join(syms), n, syms[0], n, n)
    ex = {'values': {**{'ann_' + s: 0 for s in syms}, 'geo_period_pct': 0, 'geo_ann_pct': 0, 'best': 'MÃ'}, 'unit': '%'}
    f = [('values.ann_' + s, ANNT) for s in syms] + [('values.geo_period_pct', PCT), ('values.geo_ann_pct', ANNT), ('values.best', 'token')]
    return 'Lợi suất năm kép và trung bình nhân %s' % '/'.join(syms), q, ex, code, f, syms


def log_ann_vs_bench(syms, bench, n=119):
    code = ('syms = %r; b = %r; n = %d\nout = {}\nl = {s: LN(G(s, n)) * 250 / n * 100 for s in syms}\n'
            'for s in syms: out["log_ann_" + s] = R(l[s])\n'
            'avg = sum(l.values()) / len(l)\nlb = LN(G(b, n)) * 250 / n * 100\n'
            'out["avg_log_ann"] = R(avg)\nout["bench_log_ann"] = R(lb)\nout["excess_log_pp"] = R(avg - lb)\n'
            'out["excess_simple_pct"] = R((math.exp((avg - lb) / 100) - 1) * 100)\n') % (syms, bench, n)
    q = ('Lợi suất **log quy năm** (liên tục) của một mã = ln(giá cuối/giá đầu) × 250/%d, với giá đầu = giá đóng cửa phiên **{T%s:%d}** và giá cuối = phiên **30/10/2026** (%d khoảng phiên). '
         'Tính cho **%s**; trung bình cộng của chúng; của **%s**; chênh lệch (trung bình − %s) theo điểm %%; rồi đổi chênh lệch đó '
         'sang lợi suất đơn: e^(chênh lệch) − 1.') % (n, bench, n, n, ', '.join(syms), bench, bench)
    ex = {'values': {**{'log_ann_' + s: 0 for s in syms}, 'avg_log_ann': 0, 'bench_log_ann': 0, 'excess_log_pp': 0, 'excess_simple_pct': 0}, 'unit': '%'}
    f = [('values.log_ann_' + s, ANNT) for s in syms] + [('values.avg_log_ann', ANNT), ('values.bench_log_ann', ANNT),
                                                        ('values.excess_log_pp', ANNT), ('values.excess_simple_pct', ANNT)]
    return 'Lợi suất log quy năm %d mã so với %s' % (len(syms), bench), q, ex, code, f, syms + [bench]


def ma_ladder(syms):
    code = ('syms = %r\nout = {}\nup = []\ngap = {}\n'
            'for s in syms:\n    a, b, c = MC(s, 20), MC(s, 60), MC(s, 120)\n'
            '    out[s] = {"ma20": R(a), "ma60": R(b), "ma120": R(c)}\n    gap[s] = (a / c - 1) * 100\n'
            '    out[s]["gap20_120_pct"] = R(gap[s])\n    if a > b > c: up.append(s)\n'
            'out["top_gap"] = max(syms, key=lambda s: gap[s])\nout["aligned_uptrend"] = sorted(up)\n') % (syms,)
    q = ('Với **%s**: tính **MA20, MA60, MA120** (trung bình giá đóng cửa 20/60/120 phiên gần nhất, gồm phiên 30/10/2026, nghìn đồng/cp), '
         'độ lệch MA20/MA120 − 1 (%%) của từng mã, mã có độ lệch **lớn nhất theo giá trị có dấu** (số lớn nhất, không lấy trị tuyệt đối), '
         'và danh sách mã có MA20 > MA60 > MA120.') % ', '.join(syms)
    ex = {'values': {**{s: {'ma20': 0, 'ma60': 0, 'ma120': 0, 'gap20_120_pct': 0} for s in syms}, 'top_gap': 'MÃ', 'aligned_uptrend': []},
          'unit': 'nghìn đồng/cổ phiếu'}
    f = [x for s in syms for x in (('values.%s.ma20' % s, LVL), ('values.%s.ma60' % s, LVL), ('values.%s.ma120' % s, LVL),
                                   ('values.%s.gap20_120_pct' % s, PCT))] + [('values.top_gap', 'token'), ('values.aligned_uptrend', 'set')]
    return 'Bậc thang MA20/60/120 %d mã' % len(syms), q, ex, code, f, syms


def vol_regime(syms):
    code = ('syms = %r\nout = {}\nr = {}\nfor s in syms:\n    a, b = MV(s, 20), MV(s, 120)\n    r[s] = a / b\n'
            '    out[s] = {"avg20": R(a), "avg120": R(b), "ratio": R(r[s])}\n'
            'out["ranking"] = sorted(syms, key=lambda s: -r[s])\n') % (syms,)
    q = ('Với **%s**: khối lượng khớp **bình quân 20 phiên** và **bình quân 120 phiên** (đều tính đến phiên 30/10/2026, cổ phiếu/phiên), '
         'tỷ số bình quân 20/bình quân 120 của từng mã, và **xếp hạng** các mã theo tỷ số đó từ cao đến thấp.') % ', '.join(syms)
    ex = {'values': {s: {'avg20': 0, 'avg120': 0, 'ratio': 0} for s in syms}, 'ranking': ['MÃ1', '...'], 'unit': 'cổ phiếu/phiên'}
    f = [x for s in syms for x in (('values.%s.avg20' % s, LVL), ('values.%s.avg120' % s, LVL), ('values.%s.ratio' % s, RAT))] + [('ranking', 'order')]
    return 'Chế độ thanh khoản 20/120 phiên %d mã' % len(syms), q, ex, code, f, syms


def vol_share(syms, n=120):
    code = ('syms = %r; n = %d\nout = {"totals": {}, "share_pct": {}}\ntot = {s: sum(V(s, i) for i in range(n)) for s in syms}\nT_ = sum(tot.values())\n'
            'for s in syms:\n    out["totals"][s] = R(tot[s])\n    out["share_pct"][s] = R(tot[s] / T_ * 100)\nout["grand_total"] = R(T_)\n') % (syms, n)
    q = ('Với **%s**: **tổng khối lượng khớp %d phiên** gần nhất (đến phiên 30/10/2026) của từng mã, tổng chung, và **tỷ trọng %%** của mỗi mã.') % (', '.join(syms), n)
    ex = {'values': {'totals': {s: 0 for s in syms}, 'grand_total': 0, 'share_pct': {s: 0 for s in syms}}, 'unit': 'cổ phiếu'}
    f = [('values.totals.' + s, LVL) for s in syms] + [('values.grand_total', LVL)] + [('values.share_pct.' + s, PCT) for s in syms]
    return 'Tỷ trọng khối lượng %d phiên %d mã' % (n, len(syms)), q, ex, code, f, syms


def doubling(sym, n=119):
    code = ('s = %r; n = %d\nout = {}\ng = G(s, n)\nout["ann_pct"] = R(ANN(g, n))\nout["projected_price"] = R(float(C(s)) * g ** (250.0 / n))\n'
            'out["doubling_sessions"] = R(LN(2) / LN(g ** (1.0 / n)))\n') % (sym, n)
    q = ('**%s**: từ giá đóng cửa phiên **{T%s:%d}** đến **phiên 30/10/2026** là %d khoảng phiên. Giả định tốc độ tăng trưởng kép mỗi phiên giữ '
         'nguyên: (1) lợi suất năm kép (250 phiên/năm); (2) giá dự phóng sau 250 phiên nữa = giá 30/10 × (giá cuối/giá đầu)^(250/%d), '
         'nghìn đồng/cp; (3) số phiên cần để giá **gấp đôi** = ln 2 / ln((giá cuối/giá đầu)^(1/%d)).') % (sym, sym, n, n, n, n)
    ex = {'values': {'ann_pct': 0, 'projected_price': 0, 'doubling_sessions': 0}, 'unit': 'xem từng trường'}
    f = [('values.ann_pct', ANNT), ('values.projected_price', LVL), ('values.doubling_sessions', LVL)]
    return 'Dự phóng tăng trưởng kép %s' % sym, q, ex, code, f, [sym]


def rs_chain(syms, bench, n=60):
    code = ('syms = %r; b = %r; n = %d\nout = {}\nfor s in syms: out["rs_" + s] = R(P(s, n) - P(b, n))\n'
            'gs = sum(G(s, n) for s in syms) / len(syms)\ngb = G(b, n)\nout["avg_rs_pp"] = R(sum(P(s, n) - P(b, n) for s in syms) / len(syms))\n'
            'out["excess_ann_pct"] = R(((gs / gb) ** (250.0 / n) - 1) * 100)\n') % (syms, bench, n)
    q = ('Trong %d phiên từ giá đóng cửa phiên **{T%s:%d}** đến **phiên 30/10/2026**: sức mạnh tương đối (%% thay đổi mã − %% thay đổi **%s**, điểm %%) của từng mã **%s**; '
         'trung bình cộng các RS; và lợi suất vượt trội **quy năm kép** của danh mục đều tỷ trọng so với %s = '
         '((trung bình hệ số giá cuối/giá đầu của các mã) / (hệ số của %s))^(250/%d) − 1.') % (n, bench, n, bench, ', '.join(syms), bench, bench, n)
    ex = {'values': {**{'rs_' + s: 0 for s in syms}, 'avg_rs_pp': 0, 'excess_ann_pct': 0}, 'unit': 'điểm % / %'}
    f = [('values.rs_' + s, PCT) for s in syms] + [('values.avg_rs_pp', PCT), ('values.excess_ann_pct', ANNT)]
    return 'Chuỗi sức mạnh tương đối %d mã vs %s' % (len(syms), bench), q, ex, code, f, syms + [bench]


# ---------------------------------------------------------------- C4

def staggered(pos):
    """pos: {sym: (qty, back)} bought at the close `back` sessions before 30/10."""
    code = ('pos = %r\nout = {"positions": {}}\ncost = 0\nvalue = 0\nann = {}\nw = {}\n'
            'for s, (q, k) in pos.items():\n    c0 = C(s, k) * 1000 * q\n    c1 = C(s) * 1000 * q\n    cost += c0\n    value += c1\n'
            '    ann[s] = ANN(G(s, k), k)\n    w[s] = float(c1)\n    out["positions"][s] = R(ann[s])\n'
            'out["total_cost"] = R(cost)\nout["total_value"] = R(value)\nout["pnl"] = R(value - cost)\n'
            'out["value_weighted_ann_pct"] = R(sum(ann[s] * w[s] for s in pos) / sum(w.values()))\n'
            'out["best_annualized"] = max(pos, key=lambda s: ann[s])\n') % (pos,)
    lines = '; '.join('%s cp **%s** mua tại giá đóng cửa phiên **%s**' % ('{:,}'.format(q).replace(',', '.'), s, '{T%s:%d}' % (s, k))
                      for s, (q, k) in pos.items())
    q = ('Danh mục mua rải: %s. Giữ đến **phiên 30/10/2026**. Tính: tổng giá vốn và tổng giá trị hiện tại (đồng), lãi/lỗ (đồng); '
         'lợi suất **năm kép** của từng vị thế = (giá 30/10/giá mua)^(250/số phiên nắm giữ) − 1 (số phiên nắm giữ = số khoảng phiên từ ngày mua '
         'đến 30/10); lợi suất năm kép **bình quân gia quyền theo giá trị hiện tại**; vị thế có lợi suất năm kép cao nhất.') % lines
    ex = {'values': {'positions': {s: 0 for s in pos}, 'total_cost': 0, 'total_value': 0, 'pnl': 0, 'value_weighted_ann_pct': 0,
                     'best_annualized': 'MÃ'}, 'unit': 'đồng / %'}
    f = [('values.positions.' + s, ANNT) for s in pos] + [('values.total_cost', LVL), ('values.total_value', LVL), ('values.pnl', LVL),
                                                          ('values.value_weighted_ann_pct', ANNT), ('values.best_annualized', 'token')]
    return 'Danh mục mua rải %d vị thế' % len(pos), q, ex, code, f, list(pos)


def rebalanced(syms, split=60, n=119):
    code = ('syms = %r; m = %d; n = %d\nout = {}\ng1 = sum(float(C(s, m) / C(s, n)) for s in syms) / len(syms)\n'
            'g2 = sum(G(s, m) for s in syms) / len(syms)\nreb = g1 * g2\nbh = sum(G(s, n) for s in syms) / len(syms)\n'
            'out["period1_pct"] = R((g1 - 1) * 100)\nout["period2_pct"] = R((g2 - 1) * 100)\nout["rebalanced_total_pct"] = R((reb - 1) * 100)\n'
            'out["rebalanced_ann_pct"] = R(ANN(reb, n))\nout["buy_hold_total_pct"] = R((bh - 1) * 100)\n'
            'out["rebalance_minus_buyhold_pp"] = R((reb - bh) * 100)\n') % (syms, split, n)
    q = ('Danh mục **đều tỷ trọng** %d mã **%s**, mở tại giá đóng cửa phiên **{T%s:%d}** (%d khoảng phiên trước 30/10/2026), **tái cân bằng về tỷ trọng bằng nhau** '
         'tại giá đóng cửa phiên **{T%s:%d}** (%d phiên trước 30/10/2026). Tính: lợi suất giai đoạn 1 và giai đoạn 2 (trung bình hệ số giá của các mã − 1), lợi suất cả kỳ '
         '(tích hai hệ số − 1), quy năm kép ^(250/%d), lợi suất nếu **mua và giữ** không tái cân bằng (trung bình hệ số cả kỳ − 1), và chênh '
         'lệch tái cân bằng − mua giữ (điểm %%).') % (len(syms), ', '.join(syms), syms[0], n, n, syms[0], split, split, n)
    ex = {'values': {'period1_pct': 0, 'period2_pct': 0, 'rebalanced_total_pct': 0, 'rebalanced_ann_pct': 0, 'buy_hold_total_pct': 0,
                     'rebalance_minus_buyhold_pp': 0}, 'unit': '%'}
    f = [('values.period1_pct', PCT), ('values.period2_pct', PCT), ('values.rebalanced_total_pct', PCT), ('values.rebalanced_ann_pct', ANNT),
         ('values.buy_hold_total_pct', PCT), ('values.rebalance_minus_buyhold_pp', PCT)]
    return 'Tái cân bằng danh mục %d mã' % len(syms), q, ex, code, f, syms


def dca(syms, backs=(119, 80, 40), amount=100_000_000):
    code = ('syms = %r; backs = %r; A = %d\nout = {}\ninv = 0\nval = 0\n'
            'for s in syms:\n    sh = sum(_D(A) / (C(s, k) * 1000) for k in backs)\n    out[s] = {"shares": R(sh), "avg_cost": R(_D(A) * len(backs) / sh / 1000), "value": R(sh * C(s) * 1000)}\n'
            '    inv += A * len(backs)\n    val += sh * C(s) * 1000\n'
            'out["invested"] = R(inv)\nout["value"] = R(val)\nout["pnl"] = R(val - inv)\nout["return_pct"] = R((val / inv - 1) * 100)\n') % (syms, tuple(backs), amount)
    q = ('Chiến lược mua định kỳ: với mỗi mã **%s**, mua **%s đồng** tại giá đóng cửa của mỗi phiên **%s** (lần lượt %s phiên trước 30/10/2026) '
         '(cho phép cổ phiếu lẻ, không phí). Tính cho từng mã: số cổ phiếu tích luỹ, **giá vốn bình quân** (nghìn đồng/cp), giá trị tại phiên 30/10/2026 '
         '(đồng); và cho cả danh mục: tổng vốn, tổng giá trị, lãi/lỗ (đồng), lợi suất %%.') % (
        ', '.join(syms), '{:,}'.format(amount).replace(',', '.'), ', '.join('{T%s:%d}' % (syms[0], b) for b in backs), ', '.join(str(b) for b in backs))
    ex = {'values': {**{s: {'shares': 0, 'avg_cost': 0, 'value': 0} for s in syms}, 'invested': 0, 'value': 0, 'pnl': 0, 'return_pct': 0}, 'unit': 'đồng'}
    f = [x for s in syms for x in (('values.%s.shares' % s, LVL), ('values.%s.avg_cost' % s, LVL), ('values.%s.value' % s, LVL))] + \
        [('values.invested', LVL), ('values.value', LVL), ('values.pnl', LVL), ('values.return_pct', PCT)]
    return 'Mua định kỳ %d mã' % len(syms), q, ex, code, f, syms


def signal_portfolio(syms, n=20):
    code = ('syms = %r; n = %d\nout = {}\nsel = sorted(s for s in syms if MC(s, 20) > MC(s, 60))\nout["selected"] = sel\n'
            'gs = sum(G(s, n) for s in sel) / len(sel)\nga = sum(G(s, n) for s in syms) / len(syms)\n'
            'out["selected_pct"] = R((gs - 1) * 100)\nout["selected_ann_pct"] = R(ANN(gs, n))\nout["all_pct"] = R((ga - 1) * 100)\n'
            'out["edge_pp"] = R((gs - ga) * 100)\n') % (syms, n)
    q = ('Lọc tín hiệu trong **%s**: chọn các mã có **MA20 > MA60** (giá đóng cửa, tính đến phiên 30/10/2026). Danh mục đều tỷ trọng các mã được chọn: '
         'lợi suất %d phiên từ phiên **{T%s:%d}** đến 30/10/2026 (trung bình hệ số giá cuối/giá đầu − 1) và quy năm kép ^(250/%d); lợi suất cùng kỳ '
         'của danh mục đều tỷ trọng **cả %d mã**; và **chênh lệch lợi suất %d phiên (chưa quy năm)** giữa hai danh mục (điểm %%).') % (', '.join(syms), n, syms[0], n, n, len(syms), n)
    ex = {'values': {'selected': ['MÃ'], 'selected_pct': 0, 'selected_ann_pct': 0, 'all_pct': 0, 'edge_pp': 0}, 'unit': '%'}
    f = [('values.selected', 'set'), ('values.selected_pct', PCT), ('values.selected_ann_pct', ANNT), ('values.all_pct', PCT), ('values.edge_pp', PCT)]
    return 'Danh mục tín hiệu MA20>MA60 %d mã' % len(syms), q, ex, code, f, syms
