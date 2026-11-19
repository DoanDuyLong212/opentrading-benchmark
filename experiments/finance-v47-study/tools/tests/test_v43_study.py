"""Independent offline interface fixtures; no smoke task or gold used as input."""
import copy
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from mcp_snapshot_server import build_tool_defs, replay_call, select_envelope, digest
from v43_gate import MODELS


def offline_entries():
    def envelope(data,unit,availability='available',source='fixture-alpha'):
        return {'data':data,'unit':unit,'availability':availability,
                'provenance':{'source':source,'as_of':'2024-03-31T12:00:00+07:00'}}
    return [
        ('resolve-alias',{'tool':'symbol_resolve','params':{'query':'Ngân hàng Á Châu'},
                          'envelope':envelope({'resolved':{'symbol':'ACB'},'ambiguous':False,'candidates':[]},None)}),
        ('resolve-empty',{'tool':'symbol_resolve','params':{'query':'NO_SUCH_ENTITY'},
                          'envelope':envelope({'resolved':None,'ambiguous':False,'candidates':[]},None,'empty')}),
        ('acb',{'tool':'vn_quote_history','params':{'symbol':'ACB'},
                 'envelope':envelope({'last':17.125,'last_t':'2024-03-29'},'nghìn đồng/cổ phiếu')}),
        ('vib-partial',{'tool':'vn_quote_history','params':{'symbol':'VIB'},
                 'envelope':envelope({'last':None,'last_t':'2024-03-28'},'nghìn đồng/cổ phiếu','partial','fixture-beta')})]


def test_independent_alias_multi_entity_partial_source_and_empty_receipts(tmp_path):
    entries=offline_entries();before=copy.deepcopy(entries);ledger=tmp_path/'calls.jsonl'
    fixtures=[('symbol_resolve',{'query':'Ngân hàng Á Châu'}),('symbol_resolve',{'query':'NO_SUCH_ENTITY'}),
              ('vn_quote_history',{'symbol':'ACB'}),('vn_quote_history',{'symbol':'VIB'})]
    responses=[replay_call(entries,name,args,'offline-payload',str(ledger)) for name,args in fixtures]
    assert responses[0]['data']['resolved']['symbol']=='ACB'
    assert responses[1]['availability']=='empty' and responses[1]['data']['resolved'] is None
    assert responses[2]['unit']=='nghìn đồng/cổ phiếu' and responses[2]['data']['last_t']=='2024-03-29'
    assert responses[3]['availability']=='partial' and responses[3]['provenance']['source']=='fixture-beta'
    rows=[json.loads(x) for x in ledger.read_text().splitlines()]
    assert len(rows)==4 and len({r['call_id'] for r in rows})==4
    assert all(r['status']=='ok' for r in rows)
    assert all(responses[i]['benchmark_evidence']['response_sha256']==rows[i]['response_sha256'] for i in range(4))
    assert entries==before


def test_independent_wrong_window_projection_can_correct_but_not_drift(tmp_path):
    entries=offline_entries();args={'symbol':'ACB','days':2,'columns':['c']};before=copy.deepcopy(args)
    result=replay_call(entries,'vn_quote_history',args,'offline-payload',str(tmp_path/'ledger'))
    assert args==before and result['error']['code']=='unsupported_snapshot_query'
    assert {'/days','/columns'}<=set(result['error']['argument_paths'])
    assert result['error']['retryable_with_corrected_arguments']
    assert result['error']['allowed_public_variants']==[{'symbol':'ACB'},{'symbol':'VIB'}]
    assert not {'benchmark_evidence','data','availability'}&result.keys()
    corrected=replay_call(entries,'vn_quote_history',{'symbol':'ACB'},'offline-payload',str(tmp_path/'ledger'))
    assert corrected['data']['last']==17.125
    # A different supported entity is available publicly, but cannot be mistaken for the original evidence.
    other=select_envelope(entries,'vn_quote_history',{'symbol':'VIB'})
    assert other!=corrected and other['availability']=='partial'


def test_common_description_preserves_production_metadata_and_constraints():
    definitions=build_tool_defs(offline_entries())
    original={x['name']:x for x in json.loads((ROOT/'tools/tool_contracts_v4.json').read_text())['tools']}
    for d in definitions:
        if d['name'] in ('analytics_compute','analytics_calculate'):
            expected='deterministic-derivation-v45' if d['name']=='analytics_compute' else 'grounded-calculation-v45'
            assert d['inputSchema']['x-opentrading-schema-profile']==expected
            continue
        assert d['description'].startswith('FINITE SNAPSHOT SUPPORT:')
        assert d['description'].endswith(original[d['name']]['description'])
        assert d['description'].index('snapshot_requests=')<d['description'].index('PRODUCTION API METADATA')
        assert 'allowed_public_variants' in d['description']
        assert d['inputSchema']['x-opentrading-schema-profile']=='finite-replay-c2'
        assert d.get('annotations')==original[d['name']].get('annotations')






