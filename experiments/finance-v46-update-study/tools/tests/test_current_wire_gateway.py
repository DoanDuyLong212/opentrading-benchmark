"""Historical SDK envelope migrated synthetically through the v45 stubbed gateway.
This does not certify the current v45 actual native runtime; its worker owns that proof.

The native artifact was produced with the study's own installed SDK7 and
NVIDIA-compatible provider. Upstream HTTP is stubbed: these are wire contract
checks, never NVIDIA/model inferences or evidence for financial quality.
"""
import json
from pathlib import Path
import runpy
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
HELPERS=runpy.run_path(str(ROOT/'tools/tests/test_provider_runner.py'))

@pytest.mark.parametrize('index',[0,1,2])
def test_current_native_sdk_nvidia_requests_keep_catalog_and_declared_rewrites(tmp_path,monkeypatch,index):
 from runners import provider
 from ready_check import verify_request_capture
 artifact=json.loads((ROOT/'tools/tests/fixtures/historical-v44-native-wire.json').read_text())
 assert 'no model inference' in artifact['kind'] and 'fetch stub' in artifact['kind']
 body=artifact['bodies'][index]
 assert body['model']=='nvidia/nemotron-3.5-bolt-e4b'
 body={**body,'model':provider.DEFAULT_MODEL}
 assert body.get('reasoning_effort') is None
 assert [t['function']['name'] for t in body['tools']]==['mcp__opentrading__quote']
 if index==2:
  assert body['tool_choice']=='none'
  assert 'One bounded correction.' in body['messages'][-1]['content']
 payload={'model':body['model'],'choices':[{'delta':{'content':'fixture'},'finish_reason':'stop'}],
          'usage':{'prompt_tokens':20,'completion_tokens':3}}
 raw=('data: '+json.dumps(payload)+'\n\ndata: [DONE]\n\n').encode()
 class Response:
  status=200
  headers={'Content-Type':'text/event-stream'}
  def __init__(self):self.remaining=raw
  def __enter__(self):return self
  def __exit__(self,*args):return False
  def read1(self,_size):value=self.remaining;self.remaining=b'';return value
 monkeypatch.setattr(provider.urllib.request,'urlopen',lambda *_a,**_k:Response())
 gate=HELPERS['_gateway'](tmp_path,monkeypatch,allowed=('mcp__opentrading__quote',))
 # Generic gateway unit fixture reserves only 10k; this real native prompt
 # must be checked under the preregistered 48k policy budget, without relaxing it.
 gate.options.update(max_total_tokens=48000,max_requests=24,max_output_tokens=2048,provider_timeout_s=45)
 gate.options['snapshot_tool_definitions']=[{'name':'quote'}]
 handler=HELPERS['_Handler'](body)
 gate.handle(handler)
 assert handler.response_status==200
 row=gate.rows[0]
 assert row['request_model']==body['model'] and row['effort'] is None
 assert (row['effective_temperature'],row['effective_top_p'],row['effective_max_tokens'])==(1,.95,2048)
 assert row['tool_names']==['mcp__opentrading__quote']
 verify_request_capture(row,expected_temperature=1,expected_top_p=.95)
 native=json.loads(Path(row['native_request_capture']['path']).read_text())
 effective=json.loads(Path(row['effective_request_capture']['path']).read_text())
 assert native==body
 assert native['messages']==effective['messages'] and native['tools']==effective['tools']
