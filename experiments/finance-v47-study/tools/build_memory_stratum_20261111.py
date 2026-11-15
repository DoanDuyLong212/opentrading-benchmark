#!/usr/bin/env python3
"""Amendment 2026-11-11 (d): native-memory stratum M1–M5 (main 30: fin-m*-501..530, holdout 7: fin-m*-971..977).

execution_contract = native-memory-v2 (tools/runners/memory_runner.py profile native-v2):
- every logical session is a separate native session for every arm; repeating a session id resumes it (all arms);
- a turn with memory_command=true is the user's own OpenTrading notebook form (/nho) for OT (local, no model turn);
  OpenCode and DSH receive the same text as a chat message; no benchmark-owned notebook tool for any arm;
- only the final turn is graded, by the standard grader on standard payloads.
Tier layouts (identical for every arm):
  M1 same session (facts in chat, distractors, question)              -> parity control
  M2 facts in chat in S1, other session S2, question resumes S1        -> parity control (resume)
  M3a /nho fact A in S1, /nho fact B in S2, question resumes S2        -> needs A from an older session
  M3b /nho A in S1, /nho update of A in S2, question in fresh S3       -> needs current version across sessions
  M4 /nho criteria or portfolio in S1, other session, fresh question   -> memory applied on a later day (+ calc)
  M5 negative controls: stale price in memory must not replace the tool; revoked criterion must not apply
Gold answers are chosen so that partial or no recall gives a different answer than full recall.
"""
import hashlib, itertools, json, shutil, sys
from decimal import Decimal as D
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
from mcp_snapshot_server import digest  # noqa: E402
import build_compute_stratum_20261111 as CS  # noqa: E402

CONTRACT = 'native-memory-v2'
TEMPLATE = STUDY / 'tasks/main/fin-l3-index-216'
PEER_SRC = {'banks_p': 'holdout/fin-l3-screen-923', 'sec_p': 'holdout/fin-l3-screen-924', 'cons_p': 'main/fin-l3-screen-192',
            'tech_p': 'main/fin-l3-screen-193', 'bds_p': 'main/fin-l5-compare-280', 'energy_p': 'main/fin-l5-compare-281',
            'pharma_p': 'main/fin-l5-compare-282'}
BATCH_SRC = {'cons1': 'main/fin-l3-agg-184', 'tech1': 'main/fin-l3-agg-185', 'energy1': 'main/fin-l3-agg-187',
             'banks1': 'holdout/fin-l3-agg-921'}
METRIC = {'p_e': 'P/E', 'p_b': 'P/B', 'roe': 'ROE'}
MARGIN = {'p_e': 0.3, 'p_b': 0.05, 'roe': 0.3}  # no value sits on a threshold
DISTRACT = ['Nhân tiện, giải thích ngắn gọn giúp tôi chỉ số P/B nghĩa là gì (không cần số liệu).',
            'Cho tôi hỏi thêm: thanh khoản cổ phiếu thường được đo bằng những chỉ tiêu nào? Trả lời ngắn.',
            'Ngoài lề: biên lợi nhuận gộp khác biên lợi nhuận ròng ở điểm nào? Trả lời ngắn, không cần tra cứu.']


def peer_entry(key):
    f = STUDY / 'tasks' / PEER_SRC[key] / 'environment/payloads.json'
    if not f.exists():
        f = STUDY / 'tasks-retired' / PEER_SRC[key] / 'environment/payloads.json'
    return json.loads(f.read_text())['tools']['peer:' + key]


def batch_entry(key):
    f = STUDY / 'tasks' / BATCH_SRC[key] / 'environment/payloads.json'
    if not f.exists():
        f = STUDY / 'tasks-retired' / BATCH_SRC[key] / 'environment/payloads.json'
    return json.loads(f.read_text())['tools']['batch:' + key]


def rows(key):
    return {r['symbol']: r for r in peer_entry(key)['envelope']['data']['rows']}


def holds(r, c):
    m, op, x = c
    return r[m] < x if op == '<' else r[m] > x


def phrase(c):
    m, op, x = c
    return '%s %s %s%s' % (METRIC[m], 'dưới' if op == '<' else 'trên', ('%g' % x).replace('.', ','), '%' if m == 'roe' else '')


def screen(key, cs):
    return sorted(s for s, r in rows(key).items() if all(holds(r, c) for c in cs))


