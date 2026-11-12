"""Independent captured-data review: no generator/oracle/synthesized answer logic.

Deterministic sample spans main/pilot/smoke; sealed holdout content is never read.
Arithmetic is recomputed from raw payloads with Decimal and explicit finance rules.
"""
import contextlib
from decimal import Decimal
import hashlib
import io
import json
import os
import re
from pathlib import Path
import runpy
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from mcp_snapshot_server import load_entries, replay_call, select_envelope, digest


def dec(value):
    return Decimal(str(value))


PILOT = ['fin-l1-bctc-01', 'fin-l1-gold-01', 'fin-l1-quote-01', 'fin-l1-quote-02',
         'fin-l2-crypto-01', 'fin-l2-gold-01', 'fin-l2-growth-01', 'fin-l2-margin-01',
         'fin-l2-ratio-01', 'fin-l2-tech-01', 'fin-l3-agg-01', 'fin-l3-crypto-01',
         'fin-l3-index-01', 'fin-l3-screen-01', 'fin-l3-tech-multi-01', 'fin-l3-top-01',
         'fin-l4-2nguon-01', 'fin-l4-future-01', 'fin-l4-narrative-01',
         'fin-l4-nonexist-01', 'fin-l5-compare-01', 'fin-l5-profile-01', 'fin-l5-valuation-01']
MAIN = ['fin-l1-bctc-109', 'fin-l1-quote-crypto-121', 'fin-l1-quote-gf-126',
        'fin-l1-quote-vn-101', 'fin-l2-crypto-x-166', 'fin-l2-growth-141',
        'fin-l1-macro-137', 'fin-l2-macro-calc-176', 'fin-l2-macro-calc-180',
        'fin-l2-margin-149', 'fin-l2-ratio-156', 'fin-l2-tech-161', 'fin-l3-agg-181',
        'fin-l3-screen-189', 'fin-l3-tech-multi-203', 'fin-l3-index-216',
        'fin-l5-compare-275', 'fin-l5-profile-261', 'fin-l5-valuation-291']
CASES = [('pilot', n) for n in PILOT] + [('main', n) for n in MAIN] + [
    ('smoke', n) for n in ['smoke-agg-01', 'smoke-quote-01', 'smoke-trap-01']]


def raw_task(split, name):
    task = ROOT / 'tasks' / split / name
    payload = json.loads((task / 'environment/payloads.json').read_text())
    # Unwrap file storage only, without importing replay matching or generator logic.
    data = [(v.get('tool', k), v.get('envelope', v)['data']) for k, v in payload['tools'].items()]
    keyed={key:value.get('envelope',value)['data'] for key,value in payload['tools'].items()}
    return task, {**keyed,**dict(data)}, json.loads((task / 'solution/gold.json').read_text())


