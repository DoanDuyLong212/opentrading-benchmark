#!/usr/bin/env python3
"""Amendment 2026-11-24 (d), group A: 18 more multi-session memory tasks (M2-M5) for main + 1 pilot twin.
(The 6 more M6 finance-memory tasks of group A are built by build_finance_stratum_20261124.build_extra.)

Families from or16 evidence (OT 100%% vs OpenCode 0%% on M3 split/update, M4 rule/portfolio, M5 revoke, M2 portfolio).
Same peer_compare / vn_quote_history payloads, layouts and grader as the 2026-11-11 memory stratum
(tools/build_memory_stratum_20261111.py); criteria pairs/triples are taken further down the same deterministic
search (never the ones already used) and portfolios are new. Idempotent.
"""
import hashlib, itertools, json, re, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import build_memory_stratum_20261111 as ms  # noqa: E402

CREATED = '2026-11-24'


def pick_update_k(key, k):
    """Like ms.pick_update but returns the k-th valid triple (k=0 is the one already used in main)."""
    rs = ms.rows(key)
    grids = {'p_e': (7, 8, 10, 12, 15, 17, 20, 25, 30, 35), 'p_b': (0.8, 1, 1.1, 1.2, 1.4, 1.5, 2, 3, 5),
             'roe': (4, 5, 6, 8, 10, 12, 15, 17, 20, 22)}
    ops = {'p_e': '<', 'p_b': '<', 'roe': '>'}
    ok = lambda c: all(abs(r[c[0]] - c[2]) >= ms.MARGIN[c[0]] for r in rs.values())
    cands = [(m, ops[m], x) for m in grids for x in grids[m] if ok((m, ops[m], x))]
    for a, b in itertools.permutations(cands, 2):
        if a[0] == b[0]:
            continue
        old = ms.screen(key, [a, b])
        if not old or old == ms.screen(key, [b]) or len(old) == 5:
            continue
        for x in grids[a[0]]:
            u = (a[0], a[1], x)
            if x == a[2] or not ok(u):
                continue
            new = ms.screen(key, [u, b])
            if new and new not in (old, ms.screen(key, [b])) and len(new) < 5:
                if k == 0:
                    return a, b, u
                k -= 1
    raise SystemExit('no update triple for %s k=%d' % (key, k))


def port_fact(pos):
    return 'Danh mục của tôi: ' + '; '.join('%d cp %s giá vốn %s nghìn đồng' % (q, s, ('%g' % k).replace('.', ','))
                                             for s, (q, k) in pos.items()) + '.'


