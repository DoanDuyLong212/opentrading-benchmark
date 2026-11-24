#!/usr/bin/env python3
"""Investor stratum (I), amendment 2026-11-24 (d). Specs and rules: tools/investor_specs_20261124.py (pre-registered).

Agents see only snapshot data (120 sessions to 30/10/2026, quarterly statements to Q2/2026, VN-Index). Gold applies
the pre-registered outcome rule to recorded post-snapshot closes (31/10..END), which never enter a payload, and
stores every passing answer set (`set_in`). Primary is this outcome (owner decision), scored by code only.
Idempotent: rewrites only the task directories it owns.
"""
import hashlib, itertools, json, re, shutil, sys
from decimal import Decimal as D
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import build_compute_stratum_20261111 as cs  # noqa: E402
import build_finance_stratum_20261124 as bfs  # noqa: E402
import build_memory_stratum_20261111 as ms  # noqa: E402
import investor_specs_20261124 as SP  # noqa: E402

EXT = STUDY / 'audits/snapshot-extension-2026-11-24b'
POST_FILE = EXT / 'post-20261124.json'
PRE_FILE = EXT / 'pre-120.json'
CREATED = '2026-11-24'
INDEX = 'VNINDEX'


def load():
    for path, sha in ((POST_FILE, SP.POST_SHA256), (PRE_FILE, SP.PRE_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('price file differs from pre-registered hash: ' + path.name)
    receipt = json.loads((EXT / 'RECEIPT.json').read_text())
    return json.loads(PRE_FILE.read_text()), json.loads(POST_FILE.read_text()), receipt


PRE, POST, REC = load()
TYPE_NAME = {'I1': 'chọn cổ phiếu trong ngành', 'I2': 'chọn mã tăng nhiều nhất', 'I3': 'cảnh báo rủi ro',
             'I4': 'dựng danh mục', 'I5': 'nhà đầu tư có ghi nhớ'}


def hist_env(sym):
    rows = PRE[sym]
    assert rows[-1]['t'] == SP.ENTRY and len(rows) == 120
    if sym == INDEX:
        tool, params, unit = 'vn_index_ohlcv', {'symbol': sym, 'count': 120}, 'điểm'
    else:
        tool, params, unit = 'vn_quote_history', {'symbol': sym, 'days': 170}, 'nghìn đồng/cổ phiếu (64,27 = 64.270 đ)'
    return {'tool': tool, 'params': params,
            'envelope': {'data': {'symbol': sym, 'closes': [{'t': r['t'], 'c': r['c'], 'v': r['v']} for r in rows]},
                         'units': {'c': unit, 'v': 'cổ phiếu'},
                         'provenance': {'source': 'vnstock', 'as_of': REC['recorded_at'], 'timezone': 'Asia/Ho_Chi_Minh',
                                        'data_time': SP.ENTRY},
                         'availability': 'available',
                         'warnings': ['Lịch sử 120 phiên (tới 30/10/2026) cho snapshot 2026-11-01; '
                                      'không có phiên sau 30/10/2026.']}}


def payloads(cands):
    tools = {('idx:' if s == INDEX else 'hist:') + s: hist_env(s) for s in cands + [INDEX]}
    fs = [s for s in cands if s in bfs.RAW['symbols']]
    tools.update(bfs.payloads(fs, {('q', 'KQKD'), ('q', 'CDKT')}))
    return tools, fs


def outcome(sym):
    entry = D(str(PRE[sym][-1]['c']))
    closes = [D(str(r['c'])) for r in POST[sym]]
    return {'entry': float(entry), 'end_close': float(closes[-1]), 'peak_close': float(max(closes)),
            'low_close': float(min(closes)),
            'ret': (closes[-1] / entry - 1) * 100, 'peak': (max(closes) / entry - 1) * 100, 'low': (min(closes) / entry - 1) * 100}


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)


def passing_sets(spec, oc):
    c, typ = spec['cands'], spec['type']
    if typ == 'I1':
        m = mean(oc[s]['ret'] for s in c)
        return [[s] for s in c if oc[s]['ret'] > m], 1
    if typ == 'I2':
        top = max(oc[s]['peak'] for s in c)
        return [[s] for s in c if oc[s]['peak'] == top], 1
    if typ == 'I3':
        out = []
        for pair in itertools.combinations(c, 2):
            rest = [s for s in c if s not in pair]
            if mean(oc[s]['low'] for s in pair) < mean(oc[s]['low'] for s in rest):
                out.append(sorted(pair))
        return out, 2
    if typ == 'I4':
        m = mean(oc[s]['ret'] for s in c)
        return [sorted(q) for q in itertools.combinations(c, 4) if mean(oc[s]['ret'] for s in q) > m], 4
    if typ == 'I5':
        m = mean(oc[s]['ret'] for s in spec['allowed'])
        return [[s] for s in spec['allowed'] if oc[s]['ret'] > m], 1
    raise ValueError(typ)


HEADER = ('**Bài mô phỏng danh mục giấy (paper trading), không phải khuyến nghị đầu tư.** Giả định hôm nay là 01/11/2026: '
          'dữ liệu chỉ tới phiên **30/10/2026**, và lệnh được coi là mua tại **giá đóng cửa phiên 30/10/2026**. Kết quả được '
          'chấm bằng giá đóng cửa thực tế các phiên **31/10–%s** (bạn không có dữ liệu này). Phân tích theo cách bạn thấy '
          'tốt nhất từ dữ liệu được cung cấp. **Bắt buộc phải chọn** đúng như yêu cầu: để trống/null, từ chối, chọn mã ngoài '
          'danh sách hoặc sai số lượng mã đều tính là sai.' % '/'.join(reversed(SP.END.split('-'))))


def data_text(cands, fs):
    text = ('Dữ liệu có sẵn: `vn_quote_history` (`symbol`=<mã>, `days=170`: 120 phiên giá đóng cửa/khối lượng tới '
            '30/10/2026) cho từng mã; `vn_index_ohlcv` (`symbol="VNINDEX"`, `count=120`)')
    if fs:
        text += ('; `financial_statements` (`symbol`=<mã>, `period="quarter"`, `statement="KQKD"` hoặc `"CDKT"`, '
                 'quý Q3/2024–Q2/2026) cho: %s' % ', '.join(fs))
    return text + '. Phải xem giá của **mọi** mã ứng viên trước khi chọn.'


def question(spec, fs):
    c, typ, end = spec['cands'], spec['type'], '/'.join(reversed(SP.END.split('-')))
    lst = ', '.join('**%s**' % s for s in c)
    if typ == 'I1':
        q = ('Trong nhóm **%s**: %s. Chọn **đúng 1 mã** để mua. Đạt khi lợi suất của mã bạn chọn (giá đóng cửa %s so với '
             '30/10/2026) **cao hơn trung bình** lợi suất của cả %d mã trong nhóm.' % (spec['sector'], lst, end, len(c)))
        ex = {'pick': 'MÃ'}
    elif typ == 'I2':
        q = ('Trong %s: chọn **đúng 1 mã** bạn dự đoán sẽ **tăng nhiều nhất**. Mức tăng của mỗi mã = giá đóng cửa **cao '
             'nhất** trong các phiên 31/10–%s so với giá đóng cửa 30/10/2026. Đạt khi mã bạn chọn có mức tăng lớn nhất nhóm.'
             % (lst, end))
        ex = {'pick': 'MÃ'}
    elif typ == 'I3':
        q = ('Cảnh báo rủi ro: trong %s, gắn cờ **đúng 2 mã** có rủi ro giảm giá cao nhất. Mức giảm của mỗi mã = giá đóng '
             'cửa **thấp nhất** trong các phiên 31/10–%s so với giá đóng cửa 30/10/2026. Đạt khi trung bình mức giảm của 2 mã '
             'bị gắn cờ **sâu hơn** trung bình của %d mã còn lại.' % (lst, end, len(c) - 2))
        ex = {'flags': ['MÃ1', 'MÃ2']}
    elif typ == 'I4':
        q = ('Dựng danh mục **đúng 4 mã**, tỷ trọng đều 25%%, từ 8 mã: %s. Đạt khi lợi suất danh mục (giá đóng cửa %s so với '
             '30/10/2026) **cao hơn trung bình** lợi suất của cả 8 mã.' % (lst, end))
        ex = {'portfolio': ['MÃ1', 'MÃ2', 'MÃ3', 'MÃ4']}
    else:
        q = ('Trong %s: chọn **đúng 1 mã** để mua thêm, **tuân thủ mọi ràng buộc tôi đã nhờ bạn ghi nhớ** (còn hiệu lực). '
             'Đạt khi mã bạn chọn được phép mua theo các ràng buộc đó và có lợi suất (giá đóng cửa %s so với 30/10/2026) '
             '**cao hơn trung bình** của các mã được phép mua trong danh sách.' % (lst, end))
        ex = {'pick': 'MÃ'}
    example = {'values': ex, 'source': 'vn_quote_history', 'reason': '(lý do ngắn: dữ liệu và lập luận đã dùng)'}
    return HEADER + '\n\n' + q + '\n\n' + data_text(c, fs), example


ANSWER_PATH = {'I1': 'values.pick', 'I2': 'values.pick', 'I3': 'values.flags', 'I4': 'values.portfolio', 'I5': 'values.pick'}

ORACLE = r'''
from decimal import Decimal as _D
import itertools as _it
_sol = gold['solution']
_c = _sol['candidates']
for _s in _c:
    _rows = env('hist:' + _s)['data']['closes']
    check('entry_' + _s, _rows[-1]['c'], _sol['outcomes'][_s]['entry'])
    check('entry_date_' + _s, _rows[-1]['t'], '2026-10-30')
def _m(xs):
    xs = list(xs); return sum(xs) / len(xs)
_o = {s: {k: (_D(str(v['end_close'])) / _D(str(v['entry'])) - 1) * 100 if k == 'ret' else
          ((_D(str(v['peak_close'])) if k == 'peak' else _D(str(v['low_close']))) / _D(str(v['entry'])) - 1) * 100
          for k in ('ret', 'peak', 'low')} for s, v in _sol['outcomes'].items()}
_t = _sol['type']
if _t == 'I1':
    _p = [[s] for s in _c if _o[s]['ret'] > _m(_o[x]['ret'] for x in _c)]
elif _t == 'I2':
    _p = [[s] for s in _c if _o[s]['peak'] == max(_o[x]['peak'] for x in _c)]
elif _t == 'I3':
    _p = [sorted(q) for q in _it.combinations(_c, 2)
          if _m(_o[s]['low'] for s in q) < _m(_o[s]['low'] for s in _c if s not in q)]
elif _t == 'I4':
    _p = [sorted(q) for q in _it.combinations(_c, 4) if _m(_o[s]['ret'] for s in q) > _m(_o[x]['ret'] for x in _c)]
else:
    _a = _sol['allowed']
    _p = [[s] for s in _a if _o[s]['ret'] > _m(_o[x]['ret'] for x in _a)]
check('passing_sets', _p, _sol['passing_sets'])
'''


def spec_gold(spec):
    tools, fs = payloads(spec['cands'])
    oc = {s: outcome(s) for s in spec['cands']}
    sets, size = passing_sets(spec, oc)
    if not sets:
        raise ValueError('no passing answer: ' + spec['tid'])
    q, example = question(spec, fs)
    path = ANSWER_PATH[spec['type']]
    total = len(list(itertools.combinations(spec['cands'] if spec['type'] != 'I5' else spec['allowed'], size)))
    idx = outcome(INDEX)
    sol = {'type': spec['type'], 'candidates': spec['cands'], 'allowed': spec.get('allowed'), 'entry_date': SP.ENTRY,
           'end_date': SP.END, 'passing_sets': sets, 'answer_size': size,
           'chance_base_rate': round(len(sets) / total, 4),
           'outcomes': {s: {k: (round(float(v), 4) if k in ('ret', 'peak', 'low') else v) for k, v in o.items()} for s, o in oc.items()},
           'vnindex_ret': round(float(idx['ret']), 4), 'post_sha256': SP.POST_SHA256}
    expects = [{'type': 'set_in', 'path': path, 'size': size, 'accept_sets': sets},
               {'type': 'str', 'path': 'source', 'accept': ['vn_quote_history']}]
    contract_keys = ['hist:' + s for s in spec['cands']]
    return tools, q, example, sol, expects, contract_keys


def provenance(tools, keys):
    return [{'tool': tools[k]['tool'], 'source': tools[k]['envelope']['provenance']['source'],
             'as_of': tools[k]['envelope']['provenance']['as_of'], 'matched_entry_id': k,
             'response_sha256': cs.digest(tools[k]['envelope'])} for k in keys]


def finish_gold(d, spec, sol, expects, tools, contract_keys, base):
    gold = dict(base, task_id=spec['tid'], scoring='outcome', solution=sol, as_of=REC['recorded_at'], split=spec['split'],
                expects=expects, contract_version=2, stratum='investor', tier=spec['type'],
                notes='Investor stratum (amendment 2026-11-24 d): primary = pre-registered outcome rule on recorded '
                      'post-snapshot closes (tools/investor_specs_20261124.py).',
                provenance_contract=provenance(tools, contract_keys), provenance_catalog=provenance(tools, sorted(tools)),
                payload_sha256=hashlib.sha256((d / 'environment/payloads.json').read_bytes()).hexdigest(),
                required_payload_keys=sorted(contract_keys))
    (d / 'solution/gold.json').write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n')


def write_single(spec):
    tools, q, example, sol, expects, keys = spec_gold(spec)
    d = STUDY / 'tasks' / spec['split'] / spec['tid']
    if d.exists():
        shutil.rmtree(d)
    (d / 'environment').mkdir(parents=True); (d / 'solution').mkdir(); (d / 'tests').mkdir()
    shutil.copy(STUDY / 'tools/v45_grader.py', d / 'tests/grader.py')
    pl = {'snapshot_date': '2026-11-01', 'note': 'Giá 120 phiên tới 30/10/2026 (audits/snapshot-extension-2026-11-24b) và '
          'báo cáo quý tới Q2/2026 (audits/snapshot-extension-2026-11-24).', 'tools': tools}
    (d / 'environment/payloads.json').write_text(json.dumps(pl, ensure_ascii=False, indent=1) + '\n')
    title = 'Nhà đầu tư %s — %s' % (spec['type'], TYPE_NAME[spec['type']]) + (' (%s)' % spec['sector'] if spec.get('sector') else '')
    tmpl = (cs.TEMPLATE / 'instruction.md').read_text(encoding='utf-8')
    head = '# %s\n\n%s\n\n## Yêu cầu trả lời\nTrả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n```json\n%s\n```\n\n\n' % (
        title, q, json.dumps(example, ensure_ascii=False, indent=2))
    (d / 'instruction.md').write_text(head + tmpl[tmpl.index('## Ràng buộc chung'):], encoding='utf-8')
    finish_gold(d, spec, sol, expects, tools, keys, {})
    o = (cs.TEMPLATE / 'solution/oracle.py').read_text(encoding='utf-8')
    pre, mark, rest = o.partition('# === thân oracle ===\n')
    _, sep, tail = rest.partition('\nif problems:')
    assert mark and sep
    (d / 'solution/oracle.py').write_text(pre + mark + ORACLE + '\n\nif problems:' + tail, encoding='utf-8')
    toml = (cs.TEMPLATE / 'task.toml').read_text(encoding='utf-8')
    toml = toml.replace('# Task benchmark harness tài chính (bộ 200+50) — sinh bởi tools/build_main.py',
                        '# Investor stratum — amendment 2026-11-24 (d), tools/build_investor_stratum_20261124.py')
    for k, v in (('id', spec['tid']), ('title', title.replace('"', "'")), ('created', CREATED), ('level', spec['type']),
                 ('family', '%s investor' % spec['type']), ('financebench_type', 'investment decision (outcome-scored)'),
                 ('entity', '+'.join(spec['cands'])), ('split', spec['split'])):
        toml = re.sub(r'^%s = ".*"$' % k, '%s = "%s"' % (k, v), toml, flags=re.M)
    tools_used = sorted({e['tool'] for e in tools.values()})
    toml = re.sub(r'^tools_expected = .*$', 'tools_expected = %s' % json.dumps(tools_used), toml, flags=re.M)
    toml = toml.replace('confirmatory_eligible = true', 'confirmatory_eligible = true\nstratum = "investor"\ntier = "%s"' % spec['type'])
    toml = re.sub(r'^type = "value"$', 'type = "outcome"', toml, flags=re.M)
    (d / 'task.toml').write_text(toml, encoding='utf-8')
    return d, sol


def write_memory(spec):
    tools, q, example, sol, expects, keys = spec_gold(spec)
    final = {'text': q + '\n\n' + ms.contract_text(example), 'final': True}
    fid = 'holdings' if spec['sub'] == 'holdings' else 'crit-sector'
    distract = ms.DISTRACT[int(spec['tid'][-1]) % len(ms.DISTRACT)]
    if spec['sub'] == 'exclude':
        sessions = [{'id': 'S1', 'turns': [ms.remember(fid, spec['rule']), ms.chat(distract)]},
                    {'id': 'S2', 'turns': [final]}]
    else:
        new = spec['update'].split(': ', 1)[1]
        sessions = [{'id': 'S1', 'turns': [ms.remember(fid, spec['rule'])]},
                    {'id': 'S2', 'turns': [ms.cmd(spec['update'], [ms.put(fid, new, spec['update'])]), ms.chat(distract)]},
                    {'id': 'S3', 'turns': [final]}]
    title = 'Nhà đầu tư I5 — ràng buộc ghi nhớ (%s)' % {'exclude': 'loại ngành', 'update': 'cập nhật ràng buộc',
                                                         'holdings': 'danh mục đang giữ'}[spec['sub']]
    t = {'kind': 'I5', 'tid': spec['tid'], 'split': spec['split'], 'tier': 'I5', 'subtier': 'I5-' + spec['sub'],
         'title': title, 'sessions': sessions,
         'q': {'payloads': tools, 'solution': sol, 'expects': expects, 'oracle': ORACLE}}
    d = ms.write(t)
    gold = json.loads((d / 'solution/gold.json').read_text())
    base = {k: gold[k] for k in ('subtier', 'memory_construct')}
    finish_gold(d, spec, sol, expects, tools, keys, base)
    toml = (d / 'task.toml').read_text(encoding='utf-8')
    toml = toml.replace('# Native-memory stratum — amendment 2026-11-11 (d), tools/build_memory_stratum_20261111.py',
                        '# Investor stratum (memory) — amendment 2026-11-24 (d), tools/build_investor_stratum_20261124.py')
    toml = re.sub(r'^created = ".*"$', 'created = "%s"' % CREATED, toml, flags=re.M)
    toml = re.sub(r'^family = ".*"$', 'family = "I5 investor memory"', toml, flags=re.M)
    toml = re.sub(r'^stratum = ".*"$', 'stratum = "investor"', toml, flags=re.M)
    toml = re.sub(r'^type = "value"$', 'type = "outcome"', toml, flags=re.M)
    (d / 'task.toml').write_text(toml, encoding='utf-8')
    turns = json.loads((d / 'environment/turns.json').read_text())
    turns['note'] = 'Investor memory (amendment 2026-11-24 d). Same sessions for every arm; memory_command = OT /nho form, chat for others.'
    (d / 'environment/turns.json').write_text(json.dumps(turns, ensure_ascii=False, indent=1) + '\n')
    return d, sol


def main():
    assert sum(s['split'] == 'main' for s in SP.SPECS) == 20 and sum(s['split'] == 'pilot' for s in SP.SPECS) == 5
    receipt = {'post_sha256': SP.POST_SHA256, 'pre_sha256': SP.PRE_SHA256, 'tasks': {}}
    for spec in SP.SPECS:
        d, sol = (write_memory if spec['type'] == 'I5' else write_single)(spec)
        receipt['tasks'][spec['tid']] = {'split': spec['split'], 'type': spec['type'], 'passing_sets': sol['passing_sets'],
                                         'chance_base_rate': sol['chance_base_rate'],
                                         'files': {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                   for p in sorted(d.rglob('*')) if p.is_file()}}
    out = STUDY / 'audits/taskset-revision-2026-11-24'
    (out / 'INVESTOR-BUILD.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    for k, v in receipt['tasks'].items():
        print(k, v['split'], v['type'], 'passing', len(v['passing_sets']), 'base', v['chance_base_rate'])


if __name__ == '__main__':
    main()
