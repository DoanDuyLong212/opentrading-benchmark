#!/usr/bin/env python3
"""v4.7 compute additions (plan 2026-11-16, OpenTrading#309 D2; main 10: fin-c3-*-431..440).

Long-series computations, the kind where re-typing 60-120 closes into a command is the failure (#309 A2): annualised
volatility of log returns, maximum drawdown, correlation and beta. Same data, writer, oracle library and tolerance
policy as tools/build_compute_stratum_20261111.py (its write() is reused); stratum compute, tier C3.
Tolerances: volatility % abs 0.1 pp, drawdown % abs 0.05 pp, correlation abs 0.005, beta abs 0.01.
Idempotent: rewrites the task directories it owns.
"""
import math, re, statistics as st, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import build_compute_stratum_20261111 as cs  # noqa: E402
from series_contract import dated_closes, dated_returns, series_corr, series_beta
CALENDAR = [r["t"] for r in cs.H["VNINDEX"]]
SERIES_LIB = (STUDY / "tools/series_contract.py").read_text()

VOL, DD, CORR, BETA = {'abs': 0.1}, {'abs': 0.05}, {'abs': 0.005}, {'abs': 0.01}
S30 = cs.S30


def points(sym, n):
    return dated_closes(cs.H[sym], n, calendar=CALENDAR)


def closes(sym, n):
    return [price for day, price in points(sym, n)]


def logret(sym, n):
    return [value for interval, value in dated_returns(points(sym, n))]


def vol(sym, n):
    return st.stdev(logret(sym, n)) * math.sqrt(250) * 100


def maxdd(sym, n):
    peak, worst = -1.0, 0.0
    for p in closes(sym, n):
        peak = max(peak, p)
        worst = min(worst, p / peak - 1)
    return worst * 100


def corr(a, b, n):
    return series_corr(points(a, n), points(b, n))


def beta(a, n, m='VNINDEX'):
    return series_beta(points(a, n), points(m, n))


LIB = SERIES_LIB + "\n_CALENDAR = %r\n" % CALENDAR + '''
import statistics as _st
def _points(s, n): return dated_closes(_rows(s), n, calendar=_CALENDAR)
def _cl(s, n): return [p for d, p in _points(s, n)]
def _lr(s, n): return [v for interval, v in dated_returns(_points(s, n))]
def VOL(s, n): return _st.stdev(_lr(s, n)) * math.sqrt(250) * 100
def DD(s, n):
    peak, worst = -1.0, 0.0
    for p in _cl(s, n):
        peak = max(peak, p); worst = min(worst, p / peak - 1)
    return worst * 100
def CORR(a, b, n): return series_corr(_points(a, n), _points(b, n))
def BETA(a, n): return series_beta(_points(a, n), _points('VNINDEX', n))
'''


