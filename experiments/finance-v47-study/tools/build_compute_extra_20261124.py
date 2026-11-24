#!/usr/bin/env python3
"""Amendment 2026-11-24 (d), group B: 20 more hard price-series compute tasks (main) + 2 pilot twins.

Families chosen from or16 evidence (arms split on C3/C4 multi-step series work: volume share, log-annualized vs
benchmark, volatility regime, MA ladder, relative-strength chain, geometric annualization, rebalancing, signal
portfolio, staggered buys). Saturated families (doubling, DCA) are not reused. Same templates, tolerances and
recorded 120-session history as the 2026-11-11 compute stratum (tools/compute_hard_templates_20261111.py); only the
symbol sets and windows are new. Idempotent.
"""
import hashlib, json, sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDY / 'tools'))
import build_compute_stratum_20261111 as cs  # noqa: E402
HT = cs.HT
hard = cs.hard


def build():
    main = [hard('fin-c3-volshare-441', 'C3', HT.vol_share(['VCB', 'BID', 'CTG', 'MBB', 'TCB'])),
            hard('fin-c3-volshare-442', 'C3', HT.vol_share(['HPG', 'FPT', 'MWG', 'VNM', 'GAS'])),
            hard('fin-c3-logann-443', 'C3', HT.log_ann_vs_bench(['ACB', 'VPB', 'HDB', 'TPB'], 'VN30')),
            hard('fin-c3-logann-444', 'C3', HT.log_ann_vs_bench(['PNJ', 'SAB', 'MSN', 'VJC'], 'VNINDEX')),
            hard('fin-c3-volregime-445', 'C3', HT.vol_regime(['ACB', 'STB', 'VPB', 'HDB', 'TPB'])),
            hard('fin-c3-volregime-446', 'C3', HT.vol_regime(['VIC', 'VHM', 'MSN', 'SAB', 'PNJ'])),
            hard('fin-c3-maladder-447', 'C3', HT.ma_ladder(['HPG', 'FPT', 'PNJ', 'VJC'])),
            hard('fin-c3-maladder-448', 'C3', HT.ma_ladder(['TCB', 'MBB', 'ACB', 'STB'])),
            hard('fin-c3-rschain-449', 'C3', HT.rs_chain(['HPG', 'GVR', 'POW', 'PLX', 'GAS'], 'VNINDEX')),
            hard('fin-c3-rschain-450', 'C3', HT.rs_chain(['FPT', 'MWG', 'PNJ', 'VNM', 'SAB'], 'VN30')),
            hard('fin-c3-geo-451', 'C3', HT.geo_ann(['SSI', 'VJC', 'PNJ'])),
            hard('fin-c3-geo-452', 'C3', HT.geo_ann(['MSN', 'VHM', 'STB'])),
            hard('fin-c4-rebal-453', 'C4', HT.rebalanced(['FPT', 'MWG', 'PNJ', 'VNM', 'SAB', 'MSN'])),
            hard('fin-c4-rebal-454', 'C4', HT.rebalanced(['ACB', 'STB', 'VPB', 'HDB', 'TPB', 'SSI'])),
            hard('fin-c4-signal-455', 'C4', HT.signal_portfolio(['HPG', 'FPT', 'MWG', 'VNM', 'GAS', 'PLX', 'POW', 'GVR'])),
            hard('fin-c4-signal-456', 'C4', HT.signal_portfolio(['VIC', 'VHM', 'SSI', 'PNJ', 'SAB', 'VJC', 'STB', 'TPB'])),
            hard('fin-c4-logann-457', 'C4', HT.log_ann_vs_bench(['ACB', 'STB', 'VPB', 'HDB', 'TPB', 'SSI', 'VIC', 'VHM', 'MSN', 'PNJ'], 'VN30')),
            hard('fin-c4-stagger-458', 'C4', HT.staggered({'TCB': (1500, 110), 'ACB': (2000, 85), 'PNJ': (300, 65), 'VNM': (700, 40),
                                                           'PLX': (900, 25), 'STB': (3000, 12)})),
            hard('fin-c4-stagger-459', 'C4', HT.staggered({'BID': (1000, 105), 'MBB': (2500, 88), 'SAB': (200, 72), 'VJC': (300, 55),
                                                           'GVR': (1500, 33), 'HDB': (2000, 18)})),
            hard('fin-c4-rebal-460', 'C4', HT.rebalanced(['GAS', 'PLX', 'POW', 'GVR', 'HPG', 'VJC'], split=40))]
    pilot = [hard('fin-c3-volshare-809', 'C3', HT.vol_share(['SSI', 'VPB', 'STB', 'HDB', 'TPB'])),
             hard('fin-c4-stagger-810', 'C4', HT.staggered({'VPB': (2000, 100), 'GAS': (300, 70), 'FPT': (400, 45),
                                                            'POW': (5000, 28), 'VHM': (500, 14), 'ACB': (1500, 8)}))]
    return main, pilot


def main():
    m, p = build()
    assert len(m) == 20 and len(p) == 2
    receipt = {}
    for split, specs in (('main', m), ('pilot', p)):
        for s in specs:
            d = cs.write(split, s)
            receipt[s['tid']] = {'split': split, 'solution': s['solution'],
                                 'files': {str(f.relative_to(d)): hashlib.sha256(f.read_bytes()).hexdigest()
                                           for f in sorted(d.rglob('*')) if f.is_file()}}
    (STUDY / 'audits/taskset-revision-2026-11-24/COMPUTE-EXTRA-BUILD.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + '\n')
    for k, v in receipt.items():
        print(k, v['split'], json.dumps(v['solution'], ensure_ascii=False)[:120])


if __name__ == '__main__':
    main()