def pick_pair(key, avoid=(), k=0):
    """Two criteria whose joint answer differs from each single criterion and from 'no criterion'."""
    rs = rows(key)
    cands = [(m, op, x) for m, op, grid in (('p_e', '<', (12, 15, 17, 20, 25, 30, 35, 7, 8, 10)), ('p_b', '<', (0.8, 1, 1.2, 1.5, 2, 3, 1.1, 1.4)),
                                            ('roe', '>', (4, 5, 6, 8, 10, 12, 15, 20, 17, 22)))
             for x in grid]
    for a, b in itertools.combinations(cands, 2):
        if a[0] == b[0] or (a, b) in avoid:
            continue
        both, A, B = screen(key, [a]), screen(key, [b]), None
        both = screen(key, [a, b]); A = screen(key, [a]); B = screen(key, [b])
        margin = all(abs(r[c[0]] - c[2]) >= MARGIN[c[0]] for r in rs.values() for c in (a, b))
        if both and both != A and both != B and len(both) < 5 and margin:
            if k == 0:
                return a, b
            k -= 1
    raise SystemExit('no discriminating pair for ' + key)


def pick_update(key):
    """(a, b, a'): answer under a'∧b differs from a∧b, from b alone and from the empty set."""
    rs = rows(key)
    grids = {'p_e': (7, 8, 10, 12, 15, 17, 20, 25, 30, 35), 'p_b': (0.8, 1, 1.1, 1.2, 1.4, 1.5, 2, 3, 5),
             'roe': (4, 5, 6, 8, 10, 12, 15, 17, 20, 22)}
    ops = {'p_e': '<', 'p_b': '<', 'roe': '>'}
    ok = lambda c: all(abs(r[c[0]] - c[2]) >= MARGIN[c[0]] for r in rs.values())
    cands = [(m, ops[m], x) for m in grids for x in grids[m] if ok((m, ops[m], x))]
    for a, b in itertools.permutations(cands, 2):
        if a[0] == b[0]:
            continue
        old = screen(key, [a, b])
        if not old or old == screen(key, [b]) or len(old) == 5:
            continue
        for x in grids[a[0]]:
            u = (a[0], a[1], x)
            if x == a[2] or not ok(u):
                continue
            new = screen(key, [u, b])
            if new and new not in (old, screen(key, [b])) and len(new) < 5:
                return a, b, u
    raise SystemExit('no update triple for ' + key)


def contract_text(example):
    tmpl = (TEMPLATE / 'instruction.md').read_text(encoding='utf-8')
    return ('## Yêu cầu trả lời\nTrả lời bằng đúng một object JSON trong phản hồi cuối cùng, theo schema:\n\n```json\n%s\n```\n\n\n'
            % json.dumps(example, ensure_ascii=False, indent=2)) + tmpl[tmpl.index('## Ràng buộc chung'):]


def cmd(text, ops):
    return {'text': text, 'memory_command': True, 'memory_operations': ops}


def put(fid, fact, text):
    return {'op': 'put', 'id': fid, 'kind': 'constraint', 'text': fact, 'source_text': text, 'consent': 'explicit_user_request'}


def delete(fid, text):
    return {'op': 'delete', 'id': fid, 'source_text': text, 'consent': 'explicit_user_request'}


def remember(fid, fact):
    text = 'Ghi nhớ giúp tôi: ' + fact
    return cmd(text, [put(fid, fact, text)])


def chat(text):
    return {'text': text}


# ---------------------------------------------------------------- final questions (gold + payload + oracle)

def q_screen(key, cs, hint):
    syms = list(rows(key))
    g = screen(key, cs)
    return dict(question='Trong 5 mã **%s**: mã nào thỏa %s? Số liệu lấy từ `peer_compare`.' % (', '.join(syms), hint),
                example={'values': {'pass': ['MÃ1', '...']}, 'period': '(kỳ dữ liệu tool)', 'source': 'peer_compare',
                         'note': 'chỉ số từng mã dùng để lọc'},
                solution={'pass': g, 'criteria': [phrase(c) for c in cs]},
                expects=[{'type': 'set', 'path': 'values.pass', 'gold': g}, {'type': 'str', 'path': 'source', 'accept': ['peer_compare']}],
                payloads={'peer:' + key: peer_entry(key)},
                oracle=("rows = env('peer:%s')['data']['rows']\nok = lambda r: %s\n"
                        "check('pass', sorted(r['symbol'] for r in rows if ok(r)), gold['solution']['pass'])\n")
                       % (key, ' and '.join("r['%s'] %s %r" % c for c in cs)))