def test_supervisor_proceeds_after_quality_failure_and_blocks_controls(tmp_path,monkeypatch):
    # Exercise real state-machine loop with deterministic subprocess/auditor fixtures, no provider.
    import v43_supervisor as supervisor
    seal=tmp_path/'seal';seal.write_text('{}');audit=tmp_path/'audit.json';state=tmp_path/'state.json'
    configs=[];items=[]
    for name in ('bolt','deepseek'):
        c=tmp_path/(name+'.json');c.write_text(json.dumps({'model':MODELS[name],'trial_timeout_s':240 if name=='bolt' else 900,'provider_timeout_s':45 if name=='bolt' else 240}))
        items.append({'stratum':name,'config':str(c),'out':str(tmp_path/name)})
    monkeypatch.setattr(supervisor,'validate_seal',lambda _:dict(runs=items,audit_script={'path':str(tmp_path/'audit.py')}))
    monkeypatch.setattr(supervisor,'diagnostic_quality',lambda _:dict(quality_pass=False))
    calls=[];report={'completed_runs':{}}
    def run(command,*args,**kwargs):
        calls.append(command)
        if '--execute' in command:
            name='bolt' if command[command.index('--run')+1].endswith('/bolt') else 'deepseek'
            report['completed_runs'][MODELS[name]]={'audit_controls_pass':True,'errors':[]}
            audit.write_text(json.dumps(report))
        return 0
    monkeypatch.setattr(supervisor,'run_child',run)
    monkeypatch.setattr(sys,'argv',['supervisor','--seal',str(seal),'--state',str(state),'--audit-script',str(tmp_path/'audit.py'),'--audit-output',str(audit)])
    assert supervisor.main()==0
    result=json.loads(state.read_text());assert result['status']=='completed'
    assert set(result['runs'])=={'bolt','deepseek'} and all(not v['quality_pass'] for v in result['runs'].values())
    assert len(calls)==4
    assert supervisor.main()==0 and len(calls)==4  # durable completed resume cannot relaunch




def test_acquisition_duplicate_audit_requires_actual_wire_phase_and_original_args(tmp_path):
    from intent_audit import verify_v42_local_intent
    name='opentrading_vn_quote_history';schema={'type':'object','properties':{'symbol':{'type':'string'}}}
    phase={'type':'finance-phase','phase':'bounded_finance_acquisition','transition':'enter',
           'availableToolNames':[name],'toolChoice':'auto'}
    original={'type':'tool-start','callId':'original','name':name,'input':{'symbol':'ACB'}}
    reason='Repeated or already pending/successful intent; do not replay this request.'
    event={'type':'tool-end','callId':'duplicate','ok':False,
           'financeIntent':{'sdk_call_id':'duplicate','intent_id':'fixture-intent','original_sdk_call_id':'original',
                            'correction_budget':1,'correction_used':0,'phase':'bounded_finance_acquisition','reason':reason},
           'localRejection':{'code':'policy_guard_rejected','tool':name,'rawInput':'{"symbol":"ACB"}','reason':reason,
                             'phase':'bounded_finance_acquisition','allowedTools':[name]}}
    events=[phase,original,event];capture=tmp_path/'actual-wire.json'
    capture.write_text(json.dumps({'messages':[{'role':'user','content':'One bounded evidence acquisition opportunity before final.'}]}))
    provider=[{'response_tool_call_ids':['original','duplicate'],'native_request_capture':{'path':str(capture)}}]
    verify_v42_local_intent(event,events,provider,{name:schema})
    with pytest.raises(ValueError,match='generating request'):verify_v42_local_intent(event,events,[],{name:schema})
    event['localRejection']['rawInput']='{"symbol":"VIB"}'
    with pytest.raises(ValueError,match='arguments differ'):verify_v42_local_intent(event,events,provider,{name:schema})


def test_supervisor_exception_is_durable_blocked_before_inference(tmp_path,monkeypatch):
    import v43_supervisor as supervisor
    state=tmp_path/'state.json'
    def denied(_):raise ValueError('Sealed source drift')
    monkeypatch.setattr(supervisor,'validate_seal',denied)
    monkeypatch.setattr(sys,'argv',['supervisor','--seal',str(tmp_path/'seal'),'--state',str(state),
                                   '--audit-script','unused','--audit-output','unused'])
    assert supervisor.main()==1
    result=json.loads(state.read_text())
    assert result['status']=='blocked' and result['reason']=='Sealed source drift'
    assert result['supervisor_pid']>0 and result['child_pid'] is None


def test_supervisor_cancellation_unwinds_driver_and_separate_native_session(tmp_path):
    import os,signal,subprocess,time
    native_pid=tmp_path/'native.pid';driver_pid=tmp_path/'driver.pid';state=tmp_path/'state.json'
    driver=tmp_path/'driver.py'
    driver.write_text('''import os,signal,subprocess,sys,time
from pathlib import Path
p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=True)
Path(sys.argv[1]).write_text(str(p.pid));Path(sys.argv[2]).write_text(str(os.getpid()))
try:time.sleep(60)
finally:
 os.killpg(p.pid,signal.SIGKILL)
 p.wait()
''')
    controller=tmp_path/'controller.py'
    controller.write_text('''import sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from v43_supervisor import run_child
state={'runs':{}}
try:run_child([sys.executable,sys.argv[2],sys.argv[3],sys.argv[4]],sys.argv[5],state,Path(sys.argv[6]),'cancel-fixture')
except KeyboardInterrupt:pass
''')
    proc=subprocess.Popen([sys.executable,str(controller),str(ROOT/'tools'),str(driver),str(native_pid),str(driver_pid),str(tmp_path/'log'),str(state)],start_new_session=True)
    try:
        deadline=time.monotonic()+10
        while not native_pid.exists() and time.monotonic()<deadline:time.sleep(.05)
        assert native_pid.exists()
        ids=[int(native_pid.read_text()),int(driver_pid.read_text())]
        os.kill(proc.pid,signal.SIGINT);assert proc.wait(timeout=12)==0
        for pid in ids:
            with pytest.raises(ProcessLookupError):os.kill(pid,0)
        receipt=json.loads(state.read_text())
        assert receipt['child_pid'] is None
        assert receipt['last_child_cleanup']['signals']==['SIGINT']
    finally:
        if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