def vol_task(tid, syms, n=60):
    v = {s: vol(s, n) for s in syms}
    top = max(syms, key=v.get)
    q = ('Với **%s**: tính **độ biến động năm hoá** (%%) của từng mã trong %d phiên tới **%s** = độ lệch chuẩn **mẫu** của %d '
         'lợi suất log ngày ln(giá hôm nay/giá hôm trước) × √250 × 100. Mã nào biến động cao nhất?' % (', '.join(syms), n, S30, n))
    ex = {'values': {**{s: 0 for s in syms}, 'highest': 'MÃ'}, 'unit': '%', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'}
    exp = [cs.val('values.' + s, v[s], VOL) for s in syms] + [cs.tokens('values.highest', top, syms)]
    oracle = LIB + ''.join("check('vol_%s', R(VOL('%s', %d)), gold['solution']['%s'])\n" % (s, s, n, s) for s in syms) + \
        "check('highest', max(%r, key=lambda s: VOL(s, %d)), gold['solution']['highest'])\n" % (syms, n)
    return cs.spec(tid, 'C3', 'Độ biến động năm hoá %s' % '/'.join(syms), q, ex, {**{s: cs.r4(v[s]) for s in syms}, 'highest': top}, exp, oracle, syms)


def dd_task(tid, syms, n=119):
    d = {s: maxdd(s, n) for s in syms}
    worst = min(syms, key=d.get)
    q = ('Với **%s**: tính **mức sụt giảm lớn nhất** (max drawdown, %%) của từng mã trên chuỗi giá đóng cửa %d phiên từ **%s** đến **%s** '
         '= min theo từng phiên của (giá phiên đó / giá cao nhất từ đầu chuỗi tới phiên đó − 1) × 100 (số âm). Mã nào sụt sâu nhất?'
         % (' và '.join(syms), n + 1, cs.t(syms[0], n), S30))
    ex = {'values': {**{s: 0 for s in syms}, 'deepest': 'MÃ'}, 'unit': '%', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'}
    exp = [cs.val('values.' + s, d[s], DD) for s in syms] + [cs.tokens('values.deepest', worst, syms)]
    oracle = LIB + ''.join("check('dd_%s', R(DD('%s', %d)), gold['solution']['%s'])\n" % (s, s, n, s) for s in syms)
    return cs.spec(tid, 'C3', 'Max drawdown %s' % '/'.join(syms), q, ex, {**{s: cs.r4(d[s]) for s in syms}, 'deepest': worst}, exp, oracle, syms)


def corr_task(tid, a, b, n=60):
    r = corr(a, b, n)
    q = ('Tính **hệ số tương quan Pearson** giữa %d lợi suất log ngày của **%s** và **%s** trong %d phiên tới **%s** '
         '(lợi suất log = ln(giá hôm nay/giá hôm trước)). Làm tròn 4 chữ số thập phân.' % (n, a, b, n, S30))
    ex = {'value': 0, 'unit': 'hệ số', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history', 'note': '(tuỳ chọn)'}
    oracle = LIB + "check('corr', R(CORR('%s', '%s', %d)), gold['solution']['value'])\n" % (a, b, n)
    return cs.spec(tid, 'C3', 'Tương quan %s/%s' % (a, b), q, ex, {'value': cs.r4(r)}, [cs.val('value', r, CORR)], oracle, [a, b])


def beta_task(tid, a, n=60):
    b = beta(a, n)
    q = ('Tính **beta** của **%s** so với **VNINDEX** trên %d lợi suất log ngày tới **%s** = hiệp phương sai mẫu(lợi suất %s, lợi suất VNINDEX) '
         '/ phương sai mẫu(lợi suất VNINDEX).' % (a, n, S30, a))
    ex = {'value': 0, 'unit': 'lần', 'period': '(kỳ được hỏi)', 'source': 'vn_quote_history + vn_index_ohlcv', 'note': '(tuỳ chọn)'}
    oracle = LIB + "check('beta', R(BETA('%s', %d)), gold['solution']['value'])\n" % (a, n)
    return cs.spec(tid, 'C3', 'Beta %s so với VNINDEX' % a, q, ex, {'value': cs.r4(b)}, [cs.val('value', b, BETA)], oracle, [a, 'VNINDEX'])


def build():
    return [vol_task('fin-c3-vol-431', ['VNM', 'MSN', 'SAB']),
            vol_task('fin-c3-vol-432', ['ACB', 'TCB', 'MBB']),
            vol_task('fin-c3-vol-433', ['GAS', 'PLX', 'POW']),
            dd_task('fin-c3-dd-434', ['HPG', 'GVR']),
            dd_task('fin-c3-dd-435', ['VIC', 'VHM']),
            dd_task('fin-c3-dd-436', ['SSI', 'VJC']),
            corr_task('fin-c3-corr-437', 'VCB', 'BID'),
            corr_task('fin-c3-corr-438', 'FPT', 'MWG'),
            beta_task('fin-c3-beta-439', 'SSI'),
            beta_task('fin-c3-beta-440', 'VNM')]


def main():
    specs = build()
    for s in specs:
        d = cs.write('main', s)
        toml = (d / 'task.toml').read_text(encoding='utf-8')
        toml = toml.replace('# Compute stratum — amendment 2026-11-11 (d), tools/build_compute_stratum_20261111.py',
                            '# Compute additions v4.7 — plan 2026-11-16 (OpenTrading#309 D2), tools/build_compute_series_20261116.py')
        toml = re.sub(r'^created = ".*"$', 'created = "2026-11-16"', toml, flags=re.M)
        (d / 'task.toml').write_text(toml, encoding='utf-8')
    print('built', len(specs))


if __name__ == '__main__':
    main()
