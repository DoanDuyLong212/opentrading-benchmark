"""Prospective financial contract fixes; old R3 outcomes remain immutable."""
import runpy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
G=runpy.run_path(str(ROOT/'tools/v45_grader.py'))
@pytest.mark.parametrize('label',['tỷ lệ','tỉ lệ','dimensionless','unitless','ratio','fraction','lần','x'])
def test_dimensionless_unit_canonicalization(label):
 assert G['canon_unit'](label)=='dimensionless'
 assert G['canon_unit'](label)!=G['canon_unit']('tỷ đồng')
 assert G['canon_unit'](label)!=G['canon_unit']('%')
@pytest.mark.parametrize('label',['tỷ đồng','billion VND','tỷ VND','ty dong'])
def test_currency_remains_currency(label):assert G['canon_unit'](label)=='ty_dong'
def test_empty_unit_does_not_become_dimensionless():assert G['canon_unit']('')!='dimensionless'
@pytest.mark.parametrize('reason',[
 'Snapshot không có kỳ Q4/2031; chỉ có kỳ Q2 và Q3.',
 'Kỳ Q4/2031 chưa được công bố trong snapshot.',
 'Không có trong snapshot kỳ được hỏi.',
 'Chưa công bố báo cáo quý được yêu cầu.',
 'No reports are available for the requested period.',
])
def test_generic_missing_data_predicates(reason):assert G['refusal_hit'](reason,[],False)[0]
@pytest.mark.parametrize('reason',[
 'Không phải không có kỳ Q4/2031.',
 'Không có kỳ Q4 nhưng đã có dữ liệu kỳ đó.',
 'Tool error unsupported_snapshot_query nên không có dữ liệu.',
 'Truy vấn bị từ chối; không có kỳ Q4.',
 'Không thể trả lời được.',
 'Đã công bố báo cáo quý được hỏi.',
])
def test_negation_contradiction_and_rejected_query_do_not_prove_missing_data(reason):assert not G['refusal_hit'](reason,[],False)[0]
def test_precision_is_not_silently_relaxed():
 assert not G['val_match'](52.87,52.86666666666667,{'abs':1e-6})[0]
 assert G['val_match'](52.866667,52.86666666666667,{'abs':1e-6})[0]
def test_primary_copies_and_template_are_identical():
 expected=(ROOT/'tools/v45_grader.py').read_bytes()
 for p in (ROOT/'tasks').glob('**/tests/grader.py'):
  memory=(p.parents[1]/'environment'/'turns.json').exists()
  wanted=expected.replace(b'"evidence","source_evidence"',b'"evidence","source_evidence","memory_evidence"') if memory else expected
  assert p.read_bytes()==wanted, p
 assert runpy.run_path(str(ROOT/'tools/_gen_templates.py'))['GRADER_TMPL']==expected.decode()
