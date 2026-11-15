#!/usr/bin/env python3
"""Replace the 11 root-holdout tasks that were verbatim copies of main (user decision 2026-11-10).

Same task ids and frozen payloads; new questions that no main task asks. Gold is computed here
from the payloads, the oracle body recomputes it independently, provenance is regenerated for
the keys each new question needs. Before writing, the new question text is checked against every
main question (study and root). Idempotent; writes a receipt under
experiments/finance-v46-update-study/audits/gold-audit-2026-11-10/holdout-replacements.json.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ORIGIN = STUDY.parents[1]
H = ORIGIN / 'tasks/holdout'
sys.path.insert(0, str(STUDY / 'tools'))
from mcp_snapshot_server import digest, load_entries  # noqa: E402

S30 = 'phiên 30/10/2026'


def data(task, key):
    v = json.loads((H / task / 'environment/payloads.json').read_text())['tools'][key]
    return v.get('envelope', v)['data']


def schema(obj):
    return '```json\n' + json.dumps(obj, ensure_ascii=False, indent=2) + '\n```'


def val(path, gold, tol):
    return {'type': 'value', 'path': path, 'gold': gold, 'tol': tol}


def build_specs():
    specs = {}

    # 921 banks1 batch quotes: max / min / spread (main 181 asks the mean)
    q = {x['symbol']: float(x['close']) for x in data('fin-l3-agg-921', 'batch:banks1')['quotes']}
    hi = max(q, key=q.get); lo = min(q, key=q.get)
    specs['fin-l3-agg-921'] = dict(
        title='Chênh lệch giá cao nhất – thấp nhất nhóm ngân hàng',
        question=('Trong 5 mã **ACB, STB, VPB, HDB, TPB**, ở **%s**: mã nào có **giá đóng cửa cao nhất**, mã nào '
                  '**thấp nhất**, và **chênh lệch** giữa hai giá đó là bao nhiêu **đồng**?' % S30),
        example={'values': {'max_symbol': 'MÃ', 'min_symbol': 'MÃ', 'spread': 0}, 'unit': 'đồng',
                 'period': '(kỳ được hỏi)', 'source': 'vn_equity_quote_batch', 'note': '(tuỳ chọn)'},
        solution={'max_symbol': hi, 'min_symbol': lo, 'spread': q[hi] - q[lo]},
        expects=[{'type': 'tokens', 'path': 'values.max_symbol', 'accept': [hi], 'reject': [s for s in q if s != hi]},
                 {'type': 'tokens', 'path': 'values.min_symbol', 'accept': [lo], 'reject': [s for s in q if s != lo]},
                 val('values.spread', q[hi] - q[lo], {'rel': 0.005}),
                 {'type': 'unit', 'path': 'unit', 'accept': ['đồng', 'VND']},
                 {'type': 'period', 'path': 'period', 'accept': ['30/10', '30-10', '30.10', '2026-10-30']},
                 {'type': 'str', 'path': 'source', 'accept': ['vn_equity_quote_batch']}],
        oracle=("q = {x['symbol']: float(x['close']) for x in env('batch:banks1')['data']['quotes']}\n"
                "hi = max(q, key=q.get); lo = min(q, key=q.get)\n"
                "check('max', hi, gold['solution']['max_symbol'])\ncheck('min', lo, gold['solution']['min_symbol'])\n"
                "check('spread', q[hi] - q[lo], gold['solution']['spread'])\n"
                "check('unique_extremes', sorted(q.values()).count(q[hi]) + sorted(q.values()).count(q[lo]), 2)\n"),
        keys=['batch:banks1'])

    # 922 sec1 batch quotes: strictly above 15,000 (main 182 asks the mean)
    q = {x['symbol']: float(x['close']) for x in data('fin-l3-agg-922', 'batch:sec1')['quotes']}
    above = sorted(s for s, v in q.items() if v > 15000)
    specs['fin-l3-agg-922'] = dict(
        title='Lọc giá trên 15.000 đồng nhóm chứng khoán',
        question=('Trong 5 mã **VCI, VIX, SHS, MBS, FTS**, ở **%s**: những mã nào có **giá đóng cửa lớn hơn 15.000 '
                  'đồng** (lớn hơn hẳn, không tính bằng)? Trả danh sách mã và số mã.' % S30),
        example={'values': {'pass': ['MÃ1', 'MÃ2'], 'count': 0}, 'period': '(kỳ được hỏi)',
                 'source': 'vn_equity_quote_batch', 'note': 'giá đóng cửa từng mã (đồng)'},
        solution={'pass': above, 'count': len(above)},
        expects=[{'type': 'set', 'path': 'values.pass', 'gold': above},
                 val('values.count', len(above), {'abs': 0}),
                 {'type': 'period', 'path': 'period', 'accept': ['30/10', '30-10', '30.10', '2026-10-30']},
                 {'type': 'str', 'path': 'source', 'accept': ['vn_equity_quote_batch']}],
        oracle=("q = {x['symbol']: float(x['close']) for x in env('batch:sec1')['data']['quotes']}\n"
                "sel = sorted(s for s, v in q.items() if v > 15000)\n"
                "check('pass', sel, gold['solution']['pass'])\ncheck('count', len(sel), gold['solution']['count'])\n"),
        keys=['batch:sec1'])

    # 928 / 929 yf: trios not used by main 208-215
    items = {i['ticker']: i for i in data('fin-l3-crypto-multi-928', 'yf:main')['items']}
    def pct(t): return (items[t]['price'] / items[t]['prev'] - 1) * 100
    for tid, trio, mode in (('fin-l3-crypto-multi-928', ['HG=F', 'SI=F', 'ETH-USD'], 'max'),
                            ('fin-l3-crypto-multi-929', ['CL=F', 'BZ=F', 'SOL-USD'], 'min')):
        p = {t: pct(t) for t in trio}
        win = (max if mode == 'max' else min)(p, key=p.get)
        word = 'cao nhất' if mode == 'max' else 'thấp nhất'
        specs[tid] = dict(
            title='So %% thay đổi %s' % ' – '.join(trio),
            question=('Xét 3 tài sản ở **ngày giao dịch gần nhất**: %s. Tài sản nào **%% thay đổi so với phiên trước %s**? '
                      'Nêu %% thay đổi của cả 3 (tính từ `prev` → `price`; xếp hạng bằng số chưa làm tròn).'
                      % (', '.join('`%s`' % t for t in trio), word)),
            example={'values': {'pcts': {t: 0 for t in trio}, 'winner': 'MÃ'}, 'period': 'phiên gần nhất',
                     'source': 'yf_commodities', 'note': '(tuỳ chọn)'},
            solution={'pcts': {t: round(v, 2) for t, v in p.items()}, 'winner': win},
            expects=[val('values.pcts.' + t, round(v, 2), {'abs': 0.1}) for t, v in p.items()] +
                    [{'type': 'tokens', 'path': 'values.winner', 'accept': [win], 'reject': [t for t in trio if t != win]},
                     {'type': 'str', 'path': 'source', 'accept': ['yf_commodities']}],
            oracle=("its = {x: yf_item(env('yf:main'), x) for x in %r}\n"
                    "p = {x: (its[x]['price'] / its[x]['prev'] - 1) * 100 for x in its}\n"
                    "for x, v in p.items():\n    check('pct_' + x, round(v, 2), gold['solution']['pcts'][x])\n"
                    "check('winner', %s(p, key=p.get), gold['solution']['winner'])\n") % (trio, mode),
            keys=['yf:main'])

    # 923 / 924 peer screens with filters not used in main
    rows = {r['symbol']: r for r in data('fin-l3-screen-923', 'peer:banks_p')['rows']}
    sel = sorted(s for s, r in rows.items() if r['p_b'] < 1.3 and r['roe'] > 15)
    specs['fin-l3-screen-923'] = dict(
        title='Sàng lọc ngân hàng P/B < 1.3 và ROE > 15%',
        question=('Trong 5 mã **VPB, ACB, STB, HDB, TPB**: dùng số liệu từ **`peer_compare`** — mã nào thỏa **đồng thời '
                  'P/B < 1.3 và ROE > 15%** (bất đẳng thức chặt)? Trả danh sách mã.'),
        example={'values': {'pass': ['MÃ1', 'MÃ2', '...']}, 'period': '(kỳ dữ liệu tool)', 'source': 'peer_compare',
                 'note': 'P/B và ROE từng mã dùng để lọc'},
        solution={'pass': sel, 'filter': 'P/B < 1.3 và ROE > 15%'},
        expects=[{'type': 'set', 'path': 'values.pass', 'gold': sel},
                 {'type': 'period', 'path': 'period', 'accept': ['2025']},
                 {'type': 'str', 'path': 'source', 'accept': ['peer_compare']}],
        oracle=("rows = env('peer:banks_p')['data']['rows']\n"
                "check('screen', sorted(r['symbol'] for r in rows if r['p_b'] < 1.3 and r['roe'] > 15), gold['solution']['pass'])\n"),
        keys=['peer:banks_p'])
    rows = {r['symbol']: r for r in data('fin-l3-screen-924', 'peer:sec_p')['rows']}
    sel = sorted(s for s, r in rows.items() if r['p_b'] < 2 and r['p_e'] < 15)
    specs['fin-l3-screen-924'] = dict(
        title='Sàng lọc chứng khoán P/B < 2 và P/E < 15',
        question=('Trong 5 mã **VIX, VCI, SHS, MBS, FTS**: dùng số liệu từ **`peer_compare`** — mã nào thỏa **đồng thời '
                  'P/B < 2 và P/E < 15**? Trả danh sách mã.'),
        example={'values': {'pass': ['MÃ1', 'MÃ2', '...']}, 'period': '(kỳ dữ liệu tool)', 'source': 'peer_compare',
                 'note': 'P/B và P/E từng mã dùng để lọc'},
        solution={'pass': sel, 'filter': 'P/B < 2 và P/E < 15'},
        expects=[{'type': 'set', 'path': 'values.pass', 'gold': sel},
                 {'type': 'period', 'path': 'period', 'accept': ['2025']},
                 {'type': 'str', 'path': 'source', 'accept': ['peer_compare']}],
        oracle=("rows = env('peer:sec_p')['data']['rows']\n"
                "check('screen', sorted(r['symbol'] for r in rows if r['p_b'] < 2 and r['p_e'] < 15), gold['solution']['pass'])\n"),
        keys=['peer:sec_p'])

    # 927 bank RSI maximum (main 203 counts RSI < 45)
    syms = ['ACB', 'STB', 'VPB', 'HDB', 'TPB']
    rsi = {s: float(data('fin-l3-tech-multi-927', 'tech:' + s)['rsi14']) for s in syms}
    top = max(rsi, key=rsi.get)
    specs['fin-l3-tech-multi-927'] = dict(
        title='RSI cao nhất nhóm ngân hàng',
        question=('Trong 5 mã **ACB, STB, VPB, HDB, TPB** — mã nào có **RSI-14 khung ngày cao nhất** tại **%s** '
                  'và bằng bao nhiêu?' % S30),
        example={'values': {'symbol': 'MÃ', 'rsi14': 0}, 'period': '(kỳ được hỏi)', 'source': 'signals_technical',
                 'note': 'RSI của cả 5 mã để đối chiếu'},
        solution={'symbol': top, 'rsi14': rsi[top]},
        expects=[{'type': 'tokens', 'path': 'values.symbol', 'accept': [top], 'reject': [s for s in syms if s != top]},
                 val('values.rsi14', rsi[top], {'abs': 0.1}),
                 {'type': 'period', 'path': 'period', 'accept': ['30/10', '30-10', '30.10', '2026-10-30']},
                 {'type': 'str', 'path': 'source', 'accept': ['signals_technical']},
                 {'type': 'evidence', 'path': 'note', 'paths': ['note'], 'numbers': [rsi[s] for s in syms], 'min_hits': 3}],
        oracle=("rs = {s: float(env('tech:' + s)['data']['rsi14']) for s in %r}\n"
                "m = max(rs, key=rs.get)\ncheck('symbol', m, gold['solution']['symbol'])\n"
                "check('rsi', rs[m], gold['solution']['rsi14'])\n") % syms,
        keys=['tech:' + s for s in syms])

    # 940 ETH one-session change by two sources (main 258 compares price levels)
    eth = {i['ticker']: i for i in data('fin-l4-2src-940', 'yf:main')['items']}['ETH-USD']
    closes = data('fin-l4-2src-940', 'cohlcv:ETHUSDT')['closes']
    assert closes[-1]['t'] == '2026-11-01' and closes[-2]['t'] == '2026-10-31'
    yf_pct = (eth['price'] / eth['prev'] - 1) * 100
    vn_pct = (closes[-1]['c'] / closes[-2]['c'] - 1) * 100
    stronger = 'yfinance' if abs(yf_pct) > abs(vn_pct) else 'vnstock'
    specs['fin-l4-2src-940'] = dict(
        title='% thay đổi 1 phiên ETH theo hai nguồn',
        question=('Tính **% thay đổi 1 phiên gần nhất** của ETH theo **hai nguồn**: (a) yfinance `ETH-USD` '
                  '(`prev` → `price`, tool `yf_commodities`) và (b) vnstock crypto `ETHUSDT` (nến 01/11/2026 so với '
                  'nến 31/10/2026, tool `vn_crypto_ohlcv`). Nguồn nào cho **biến động mạnh hơn** (|%| lớn hơn)?'),
        example={'values': {'yf_pct': 0, 'vnstock_pct': 0, 'stronger': 'yfinance hoặc vnstock'}, 'unit': '%',
                 'source': 'yf_commodities + vn_crypto_ohlcv', 'note': '(tuỳ chọn)'},
        solution={'yf_pct': round(yf_pct, 2), 'vnstock_pct': round(vn_pct, 2), 'stronger': stronger},
        expects=[val('values.yf_pct', round(yf_pct, 2), {'abs': 0.05}),
                 val('values.vnstock_pct', round(vn_pct, 2), {'abs': 0.05}),
                 {'type': 'tokens', 'path': 'values.stronger', 'accept': [stronger]},
                 {'type': 'unit', 'path': 'unit', 'accept': ['%', 'phần trăm']},
                 {'type': 'str_all', 'path': 'source', 'accept': ['yf_commodities', 'vn_crypto_ohlcv']}],
        oracle=("it = yf_item(env('yf:main'), 'ETH-USD')\ncl = env('cohlcv:ETHUSDT')['data']['closes']\n"
                "check('dates', [cl[-2]['t'], cl[-1]['t']], ['2026-10-31', '2026-11-01'])\n"
                "a = (it['price'] / it['prev'] - 1) * 100\nb = (cl[-1]['c'] / cl[-2]['c'] - 1) * 100\n"
                "check('yf', round(a, 2), gold['solution']['yf_pct'])\ncheck('vn', round(b, 2), gold['solution']['vnstock_pct'])\n"
                "check('stronger', 'yfinance' if abs(a) > abs(b) else 'vnstock', gold['solution']['stronger'])\n"),
        keys=['cohlcv:ETHUSDT', 'yf:main'])

    # 938 ETHUSDT 10-day window: minimum close, its date, and range (replaces quarantined narrative copy)
    closes = data('fin-l4-narrative-938', 'cohlcv:ETHUSDT')['closes']
    lo = min(closes, key=lambda x: x['c']); hi = max(closes, key=lambda x: x['c'])
    assert [x['c'] for x in closes].count(lo['c']) == 1
    specs['fin-l4-narrative-938'] = dict(
        title='Đáy và biên độ 10 ngày ETHUSDT',
        question=('Trong **10 nến ngày gần nhất** của cặp **ETHUSDT** (nguồn vnstock crypto, theo **VND**): giá đóng '
                  'cửa **thấp nhất** là bao nhiêu và vào **ngày nào**? **Biên độ** (đóng cửa cao nhất − thấp nhất) '
                  'trong 10 ngày là bao nhiêu **đồng**?'),
        example={'values': {'min_close': 0, 'min_date': 'yyyy-mm-dd', 'range': 0}, 'unit': 'đồng',
                 'source': 'vn_crypto_ohlcv', 'note': '(tuỳ chọn)'},
        solution={'min_close': lo['c'], 'min_date': lo['t'], 'range': round(hi['c'] - lo['c'], 2)},
        expects=[val('values.min_close', lo['c'], {'rel': 0.005}),
                 {'type': 'period', 'path': 'values.min_date',
                  'accept': [lo['t'], '%s/%s' % (lo['t'][8:], lo['t'][5:7])]},
                 val('values.range', round(hi['c'] - lo['c'], 2), {'rel': 0.005}),
                 {'type': 'unit', 'path': 'unit', 'accept': ['đồng', 'VND']},
                 {'type': 'str', 'path': 'source', 'accept': ['vn_crypto_ohlcv']}],
        oracle=("cl = env('cohlcv:ETHUSDT')['data']['closes']\ncheck('n', len(cl), 10)\n"
                "lo = min(cl, key=lambda x: x['c']); hi = max(cl, key=lambda x: x['c'])\n"
                "check('min', lo['c'], gold['solution']['min_close'])\ncheck('date', lo['t'], gold['solution']['min_date'])\n"
                "check('range', round(hi['c'] - lo['c'], 2), gold['solution']['range'])\n"),
        keys=['cohlcv:ETHUSDT'],
        toml={'level': 'L3', 'family': 'L3·B aggregate', 'financebench_type': 'aggregation',
              'tools_expected': ['vn_crypto_ohlcv'], 'eligible': True, 'scoring': 'value'})

    # 944 / 945 peer rankings on other metrics (main 275/276 rank by ROE)
    for tid, key, syms, metric, label in (
            ('fin-l5-compare-944', 'peer:banks_p', ['VPB', 'ACB', 'STB', 'HDB', 'TPB'], 'p_b', 'P/B'),
            ('fin-l5-compare-945', 'peer:sec_p', ['VIX', 'VCI', 'SHS', 'MBS', 'FTS'], 'p_e', 'P/E')):
        rows = {r['symbol']: r for r in data(tid, key)['rows']}
        rank = [s for s in sorted(rows, key=lambda s: rows[s][metric])]
        assert len({rows[s][metric] for s in rank}) == 5
        specs[tid] = dict(
            title='Xếp hạng %s tăng dần' % label,
            question=('Dùng **`peer_compare`** cho 5 mã **%s**: nêu **%s** của từng mã và **xếp hạng 5 mã theo %s từ thấp '
                      'đến cao**.' % (', '.join(syms), label, label)),
            example={'values': {s: 0 for s in syms}, 'ranking': ['MÃ1', 'MÃ2', '...'], 'period': '(kỳ dữ liệu tool)',
                     'source': 'peer_compare', 'note': '(tuỳ chọn)'},
            solution={**{s: rows[s][metric] for s in syms}, 'ranking': rank},
            expects=[val('values.' + s, rows[s][metric], {'rel': 0.005}) for s in syms] +
                    [{'type': 'list_order', 'path': 'ranking', 'gold': rank},
                     {'type': 'period', 'path': 'period', 'accept': ['2025']},
                     {'type': 'str', 'path': 'source', 'accept': ['peer_compare']}],
            oracle=("rows = env(%r)['data']['rows']\nfor r in rows:\n    check(r['symbol'], float(r[%r]), gold['solution'][r['symbol']])\n"
                    "check('ranking', [r['symbol'] for r in sorted(rows, key=lambda r: r[%r])], gold['solution']['ranking'])\n")
                   % (key, metric, metric),
            keys=[key])
    return specs


def norm(text):
    return re.sub(r'\s+', ' ', text).strip()


def main_questions():
    out = set()
    for root in (STUDY / 'tasks/main', ORIGIN / 'tasks/main'):
        for p in root.glob('*/instruction.md'):
            head = p.read_text(encoding='utf-8').split('## Ràng buộc chung')[0]
            out.add(norm(re.sub(r'^#.*\n', '', head, count=1)))
    return out


def provenance(task, keys):
    entries, _ = load_entries(H / task / 'environment/payloads.json')
    found = {}
    for entry_id, item in entries:
        if entry_id in keys:
            env = item['envelope']
            found[entry_id] = {'tool': item['tool'], 'source': env['provenance']['source'], 'as_of': env['provenance']['as_of'],
                               'matched_entry_id': entry_id, 'response_sha256': digest(env)}
    missing = set(keys) - set(found)
    if missing:
        raise SystemExit('%s: payload entries missing %s' % (task, missing))
    return [found[k] for k in keys]


def apply(task, spec, mains):
    d = H / task
    head = '# %s\n\n%s\n\n## Yêu cầu trả lời\nTrả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n%s\n\n\n' % (
        spec['title'], spec['question'], schema(spec['example']))
    q_norm = norm(spec['question'])
    if q_norm in mains:
        raise SystemExit('%s: new question duplicates a main question' % task)
    ins = d / 'instruction.md'
    text = ins.read_text(encoding='utf-8')
    _, sep, contract = text.partition('## Ràng buộc chung')
    assert sep, task
    ins.write_text(head + sep + contract, encoding='utf-8')

    gpath = d / 'solution/gold.json'
    raw = gpath.read_text(encoding='utf-8')
    indent = 1 if raw.startswith('{\n "') else 2
    gold = json.loads(raw)
    for k in ('verdict_accept', 'verdict_reject', 'evidence', 'refusal_tokens', 'bonus_numbers', 'bonus_strings'):
        gold.pop(k, None)
    gold.update(scoring='value', solution=spec['solution'], expects=spec['expects'],
                notes='Holdout replacement 2026-11-10: previous question was a verbatim copy of a main task; '
                      'same frozen payload, new question not asked by any main task.',
                provenance_contract=provenance(task, spec['keys']), required_payload_keys=sorted(spec['keys']))
    gpath.write_text(json.dumps(gold, ensure_ascii=False, indent=indent) + '\n', encoding='utf-8')

    opath = d / 'solution/oracle.py'
    o = opath.read_text(encoding='utf-8')
    pre, mark, rest = o.partition('# === thân oracle ===\n')
    _, sep2, tail = rest.partition('\nif problems:')
    assert mark and sep2, task
    opath.write_text(pre + mark + spec['oracle'].strip('\n') + '\n\n' + 'if problems:' + tail, encoding='utf-8')

    tpath = d / 'task.toml'
    t = tpath.read_text(encoding='utf-8')
    t = re.sub(r'^title = ".*"$', 'title = "%s"' % spec['title'].replace('"', "'"), t, flags=re.M)
    extra = spec.get('toml')
    if extra:
        t = re.sub(r'^level = ".*"$', 'level = "%s"' % extra['level'], t, flags=re.M)
        t = re.sub(r'^family = ".*"$', 'family = "%s"' % extra['family'], t, flags=re.M)
        t = re.sub(r'^financebench_type = ".*"$', 'financebench_type = "%s"' % extra['financebench_type'], t, flags=re.M)
        t = re.sub(r'^tools_expected = .*$', 'tools_expected = %s' % json.dumps(extra['tools_expected']), t, flags=re.M)
        t = re.sub(r'^confirmatory_eligible = .*$', 'confirmatory_eligible = true', t, flags=re.M)
        t = re.sub(r'^exclusion_reason = .*\n', '', t, flags=re.M)
        t = re.sub(r'^type = ".*"$', 'type = "%s"' % extra['scoring'], t, flags=re.M)
    tpath.write_text(t, encoding='utf-8')


def main():
    specs = build_specs()
    assert len(specs) == 11
    mains = main_questions()
    receipt = {}
    for task, spec in specs.items():
        apply(task, spec, mains)
        receipt[task] = {f: hashlib.sha256((H / task / f).read_bytes()).hexdigest()
                         for f in ('instruction.md', 'solution/gold.json', 'solution/oracle.py', 'task.toml')}
        receipt[task]['solution'] = spec['solution']
    out = STUDY / 'audits/gold-audit-2026-11-10/holdout-replacements.json'
    out.write_text(json.dumps({'decision': 'user 2026-11-10: replace 11 verbatim main replicas in holdout',
                               'tasks': receipt}, ensure_ascii=False, indent=1) + '\n')
    for task, spec in specs.items():
        print(task, json.dumps(spec['solution'], ensure_ascii=False))


if __name__ == '__main__':
    main()
