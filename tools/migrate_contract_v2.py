#!/usr/bin/env python3
"""Explicit mechanical task-contract migration; never rebuild financial data/gold.

Archives v1 bytes+hashes before editing. Holdout receives exactly the same mechanical
schema/provenance migration, without model execution or outcome-dependent tuning.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile
import tomllib

from _gen_templates import GRADER_TMPL
from mcp_snapshot_server import SCHEMAS, load_entries, digest

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'contract-v2'
BLOCK = '''\n\n## Hợp đồng dữ liệu và bằng chứng
- Snapshot cố định: `{snapshot}`. Không cần đọc task.toml; metadata này được cung cấp trực tiếp trong đề.
- `source` là tên tool MCP; `evidence[].source` là nhà cung cấp trong `provenance.source`. Đây là hai namespace riêng.
- Thêm trường `evidence` vào object JSON trả lời: danh sách các đối tượng `{{"tool":"tên tool", "source":"provenance.source", "as_of":"provenance.as_of", "call_id":"benchmark_evidence.call_id", "payload_sha256":"benchmark_evidence.payload_sha256", "matched_entry_id":"benchmark_evidence.matched_entry_id", "response_sha256":"benchmark_evidence.response_sha256"}}` lấy từ phản hồi tool thực gọi. Dẫn đầy đủ các phản hồi cần thiết cho chỉ tiêu/mã/kỳ được hỏi (kể cả các mã riêng biệt cùng tool/nguồn/timestamp); catalog có thể chứa dữ liệu không liên quan. Không suy đoán timestamp và không dùng thời gian của máy làm as_of.
- Khi từ chối, bắt buộc có trường `value` với JSON `null`; chuỗi "null", thiếu trường, object hay số đều không hợp lệ. Thời kỳ phải nêu đúng năm, quý/tháng/ngày và đủ hai kỳ nếu đề yêu cầu so sánh.
'''


def legacy_requests(tool, envelope):
    """Recover identities from recorded envelope, never allow arbitrary arguments.

    Synthetic merged single-symbol captures are split at replay time. Exact
    history lengths are unknown for these trimmed captures, so no length is
    invented: only omitted/default optional args replay the fixed captured data.
    """
    data = envelope.get('data') or {}
    if tool == 'vn_quote_history' and 'banks' in data:
        return [{'params': {'symbol': r['symbol']}, 'select_row': ['banks', r['symbol']]} for r in data['banks']]
    if tool == 'signals_technical' and 'rows' in data:
        return [{'params': {'symbol': r['symbol'], 'interval': data['interval']}, 'select_row': ['rows', r['symbol']]} for r in data['rows']]
    if tool == 'peer_compare':
        symbols = [r['symbol'] for r in data['rows']]
        params = {'symbol': symbols[0], 'peers': symbols[1:]}
    elif tool == 'vs_indicator_data': params = {'indicator': 'CPI'}
    elif tool == 'vn_msn_fx_gold': params = {'symbols': [r['symbol'] for r in data['series']]}
    elif tool == 'yf_commodities': params = {'tickers': [r['ticker'] for r in data['items']]}
    elif tool == 'crypto_spot': params = {'symbols': data['requested']}
    elif tool == 'symbol_resolve': params = {'query': data['query']}
    elif tool == 'market_movers': params = {'universe': data['universe'], 'top_n': len(data['gainers'])}
    elif tool == 'vs_overview_trading': params = {'symbol': data['overview']['data'][0]['StockCode']}
    elif tool == 'stock_overview': params = {'symbol': data['trading']['StockCode']}
    else:
        params = {'symbol': data['symbol']}
        if tool == 'financial_statements': params['period'] = data['period']
        if tool == 'financial_detail': params['statement'] = data['statement']
    return [{'params': params}]


def required_replay_entries(task, entries, meta):
    """Trace actual payload lookups in the existing trusted oracle, not inlined helpers.

    This discovers only source dependencies. It does not generate financial gold.
    Entity metadata disambiguates rows in historical merged single-symbol captures.
    """
    oracle=task/'solution/oracle.py'; path=str(oracle)
    used=set(); previous=sys.getprofile()
    def trace(frame,event,arg):
        if event=='call' and frame.f_code.co_filename==path and frame.f_code.co_name=='env':
            name=frame.f_locals.get('name')
            if isinstance(name,str): used.add(name)
    try:
        sys.setprofile(trace)
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(oracle.read_text(),path,'exec'),{'__file__':path,'__name__':'contract_source_dependencies'})
    finally:
        sys.setprofile(previous)
    if not used: raise ValueError('No oracle source dependencies: '+str(task))
    candidates=[(key,item) for key,item in entries if key in used or key.rsplit(':',1)[0] in used]
    entities=set(re.findall(r'[A-Z][A-Z0-9=.-]*',meta.get('entity','')))
    # Only narrow symbols if at least one recorded symbol matches the explicit
    # entity list. Group labels such as banks1 retain every oracle-used entry.
    symbols={item.get('params',{}).get('symbol') for _,item in candidates}
    if entities & symbols:
        candidates=[(key,item) for key,item in candidates if not item.get('params',{}).get('symbol')
                    or item['params']['symbol'] in entities]
    if not candidates: raise ValueError('Empty required replay contract: '+str(task))
    return candidates,sorted(used)


def ambiguous_cpi_series(entries):
    """A missing series dimension cannot be restored by thresholds or gold values."""
    for _,item in entries:
        if item['tool']!='vs_indicator_data': continue
        seen={}
        for row in item['envelope'].get('data',{}).get('rows',[]):
            name=row.get('n',row.get('indicator'));period=row.get('p',row.get('period'))
            value=row.get('v',row.get('value'))
            key=(name,period,row.get('unit',row.get('u')))
            if name and period and key in seen and seen[key]!=value: return True
            seen[key]=value
    return False


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--apply', action='store_true')
    ap.add_argument('--refresh-contracts', action='store_true', help='Idempotently refresh v2 grader/evidence/period metadata without replacing the v1 archive')
    args=ap.parse_args()
    task_dirs = sorted(p.parent for split in ('pilot','smoke','main','holdout') for p in (ROOT/'tasks'/split).glob('*/task.toml'))
    archive_dir=ROOT/'audits'/'contract-v2'; archive_dir.mkdir(parents=True,exist_ok=True)
    receipt_path=archive_dir/'migration.json'
    if receipt_path.exists() and not args.refresh_contracts:
        raise SystemExit('migration already applied; refusing to overwrite archived v1')
    files=[p for task in task_dirs for p in (task/'instruction.md',task/'task.toml',task/'solution/gold.json',task/'tests/grader.py')]
    receipt=(json.loads(receipt_path.read_text()) if receipt_path.exists() else {'migration':VERSION,'method':'identical mechanical contract update across splits; gold numerical values and payload bytes preserved',
             'old_files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}})
    if not args.apply:
        print(json.dumps({'would_migrate':len(task_dirs),'files':len(files)}));return
    if not (archive_dir/'v1-task-artifacts.tar.gz').exists():
        with tarfile.open(archive_dir/'v1-task-artifacts.tar.gz','w:gz') as archive:
            for p in files:archive.add(p,arcname=str(p.relative_to(ROOT)))
    for task in task_dirs:
        payload_file=task/'environment/payloads.json'; payload=json.loads(payload_file.read_text())
        bare={key:legacy_requests(key,value) for key,value in payload['tools'].items() if 'envelope' not in value}
        corrections={}
        for key,value in payload['tools'].items():
            if value.get('tool') == 'vn_crypto_ohlcv' and 'days' in value.get('params', {}):
                corrections[key]={'params':{'symbol':value['params']['symbol'],'count':len(value['envelope']['data']['closes'])},'reason':'recorded days is not a real tool parameter; count reconstructed from captured closes length'}
        if bare or corrections:
            (task/'environment/request_contracts.json').write_text(json.dumps({'version':2,'reconstruction':'entity identity from recorded envelope; original optional capture arguments unavailable', 'requests':bare, 'parameter_corrections':corrections},indent=2,ensure_ascii=False)+'\n')
        entries,_=load_entries(payload_file)
        meta=tomllib.loads((task/'task.toml').read_text())
        required_entries,required_keys=required_replay_entries(task,entries,meta)
        ambiguous_cpi=ambiguous_cpi_series(required_entries)
        required_ids={key for key,_ in required_entries}
        contract=[]; catalog=[]
        for entry_id, item in entries:
            provenance=item['envelope'].get('provenance') or {}
            row={'tool':item['tool'],'source':provenance.get('source'),'as_of':provenance.get('as_of'),
                 'matched_entry_id':entry_id, 'response_sha256':digest(item['envelope'])}
            catalog.append(row)
            if entry_id in required_ids: contract.append(row)
        gold_file=task/'solution/gold.json'; gold=json.loads(gold_file.read_text())
        evidence_rubric=gold.get('evidence') or {}
        incomplete_narrative=('narrative' in meta.get('family','') and gold.get('scoring')=='verdict'
            and evidence_rubric.get('min_hits',1)<len(evidence_rubric.get('numbers',[])))
        gold.update(contract_version=2, provenance_contract=contract, provenance_catalog=catalog,
                    required_payload_keys=required_keys,payload_sha256=hashlib.sha256(payload_file.read_bytes()).hexdigest())
        # Every revenue-growth question compares the last two captured quarters.
        # This repairs the period contract only; original gold numbers stay intact.
        tool_names={item['tool'] for _,item in entries}
        spot_unit=False
        for exp in gold.get('expects',[]):
            if exp['type']=='unit' and set(exp.get('accept',[]))=={'USD','USDT'}:
                spot_unit='crypto_spot' in tool_names
                exp['accept']=['USDT'] if spot_unit else ['USD']
        if 'growth' in meta.get('family',''):
            fs=next(item['envelope']['data'] for _,item in entries if item['tool']=='financial_statements')
            periods=fs['periods'][-2:]
            for exp in gold.get('expects',[]):
                if exp['type']=='period': exp['accept']=list(periods)
        gold_file.write_text(json.dumps(gold,ensure_ascii=False,indent=2)+'\n')
        (task/'tests/grader.py').write_text(GRADER_TMPL)
        instruction=(task/'instruction.md').read_text().replace('đúng snapshot của task (`task.toml` → `snapshot_date`)','đúng snapshot được ghi trong hợp đồng dữ liệu dưới đây')
        instruction=re.sub(r"""("source"\s*:\s*)'([^']*)'""",lambda m:m[1]+json.dumps(m[2],ensure_ascii=False),instruction)
        # Stablecoins and fiat are different units. Captured BTCUSDT is quoted
        # in USDT; the cross-currency exercise needs an explicit parity premise.
        if spot_unit:
            instruction=instruction.replace('theo **USD**','theo **USDT**').replace('"unit": "USD"','"unit": "USDT"')
        parity='Trong bài tập quy đổi này, giả định **1 USDT = 1 USD**; đây là giả định tính toán, không phải tỷ giá USDT/USD được quan sát.'
        if 'crypto_spot' in tool_names and 'vn_msn_fx_gold' in tool_names and parity not in instruction:
            instruction=instruction.replace('## Yêu cầu trả lời',parity+'\n\n## Yêu cầu trả lời',1)
        instruction=instruction.replace('Ghi kết quả vào file `answer.json` ở thư mục hiện hành, theo schema:', 'Trả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:').replace('Mọi số trong `answer.json`', 'Mọi số trong object JSON trả lời')
        instruction=instruction.split('## Hợp đồng dữ liệu và bằng chứng')[0].rstrip()
        instruction += BLOCK.format(snapshot=payload['snapshot_date'])
        (task/'instruction.md').write_text(instruction)
        toml=(task/'task.toml').read_text().replace('version = 1','version = 2',1)
        toml=re.sub(r'^confirmatory_eligible = .*\n|^exclusion_reason = .*\n','',toml,flags=re.M)
        excluded=ambiguous_cpi or incomplete_narrative
        eligibility='confirmatory_eligible = '+('false' if excluded else 'true')+'\n'
        if excluded:
            reason='ambiguous_cpi_series_dimension' if ambiguous_cpi else 'incomplete_narrative_evidence_rubric'
            eligibility+='exclusion_reason = '+json.dumps(reason)+'\n'
        # Removing the previous eligibility block leaves its blank separator.
        # Normalize that boundary so repeated refreshes preserve exact bytes.
        toml=re.sub(r'\s*\n\[scoring\]', '\n\n'+eligibility+'\n[scoring]', toml, count=1)
        (task/'task.toml').write_text(toml)
    receipt['new_files']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    receipt['tasks_migrated']=len(task_dirs)
    receipt['contract_revision']='required-response-evidence-comparison-periods-and-distinct-currency-units'
    adjustments={}
    with tarfile.open(archive_dir/'v1-task-artifacts.tar.gz') as archive:
        for task in task_dirs:
            rel=str((task/'solution/gold.json').relative_to(ROOT))
            before=json.load(archive.extractfile(rel)); after=json.loads((ROOT/rel).read_text())
            row={}
            meta=tomllib.loads((task/'task.toml').read_text())
            if not meta.get('confirmatory_eligible',True):
                row['confirmatory_eligible']=False;row['exclusion_reason']=meta['exclusion_reason']
            old_expects=before.get('expects',[]);new_expects=after.get('expects',[])
            for old,new in zip(old_expects,new_expects):
                if old.get('accept')!=new.get('accept'):
                    row.setdefault('field_contracts',[]).append({'type':new['type'],'path':new.get('path','value'),
                        'old_accept':old.get('accept'),'new_accept':new.get('accept')})
            if len(after['provenance_contract'])<len(after['provenance_catalog']):
                row['required_replay_entries']=[r['matched_entry_id'] for r in after['provenance_contract']]
                row['catalog_replay_entries']=[r['matched_entry_id'] for r in after['provenance_catalog']]
                row['source_dependency_method']='actual existing oracle env lookups + explicit entity metadata for merged single-symbol captures'
            if row:adjustments[str(task.relative_to(ROOT))]=row
    receipt['contract_adjustments']=adjustments
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    print('Migrated',len(task_dirs),'tasks; v1 archived',archive_dir)


if __name__=='__main__':main()