def build():
    T = []

    def add(tid, split, tier, title, q, facts, variant=0, update=None, revoke=None):
        final_text = q['question'] + '\n\n' + ms.contract_text(q['example'])
        T.append(dict(tid=tid, split=split, tier=tier.split('-')[0][:2] if tier.startswith('M5') else tier[:2], subtier=tier,
                      title=title, sessions=ms.layout(tier, facts, final_text, variant, update, revoke), q=q))

    # M3a (4): k=4 / k=5 (k=0..3 are used by M1, M2, M3a and M5 in main)
    for i, (key, k) in enumerate((('cons_p', 4), ('tech_p', 4), ('bds_p', 4), ('pharma_p', 4))):
        a, b = ms.pick_pair(key, k=k)
        add('fin-m3-split-%d' % (531 + i), 'main', 'M3a', 'Memory M3 — hai tiêu chí ghi nhớ ở hai phiên (%s, bộ 2)' % key,
            ms.q_screen(key, [a, b], 'tất cả các tiêu chí tôi đã nhờ bạn ghi nhớ'),
            [('c1-%s' % key, ms.crit_fact(a)), ('c2-%s' % key, ms.crit_fact(b))], i + 1)
    # M3b (4): second valid update triple
    for i, key in enumerate(('bds_p', 'cons_p', 'tech_p', 'pharma_p')):
        a, b, upd = pick_update_k(key, 1)
        add('fin-m3-update-%d' % (535 + i), 'main', 'M3b', 'Memory M3 — tiêu chí được cập nhật ở phiên sau (%s, bộ 2)' % key,
            ms.q_screen(key, [upd, b], 'các tiêu chí hiện hành tôi đã nhờ bạn ghi nhớ (theo bản cập nhật mới nhất)'),
            [('c1-%s' % key, ms.crit_fact(a)), ('c2-%s' % key, ms.crit_fact(b))], i + 1, update=ms.crit_fact(upd))
    # M4 rule (3): a remembered criterion silently applied to "highest ROE"
    for i, (key, crits) in enumerate((('energy_p', (('p_b', '<', 1), ('p_e', '<', 8))),
                                      ('bds_p', (('p_b', '<', 1.1),)),
                                      ('cons_p', (('p_b', '<', 2),)))):
        rs = ms.rows(key)
        c = next(c for c in crits if max(rs, key=lambda s: rs[s]['roe']) not in ms.screen(key, [c]) and ms.screen(key, [c]))
        add('fin-m4-rule-%d' % (539 + i), 'main', 'M4', 'Memory M4 — tiêu chí đã ghi nhớ tự áp dụng (%s, bộ 2)' % key,
            ms.q_top(key, [c], 'roe', 'theo tiêu chí đầu tư tôi đã nhờ bạn ghi nhớ'), [('rule-%s' % key, ms.crit_fact(c))], i + 1)
    # M4 portfolio (3)
    for i, pos in enumerate(({'STB': (3000, 38), 'GAS': (500, 66), 'SAB': (300, 52), 'VIC': (200, 120)},
                             {'TPB': (4000, 16), 'HDB': (2500, 27), 'SSI': (2000, 33), 'PNJ': (400, 75), 'GVR': (900, 31)},
                             {'BID': (1500, 40), 'CTG': (1800, 38), 'VNM': (600, 60), 'POW': (7000, 13.5)})):
        add('fin-m4-port-%d' % (542 + i), 'main', 'M4', 'Memory M4 — danh mục đã ghi nhớ, định giá ở phiên sau (bộ 2)',
            ms.q_portfolio(pos, 'danh mục của tôi (đã nhờ bạn ghi nhớ)'), [('portfolio', port_fact(pos))], i + 1)
    # M5 revoke (3)
    for i, (key, k) in enumerate((('cons_p', 5), ('tech_p', 5), ('energy_p', 4))):
        a, b = ms.pick_pair(key, k=k)
        q = ms.q_screen(key, [b], 'các tiêu chí **hiện còn hiệu lực** tôi đã nhờ bạn ghi nhớ')
        assert ms.screen(key, [a, b]) != ms.screen(key, [b]), key
        q['solution']['pass_if_revoked_applied'] = ms.screen(key, [a, b])
        add('fin-m5-revoke-%d' % (545 + i), 'main', 'M5-revoke', 'Memory M5 — tiêu chí đã xoá không được áp dụng (%s, bộ 2)' % key,
            q, [('ra-%s' % key, ms.crit_fact(a)), ('rb-%s' % key, ms.crit_fact(b))], i, revoke=('ra-%s' % key, None))
    # M2 portfolio (1)
    pos = {'STB': (2000, 40), 'PNJ': (200, 70), 'VJC': (150, 100)}
    add('fin-m2-port-548', 'main', 'M2', 'Memory M2 — danh mục ở phiên trước, quay lại phiên (bộ 2)',
        ms.q_portfolio(pos, 'danh mục tôi đã nêu đầu cuộc trao đổi này'), [('p', port_fact(pos))], 2)
    # pilot twin: M5 revoke
    a, b = ms.pick_pair('bds_p', k=5)
    q = ms.q_screen('bds_p', [b], 'các tiêu chí **hiện còn hiệu lực** tôi đã nhờ bạn ghi nhớ')
    q['solution']['pass_if_revoked_applied'] = ms.screen('bds_p', [a, b])
    add('fin-m5-revoke-857', 'pilot', 'M5-revoke', 'Memory M5 — tiêu chí đã xoá không được áp dụng (bds_p, pilot)',
        q, [('ra-bds_p', ms.crit_fact(a)), ('rb-bds_p', ms.crit_fact(b))], 1, revoke=('ra-bds_p', None))
    return T


def main():
    T = build()
    assert sum(t['split'] == 'main' for t in T) == 18 and sum(t['split'] == 'pilot' for t in T) == 1
    seen = {}
    receipt = {}
    for t in T:
        sig = json.dumps([t['q']['solution'], [x['text'] for s in t['sessions'] for x in s['turns']][:-1]], ensure_ascii=False)
        assert sig not in seen, (t['tid'], seen.get(sig))
        seen[sig] = t['tid']
        d = ms.write(t)
        toml = (d / 'task.toml').read_text(encoding='utf-8')
        toml = toml.replace('# Native-memory stratum — amendment 2026-11-11 (d), tools/build_memory_stratum_20261111.py',
                            '# Native-memory stratum (group A) — amendment 2026-11-24 (d), tools/build_memory_extra_20261124.py')
        toml = re.sub(r'^created = ".*"$', 'created = "%s"' % CREATED, toml, flags=re.M)
        (d / 'task.toml').write_text(toml, encoding='utf-8')
        receipt[t['tid']] = {'split': t['split'], 'tier': t['subtier'], 'solution': t['q']['solution'],
                             'files': {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(d.rglob('*')) if p.is_file()}}
    (STUDY / 'audits/taskset-revision-2026-11-24/MEMORY-EXTRA-BUILD.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    for k, v in receipt.items():
        print(k, v['split'], v['tier'], json.dumps(v['solution'], ensure_ascii=False)[:130])


if __name__ == '__main__':
    main()