def finance_result(name, data):
    def tool(which): return data[which]
    def series(symbol): return next(r['closes'] for r in tool('vn_msn_fx_gold')['series'] if r['symbol'] == symbol)
    def statement_rows(d): return d.get('rows', d.get('statements', {}).get('Kết quả kinh doanh'))
    def latest(row): return list(row['values'].values())[-1] if isinstance(row['values'], dict) else row['values'][-1]
    def row(d, phrase): return next(r for r in statement_rows(d) if phrase in r['name'])
    if name in ('fin-l1-macro-137','fin-l2-macro-calc-176','fin-l2-macro-calc-180'):
        by_period={r['p']:dec(r['v']) for r in data['gdp:full']['total']}
        q3=by_period['Quý 3/2026']
        if name=='fin-l1-macro-137': return {'value':q3}
        base=by_period['Quý 2/2026' if name.endswith('176') else 'Quý 3/2025']
        return {'value':(q3/base-1)*100}
    if 'nonexist' in name or name == 'smoke-trap-01':
        return {'resolved_null': tool('symbol_resolve')['resolved'] is None}
    if 'future' in name:
        d = tool('financial_statements')
        return {'q4_absent': 'Q4/2026' not in d['periods'], 'latest': d['periods'][-1],
                'latest_lnst_me_bn': dec(latest(row(d, 'LNST của CĐ cty mẹ'))) / 10**9}
    if name == 'fin-l4-narrative-01':
        decreased = [any(b['c'] < a['c'] for a, b in zip(s['closes'], s['closes'][1:])) for s in tool('vn_msn_fx_gold')['series']]
        return {'verdict': 'đúng' if all(decreased) else 'sai'}
    if name == 'fin-l4-2nguon-01':
        a = dec(tool('vn_quote_history')['last']) * 1000
        b = tool('vs_overview_trading')['overview']['data'][0]['ClosePrice']
        return {'close': a, 'match': a == b}
    if 'bctc' in name:
        return {'value': dec(latest(row(tool('financial_statements'), 'Tổng LNST'))) / 10**9}
    if 'growth' in name:
        r = row(tool('financial_statements'), 'Doanh thu thuần')
        a, b = list(r['values'].values())[-2:]
        return {'value': (dec(b) / dec(a) - 1) * 100}
    if 'margin' in name or 'profile' in name:
        d = tool('financial_detail')
        revenue = dec(latest(row(d, 'Doanh thu thuần')))
        gross = dec(latest(row(d, 'Lợi nhuận gộp')))
        margin = gross / revenue * 100
        if 'margin' in name: return {'value': margin}
        ov = tool('stock_overview')['trading']
        suffix = 'q3_bn' if name == 'fin-l5-profile-01' else 'q_bn'
        return {'revenue_' + suffix: revenue, 'gross_profit_' + suffix: gross,
                'gross_margin_pct': margin, 'pe': ov['PE'], 'market_cap_bn': dec(ov['MarketCapital']) / 10**9}
    if 'valuation' in name:
        d = tool('valuation_run')
        return {k: d[k] for k in ('price', 'per', 'pb')}
    if 'ratio' in name: return {'value': tool('valuation_run')['per']}
    if 'screen' in name:
        roe, pe = (20, 10) if name == 'fin-l3-screen-01' else (15, 15)
        return {'pass': sorted(r['symbol'] for r in tool('peer_compare')['rows'] if r['roe'] > roe and r['p_e'] < pe)}
    if 'compare' in name:
        rows = tool('peer_compare')['rows']
        return {**{r['symbol']: {'pe': r['p_e'], 'pb': r['p_b'], 'roe': r['roe']} for r in rows},
                'ranking': [r['symbol'] for r in sorted(rows, key=lambda r: r['roe'], reverse=True)]}
    if 'tech-multi' in name:
        if name == 'fin-l3-tech-multi-01':
            r = min([r for r in tool('signals_technical')['rows'] if r['symbol'] != 'VCB'], key=lambda r: r['rsi14'])
            return {'symbol': r['symbol'], 'rsi14': r['rsi14']}
        # Raw main storage contains one entry per symbol, so use raw payload separately below.
        return None
    if '-tech-' in name:
        d = tool('signals_technical')
        return {'value': next(r['rsi14'] for r in d['rows'] if r['symbol'] == 'VCB') if 'rows' in d else d['rsi14']}
    if 'index' in name:
        d = tool('vn_index_ohlcv'); bars = d.get('bars', d.get('closes')); key = 'close' if 'bars' in d else 'c'
        return {'value': (dec(bars[-1][key]) / dec(bars[0][key]) - 1) * 100}
    if name == 'fin-l3-top-01':
        rs = sorted(tool('market_movers')['gainers'], key=lambda r: r['percent_change'], reverse=True)[:3]
        return {'top': [{'symbol': r['symbol'], 'pct': r['percent_change'], 'close': r['close_price']} for r in rs]}
    if '-agg-' in name:
        d = next(iter(data.values())); rs = d.get('banks', d.get('quotes'))
        prices = {r['symbol']: dec(r.get('last', r.get('close'))) for r in rs}
        return {**prices, 'mean': sum(prices.values()) / len(prices)}
    if name == 'fin-l3-crypto-01':
        rows = tool('yf_commodities')['items']; vals = {r['ticker']: (dec(r['price']) / dec(r['prev']) - 1) * 100 for r in rows}
        return {'gold_pct': vals['GC=F'], 'oil_pct': vals['CL=F'], 'btc_pct': vals['BTC-USD'], 'winner': max(vals, key=vals.get)}
    if name in ('fin-l2-crypto-01', 'fin-l2-crypto-x-166'):
        price = tool('crypto_spot')['tickers'][0]['last'] if 'crypto_spot' in data else next(r['price'] for r in tool('yf_commodities')['items'] if r['ticker'] == 'BTC-USD')
        return {'value': dec(price) * dec(series('USDVND')[-1]['c']) / 10**6}
    if name == 'fin-l2-gold-01':
        rs = series('USDVND'); return {'value': rs[-1]['c'], 'change': rs[-1]['c'] - rs[-2]['c']}
    if name == 'fin-l1-gold-01': return {'value': series('XAUUSD')[-1]['c']}
    if name == 'fin-l1-quote-gf-126': return {'value': series('XAGUSD')[-1]['c']}
    if name == 'fin-l1-quote-crypto-121': return {'value': next(r['price'] for r in tool('yf_commodities')['items'] if r['ticker'] == 'BTC-USD')}
    if name == 'fin-l1-quote-02': return {'value': tool('crypto_spot')['tickers'][0]['last']}
    d = tool('vn_quote_history')
    return {k: d[v] for k, v in [('value', 'last'), ('last_t', 'last_t')]}