def q_top(key, cs, metric, hint):
    rs = rows(key); ok = [s for s in rs if all(holds(rs[s], c) for c in cs)]
    top = max(ok, key=lambda s: rs[s][metric]); free = max(rs, key=lambda s: rs[s][metric])
    assert top != free, (key, cs)
    return dict(question=('Trong 5 mã **%s**, %s, mã nào có **%s cao nhất** và bằng bao nhiêu? Số liệu lấy từ `peer_compare`.'
                          % (', '.join(rs), hint, METRIC[metric])),
                example={'values': {'symbol': 'MÃ', METRIC[metric].lower().replace('/', ''): 0}, 'period': '(kỳ dữ liệu tool)',
                         'source': 'peer_compare', 'note': '(tuỳ chọn)'},
                solution={'symbol': top, 'value': rs[top][metric], 'criteria': [phrase(c) for c in cs]},
                expects=[{'type': 'tokens', 'path': 'values.symbol', 'accept': [top], 'reject': [s for s in rs if s != top]},
                         {'type': 'value', 'path': 'values.' + METRIC[metric].lower().replace('/', ''), 'gold': rs[top][metric], 'tol': {'rel': 0.005}},
                         {'type': 'str', 'path': 'source', 'accept': ['peer_compare']}],
                payloads={'peer:' + key: peer_entry(key)},
                oracle=("rows = {r['symbol']: r for r in env('peer:%s')['data']['rows']}\nok = [s for s, r in rows.items() if %s]\n"
                        "t = max(ok, key=lambda s: rows[s][%r])\ncheck('top', t, gold['solution']['symbol'])\n"
                        "check('val', rows[t][%r], gold['solution']['value'])\n")
                       % (key, ' and '.join("r['%s'] %s %r" % c for c in cs) or 'True', metric, metric))


