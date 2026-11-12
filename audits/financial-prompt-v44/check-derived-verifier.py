"""Independent derived-audit negative controls over frozen source envelopes, no inference."""
import copy,hashlib,json,sys,tempfile
from pathlib import Path
WORK=Path('/home/doanlong/extra/benchmark');STUDY=WORK/'experiments/finance-v44-study'
sys.path[:0]=[str(STUDY/'tools'),str(Path(__file__).parent)]
from mcp_snapshot_server import load_entries,replay_call,replay_compute
from derived_verifier import verify_derived,smoke_financial_canary
checks=[]
def check(name,value):
    if not value:raise AssertionError(name)
    checks.append(name)
task=STUDY/'tasks/smoke/smoke-agg-01';payload=task/'environment/payloads.json';entries,_=load_entries(payload);payloadsha=hashlib.sha256(payload.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory() as t:
    log=Path(t)/'ledger';sources={};refs=[]
    for symbol in ('VCB','BID','CTG','TCB','MBB'):
        env=replay_call(entries,'vn_quote_history',{'symbol':symbol},payloadsha,str(log));receipt=env['benchmark_evidence'];sources[receipt['call_id']]=env;refs.append({'call_id':receipt['call_id'],'path':'/data/last'})
    args={'operation':'mean','operands':refs,'input_unit':'nghìn đồng/cổ phiếu','output_unit':'nghìn đồng/cổ phiếu'};replay_compute(args,sources,payloadsha,str(log))
    ledger=[json.loads(x) for x in log.read_text().splitlines()];proof=verify_derived(task,ledger)
    check('actual five-source mean independently32.18',len(proof)==1 and proof[0]['value_decimal']=='32.18')
    variants=[]
    x=copy.deepcopy(ledger);x[-1]['derivation']['value']=99;variants.append(('tamperednumericresult',x))
    x=copy.deepcopy(ledger);x[-1]['derivation']['inputs'][0]['source_response_sha256']='forged';variants.append(('tamperedsourcehash',x))
    x=copy.deepcopy(ledger);x[-1]['response_sha256']='forged';variants.append(('tamperedderivedhash',x))
    x=copy.deepcopy(ledger);x[-1]['source']='vnstock';variants.append(('syntheticupstreammetadata',x))
    x=copy.deepcopy(ledger);x[-1]['arguments']['operands'][0]['call_id']='foreignsession';variants.append(('foreignsessionreference',x))
    x=copy.deepcopy(ledger);x[0]['ended_at']='9999-01-01';variants.append(('futuresource',x))
    x=copy.deepcopy(ledger);x[-1]['arguments']['input_unit']='VND';variants.append(('wrongunit',x))
    x=copy.deepcopy(ledger);x[-1]['arguments']['operands'][1]=x[-1]['arguments']['operands'][0];variants.append(('duplicatedaggregateoperand',x))
    for name,rows in variants:
        try:verify_derived(task,rows)
        except (ValueError,KeyError):rejected=True
        else:rejected=False
        check(name+'rejected',rejected)
    values={env['data']['symbol']:env['data']['last'] for env in sources.values()};values['mean']=32.18
    answer={'values':values,'unit':'nghìn đồng','period':'phiên 2026-10-30','source':'vn_quote_history'}
    check('actualsource numeric period unit canary passes',smoke_financial_canary(task,answer,ledger)['pass'])
    for label,change in [('wrongperiod',{'period':'2026-10-29'}),('wrongunit',{'unit':'đồng'}),('wrongsource',{'source':'vnstock'}),('wrongmean',{'values':{**values,'mean':31}}),('missingyear',{'period':'30/10'})]:
        check('secondarycanary '+label+' fails',not smoke_financial_canary(task,{**answer,**change},ledger)['pass'])
    quote=STUDY/'tasks/smoke/smoke-quote-01';qp=quote/'environment/payloads.json';qe,_=load_entries(qp);ql=Path(t)/'quoteledger'
    env=replay_call(qe,'vn_quote_history',{'symbol':'HPG'},hashlib.sha256(qp.read_bytes()).hexdigest(),str(ql));qr=[json.loads(x) for x in ql.read_text().splitlines()]
    ans={'value':env['data']['last'],'unit':'nghìn đồng','period':'phiên '+env['data']['last_t'],'source':'vn_quote_history'}
    check('latestquoteperiod canary passes',smoke_financial_canary(quote,ans,qr)['pass'])
    check('latestquote wrongperiod rejected',not smoke_financial_canary(quote,{**ans,'period':'2026-10-29'},qr)['pass'])
# Source-specific operations independently reconstructed from original public envelopes.
for task_name,tool,op,paths,unit,outunit in [
 ('fin-l2-growth-01','financial_statements','growth_pct',['/data/statements/Kết quả kinh doanh/0/values/Q3~12026','/data/statements/Kết quả kinh doanh/0/values/Q2~12026'],'VND','%'),
 ('fin-l2-margin-01','financial_detail','margin_pct',['/data/rows/2/values/3','/data/rows/0/values/3'],'tỷ đồng','%'),
 ('fin-l1-bctc-01','financial_statements','scale',['/data/statements/Kết quả kinh doanh/0/values/Q2~12026'],'VND','tỷ đồng')]:
    task=STUDY/'tasks/pilot'/task_name;payload=task/'environment/payloads.json';entries,_=load_entries(payload);payloadsha=hashlib.sha256(payload.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory() as t:
        log=Path(t)/'ledger';entry=next(e for _,e in entries if e['tool']==tool)
        env=replay_call(entries,tool,entry['params'],payloadsha,str(log));cid=env['benchmark_evidence']['call_id']
        args={'operation':op,'operands':[{'call_id':cid,'path':path} for path in paths],'input_unit':unit,'output_unit':outunit}
        replay_compute(args,{cid:env},payloadsha,str(log));ledger=[json.loads(x) for x in log.read_text().splitlines()]
        proof=verify_derived(task,ledger)
        check('actual public '+task_name+' '+op+' independently reconstructed',len(proof)==1 and proof[0]['operation']==op)
        bad=copy.deepcopy(ledger);bad[-1]['derivation']['source_scopes'][0]['period']='forged'
        try:verify_derived(task,bad)
        except (ValueError,KeyError):rejected=True
        else:rejected=False
        check('actual '+op+' scope tamper rejected',rejected)
result={'pass':True,'checks':checks,'verifier_sha256':hashlib.sha256(Path(__file__).with_name('derived_verifier.py').read_bytes()).hexdigest()}
Path(__file__).with_name('derived-verifier-check.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'pass':True,'checks':len(checks)}))
