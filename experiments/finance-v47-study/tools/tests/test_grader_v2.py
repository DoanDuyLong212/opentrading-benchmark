"""Adversarial grader regressions; fixture evidence cannot pass a live driver ledger."""
import copy
import contextlib
import io
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from _gen_templates import GRADER_TMPL

NAMESPACE={'__file__':__file__,'__name__':'grader_test'}
exec(compile(GRADER_TMPL,'grader-v2','exec'),NAMESPACE)


def grade(tmp_path, answer, gold):
    a,g,o=(tmp_path/name for name in ['a.json','g.json','o.json'])
    a.write_text(json.dumps(answer));g.write_text(json.dumps(gold))
    argv=sys.argv;sys.argv=['grader',str(a),'-g',str(g),'-o',str(o)]
    try:
        with contextlib.redirect_stdout(io.StringIO()):NAMESPACE['main']()
    finally:sys.argv=argv
    return json.loads(o.read_text())


@pytest.mark.parametrize('value',[False,True,{},[],float('nan'),float('inf'),'1e999'])
def test_nonfinite_boolean_and_container_values_rejected(tmp_path,value):
    assert not grade(tmp_path,{'value':value},{'scoring':'value','expects':[{'type':'value','gold':100,'tol':{'rel':.005}}]})['success']


@pytest.mark.parametrize('answer',[{},[],None,1,'answer',{'value':'null','reason':'unavailable'},{'value':{'amount':3},'reason':'unavailable'},{'value':False,'reason':'unavailable'}])
def test_refusal_requires_present_json_null(tmp_path,answer):
    assert not grade(tmp_path,answer,{'scoring':'refusal','refusal_tokens':['unavailable']})['success']


def test_null_refusal_with_reason_passes(tmp_path):
    assert grade(tmp_path,{'value':None,'reason':'unavailable'},{'scoring':'refusal','refusal_tokens':['unavailable']})['success']


@pytest.mark.parametrize('reason',[
    'Mã XYZX không được tìm thấy trong dữ liệu snapshot.',
    'Chỉ tiêu này chưa được công bố tại thời điểm snapshot.',
    'Báo cáo chưa được phát hành.',
    'Không tìm thấy dữ liệu cho mã được hỏi.',
])
def test_vietnamese_refusal_passive_paraphrases(tmp_path, reason):
    gold={'scoring':'refusal','refusal_tokens':['không tìm thấy','chưa công bố','chưa phát hành']}
    assert grade(tmp_path,{'value':None,'reason':reason},gold)['success']


@pytest.mark.parametrize('reason',[
    'Không phải không được tìm thấy mã này.',
    'Không phải là không tìm thấy mã này.',
    'Không không tìm thấy.',
    'Không tìm thấy lúc đầu nhưng đã tìm thấy dữ liệu.',
    'Chưa được công bố, nhưng đã công bố trong snapshot.',
    'Không tìm thấy, nhưng mã vẫn tồn tại.',
    'not unavailable',
])
def test_refusal_double_negations_and_opposite_claims_rejected(tmp_path, reason):
    gold={'scoring':'refusal','refusal_tokens':['không tìm thấy','chưa công bố','unavailable']}
    assert not grade(tmp_path,{'value':None,'reason':reason},gold)['success']


def test_passive_refusal_still_requires_null(tmp_path):
    gold={'scoring':'refusal','refusal_tokens':['không tìm thấy']}
    assert not grade(tmp_path,{'value':123,'reason':'Không được tìm thấy.'},gold)['success']


@pytest.mark.parametrize('period',['Q1/1900 không phải Q3/2026','Q3/2025','Q3/2026 so với Q1/2026','Q3/2026','Q3/2026 so với Q2/2025'])
def test_wrong_or_incomplete_comparison_period_rejected(tmp_path,period):
    gold={'scoring':'value','expects':[{'type':'period','path':'period','accept':['Q3/2026','q3/26','Q2/2026','q2/26','so với']}]}
    assert not grade(tmp_path,{'period':period},gold)['success']


@pytest.mark.parametrize('period',['Q3/2026 so với Q2/2026','quý 3 năm 2026 / quý 2 năm 2026','Q3/26 vs Q2/26'])
def test_comparison_period_valid_variants(tmp_path,period):
    gold={'scoring':'value','expects':[{'type':'period','path':'period','accept':['Q3/2026','Q2/2026']}]}
    assert grade(tmp_path,{'period':period},gold)['success']


@pytest.mark.parametrize('source',['không dùng vn_quote_history','NOT vn_quote_history','vn_quote_history_fake','vn_quote_history or invented','vnstock'])
def test_source_requires_canonical_tool(tmp_path,source):
    gold={'scoring':'value','expects':[{'type':'str','path':'source','accept':['vn_quote_history']}]}
    assert not grade(tmp_path,{'source':source},gold)['success']


def test_numeric_tolerance_boundary(tmp_path):
    gold={'scoring':'value','expects':[{'type':'value','gold':100,'tol':{'abs':.5}}]}
    assert grade(tmp_path,{'value':100.5},gold)['success']
    assert not grade(tmp_path,{'value':100.5001},gold)['success']


def test_provenance_namespace_and_timestamp_checked_separately(tmp_path):
    row={'tool':'vn_quote_history','source':'vnstock','as_of':'2026-11-01T00:00:00+07:00',
         'matched_entry_id':'quote:EIB','response_sha256':'c'*64}
    gold={'scoring':'value','expects':[{'type':'value','gold':100}], 'provenance_contract':[row],'payload_sha256':'a'*64}
    answer={'value':100,'evidence':[{**row,'call_id':'fixture','payload_sha256':'a'*64}]}
    assert grade(tmp_path,answer,gold)['success']
    for key,val in [('source','vn_quote_history'),('as_of','2025-01-01'),('payload_sha256','b'*64),('call_id',None)]:
        bad=copy.deepcopy(answer);bad['evidence'][0][key]=val
        result=grade(tmp_path,bad,gold)
        assert not result['success']
        assert result['semantic_correctness']

@pytest.mark.parametrize('period',['2026-10-30 và 2026-10-29','30/10/2025','không phải 30/10/2026'])
def test_date_extra_wrong_endpoint_rejected(tmp_path,period):
    gold={'scoring':'value','expects':[{'type':'period','path':'period','accept':['30/10','2026-10-30']}]}
    assert not grade(tmp_path,{'period':period},gold)['success']


@pytest.mark.parametrize('period',['tháng 9/2026','9/2026','T9/2026'])
def test_month_valid_aliases_preserved(tmp_path,period):
    gold={'scoring':'value','expects':[{'type':'period','path':'period','accept':['tháng 9/2026','9/2026','t9/2026']}]}
    assert grade(tmp_path,{'period':period},gold)['success']
