"""Amendment 2026-11-11 (d) D2: record 120-session daily history (data_time <= 2026-10-30) for the compute stratum.

The opentrading MCP history tools currently fail (MCP server calls the vnstock gen-6 `Market()` API while vnstock
4.0.4 is installed). History is therefore recorded with the same provider library directly (vnstock Quote, source
VCI) and stored in the exact `vn_quote_history` / `vn_index_ohlcv` envelope shape, with that fact in provenance.
Every session that overlaps an existing frozen snapshot payload must match it exactly, or the symbol is rejected.
"""
import contextlib, datetime, glob, io, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'audits/snapshot-extension-2026-11-11'
END = '2026-10-30'
N = 120
STOCKS = ['ACB', 'STB', 'VPB', 'HDB', 'TPB', 'VCB', 'BID', 'CTG', 'MBB', 'TCB', 'HPG', 'FPT', 'MWG', 'VNM', 'VIC',
          'VHM', 'MSN', 'GAS', 'SAB', 'VJC', 'PNJ', 'SSI', 'PLX', 'POW', 'GVR']
INDEXES = ['VNINDEX', 'VN30']


def fetch(symbol):
    from vnstock import Quote
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        df = Quote(symbol=symbol, source='VCI').history(start='2026-03-01', end=END, interval='1D')
    rows = [{'t': str(r.time)[:10], 'o': float(r.open), 'h': float(r.high), 'l': float(r.low), 'c': float(r.close),
             'v': int(r.volume)} for r in df.itertuples()]
    rows = [r for r in rows if r['t'] <= END][-N:]
    if len(rows) != N or rows[-1]['t'] != END:
        raise RuntimeError(f'{symbol}: got {len(rows)} rows ending {rows[-1]["t"] if rows else None}')
    return rows


def frozen_points():
    pts = {}
    for f in glob.glob(str(ROOT / 'tasks/**/environment/payloads.json'), recursive=True):
        for e in json.load(open(f)).get('tools', {}).values():
            if e.get('tool') not in ('vn_quote_history', 'vn_index_ohlcv'):
                continue
            d = e.get('envelope', {}).get('data', {})
            for c in d.get('closes', []) or []:
                pts.setdefault((d.get('symbol'), str(c['t'])[:10]), set()).add(c['c'])
    return pts


def main():
    recorded_at = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat()
    frozen = frozen_points()
    out, receipt = {}, {'recorded_at': recorded_at, 'end': END, 'sessions': N, 'method': __doc__.strip(), 'symbols': {}}
    for sym in STOCKS + INDEXES:
        rows = fetch(sym)
        checks = [(t, sorted(v)) for (s, t), v in frozen.items() if s == sym]
        mism = [(t, v, next((r['c'] for r in rows if r['t'] == t), None)) for t, v in checks
                if next((r['c'] for r in rows if r['t'] == t), None) not in v]
        receipt['symbols'][sym] = {'rows': len(rows), 'first': rows[0]['t'], 'last': rows[-1]['t'],
                                   'frozen_overlap_checked': len(checks), 'mismatches': mism}
        if mism:
            print('REJECT', sym, mism[:3]); continue
        out[sym] = rows
        print(sym, len(rows), rows[0]['t'], rows[-1]['t'], 'overlap', len(checks))
    (OUT / 'history-120.json').write_text(json.dumps(out, ensure_ascii=False))
    (OUT / 'RECEIPT.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
