"""Pre-registered recommendation stratum (R), amendment 2026-11-25 (f). Owner: option A (replace S1/S2-buy with
buy/hold/sell recommendation tasks), threshold 2 %, measured at the last close ("Giá cuối 23/11").

Written and committed BEFORE any post-snapshot return of these tickers was computed or viewed. One ticker per task,
chosen by sector spread from audits/snapshot-extension-2026-11-25b/pre-120.json. Same outcome file and hash as the
investor stratum (investor_specs_20261124.POST_SHA256).

Entry: close of 30/10/2026. Exit: close of END (2026-11-23). ret = close(END) / close(30/10) - 1.
  MUA (buy)  passes iff ret >  +2 %
  BÁN (sell) passes iff ret <  -2 %
  GIỮ (hold) passes iff -2 % <= ret <= +2 %
Exactly one call is correct per ticker. A null, refusal, or any other word fails. Primary = this outcome, scored by
code (no LLM judge). The continuous return is reported as a diagnostic.
"""
THRESHOLD_PCT = 2
CALLS = ('MUA', 'GIỮ', 'BÁN')

SPECS = [
    # main (16)
    {'tid': 'fin-r1-call-771', 'split': 'main', 'sym': 'VCB'}, {'tid': 'fin-r1-call-772', 'split': 'main', 'sym': 'TCB'},
    {'tid': 'fin-r1-call-773', 'split': 'main', 'sym': 'SSI'}, {'tid': 'fin-r1-call-774', 'split': 'main', 'sym': 'VND'},
    {'tid': 'fin-r1-call-775', 'split': 'main', 'sym': 'HPG'}, {'tid': 'fin-r1-call-776', 'split': 'main', 'sym': 'NKG'},
    {'tid': 'fin-r1-call-777', 'split': 'main', 'sym': 'MWG'}, {'tid': 'fin-r1-call-778', 'split': 'main', 'sym': 'PNJ'},
    {'tid': 'fin-r1-call-779', 'split': 'main', 'sym': 'FPT'}, {'tid': 'fin-r1-call-780', 'split': 'main', 'sym': 'GAS'},
    {'tid': 'fin-r1-call-781', 'split': 'main', 'sym': 'PLX'}, {'tid': 'fin-r1-call-782', 'split': 'main', 'sym': 'DGC'},
    {'tid': 'fin-r1-call-783', 'split': 'main', 'sym': 'VHM'}, {'tid': 'fin-r1-call-784', 'split': 'main', 'sym': 'KDH'},
    {'tid': 'fin-r1-call-785', 'split': 'main', 'sym': 'VNM'}, {'tid': 'fin-r1-call-786', 'split': 'main', 'sym': 'VJC'},
    # holdout (4) — replaces the 4 retired holdout S1/S2-buy tasks
    {'tid': 'fin-r1-call-995', 'split': 'holdout', 'sym': 'BID'}, {'tid': 'fin-r1-call-996', 'split': 'holdout', 'sym': 'HCM'},
    {'tid': 'fin-r1-call-997', 'split': 'holdout', 'sym': 'GMD'}, {'tid': 'fin-r1-call-998', 'split': 'holdout', 'sym': 'REE'},
    # pilot (1)
    {'tid': 'fin-r1-call-869', 'split': 'pilot', 'sym': 'DPM'},
]