def assert_finance_equal(actual, gold):
    if isinstance(actual, dict):
        for k, v in actual.items():
            if k in gold: assert_finance_equal(v, gold[k])
    elif isinstance(actual, list):
        assert len(actual) == len(gold)
        for a, g in zip(actual, gold): assert_finance_equal(a, g)
    elif isinstance(actual, (int, float, Decimal)) and not isinstance(actual, bool):
        # Dataset solutions round to two decimals; allow at most the rounding unit.
        assert abs(dec(actual) - dec(gold)) <= Decimal('0.011'), (actual, gold)
    else:
        assert actual == gold


@pytest.mark.parametrize('split,name', CASES)
def test_independent_finance_calculation(split, name):
    task, data, gold = raw_task(split, name)
    actual = finance_result(name, data)
    if name == 'fin-l3-tech-multi-203':
        p = json.loads((task / 'environment/payloads.json').read_text())
        actual = {'count': sum(v['envelope']['data']['rsi14'] < 45 for v in p['tools'].values())}
    assert actual, name
    assert_finance_equal(actual, gold['solution'])


def grade_raw(tmp_path, raw, gold):
    from _gen_templates import GRADER_TMPL
    namespace = {'__name__': 'independent', '__file__': __file__}
    exec(compile(GRADER_TMPL, 'independent-grader', 'exec'), namespace)
    a, g, o = [tmp_path / x for x in ('a.json', 'g.json', 'o.json')]
    a.write_text(raw); g.write_text(json.dumps(gold))
    old = sys.argv; sys.argv = ['grader', str(a), '-g', str(g), '-o', str(o)]
    try:
        with contextlib.redirect_stdout(io.StringIO()): namespace['main']()
    finally: sys.argv = old
    return json.loads(o.read_text())


@pytest.mark.parametrize('raw', ['{"value": 999, "value": 100}', '{"value":100,"x":{"a":1,"a":2}}', '{"value":100} {"value":200}', '{"value":NaN}', '{"value":1e999}', '{"value":' + '9'*400 + '}'])
def test_ambiguous_or_nonfinite_json_cannot_pass(tmp_path, raw):
    assert not grade_raw(tmp_path, raw, {'scoring':'value', 'expects':[{'type':'value','gold':100}]})['success']


@pytest.mark.parametrize('split,name', [('pilot', 'fin-l2-growth-01'), ('main','fin-l2-growth-141')])
def test_comparison_requires_both_captured_quarters(tmp_path, split, name):
    _, _, gold = raw_task(split, name)
    contract = {'scoring':'value','expects':[e for e in gold['expects'] if e['type']=='period']}
    assert grade_raw(tmp_path, '{"period":"Q3/2026 so với Q2/2026"}', contract)['success']
    for period in ['Q3/2026', 'Q3/2026 so với Q1/2026', 'Q3/2026 và Q2/2026 và Q1/2026']:
        assert not grade_raw(tmp_path, json.dumps({'period':period}), contract)['success']


