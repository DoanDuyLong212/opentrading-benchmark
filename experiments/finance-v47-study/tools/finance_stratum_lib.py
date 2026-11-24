"""Shared, payload-only computations for the 2026-11-24 fundamental (C5) and finance-memory (M6) strata.

This file is embedded verbatim into every generated oracle (it needs only `env(key)` from the oracle template),
so gold and oracle come from one definition. Every input is read from the task's own frozen payload envelopes.
Statement envelopes are keyed 'fs:<SYM>:<q|y>:<KQKD|CDKT>'.
"""
from decimal import Decimal as _D

REV, GP, OP, NI, NIP = 'Doanh thu thuần', 'Lợi nhuận gộp', 'LN thuần từ HĐKD', 'LNST thu nhập DN', 'LNST của CĐ cty mẹ'
CA, TA, TL, CL, EQ, MI = ('Tài sản ngắn hạn', 'Tổng tài sản', 'Nợ phải trả', 'Nợ ngắn hạn', 'Vốn chủ sở hữu',
                          'Lợi ích của CĐ thiểu số')
SECTION = {REV: 'KQKD', GP: 'KQKD', OP: 'KQKD', NI: 'KQKD', NIP: 'KQKD',
           CA: 'CDKT', TA: 'CDKT', TL: 'CDKT', CL: 'CDKT', EQ: 'CDKT', MI: 'CDKT'}
TTM = ['Q3/2025', 'Q4/2025', 'Q1/2026', 'Q2/2026']
PRIOR_TTM = ['Q3/2024', 'Q4/2024', 'Q1/2025', 'Q2/2025']
EQ_POINTS = ['Q2/2025', 'Q3/2025', 'Q4/2025', 'Q1/2026', 'Q2/2026']


def fs_key(sym, freq, item):
    return 'fs:%s:%s:%s' % (sym, freq, SECTION[item])


def item(sym, freq, name, period):
    data = env(fs_key(sym, freq, name))['data']
    for rows in data['statements'].values():
        for row in rows:
            if row['name'] == name:
                value = row['values'].get(period)
                if value is None:
                    raise KeyError('%s %s %s missing' % (sym, name, period))
                return _D(str(value))
    raise KeyError('%s row %s missing' % (sym, name))


def q(sym, name, period):
    return item(sym, 'q', name, period)


def y(sym, name, year):
    return item(sym, 'y', name, year)


def ttm(sym, name, quarters=TTM):
    return sum(q(sym, name, p) for p in quarters)


def equity(sym, freq, period):
    """Vốn chủ sở hữu as published (the source leaves Lợi ích của CĐ thiểu số empty for every period)."""
    return item(sym, freq, EQ, period)


def avg(values):
    values = list(values)
    return sum(values) / len(values)


def pct(a, b):
    return (a / b - 1) * 100


def roe_ttm(sym):
    return ttm(sym, NIP) / avg(equity(sym, 'q', p) for p in EQ_POINTS) * 100


def roe_fy(sym, year='2025'):
    return y(sym, NIP, year) / equity(sym, 'y', year) * 100


def margin_ttm(sym, name, quarters=TTM):
    return ttm(sym, name, quarters) / ttm(sym, REV, quarters) * 100


def dupont(sym, year='2025', prev='2024'):
    rev, nip = y(sym, REV, year), y(sym, NIP, year)
    assets = avg([y(sym, TA, prev), y(sym, TA, year)])
    eq = avg([equity(sym, 'y', prev), equity(sym, 'y', year)])
    margin, turnover, multiplier = nip / rev * 100, rev / assets, assets / eq
    return {'margin': margin, 'turnover': turnover, 'leverage': multiplier, 'roe': margin * turnover * multiplier}


def dupont_driver(a, b):
    """Component with the largest relative gap |ln(A/B)| between two companies."""
    import math
    da, db = dupont(a), dupont(b)
    return max(('margin', 'turnover', 'leverage'), key=lambda k: abs(math.log(float(da[k] / db[k]))))


def cagr(sym, name, first='2021', last='2025'):
    years = int(last) - int(first)
    return ((y(sym, name, last) / y(sym, name, first)) ** (_D(1) / _D(years)) - 1) * 100


def debt_ratio(sym, period='Q2/2026'):
    return q(sym, TL, period) / q(sym, TA, period) * 100


def debt_to_equity(sym, period):
    return q(sym, TL, period) / equity(sym, 'q', period)


def current_ratio(sym, period='Q2/2026'):
    return q(sym, CA, period) / q(sym, CL, period)


def R(x):
    return float(round(_D(x), 4))
