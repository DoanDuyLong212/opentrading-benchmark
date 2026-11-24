"""Amendment 2026-11-24 (d): daily prices for the investor stratum (I).

Two windows per symbol, both from vnstock Quote (source VCI), the same provider used for history-120 (2026-11-11):
  pre  : the 120 sessions ending 2026-10-30 (last session of the 2026-11-01 MCP snapshot) -> task payloads
  post : sessions 2026-10-31 .. 2026-11-23 -> grading only, never served to agents. The owner asked for 'today' (24/11);
         at 18:50 on 24/11 no source had a 24/11 session (VCI daily bars end 23/11; the DNSE board's last match is
         23/11 14:45), so the window ends at the latest recorded session, 23/11.
Every pre-window session that overlaps history-120 or a frozen task payload must match exactly, or the symbol is rejected.
    python3 tools/record_prices_20261124.py
"""
import contextlib, datetime, glob, io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'audits/snapshot-extension-2026-11-24b'
SNAP_END, END, N = '2026-10-30', '2026-11-23', 120
STOCKS = sorted(set(
    'ACB BID CTG MBB TCB VCB STB VPB HDB TPB SSI VND HCM VCI SHS HPG HSG NKG MWG FRT PNJ DGW GAS PLX PVS PVD DCM DPM DGC '
    'VHM VIC KDH NLG DXG VNM SAB MSN KDC POW REE PC1 GEX GMD HAH VJC VHC ANV DHG IMP TRA CTD VCG GVR BMP NTP FPT DBC VGS'.split()))
INDEXES = ['VNINDEX', 'VN30']


def fetch(symbol):
    from vnstock import Quote
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        df = Quote(symbol=symbol, source='VCI').history(start='2026-03-01', end=END, interval='1D')
    return [{'t': str(r.time)[:10], 'o': float(r.open), 'h': float(r.high), 'l': float(r.low), 'c': float(r.close),
             'v': int(r.volume)} for r in df.itertuples()]


def frozen_points():
    pts = {}
    h120 = json.loads((ROOT / 'audits/snapshot-extension-2026-11-11/history-120.json').read_text())
    for s, rows in h120.items():
        for r in rows:
            pts.setdefault((s, r['t']), set()).add(r['c'])
    for f in glob.glob(str(ROOT / 'tasks/**/environment/payloads.json'), recursive=True):
        for e in json.load(open(f)).get('tools', {}).values():
            if e.get('tool') not in ('vn_quote_history', 'vn_index_ohlcv'):
                continue
            d = e.get('envelope', {}).get('data', {})
            for c in d.get('closes', []) or []:
                if 'c' in c:
                    pts.setdefault((d.get('symbol'), str(c['t'])[:10]), set()).add(c['c'])
    return pts


def main():
    recorded_at = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat()
    frozen = frozen_points()
    pre, post = {}, {}
    receipt = {'recorded_at': recorded_at, 'snapshot_end': SNAP_END, 'end': END, 'sessions_pre': N,
               'method': __doc__.strip(), 'symbols': {}, 'rejected': {}}
    for sym in STOCKS + INDEXES:
        try:
            rows = fetch(sym)
        except Exception as exc:
            receipt['rejected'][sym] = 'fetch: %s: %s' % (type(exc).__name__, exc); print('FAIL', sym, exc); continue
        a = [r for r in rows if r['t'] <= SNAP_END][-N:]
        b = [r for r in rows if SNAP_END < r['t'] <= END]
        if len(a) != N or a[-1]['t'] != SNAP_END or not b or b[-1]['t'] != END:
            receipt['rejected'][sym] = 'window: pre %d ending %s, post %d ending %s' % (
                len(a), a[-1]['t'] if a else None, len(b), b[-1]['t'] if b else None); print('REJECT', sym, receipt['rejected'][sym]); continue
        checks = [(t, sorted(v)) for (s, t), v in frozen.items() if s == sym]
        mism = [(t, v, next((r['c'] for r in a if r['t'] == t), None)) for t, v in checks
                if any(r['t'] == t for r in a) and next(r['c'] for r in a if r['t'] == t) not in v]
        receipt['symbols'][sym] = {'pre': [a[0]['t'], a[-1]['t']], 'post': [b[0]['t'], b[-1]['t'], len(b)],
                                   'frozen_overlap_checked': sum(1 for t, _ in checks if any(r['t'] == t for r in a)),
                                   'mismatches': mism}
        if mism:
            receipt['rejected'][sym] = 'mismatch with frozen snapshot'; print('REJECT', sym, mism[:3]); continue
        pre[sym], post[sym] = a, b
        print(sym, 'post', len(b), 'overlap', receipt['symbols'][sym]['frozen_overlap_checked'])
    (OUT / 'pre-120.json').write_text(json.dumps(pre, ensure_ascii=False))
    (OUT / 'post-20261124.json').write_text(json.dumps(post, ensure_ascii=False))
    (OUT / 'RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1))
    print('kept', len(pre), 'rejected', len(receipt['rejected']))


if __name__ == '__main__':
    main()
