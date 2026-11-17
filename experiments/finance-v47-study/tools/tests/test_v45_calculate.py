"""Current provider route identity contract, independent of historical arithmetic."""
import json, sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def test_only_documented_super_route_alias_accepted(tmp_path):
 from test_v45_provider_compute import setup,success
 from runners.provider import DEFAULT_MODEL,normalize_model
 from unittest.mock import patch
 g,h=setup(tmp_path);g.accepted_response_model='private/nvidia/nemotron-3.5-super-120b-a12b';g.admission={'checkpoint_unverified':True,'admission_contract':'user-authorized-requested-route-v2'}
 with patch('urllib.request.urlopen',return_value=success(g.accepted_response_model)):g.handle(h)
 assert h.status==200 and g.rows[0]['checkpoint_unverified'] is True and g.rows[0]['requested_model']==DEFAULT_MODEL
 (tmp_path/'second').mkdir();g,h=setup(tmp_path/'second')
 g.accepted_response_model='private/nvidia/nemotron-3.5-super-120b-a12b'
 with patch('urllib.request.urlopen',return_value=success('other-private-model')):g.handle(h)
 assert h.status==424 and g.rows[0]['error']=='provider_response_model_mismatch'