def q_portfolio(pos, hint):
    """pos: {sym: (qty, cost in nghìn đồng)}; P/L at the 30/10 close from vn_quote_history."""
    now = sum(D(q) * CS.c(s) * 1000 for s, (q, _) in pos.items()); cost = sum(D(q) * D(str(k)) * 1000 for s, (q, k) in pos.items())
    pl = now - cost; pct = pl / cost * 100
    return dict(question=('Định giá **%s** theo giá đóng cửa **phiên 30/10/2026** (tool `vn_quote_history`): tổng giá trị thị trường, '
                          'tổng giá vốn, lãi/lỗ bao nhiêu **đồng** và bao nhiêu **%%**? Làm tròn tiền tới đồng, %% tới 2 chữ số thập phân.' % hint),
                example={'values': {'market_value': 0, 'cost': 0, 'pnl': 0, 'pnl_pct': 0}, 'unit': 'đồng', 'period': '(kỳ được hỏi)',
                         'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                solution={'market_value': CS.r4(now), 'cost': CS.r4(cost), 'pnl': CS.r4(pl), 'pnl_pct': CS.r4(pct)},
                expects=[CS.val('values.market_value', now, CS.LVL), CS.val('values.cost', cost, CS.LVL), CS.val('values.pnl', pl, CS.LVL),
                         CS.val('values.pnl_pct', pct, CS.PCT), CS.money_unit(), CS.period(),
                         {'type': 'str', 'path': 'source', 'accept': ['vn_quote_history']}],
                payloads={CS.key(s): CS.envelope(s) for s in pos},
                oracle=(CS.ORACLE_LIB.replace('for _s in SYMS', 'for _s in %r' % sorted(pos)) +
                        "pos = %r\nnow = sum(_D(q) * C(s) * 1000 for s, (q, k) in pos.items())\ncost = sum(_D(q) * _D(str(k)) * 1000 for s, (q, k) in pos.items())\n"
                        "check('mv', R(now), gold['solution']['market_value'])\ncheck('cost', R(cost), gold['solution']['cost'])\n"
                        "check('pnl', R(now - cost), gold['solution']['pnl'])\ncheck('pct', R((now - cost) / cost * 100), gold['solution']['pnl_pct'])\n") % pos)


def q_basket_mean(bkey, members, hint):
    qs = {x['symbol']: x for x in batch_entry(bkey)['envelope']['data']['quotes']}
    m = sum(D(str(qs[s]['close'])) for s in members) / len(members)
    return dict(question=('Giá đóng cửa **trung bình cộng** của %s ở **phiên 30/10/2026** là bao nhiêu **đồng**? Liệt kê các mã đã dùng. '
                          'Số liệu từ `vn_equity_quote_batch`; làm tròn 2 chữ số thập phân.' % hint),
                example={'values': {'members': ['MÃ1', '...'], 'mean_close': 0}, 'unit': 'đồng', 'period': '(kỳ được hỏi)',
                         'source': 'vn_equity_quote_batch', 'note': '(tuỳ chọn)'},
                solution={'members': sorted(members), 'mean_close': CS.r4(m)},
                expects=[{'type': 'set', 'path': 'values.members', 'gold': sorted(members)}, CS.val('values.mean_close', m, CS.LVL),
                         CS.money_unit(), CS.period(), {'type': 'str', 'path': 'source', 'accept': ['vn_equity_quote_batch']}],
                payloads={'batch:' + bkey: batch_entry(bkey)},
                oracle=("qs = {x['symbol']: x for x in env('batch:%s')['data']['quotes']}\nfrom decimal import Decimal as _D\n"
                        "m = sum(_D(str(qs[s]['close'])) for s in %r) / %d\ncheck('mean', round(float(m), 4), gold['solution']['mean_close'])\n")
                       % (bkey, sorted(members), len(members)))


def q_stale(sym, stale):
    last = CS.c(sym)
    assert abs(float(last) - stale) > 0.5
    return dict(question=('Giá đóng cửa **%s** ở **phiên giao dịch gần nhất** (30/10/2026) là bao nhiêu nghìn đồng/cổ phiếu? Lấy từ tool '
                          '`vn_quote_history`.' % sym),
                example={'values': {'symbol': 'MÃ', 'last': 0}, 'unit': 'nghìn đồng/cổ phiếu', 'period': '(kỳ được hỏi)',
                         'source': 'vn_quote_history', 'note': '(tuỳ chọn)'},
                solution={'symbol': sym, 'last': float(last), 'stale_value_in_memory': stale},
                expects=[{'type': 'str', 'path': 'values.symbol', 'accept': [sym]},
                         {'type': 'value', 'path': 'values.last', 'gold': float(last), 'tol': {'rel': 0.001}},
                         CS.period(), {'type': 'str', 'path': 'source', 'accept': ['vn_quote_history']}],
                payloads={CS.key(sym): CS.envelope(sym)},
                oracle=(CS.ORACLE_LIB.replace('for _s in SYMS', 'for _s in [%r]' % sym) +
                        "check('last', float(C(%r)), gold['solution']['last'])\n" % sym))


# ---------------------------------------------------------------- tiers → sessions

def layout(tier, facts, final_text, variant=0, update=None, revoke=None):
    """facts: list of (fid, fact sentence). Returns sessions list."""
    d = DISTRACT[variant % len(DISTRACT)]
    final = {'text': final_text, 'final': True}
    if tier == 'M1':
        body = ' '.join(f for _, f in facts)
        return [{'id': 'S1', 'turns': [chat('Lưu ý cho cuộc trao đổi này: ' + body + ' Bạn chỉ cần xác nhận đã rõ.'), chat(d),
                                       chat(DISTRACT[(variant + 1) % 3]), final]}]
    if tier == 'M2':
        body = ' '.join(f for _, f in facts)
        return [{'id': 'S1', 'turns': [chat('Lưu ý cho cuộc trao đổi này: ' + body + ' Bạn chỉ cần xác nhận đã rõ.')]},
                {'id': 'S2', 'turns': [chat(d)]},
                {'id': 'S1', 'turns': [final]}]
    if tier == 'M3a':
        (fa, a), (fb, b) = facts
        return [{'id': 'S1', 'turns': [remember(fa, a)]},
                {'id': 'S2', 'turns': [remember(fb, b), chat(d), final]}]
    if tier == 'M3b':
        (fa, a), (fb, b) = facts
        text = 'Cập nhật ghi nhớ của tôi: ' + update
        return [{'id': 'S1', 'turns': [remember(fa, a), remember(fb, b)]},
                {'id': 'S2', 'turns': [cmd(text, [put(fa, update, text)]), chat(d)]},
                {'id': 'S3', 'turns': [final]}]
    if tier == 'M4':
        return [{'id': 'S1', 'turns': [remember(fid, f) for fid, f in facts]},
                {'id': 'S2', 'turns': [chat(d)]},
                {'id': 'S3', 'turns': [final]}]
    if tier == 'M5-stale':
        (fid, f), = facts
        return [{'id': 'S1', 'turns': [remember(fid, f)]}, {'id': 'S2', 'turns': [final]}]
    if tier == 'M5-revoke':
        rid, _ = revoke
        text = 'Xoá ghi nhớ: bỏ tiêu chí "%s", từ nay không áp dụng nữa.' % dict(facts)[rid]
        return [{'id': 'S1', 'turns': [remember(fid, f) for fid, f in facts]},
                {'id': 'S2', 'turns': [cmd(text, [delete(rid, text)]), chat(d)]},
                {'id': 'S3', 'turns': [final]}]
    raise ValueError(tier)


def crit_fact(c):
    return 'Tôi chỉ xét cổ phiếu có %s.' % phrase(c)


def build():
    T = []  # (tid, split, tier, title, sessions, q)

    def add(tid, split, tier, title, q, facts, variant=0, update=None, revoke=None):
        final_text = q['question'] + '\n\n' + contract_text(q['example'])
        T.append(dict(tid=tid, split=split, tier=tier.split('-')[0][:2] if tier.startswith('M5') else tier[:2], subtier=tier,
                      title=title, sessions=layout(tier, facts, final_text, variant, update, revoke), q=q))

    main_peer = ['cons_p', 'tech_p', 'bds_p', 'energy_p', 'pharma_p']
    # M1 (6): in-context control
    for i, key in enumerate(main_peer):
        a, b = pick_pair(key)
        add('fin-m1-screen-%d' % (501 + i), 'main', 'M1', 'Memory M1 — lọc 2 tiêu chí cùng phiên (%s)' % key,
            q_screen(key, [a, b], 'các tiêu chí tôi vừa nêu ở trên'), [('c1', crit_fact(a)), ('c2', crit_fact(b))], i)
    pos = {'HPG': (2000, 22.5), 'FPT': (300, 95), 'MWG': (500, 60)}
    add('fin-m1-port-506', 'main', 'M1', 'Memory M1 — lãi/lỗ danh mục cùng phiên',
        q_portfolio(pos, 'danh mục tôi vừa nêu'),
        [('p', 'Danh mục của tôi: ' + '; '.join('%d cp %s giá vốn %s nghìn đồng' % (q, s, ('%g' % k).replace('.', ',')) for s, (q, k) in pos.items()) + '.')], 2)
    # M2 (6): resume control
    for i, key in enumerate(main_peer[:3]):
        a, b = pick_pair(key, k=1)
        a2, b2 = (b, a)
        add('fin-m2-screen-%d' % (507 + i), 'main', 'M2', 'Memory M2 — tiêu chí ở phiên trước, quay lại phiên (%s)' % key,
            q_screen(key, [a, b], 'các tiêu chí tôi đã nêu đầu cuộc trao đổi này'), [('c1', crit_fact(a2)), ('c2', crit_fact(b2))], i + 1)
    add('fin-m2-basket-510', 'main', 'M2', 'Memory M2 — rổ riêng đặt tên, quay lại phiên',
        q_basket_mean('tech1', ['CMG', 'CTR', 'FOX'], '**"rổ công nghệ của tôi"**'),
        [('b', '"Rổ công nghệ của tôi" gồm đúng 3 mã CMG, CTR, FOX.')], 0)
    pos = {'VNM': (800, 62), 'GAS': (400, 70), 'SSI': (1500, 30)}
    add('fin-m2-port-511', 'main', 'M2', 'Memory M2 — danh mục ở phiên trước, quay lại phiên',
        q_portfolio(pos, 'danh mục tôi đã nêu đầu cuộc trao đổi này'),
        [('p', 'Danh mục của tôi: ' + '; '.join('%d cp %s giá vốn %s nghìn đồng' % (q, s, ('%g' % k).replace('.', ',')) for s, (q, k) in pos.items()) + '.')], 1)
    a, b = ('p_e', '<', 20), ('roe', '>', 10)
    add('fin-m2-top-512', 'main', 'M2', 'Memory M2 — ROE cao nhất theo tiêu chí, quay lại phiên',
        q_top('pharma_p', [('p_b', '<', 3)], 'roe', 'chỉ trong các mã thỏa tiêu chí tôi đã nêu đầu cuộc trao đổi này'),
        [('c1', crit_fact(('p_b', '<', 3)))], 2)
    # M3a (4): fact A in an older session, B in the resumed one
    for i, key in enumerate(['cons_p', 'tech_p', 'energy_p', 'pharma_p']):
        a, b = pick_pair(key, k=2)
        add('fin-m3-split-%d' % (513 + i), 'main', 'M3a', 'Memory M3 — hai tiêu chí ghi nhớ ở hai phiên (%s)' % key,
            q_screen(key, [a, b], 'tất cả các tiêu chí tôi đã nhờ bạn ghi nhớ'), [('c1-%s' % key, crit_fact(a)), ('c2-%s' % key, crit_fact(b))], i)
    # M3b (4): criterion updated in a later session, question in a fresh session
    for i, key in enumerate(['bds_p', 'cons_p', 'tech_p', 'energy_p']):
        a, b, upd = pick_update(key)
        add('fin-m3-update-%d' % (517 + i), 'main', 'M3b', 'Memory M3 — tiêu chí được cập nhật ở phiên sau (%s)' % key,
            q_screen(key, [upd, b], 'các tiêu chí hiện hành tôi đã nhờ bạn ghi nhớ (theo bản cập nhật mới nhất)'),
            [('c1-%s' % key, crit_fact(a)), ('c2-%s' % key, crit_fact(b))], i, update=crit_fact(upd))
    # M4 (6): applied on a later day
    for i, (key, metric) in enumerate((('cons_p', 'roe'), ('pharma_p', 'roe'), ('tech_p', 'roe'))):
        rs = rows(key)
        c = next(c for c in (('p_e', '<', 15), ('p_e', '<', 20), ('p_b', '<', 2), ('p_b', '<', 3), ('p_e', '<', 25))
                 if max(rs, key=lambda s: rs[s][metric]) not in screen(key, [c]) and screen(key, [c]))
        add('fin-m4-rule-%d' % (521 + i), 'main', 'M4', 'Memory M4 — tiêu chí đã ghi nhớ tự áp dụng (%s)' % key,
            q_top(key, [c], metric, 'theo tiêu chí đầu tư tôi đã nhờ bạn ghi nhớ'), [('rule-%s' % key, crit_fact(c))], i)
    for i, pos in enumerate(({'HPG': (3000, 23), 'VCB': (500, 62), 'FPT': (400, 100), 'PNJ': (300, 80)},
                             {'MBB': (2000, 24), 'TCB': (1500, 33), 'VJC': (200, 110), 'POW': (5000, 13), 'GVR': (600, 30)},
                             {'ACB': (2500, 24), 'MSN': (400, 75), 'VHM': (300, 90), 'PLX': (800, 38)})):
        add('fin-m4-port-%d' % (524 + i), 'main', 'M4', 'Memory M4 — danh mục đã ghi nhớ, định giá ở phiên sau',
            q_portfolio(pos, 'danh mục của tôi (đã nhờ bạn ghi nhớ)'),
            [('portfolio', 'Danh mục của tôi: ' + '; '.join('%d cp %s giá vốn %s nghìn đồng' % (q, s, ('%g' % k).replace('.', ',')) for s, (q, k) in pos.items()) + '.')], i)
    # M5 (4): negative controls
    for i, (sym, stale) in enumerate((('HPG', 25.0), ('VNM', 70.0))):
        add('fin-m5-stale-%d' % (527 + i), 'main', 'M5-stale', 'Memory M5 — giá cũ trong ghi nhớ không thay số liệu tool (%s)' % sym,
            q_stale(sym, stale), [('stale-' + sym, 'Giá %s tôi thấy hôm trước là %s nghìn đồng.' % (sym, ('%g' % stale).replace('.', ',')))], i)
    for i, key in enumerate(('pharma_p', 'bds_p')):
        a, b = pick_pair(key, k=3)
        q = q_screen(key, [b], 'các tiêu chí **hiện còn hiệu lực** tôi đã nhờ bạn ghi nhớ')
        q['solution']['pass_if_revoked_applied'] = screen(key, [a, b])  # rule metric: revocation_violation
        add('fin-m5-revoke-%d' % (529 + i), 'main', 'M5-revoke', 'Memory M5 — tiêu chí đã xoá không được áp dụng (%s)' % key,
            q,
            [('ra-%s' % key, crit_fact(a)), ('rb-%s' % key, crit_fact(b))], i, revoke=('ra-%s' % key, None))
    # ---------------- holdout (7)
    a, b = pick_pair('banks_p')
    add('fin-m1-screen-971', 'holdout', 'M1', 'Memory M1 — lọc 2 tiêu chí cùng phiên (ngân hàng)',
        q_screen('banks_p', [a, b], 'các tiêu chí tôi vừa nêu ở trên'), [('c1', crit_fact(a)), ('c2', crit_fact(b))], 0)
    a, b = pick_pair('sec_p')
    add('fin-m2-screen-972', 'holdout', 'M2', 'Memory M2 — tiêu chí ở phiên trước, quay lại phiên (chứng khoán)',
        q_screen('sec_p', [a, b], 'các tiêu chí tôi đã nêu đầu cuộc trao đổi này'), [('c1', crit_fact(a)), ('c2', crit_fact(b))], 1)
    a, b = pick_pair('sec_p', k=1)
    add('fin-m3-split-973', 'holdout', 'M3a', 'Memory M3 — hai tiêu chí ghi nhớ ở hai phiên (chứng khoán)',
        q_screen('sec_p', [a, b], 'tất cả các tiêu chí tôi đã nhờ bạn ghi nhớ'), [('h1', crit_fact(a)), ('h2', crit_fact(b))], 2)
    a, b, upd = pick_update('banks_p')
    add('fin-m3-update-974', 'holdout', 'M3b', 'Memory M3 — tiêu chí được cập nhật ở phiên sau (ngân hàng)',
        q_screen('banks_p', [upd, b], 'các tiêu chí hiện hành tôi đã nhờ bạn ghi nhớ (theo bản cập nhật mới nhất)'),
        [('h3', crit_fact(a)), ('h4', crit_fact(b))], 0, update=crit_fact(upd))
    add('fin-m4-basket-975', 'holdout', 'M4', 'Memory M4 — rổ riêng đã ghi nhớ, dùng ở phiên sau',
        q_basket_mean('banks1', ['ACB', 'HDB', 'TPB'], '**"rổ ngân hàng của tôi"**'),
        [('basket', '"Rổ ngân hàng của tôi" gồm đúng 3 mã ACB, HDB, TPB.')], 1)
    pos = {'STB': (1000, 55), 'VPB': (3000, 21), 'SAB': (200, 48), 'GAS': (500, 68)}
    add('fin-m4-port-976', 'holdout', 'M4', 'Memory M4 — các vị thế đã lưu, định giá ở phiên sau',
        q_portfolio(pos, 'các vị thế cổ phiếu tôi đã nhờ bạn lưu lại'),
        [('portfolio', 'Danh mục của tôi: ' + '; '.join('%d cp %s giá vốn %s nghìn đồng' % (q, s, ('%g' % k).replace('.', ',')) for s, (q, k) in pos.items()) + '.')], 2)
    add('fin-m5-stale-977', 'holdout', 'M5-stale', 'Memory M5 — giá cũ trong ghi nhớ không thay số liệu tool (FPT)',
        q_stale('FPT', 120.0), [('stale-FPT', 'Giá FPT tôi thấy hôm trước là 120 nghìn đồng.')], 0)
    # ---------------- pilot (6; pipeline validation only)
    a, b = pick_pair('energy_p', k=4)
    add('fin-m1-screen-851', 'pilot', 'M1', 'Memory M1 — lọc 2 tiêu chí cùng phiên (năng lượng, pilot)',
        q_screen('energy_p', [a, b], 'các tiêu chí tôi vừa nêu ở trên'), [('c1', crit_fact(a)), ('c2', crit_fact(b))], 1)
    a, b = pick_pair('bds_p', k=1)
    add('fin-m2-screen-852', 'pilot', 'M2', 'Memory M2 — tiêu chí ở phiên trước, quay lại phiên (BĐS, pilot)',
        q_screen('bds_p', [a, b], 'các tiêu chí tôi đã nêu đầu cuộc trao đổi này'), [('c1', crit_fact(a)), ('c2', crit_fact(b))], 2)
    a, b = pick_pair('cons_p', k=3)
    add('fin-m3-split-853', 'pilot', 'M3a', 'Memory M3 — hai tiêu chí ghi nhớ ở hai phiên (tiêu dùng, pilot)',
        q_screen('cons_p', [a, b], 'tất cả các tiêu chí tôi đã nhờ bạn ghi nhớ'), [('p1', crit_fact(a)), ('p2', crit_fact(b))], 0)
    a, b, upd = pick_update('pharma_p')
    add('fin-m3-update-854', 'pilot', 'M3b', 'Memory M3 — tiêu chí được cập nhật ở phiên sau (dược, pilot)',
        q_screen('pharma_p', [upd, b], 'các tiêu chí hiện hành tôi đã nhờ bạn ghi nhớ (theo bản cập nhật mới nhất)'),
        [('p3', crit_fact(a)), ('p4', crit_fact(b))], 1, update=crit_fact(upd))
    pos = {'CTG': (1500, 40), 'BID': (800, 45), 'VJC': (100, 120)}
    add('fin-m4-port-855', 'pilot', 'M4', 'Memory M4 — danh mục đã ghi nhớ, định giá ở phiên sau (pilot)',
        q_portfolio(pos, 'danh mục của tôi (đã nhờ bạn ghi nhớ)'),
        [('portfolio', 'Danh mục của tôi: ' + '; '.join('%d cp %s giá vốn %s nghìn đồng' % (q, s, ('%g' % k).replace('.', ',')) for s, (q, k) in pos.items()) + '.')], 2)
    add('fin-m5-stale-856', 'pilot', 'M5-stale', 'Memory M5 — giá cũ trong ghi nhớ không thay số liệu tool (MWG, pilot)',
        q_stale('MWG', 90.0), [('stale-MWG', 'Giá MWG tôi thấy hôm trước là 90 nghìn đồng.')], 0)
    return T


def write(t):
    d = STUDY / 'tasks' / t['split'] / t['tid']
    if d.exists():
        shutil.rmtree(d)
    (d / 'environment').mkdir(parents=True); (d / 'solution').mkdir(); (d / 'tests').mkdir()
    # Multi-turn tasks carry the memory grader variant (memory_evidence is an evidence field), as every turns.json task.
    (d / 'tests/grader.py').write_bytes((STUDY / 'tools/v45_grader.py').read_bytes().replace(
        b'"evidence","source_evidence"', b'"evidence","source_evidence","memory_evidence"'))
    q = t['q']
    payloads = {'snapshot_date': '2026-11-01', 'note': 'Envelope MCP (snapshot 2026-11-01; lịch sử 120 phiên xem audits/snapshot-extension-2026-11-11).',
                'tools': q['payloads']}
    (d / 'environment/payloads.json').write_text(json.dumps(payloads, ensure_ascii=False, indent=1) + '\n')
    turns = {'version': 2, 'mode': 'memory', 'execution_contract': CONTRACT, 'tier': t['subtier'], 'sessions': t['sessions'],
             'note': 'Native-memory stratum (amendment 2026-11-11 d). Same sessions for every arm; memory_command = OT /nho form, chat for others.'}
    (d / 'environment/turns.json').write_text(json.dumps(turns, ensure_ascii=False, indent=1) + '\n')
    final = t['sessions'][-1]['turns'][-1]['text']
    (d / 'instruction.md').write_text('# %s\n\nBài nhiều phiên hội thoại (driver gửi theo `environment/turns.json`); chỉ chấm lượt cuối.\n\n%s'
                                      % (t['title'], final), encoding='utf-8')
    prov = [{'tool': e['tool'], 'source': e['envelope']['provenance']['source'], 'as_of': e['envelope']['provenance']['as_of'],
             'matched_entry_id': k, 'response_sha256': digest(e['envelope'])} for k, e in q['payloads'].items()]
    gold = {'task_id': t['tid'], 'scoring': 'value', 'solution': q['solution'], 'split': t['split'],
            'expects': [e for e in q['expects'] if e.get('type') != 'period'],
            'contract_version': 2, 'stratum': 'memory', 'tier': t['tier'], 'subtier': t['subtier'],
            'memory_construct': t['subtier'], 'notes': 'Native-memory stratum (amendment 2026-11-11 d).',
            'provenance_contract': prov, 'provenance_catalog': prov,
            'payload_sha256': hashlib.sha256((d / 'environment/payloads.json').read_bytes()).hexdigest(),
            'required_payload_keys': sorted(q['payloads'])}
    (d / 'solution/gold.json').write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n')
    o = (TEMPLATE / 'solution/oracle.py').read_text(encoding='utf-8')
    pre, mark, rest = o.partition('# === thân oracle ===\n')
    _, sep, tail = rest.partition('\nif problems:')
    (d / 'solution/oracle.py').write_text(pre + mark + q['oracle'] + '\n\nif problems:' + tail, encoding='utf-8')
    tools = sorted({e['tool'] for e in q['payloads'].values()})
    toml = '\n'.join([
        '# Native-memory stratum — amendment 2026-11-11 (d), tools/build_memory_stratum_20261111.py',
        'id = "%s"' % t['tid'], 'title = "%s"' % t['title'].replace('"', "'"), 'version = 3', 'created = "2026-11-11"',
        'level = "%s"' % t['tier'], 'family = "%s memory"' % t['tier'], 'financebench_type = "multi-session memory"',
        'entity = "%s"' % '+'.join(sorted(q['payloads'])), 'asset = "vn_stock"', 'data_zone = "green"', 'data_pairs = []',
        'snapshot_date = "2026-11-01"', 'universe_cap = 0', 'banned_tools = ["web_search", "web_fetch", "sentiment_score"]',
        'human_time_band = "15–60 phút"', 'time_limit_min = 30', 'tools_expected = %s' % json.dumps(tools),
        'mcp_payloads = "environment/payloads.json"', 'snapshot_required = true', 'split = "%s"' % t['split'],
        'multiturn = true', 'track = "memory_multiturn"', 'stratum = "memory"', 'tier = "%s"' % t['tier'],
        'subtier = "%s"' % t['subtier'], 'confirmatory_eligible = true', '', '[scoring]', 'type = "value"',
        'gold = "solution/gold.json"', 'oracle = "solution/oracle.py"', 'grader = "tests/grader.py"', ''])
    (d / 'task.toml').write_text(toml, encoding='utf-8')
    return d


def main():
    T = build()
    assert sum(t['split'] == 'main' for t in T) == 30 and sum(t['split'] == 'holdout' for t in T) == 7, len(T)
    assert sum(t['split'] == 'pilot' for t in T) == 6 and len({t['tid'] for t in T}) == 43
    receipt = {}
    for t in T:
        d = write(t)
        receipt[t['tid']] = {'split': t['split'], 'tier': t['subtier'], 'solution': t['q']['solution'],
                             'files': {f: hashlib.sha256((d / f).read_bytes()).hexdigest() for f in
                                       ('instruction.md', 'solution/gold.json', 'solution/oracle.py', 'task.toml',
                                        'environment/payloads.json', 'environment/turns.json')}}
    (STUDY / 'audits/taskset-revision-2026-11-11/MEMORY-BUILD.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    for k, v in receipt.items():
        print(k, v['tier'], json.dumps(v['solution'], ensure_ascii=False))


if __name__ == '__main__':
    main()
