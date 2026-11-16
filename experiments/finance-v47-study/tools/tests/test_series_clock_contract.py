"""Offline regression for #12's dated observations and #11's conservative policy."""
import math
import sys
from pathlib import Path
import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import build_compute_series_20261116 as builder
from clock_policy import ARMS, audit_clock_observations, comparative_eligible
import judge_primary

DAYS = ['2026-10-27', '2026-10-28', '2026-10-29', '2026-10-30']


def rows(logs):
    return [{'t': d, 'c': math.exp(x)} for d, x in zip(DAYS, logs)]


@pytest.fixture(params=['module', 'embedded'])
def lib(request):
    if request.param == 'module':
        import series_contract
        return vars(series_contract)
    ns = {}
    exec(builder.LIB, ns)
    return ns


def test_independent_hand_computed_returns(lib):
    # Market log returns [1,2,3], asset [2,1,4]: means 2,7/3;
    # sample market variance=1, covariance=1, asset variance=7/3.
    left = lib['dated_closes'](rows([0, 2, 3, 7]), 3)
    right = lib['dated_closes'](rows([0, 1, 3, 6]), 3)
    assert lib['series_beta'](left, right) == pytest.approx(1)
    assert lib['series_corr'](left, right) == pytest.approx(math.sqrt(3 / 7))


@pytest.mark.parametrize('mutation', ['shuffle', 'duplicate', 'missing', 'first', 'end', 'zero', 'negative', 'nan', 'infinity', 'bad_iso'])
def test_invalid_series_rejected(lib, mutation):
    data = rows([0, 1, 3, 6])
    if mutation == 'shuffle': data[0], data[1] = data[1], data[0]
    elif mutation == 'duplicate': data[1]['t'] = data[0]['t']
    elif mutation == 'missing': data.pop(1)
    elif mutation == 'first': data.pop(0)
    elif mutation == 'end': data[-1]['t'] = '2026-10-31'
    elif mutation == 'bad_iso': data[0]['t'] = '20261027'
    else: data[1]['c'] = {'zero': 0, 'negative': -1, 'nan': float('nan'), 'infinity': float('inf')}[mutation]
    with pytest.raises(ValueError):
        lib['dated_closes'](data, 3, calendar=DAYS)


def test_window_and_intervals(lib):
    data = rows([0, 1, 3, 6])
    data[0]['t'] = '2026-10-26'
    with pytest.raises(ValueError, match='window'):
        lib['dated_closes'](data, 3, calendar=DAYS)
    left = lib['dated_closes'](data, 3)
    right = lib['dated_closes'](rows([0, 2, 3, 7]), 3)
    with pytest.raises(ValueError, match='intervals'):
        lib['series_beta'](left, right)
    flat = lib['dated_closes'](rows([0, 0, 0, 0]), 3)
    with pytest.raises(ValueError, match='variance'):
        lib['series_beta'](right, flat)
    with pytest.raises(ValueError, match='two paired'):
        lib['series_corr'](right[-2:], flat[-2:])


def test_clock_wire_audit():
    obs = [dict(arm=a, stage=s, native_date='2026-11-01', snapshot_date='2026-11-01',
                redacted_request='complete synthetic request: '+a+s)
           for a in ARMS for s in ('first', 'continuation')]
    assert audit_clock_observations(obs, '2026-11-01')['parity_verified']
    obs[-1]['native_date'] = '2026-11-16'
    assert not audit_clock_observations(obs, '2026-11-01')['parity_verified']
    assert not audit_clock_observations(obs[:1], '2026-11-01')['parity_verified']
    assert not comparative_eligible('fin-s3-asof-486')
    assert not comparative_eligible('fin-s2-buy-483')


def test_summary_diagnostic_denominator():
    base = dict(arm='ot', scoring='answerable', primary=True, strict_success=True,
                raw_format_valid=True, dnf=False, dnf_infra=False, fp=False,
                false_refusal=False, judge_verdict='correct', numeric_gate=True,
                manual_rejected=False, stratum='safety')
    recs = [dict(base, task='fin-s2-buy-483', tier='S2'),
            dict(base, task='fin-s3-asof-486', tier='S3')]
    assert judge_primary.summarize(recs, 'ot', 10) == {}
    assert judge_primary.by_stratum(recs, 'ot', 10) == {}
    assert judge_primary.by_stratum(recs, 'ot', 10, diagnostic=True)['safety']['arms']['ot']['scheduled'] == 2


def test_diagnostic_never_bootstrapped():
    base = dict(task='fin-s3-asof-486', stratum='safety', tier='S3', primary=True)
    recs = [dict(base, arm=arm) for arm in ('ot', 'dsh')]
    assert judge_primary.by_stratum(recs, 'ot', 10) == {}
    diagnostic = judge_primary.by_stratum(recs, 'ot', 10, diagnostic=True)
    assert diagnostic['safety']['diagnostic_scheduled'] == 2
    assert all('paired_task_bootstrap' not in arm for arm in diagnostic['safety']['arms'].values())
