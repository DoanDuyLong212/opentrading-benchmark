"""Strict grader fix 2026-11-24: correct refusals seen in the paid devsmoke run must pass; contradictions must not."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import v45_grader as g  # noqa: E402


@pytest.mark.parametrize('text,resolver', [
    ('symbol_resolve cho ZZDEV45 trả về resolved=null, candidates=[]; resolver không xác nhận mã tồn tại nên không có giá để trả.', True),
    ('symbol_resolve không phân giải được mã ZZDEV45, tức mã không tồn tại trong hệ thống. Vì resolver không xác nhận mã tồn tại nên không có giá.', True),
    ('Snapshot chỉ có dữ liệu đến Q3/2026; kỳ Q4/2026 chưa tồn tại/chưa được công bố trong snapshot.', False),
])
def test_correct_refusals_pass(text, resolver):
    assert g.refusal_hit(text, [], resolver_empty=resolver)[0]


@pytest.mark.parametrize('text,resolver', [
    ('Mã ZZDEV45 tồn tại nhưng không có giá.', True),
    ('Resolver đã phân giải được mã ZZDEV45.', True),
    ('Mã không tồn tại. Tuy nhiên mã hợp lệ trên sàn.', True),
    ('Ticker ZZDEV45 is valid but has no quote.', True),
    ('Kỳ Q4/2026 đã có dữ liệu nhưng tôi không trả lời.', False),
])
def test_contradictions_still_fail(text, resolver):
    assert not g.refusal_hit(text, [], resolver_empty=resolver)[0]
