"""Amendment 2026-11-25: record quarterly and annual financial statements for the fundamental compute (C5) and
finance-memory (M6) strata.

Run with the opentrading-mcp environment (its Vietstock `financeinfo` provider, the same no-JWT source the frozen
`financial_statements` payloads came from):
    cd ~/MCP-server && set -a && . ./.env && set +a && \
    uv run --frozen python <study>/tools/record_statements_20261125.py <study>/audits/snapshot-extension-2026-11-25/raw.json
Raw provider output is stored unmodified; period filtering, cross-checks and envelopes are done by the task builder.
"""
import json, sys, time
from datetime import datetime, timezone

SYMBOLS = ['FPT', 'MWG', 'HPG', 'VNM', 'MSN', 'PNJ', 'KDC', 'DCM', 'DBC', 'VGS', 'GAS', 'SAB', 'PLX', 'REE', 'DGC', 'GVR',
           'POW', 'VJC', 'HSG', 'NKG', 'DPM', 'FRT', 'DHG', 'IMP', 'PVS', 'PVD', 'CTD', 'VCG', 'GEX', 'BMP', 'NTP', 'VHC',
           'ANV', 'KDH', 'NLG', 'DXG', 'PC1', 'GMD', 'HAH', 'TRA']


def main(out):
    from opentrading_mcp.providers import vietstock as vs
    raw, errors = {}, {}
    for sym in SYMBOLS:
        for period in ('quarter', 'year'):
            try:
                data, warnings = vs.align_financeinfo(vs.financeinfo(sym, period), 'all', 12)
                raw.setdefault(sym, {})[period] = {'data': data, 'warnings': warnings}
            except Exception as exc:  # recorded, never silently dropped
                errors['%s/%s' % (sym, period)] = '%s: %s' % (type(exc).__name__, exc)
            time.sleep(0.3)
    doc = {'recorded_at': datetime.now(timezone.utc).astimezone().isoformat(), 'source': 'vietstock financeinfo (opentrading-mcp '
           'providers.vietstock.financeinfo + align_financeinfo, statement=all, periods_n=12)', 'symbols': raw, 'errors': errors}
    with open(out, 'w', encoding='utf-8') as fp:
        json.dump(doc, fp, ensure_ascii=False, indent=1)
    print('recorded', len(raw), 'symbols;', len(errors), 'errors')


if __name__ == '__main__':
    main(sys.argv[1])
