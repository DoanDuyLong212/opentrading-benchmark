#!/usr/bin/env python3
"""Apply the user-approved 2026-11-10 gold/task audit fixes (pre-inference).

See audits/gold-audit-2026-11-10/FINDINGS.md. Every edit is explicit and asserted
(exact occurrence counts); provenance entries are regenerated from the frozen
payloads with mcp_snapshot_server.load_entries/digest, never typed by hand.
Changed study files are registered in audits/CORPUS-MIGRATION.json; a receipt is
written to audits/gold-audit-2026-11-10/patch-receipt.json. Idempotent: a second
run finds nothing to change and exits non-zero only on inconsistency.

  python3 tools/apply_gold_audit_20261110.py            # study corpus
  python3 tools/apply_gold_audit_20261110.py --root-holdout   # also root tasks/holdout
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
ORIGIN = STUDY.parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from mcp_snapshot_server import digest, load_entries  # noqa: E402

AUDIT = 'gold-audit-2026-11-10'
CHANGED = {}          # path -> before sha
NOTES = {}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def remember(path):
    path = Path(path)
    CHANGED.setdefault(path, sha(path))


def replace_once(path, old, new, *, count=1):
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    if new in text:
        return  # already applied (new may contain old as a prefix)
    n = text.count(old)
    if n != count:
        raise SystemExit('%s: expected %d occurrence(s) of %r, found %d' % (path, count, old, n))
    remember(path)
    path.write_text(text.replace(old, new), encoding='utf-8')


def load_gold(task):
    return json.loads((task / 'solution/gold.json').read_text(encoding='utf-8'))


def save_gold(task, gold):
    path = task / 'solution/gold.json'
    raw = path.read_text(encoding='utf-8')
    indent = 1 if raw.startswith('{\n "') else 2
    new = json.dumps(gold, ensure_ascii=False, indent=indent) + '\n'
    if new != raw:
        remember(path)
        path.write_text(new, encoding='utf-8')


def expect(gold, path, typ=None):
    hits = [e for e in gold['expects'] if e.get('path') == path and (typ is None or e['type'] == typ)]
    if len(hits) != 1:
        raise SystemExit('%s: expected one expect at %s, found %d' % (gold['task_id'], path, len(hits)))
    return hits[0]


def provenance_entry(task, key):
    entries, _ = load_entries(task / 'environment/payloads.json')
    for entry_id, item in entries:
        if entry_id == key:
            env = item['envelope']
            return {'tool': item['tool'], 'source': env['provenance']['source'],
                    'as_of': env['provenance']['as_of'], 'matched_entry_id': entry_id,
                    'response_sha256': digest(env)}
    raise SystemExit('%s: no payload entry %s' % (task, key))


def set_source(task, accept, *, all_tools):
    gold = load_gold(task)
    e = expect(gold, 'source')
    e.clear()
    e.update({'type': 'str_all' if all_tools else 'str', 'path': 'source', 'accept': list(accept)})
    save_gold(task, gold)


def to_tokens_with_reject(task, path, reject):
    gold = load_gold(task)
    e = [x for x in gold['expects'] if x.get('path') == path and x['type'] in ('str', 'tokens')]
    if len(e) != 1:
        raise SystemExit('%s: winner/symbol expect %s not unique' % (task.name, path))
    e = e[0]
    accept = e['accept']
    clash = [r for r in reject if any(r.lower() == a.lower() for a in accept)]
    if clash:
        raise SystemExit('%s: reject overlaps accept %s' % (task.name, clash))
    e['type'] = 'tokens'
    e['reject'] = list(reject)
    save_gold(task, gold)


def replace_oracle_body(task, body):
    path = task / 'solution/oracle.py'
    text = path.read_text(encoding='utf-8')
    head, sep, rest = text.partition('# === thân oracle ===\n')
    if not sep:
        raise SystemExit('%s: oracle marker missing' % path)
    _, sep2, tail = rest.partition('\nif problems:')
    if not sep2:
        raise SystemExit('%s: oracle tail missing' % path)
    new = head + sep + body.strip('\n') + '\n\n' + 'if problems:' + tail
    if new != text:
        remember(path)
        path.write_text(new, encoding='utf-8')


# ----------------------------------------------------------------- study fixes
def study_fixes():
    T = STUDY / 'tasks'
    S30 = '**phiên 30/10/2026**'

    # A1: tools without a session date -> state the session in the question.
    for split, name in [('pilot', 'fin-l2-tech-01')] + [('main', 'fin-l2-tech-%d' % i) for i in range(162, 166)]:
        replace_once(T / split / name / 'instruction.md', 'trên khung ngày (**1D**) là bao nhiêu?',
                     'trên khung ngày (**1D**) tại %s (phiên giao dịch gần nhất của snapshot) là bao nhiêu?' % S30)
    for split, name in [('pilot', 'fin-l3-tech-multi-01'), ('main', 'fin-l3-tech-multi-204'),
                        ('main', 'fin-l3-tech-multi-206'), ('main', 'fin-l3-tech-multi-207')]:
        replace_once(T / split / name / 'instruction.md', 'RSI-14 khung ngày', 'RSI-14 khung ngày tại %s' % S30)
    for name in ('fin-l3-tech-multi-203', 'fin-l3-tech-multi-205', 'fin-l4-chain-303'):
        replace_once(T / 'main' / name / 'instruction.md', 'RSI-14 (khung ngày)', 'RSI-14 (khung ngày, %s)' % S30)
    for split, name in [('pilot', 'fin-l3-top-01')] + [('main', 'fin-l3-top-%d' % i) for i in range(197, 202)]:
        replace_once(T / split / name / 'instruction.md', 'phiên gần nhất trong rổ', 'phiên gần nhất (%s) trong rổ' % S30)
    NOTES['A1'] = 'session date stated in 17 study questions (tools return no session date)'

    # A3: GC=F / SI=F exist only in yf_commodities.
    for name in ('fin-l2-gf-compare-174', 'fin-l2-gf-compare-175'):
        task = T / 'main' / name
        replace_once(task / 'instruction.md', '"source": "vn_msn_fx_gold",', '"source": "yf_commodities",')
        set_source(task, ['yf_commodities'], all_tools=False)
        gold = load_gold(task)
        if [c['tool'] for c in gold['provenance_contract']] != ['yf_commodities']:
            raise SystemExit('%s: unexpected provenance contract' % name)
    NOTES['A3'] = 'gf-compare-174/175 source = yf_commodities'

    # A4 + B5: 3 source tools; specify latest daily bar and yf base.
    for name in ('fin-l4-2src-257', 'fin-l4-2src-258'):
        task = T / 'main' / name
        replace_once(task / 'instruction.md', '"source": "yf_commodities + vn_crypto_ohlcv",',
                     '"source": "yf_commodities + vn_crypto_ohlcv + vn_msn_fx_gold",')
        replace_once(task / 'instruction.md', 'Hai nguồn lệch nhau bao nhiêu **%**?',
                     'Giá vnstock lấy close của nến ngày mới nhất trong dữ liệu (01/11/2026); lấy giá yfinance làm mốc '
                     '(mẫu số). Hai nguồn lệch nhau bao nhiêu **%** (giá trị tuyệt đối)?')
        set_source(task, ['yf_commodities', 'vn_crypto_ohlcv', 'vn_msn_fx_gold'], all_tools=True)
        tools = sorted(c['tool'] for c in load_gold(task)['provenance_contract'])
        if tools != ['vn_crypto_ohlcv', 'vn_msn_fx_gold', 'yf_commodities']:
            raise SystemExit('%s: provenance contract mismatch %s' % (name, tools))
    NOTES['A4'] = '2src-257/258 source = 3 tools (USDVND from vn_msn_fx_gold)'

    # A2: rewrite compare-288/289/290 to answerable 1-session comparisons.
    specs = {
        'fin-l5-compare-288': ('NG=F', 'XAUUSD', 'xauusd_pct'),
        'fin-l5-compare-289': ('HG=F', 'USDVND', 'usdvnd_pct'),
        'fin-l5-compare-290': ('BZ=F', 'XAGUSD', 'xagusd_pct'),
    }
    for name, (sym, ref, ref_key) in specs.items():
        task = T / 'main' / name
        payload = json.loads((task / 'environment/payloads.json').read_text())
        yf = next(i for i in payload['tools']['yf:main']['envelope']['data']['items'] if i['ticker'] == sym)
        ser = next(s['closes'] for s in payload['tools']['msn:main']['envelope']['data']['series'] if s['symbol'] == ref)
        assert ser[-1]['t'] == '2026-10-30' and ser[-2]['t'] == '2026-10-29', (name, ser[-2:])
        sym_pct = round((yf['price'] / yf['prev'] - 1) * 100, 2)
        ref_pct = round((ser[-1]['c'] / ser[-2]['c'] - 1) * 100, 2)
        verdict = 'mạnh hơn' if abs(yf['price'] / yf['prev'] - 1) > abs(ser[-1]['c'] / ser[-2]['c'] - 1) else 'yếu hơn'
        other = 'yếu hơn' if verdict == 'mạnh hơn' else 'mạnh hơn'
        ins = task / 'instruction.md'
        text = ins.read_text(encoding='utf-8')
        head, sep, contract = text.partition('## Ràng buộc chung')
        if not sep:
            raise SystemExit('%s: contract marker missing' % name)
        new_head = (
            '# Biến động 1 phiên %s vs %s\n\n'
            'So sánh **%% thay đổi 1 phiên gần nhất** của **%s** (theo `yf_commodities`, từ `prev` → `price`) và của '
            '**%s** (đóng cửa phiên 30/10/2026 so với phiên 29/10/2026, theo `vn_msn_fx_gold`): các %% là bao nhiêu? '
            'Biến động của %s **mạnh hơn hay yếu hơn** %s (so |%%|)?\n\n'
            '## Yêu cầu trả lời\n'
            'Trả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n'
            '```json\n{\n  "values": {"sym_pct": 0, "%s": 0, "so_sanh": "mạnh hơn hoặc yếu hơn"},\n'
            '  "period": "phiên gần nhất (30/10/2026)",\n'
            '  "source": "yf_commodities + vn_msn_fx_gold",\n  "note": "(tuỳ chọn)"\n}\n```\n\n'
            '- `sym_pct` là %% thay đổi của %s; `%s` là %% thay đổi của %s. Biến động mạnh hơn = |%%| lớn hơn.\n\n'
        ) % (sym, ref, sym, ref, sym, ref, ref_key, sym, ref_key, ref)
        if head != new_head:
            remember(ins)
            ins.write_text(new_head + sep + contract, encoding='utf-8')
        gold = load_gold(task)
        gold['solution'] = {'sym_pct': sym_pct, ref_key: ref_pct, 'so_sanh': verdict}
        gold['notes'] = ('Rewritten 2026-11-10 (gold audit A2): yf_commodities has only price/prev, so the 5-session '
                         'question was unanswerable; now 1-session for both assets. %s %.4f%% vs %s %.4f%%.'
                         % (sym, (yf['price'] / yf['prev'] - 1) * 100, ref, (ser[-1]['c'] / ser[-2]['c'] - 1) * 100))
        gold['expects'] = [
            {'type': 'value', 'path': 'values.sym_pct', 'gold': sym_pct, 'tol': {'abs': 0.05}},
            {'type': 'value', 'path': 'values.' + ref_key, 'gold': ref_pct, 'tol': {'abs': 0.05}},
            {'type': 'verdict', 'path': 'values.so_sanh', 'accept': [verdict], 'reject': [other]},
            {'type': 'str_all', 'path': 'source', 'accept': ['yf_commodities', 'vn_msn_fx_gold']},
        ]
        gold['provenance_contract'] = [provenance_entry(task, 'yf:main'), provenance_entry(task, 'msn:main')]
        gold['required_payload_keys'] = ['msn:main', 'yf:main']
        save_gold(task, gold)
        replace_oracle_body(task, (
            "it = yf_item(env('yf:main'), %r)\n"
            "cl = msn_series(env)[%r]\n"
            "sp = (it['price'] / it['prev'] - 1) * 100\n"
            "rp = (cl[-1]['c'] / cl[-2]['c'] - 1) * 100\n"
            "check('ref_dates', [cl[-2]['t'], cl[-1]['t']], ['2026-10-29', '2026-10-30'])\n"
            "check('sym_pct', round(sp, 2), gold['solution']['sym_pct'])\n"
            "check('ref_pct', round(rp, 2), gold['solution'][%r])\n"
            "check('so_sanh', 'mạnh hơn' if abs(sp) > abs(rp) else 'yếu hơn', gold['solution']['so_sanh'])\n"
        ) % (sym, ref, ref_key))
    NOTES['A2'] = 'compare-288/289/290 rewritten to 1-session vs XAUUSD/USDVND/XAGUSD'

    # A5: top-202 duplicate of 201 -> full top-5 volume leaders.
    task = T / 'main' / 'fin-l3-top-202'
    payload = json.loads((task / 'environment/payloads.json').read_text())
    lead = payload['tools']['movers:vn30']['envelope']['data']['volume_leaders'][:5]
    vols = [r['vol'] for r in lead]
    assert vols == sorted(vols, reverse=True) and len(set(vols)) == 5
    ins = task / 'instruction.md'
    text = ins.read_text(encoding='utf-8')
    head, sep, contract = text.partition('## Ràng buộc chung')
    rows = ',\n'.join('    "%d": {"symbol": "MÃ", "vol": 0, "close": 0}' % i for i in range(1, 6))
    new_head = (
        '# Bảng 5 mã khối lượng lớn nhất VN30\n\n'
        'Liệt kê **đầy đủ 5 mã có khối lượng khớp lệnh lớn nhất** phiên gần nhất (%s) trong rổ **VN30** '
        '(đúng thứ hạng), kèm khối lượng (cổ phiếu) và giá đóng cửa (đồng).\n\n'
        '## Yêu cầu trả lời\n'
        'Trả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n'
        '```json\n{\n  "values": {\n%s\n  },\n  "period": "(kỳ được hỏi)",\n  "source": "market_movers",\n'
        '  "note": "(tuỳ chọn)"\n}\n```\n\n- Giá theo **đồng** (bảng giá).\n\n'
    ) % (S30, rows)
    if head != new_head:
        remember(ins)
        ins.write_text(new_head + sep + contract, encoding='utf-8')
    gold = load_gold(task)
    gold['solution'] = {str(i): {'symbol': r['symbol'], 'vol': float(r['vol']), 'close': float(r['close'])}
                        for i, r in enumerate(lead, 1)}
    exp = []
    for i, r in enumerate(lead, 1):
        exp += [{'type': 'str', 'path': 'values.%d.symbol' % i, 'accept': [r['symbol']]},
                {'type': 'value', 'path': 'values.%d.vol' % i, 'gold': float(r['vol']), 'tol': {'rel': 0.005}},
                {'type': 'value', 'path': 'values.%d.close' % i, 'gold': float(r['close']), 'tol': {'rel': 0.005}}]
    exp += [e for e in gold['expects'] if e['path'] in ('period', 'source')]
    gold['expects'] = exp
    gold['notes'] = 'Rewritten 2026-11-10 (gold audit A5): previously an exact duplicate of 201; now volume leaders top-5.'
    save_gold(task, gold)
    replace_oracle_body(task, (
        "rows = env('movers:vn30')['data']['volume_leaders'][:5]\n"
        "check('vol_sorted', [r['vol'] for r in rows], sorted([r['vol'] for r in rows], reverse=True))\n"
        "for i, r in enumerate(rows, 1):\n"
        "    s = gold['solution'][str(i)]\n"
        "    check('sym%d' % i, r['symbol'], s['symbol'])\n"
        "    check('vol%d' % i, float(r['vol']), s['vol'])\n"
        "    check('close%d' % i, float(r['close']), s['close'])\n"))
    replace_once(task / 'task.toml', 'title = "Bảng 5 mã giảm mạnh nhất"', 'title = "Bảng 5 mã khối lượng lớn nhất VN30"')
    NOTES['A5'] = 'top-202 rewritten to volume leaders top-5'

    # A6: winner/symbol picked from a candidate set -> tokens + reject other candidates.
    winners = {
        ('pilot', 'fin-l3-crypto-01', 'values.winner'): ['GC=F', 'BTC-USD', 'Bitcoin', 'vàng'],
        ('pilot', 'fin-l3-tech-multi-01', 'values.symbol'): ['HPG', 'HCM', 'VND', 'SHB'],
        ('main', 'fin-l3-crypto-multi-208', 'values.winner'): ['GC=F', 'BTC-USD'],
        ('main', 'fin-l3-crypto-multi-209', 'values.winner'): ['HG=F', 'NG=F'],
        ('main', 'fin-l3-crypto-multi-210', 'values.winner'): ['ETH-USD', 'SOL-USD'],
        ('main', 'fin-l3-crypto-multi-211', 'values.winner'): ['BZ=F', 'NG=F', 'Brent'],
        ('main', 'fin-l3-crypto-multi-212', 'values.winner'): ['GC=F', 'BTC-USD'],
        ('main', 'fin-l3-crypto-multi-213', 'values.winner'): ['HG=F', 'BZ=F'],
        ('main', 'fin-l3-crypto-multi-214', 'values.winner'): ['ETH-USD', 'BNB-USD'],
        ('main', 'fin-l3-crypto-multi-215', 'values.winner'): ['GC=F', 'SI=F'],
        ('main', 'fin-l3-tech-multi-204', 'values.symbol'): ['VCI', 'VIX', 'SHS', 'MBS'],
        ('main', 'fin-l3-tech-multi-206', 'values.symbol'): ['KDH', 'NLG', 'PDR', 'KBC'],
        ('main', 'fin-l3-tech-multi-207', 'values.symbol'): ['PVD', 'BSR', 'PLX', 'POW'],
        ('main', 'fin-l4-chain-303', 'values.symbol'): ['VCI', 'VIX', 'SHS', 'MBS'],
        ('main', 'fin-l4-chain-304', 'values.symbol'): ['PVD', 'BSR', 'PLX', 'POW'],
        ('main', 'fin-l4-chain-305', 'values.symbol'): ['ACB', 'STB', 'VPB', 'HDB'],
        ('main', 'fin-l4-chain-306', 'values.symbol'): ['TCB', 'LPB', 'MSN', 'BCM'],
        ('main', 'fin-l5-compare-283', 'values.winner'): ['SOL-USD', 'SOL', 'solana'],
        ('main', 'fin-l5-compare-284', 'values.winner'): ['SOL-USD', 'SOL', 'solana'],
        ('main', 'fin-l5-compare-285', 'values.winner'): ['BTC-USD', 'BTC', 'bitcoin'],
        ('main', 'fin-l5-compare-286', 'values.winner'): ['BTC-USD', 'BTC', 'bitcoin'],
        ('main', 'fin-l5-compare-287', 'values.winner'): ['BTCUSDT', 'BTC', 'bitcoin'],
    }
    for (split, name, path), reject in winners.items():
        to_tokens_with_reject(T / split / name, path, reject)
    NOTES['A6'] = 'winner/symbol fields: tokens + reject other candidates (%d tasks)' % len(winners)

    # A7 (found by judge calibration on superseded or9): comparison tasks ask for the previous
    # session in `note`, but answers naturally put both sessions in `period`, which the
    # exact date-set check rejects (3/3 arms on fin-l2-gold-01). Clarify the period field.
    a7 = '"period": "phiên được hỏi (chỉ ghi 30/10/2026; phiên so sánh ghi trong note)",'
    for split, name in [('pilot', 'fin-l2-gold-01')] + [('main', 'fin-l2-gf-compare-%d' % i) for i in range(172, 176)]:
        replace_once(T / split / name / 'instruction.md', '"period": "(kỳ được hỏi)",', a7)
    NOTES['A7'] = 'comparison tasks: period = asked session only (pilot gold-01, gf-compare-172..175)'

    # B2-B5 wording; typo fixes.
    replace_once(T / 'main/fin-l5-profile-261/instruction.md', '(quý gần nhất: Q4/2026)',
                 '(quý gần nhất theo nhãn kỳ của nguồn: Q4/2026 — CTD dùng niên độ tài chính riêng; nhãn kỳ do '
                 '`financial_detail` trả về, không phải quý dương lịch chưa kết thúc)')
    p285 = T / 'main/fin-l5-compare-285/instruction.md'
    replace_once(p285, '(|%| lớn hơn)?', '(|%| lớn hơn)? So sánh bằng số chưa làm tròn; chỉ làm tròn kết quả '
                 'hiển thị đến hai chữ số thập phân.')
    replace_once(T / 'main/fin-l5-compare-277/instruction.md', 'rồi **xếp hạng 5 mã theo ROE giảm dần**.',
                 'rồi **xếp hạng 5 mã theo ROE giảm dần**. Xếp hạng theo đúng giá trị ROE tool trả về (kể cả giá '
                 'trị bất thường, ví dụ khi vốn chủ sở hữu âm); nêu bất thường trong `note` nếu có.')
    replace_once(T / 'main/fin-l1-quote-crypto-125/instruction.md', '(nguồn vnstock crypto) là bao nhiêu',
                 '(nguồn vnstock crypto; nến ngày mới nhất trong dữ liệu, 01/11/2026) là bao nhiêu')
    replace_once(T / 'main/fin-l5-compare-287/instruction.md', '**% thay đổi phiên cuối**',
                 '**% thay đổi phiên cuối** (nến ngày 01/11/2026 so với nến 31/10/2026)')
    for path in sorted(T.glob('*/*/instruction.md')):
        text = path.read_text(encoding='utf-8')
        if '%%' in text:
            remember(path)
            path.write_text(text.replace('%%', '%'), encoding='utf-8')
    NOTES['B'] = 'B2 CTD fiscal label, B3 unrounded tie rule, B4 ROE anomaly, B5 latest daily bar, %% typos'


# ------------------------------------------------------------ root holdout fixes
def root_holdout_fixes():
    H = ORIGIN / 'tasks/holdout'
    S30 = '**phiên 30/10/2026**'
    for name in ('fin-l2-tech-916', 'fin-l2-tech-917'):
        replace_once(H / name / 'instruction.md', 'trên khung ngày (**1D**) là bao nhiêu?',
                     'trên khung ngày (**1D**) tại %s (phiên giao dịch gần nhất của snapshot) là bao nhiêu?' % S30)
    replace_once(H / 'fin-l3-tech-multi-927/instruction.md', 'RSI-14 (khung ngày)', 'RSI-14 (khung ngày, %s)' % S30)
    task = H / 'fin-l4-2src-940'
    replace_once(task / 'instruction.md', '"source": "yf_commodities + vn_crypto_ohlcv",',
                 '"source": "yf_commodities + vn_crypto_ohlcv + vn_msn_fx_gold",')
    replace_once(task / 'instruction.md', 'Hai nguồn lệch nhau bao nhiêu **%**?',
                 'Giá vnstock lấy close của nến ngày mới nhất trong dữ liệu (01/11/2026); lấy giá yfinance làm mốc '
                 '(mẫu số). Hai nguồn lệch nhau bao nhiêu **%** (giá trị tuyệt đối)?')
    set_source(task, ['yf_commodities', 'vn_crypto_ohlcv', 'vn_msn_fx_gold'], all_tools=True)
    replace_once(H / 'fin-l2-gf-compare-919/instruction.md', '"period": "(kỳ được hỏi)",',
                 '"period": "phiên được hỏi (chỉ ghi 29/10/2026; phiên so sánh ghi trong note)",')
    to_tokens_with_reject(H / 'fin-l3-crypto-multi-928', 'values.winner', ['GC=F', 'BTC-USD'])
    to_tokens_with_reject(H / 'fin-l3-crypto-multi-929', 'values.winner', ['HG=F', 'NG=F'])
    for path in sorted(H.glob('*/instruction.md')):
        text = path.read_text(encoding='utf-8')
        if '%%' in text:
            remember(path)
            path.write_text(text.replace('%%', '%'), encoding='utf-8')
    NOTES['root_holdout'] = 'A1 916/917/927, A4+B5 940, A6 928/929, B6 %% typos'


def register():
    migration_path = STUDY / 'audits/CORPUS-MIGRATION.json'
    migration = json.loads(migration_path.read_text())
    receipt = {'audit': AUDIT, 'notes': NOTES, 'files': {}}
    for path, before in sorted(CHANGED.items(), key=lambda kv: str(kv[0])):
        after = sha(path)
        if after == before:
            continue
        try:
            rel = str(path.relative_to(STUDY))
            entry = migration['changed'].get(rel)
            root = ORIGIN / rel
            migration['changed'][rel] = {
                'root_sha256': entry['root_sha256'] if entry else (sha(root) if root.exists() else None),
                'study_sha256': after}
            scope = 'study'
        except ValueError:
            rel = str(path.relative_to(ORIGIN))
            scope = 'root'
        receipt['files'][rel] = {'scope': scope, 'before_sha256': before, 'after_sha256': after}
    migration.setdefault('content_corrections', {})[AUDIT] = (
        'A1 session date stated; A2 compare-288..290 rewritten 1-session; A3 174/175 source yf; '
        'A4 257/258 3-tool source; A5 top-202 volume top-5; A6 winner reject lists; '
        'A7 comparison-task period = asked session only; B2-B5 wording')
    migration_path.write_text(json.dumps(migration, ensure_ascii=False, indent=2) + '\n')
    out = STUDY / 'audits' / AUDIT / 'patch-receipt.json'
    previous = json.loads(out.read_text()) if out.exists() else {'files': {}}
    previous['files'].update(receipt['files'])
    previous.update({k: v for k, v in receipt.items() if k != 'files'})
    out.write_text(json.dumps(previous, ensure_ascii=False, indent=1) + '\n')
    return receipt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root-holdout', action='store_true')
    a = ap.parse_args()
    study_fixes()
    if a.root_holdout:
        root_holdout_fixes()
    receipt = register()
    print('changed files:', len(receipt['files']))
    for k, v in NOTES.items():
        print(' ', k, '-', v)


if __name__ == '__main__':
    main()
