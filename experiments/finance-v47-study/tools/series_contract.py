"""Dated close/return contract, embedded verbatim in generated standalone oracles."""
import datetime
import math
import statistics


def dated_closes(rows, n, end='2026-10-30', calendar=None):
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError('window must contain at least one return')
    dates, values = [], []
    for row in rows:
        day = row['t']
        if not isinstance(day, str) or datetime.date.fromisoformat(day).isoformat() != day:
            raise ValueError('date must be canonical ISO YYYY-MM-DD')
        if dates and day <= dates[-1]:
            raise ValueError('dates must be unique and strictly chronological')
        raw = row['c']
        if isinstance(raw, bool):
            raise ValueError('close must be finite and positive')
        price = float(raw)
        if not math.isfinite(price) or price <= 0:
            raise ValueError('close must be finite and positive')
        dates.append(day)
        values.append(price)
    if len(dates) < n + 1:
        raise ValueError('insufficient closes: need n+1')
    if dates[-1] != end:
        raise ValueError('series must end on declared date')
    if calendar is not None and dates[-n-1:] != list(calendar)[-n-1:]:
        raise ValueError('missing or mismatched date in declared window')
    return list(zip(dates[-n-1:], values[-n-1:]))


def dated_returns(points):
    return [((a[0], b[0]), math.log(b[1] / a[1])) for a, b in zip(points, points[1:])]


def paired_returns(left, right):
    a, b = dated_returns(left), dated_returns(right)
    if len(a) < 2 or len(a) != len(b):
        raise ValueError('at least two paired returns required')
    if [r[0] for r in a] != [r[0] for r in b]:
        raise ValueError('return date intervals must match exactly')
    return [r[1] for r in a], [r[1] for r in b]


def series_corr(left, right):
    a, b = paired_returns(left, right)
    if statistics.variance(a) == 0 or statistics.variance(b) == 0:
        raise ValueError('correlation requires nonzero variance')
    return statistics.correlation(a, b)


def series_beta(left, right):
    a, b = paired_returns(left, right)
    variance = statistics.variance(b)
    if variance == 0:
        raise ValueError('benchmark variance must be nonzero')
    return statistics.covariance(a, b) / variance