@pytest.mark.parametrize('kind,path,value,expect', [
    ('unit','unit','USD chứ không phải %', {'accept':['%']}),
    ('unit','unit','không dùng đồng', {'accept':['đồng']}),
    ('unit','unit','đồng và USD', {'accept':['đồng']}),
    ('tokens','line','Không dùng Tổng LNST', {'accept':['Tổng LNST']}),
    ('verdict','verdict','không đúng, nhưng đúng', {'accept':['sai','không đúng'], 'reject':['đúng']}),
    ('verdict','verdict','không sai', {'accept':['sai'], 'reject':['đúng']}),
])
def test_explicitly_contradictory_finance_fields_rejected(tmp_path, kind, path, value, expect):
    gold = {'scoring':'value','expects':[{'type':kind,'path':path, **expect}]}
    assert not grade_raw(tmp_path, json.dumps({path:value}), gold)['success']


@pytest.mark.parametrize('period', ['30/10/25', '30-10-25'])
def test_short_year_cannot_hide_wrong_financial_period(tmp_path, period):
    gold={'scoring':'value','expects':[{'type':'period','accept':['30/10','2026-10-30']}]}
    gold['expects'][0]['path']='period'
    assert not grade_raw(tmp_path,json.dumps({'period':period}),gold)['success']


def test_stablecoin_and_reciprocal_fx_units_are_distinct(tmp_path):
    from _gen_templates import GRADER_TMPL
    ns={'__name__':'units'};exec(GRADER_TMPL,ns)
    assert ns['canon_unit']('USD') != ns['canon_unit']('USDT')
    assert ns['canon_unit']('USD/VND') != ns['canon_unit']('VND/USD')
    assert ns['canon_unit']('đồng/USD') == ns['canon_unit']('VND/USD')
    gold={'scoring':'value','expects':[{'type':'unit','path':'unit','accept':['USD']}]}
    assert not grade_raw(tmp_path,'{"unit":"USDT"}',gold)['success']


def test_one_bank_response_cannot_ground_all_bank_answers(tmp_path):
    task, _, gold = raw_task('pilot', 'fin-l3-agg-01')
    entries, _ = load_entries(task / 'environment/payloads.json')
    env = replay_call(entries, 'vn_quote_history', {'symbol':'VCB'}, gold['payload_sha256'])
    evidence = env['benchmark_evidence']
    contract = {k: gold[k] for k in ('provenance_contract','payload_sha256')}
    contract.update(scoring='value', expects=[{'type':'value','gold':32.18}])
    assert len(gold['provenance_contract']) == 5
    assert not grade_raw(tmp_path, json.dumps({'value':32.18, 'evidence':[evidence]}), contract)['success']


@pytest.mark.parametrize('split,name,expected_ids',[
    ('main','fin-l1-quote-gf-126',{'msn:main'}),
    ('main','fin-l2-macro-calc-176',{'gdp:full'}),
    ('pilot','fin-l2-tech-01',{'signals_technical:5'}),
    ('pilot','fin-l3-tech-multi-01',{'signals_technical:'+str(i) for i in range(5)}),
])
def test_only_question_required_responses_are_mandatory(split,name,expected_ids):
    _,_,gold=raw_task(split,name)
    assert {row['matched_entry_id'] for row in gold['provenance_contract']} == expected_ids
    assert len(gold['provenance_catalog']) > len(gold['provenance_contract'])


def test_cpi_missing_series_dimension_is_quarantined_but_gdp_decoy_is_safe():
    import tomllib
    for split,name,eligible in [('main','fin-l1-macro-131',False),('pilot','fin-l1-macro-01',False),
                                ('main','fin-l2-macro-calc-176',True)]:
        meta=tomllib.loads((ROOT/'tasks'/split/name/'task.toml').read_text())
        assert meta['confirmatory_eligible'] is eligible
        if not eligible: assert meta['exclusion_reason']=='ambiguous_cpi_series_dimension'


def test_all_instruction_json_examples_parse():
    # Format-only mechanical validation includes holdout; no answer values used.
    for path in ROOT.glob('tasks/*/*/instruction.md'):
        for example in re.findall(r'```json\s*\n(.*?)```',path.read_text(),re.S):
            assert isinstance(json.loads(example),dict), str(path)


def test_incomplete_narrative_answer_is_diagnostic_only(tmp_path):
    import tomllib
    task,_,gold=raw_task('main','fin-l4-narrative-244')
    entries,_=load_entries(task/'environment/payloads.json')
    call=replay_call(entries,'vn_quote_history',{'symbol':'ANV','days':10},gold['payload_sha256'])
    # Exact repro: the prompt asks for all ten closes, but one matching price
    # satisfies the inherited note rubric. It must never enter confirmatory scores.
    answer={'verdict':'sai','note':'17.83','evidence':[call['benchmark_evidence']]}
    assert grade_raw(tmp_path,json.dumps(answer),gold)['success']
    meta=tomllib.loads((task/'task.toml').read_text())
    assert meta['confirmatory_eligible'] is False
    assert meta['exclusion_reason']=='incomplete_narrative_evidence_rubric'


def test_replay_native_defaults_and_exact_request_identity():
    task, _, _ = raw_task('main','fin-l1-quote-vn-101')
    entries, _ = load_entries(task/'environment/payloads.json')
    assert select_envelope(entries,'vn_quote_history',{'symbol':'EIB'})['data']['last'] == 16.1
    assert select_envelope(entries,'vn_quote_history',{'symbol':'EIB','days':365,'summary':False})['data']['last'] == 16.1
    for request in [{'symbol':'EIB','days':5}, {'symbol':'EIB','summary':True}, {'symbol':'EIB','start':'2026-10-01'}, {'symbol':'OTHER'}]:
        with pytest.raises(ValueError): select_envelope(entries, 'vn_quote_history', request)


def test_original_finance_solution_and_payload_hashes_preserved():
    # Holdout archive content is not opened. Hash-only payload verification applies all splits.
    receipt=json.loads((ROOT/'audits/contract-v2/migration.json').read_text())
    with tarfile.open(ROOT/'audits/contract-v2/v1-task-artifacts.tar.gz') as archive:
        for member in archive.getmembers():
            if '/holdout/' in member.name or not member.name.endswith('/solution/gold.json'): continue
            before=json.load(archive.extractfile(member));after=json.loads((ROOT/member.name).read_text())
            assert before.get('solution') == after.get('solution'), member.name
            b=[e.get('gold') for e in before.get('expects',[]) if e['type']=='value']
            a=[e.get('gold') for e in after.get('expects',[]) if e['type']=='value']
            assert a == b, member.name
    # Frozen committed payload bytes are independently compared against Git, not generated fixtures.
    import subprocess
    for p in ROOT.glob('tasks/*/*/environment/payloads.json'):
        raw=subprocess.run(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT,capture_output=True,check=True).stdout
        assert hashlib.sha256(raw).digest() == hashlib.sha256(p.read_bytes()).digest(), str(p)


@pytest.mark.asyncio
async def test_real_stdio_records_schema_invalid_and_wrong_entity_calls(tmp_path):
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    task, _, _ = raw_task('main', 'fin-l1-quote-vn-101')
    ledger=tmp_path/'ledger.jsonl'
    params=StdioServerParameters(command=sys.executable,
        args=[str(ROOT/'tools/mcp_snapshot_server.py'), str(task/'environment/payloads.json')],
        env={**os.environ,'BENCH_MCP_LEDGER':str(ledger)})
    with anyio.fail_after(25):
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                for arguments in [{'symbol':'EIB'}, {'symbol':'WRONG_ENTITY'}, {'symbol':'EIB','days':True}]:
                    result=await session.call_tool('vn_quote_history',arguments)
                    body=json.loads(result.content[0].text)
                    if arguments=={'symbol':'EIB'}:
                        assert result.isError is False
                        assert body['data']['last']==16.1
                        assert body['benchmark_evidence']['call_id']
                    else:
                        assert result.isError is True
                        assert body['request_rejected'] is True
                        expected = 'not_recorded' if arguments['symbol'] == 'WRONG_ENTITY' else 'invalid_request'
                        assert body['error']['code'] == expected
                        assert body['error']['snapshot_requests']
                        assert not ({'data', 'availability', 'benchmark_evidence'} & body.keys())
    rows=[json.loads(line) for line in ledger.read_text().splitlines()]
    assert [r['status'] for r in rows]==['ok','rejected','rejected']
    assert len({r['call_id'] for r in rows})==3
