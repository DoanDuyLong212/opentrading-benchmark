"""Pre-registered investor stratum (I), amendment 2026-11-24 (d). Owner: "lãi lỗ điểm chính", leader replaced by
"chọn cổ tăng nhiều nhất (giá đó tới max ngày hôm nay)", end = today.

Written and committed BEFORE any post-snapshot return was computed or viewed. Candidate sets were chosen by sector
from the symbols recorded in audits/snapshot-extension-2026-11-24b/pre-120.json; the builder reads
post-20261124.json only after this file is committed (POST_SHA256 pins the exact outcome file).

Entry: close of 30/10/2026 (last session of the 2026-11-01 MCP snapshot). Window: sessions 31/10..END.
END = 2026-11-23: the owner asked for 24/11, but at 18:50 on 24/11 no source had a 24/11 session (see
tools/record_prices_20261124.py). Re-recording later only changes END and POST_SHA256; rules and sets stay fixed.

Outcome metrics (all from daily closes, never intraday):
  ret(s)  = close(END) / close(30/10) - 1                      (hold to END)
  peak(s) = max(close over 31/10..END) / close(30/10) - 1     ("tăng nhiều nhất": up to the window's highest close)
  low(s)  = min(close over 31/10..END) / close(30/10) - 1     (worst point after entry)
Pass rules (binary, deterministic; primary = this outcome, owner decision):
  I1 pick     : pick one candidate; pass iff ret(pick) > mean ret(candidates)
  I2 maxgain  : pick one candidate; pass iff peak(pick) == max peak(candidates) (ties: any tied symbol passes)
  I3 risk     : flag exactly 2; pass iff mean low(flagged) < mean low(others)
  I4 portfolio: choose exactly 4, equal weight; pass iff mean ret(chosen) > mean ret(candidates)
  I5 memory   : pick one candidate allowed by the remembered (and updated) constraints;
                pass iff pick is allowed and ret(pick) > mean ret(allowed)
A null, refusal, symbol outside the list or wrong count fails. Continuous ret/peak/low of every answer and the
VN-Index window return are reported as diagnostics.
"""
END = '2026-11-23'
ENTRY = '2026-10-30'
POST_SHA256 = 'fdfa27527f56099a0534909f9abd1a7d69cb5b616b857aacd8755654d522f06c'
PRE_SHA256 = '8aa406b70be853bf70386e8043516be47d7b8e27af94271e71991d9298f5de57'

SPECS = [
    # ---- main (20)
    {'tid': 'fin-i1-pick-701', 'split': 'main', 'type': 'I1', 'sector': 'ngân hàng', 'cands': ['VCB', 'BID', 'CTG', 'MBB', 'TCB', 'ACB']},
    {'tid': 'fin-i1-pick-702', 'split': 'main', 'type': 'I1', 'sector': 'chứng khoán', 'cands': ['SSI', 'VND', 'HCM', 'VCI', 'SHS']},
    {'tid': 'fin-i1-pick-703', 'split': 'main', 'type': 'I1', 'sector': 'bất động sản', 'cands': ['VHM', 'VIC', 'KDH', 'NLG', 'DXG']},
    {'tid': 'fin-i1-pick-704', 'split': 'main', 'type': 'I1', 'sector': 'thép và vật liệu', 'cands': ['HPG', 'HSG', 'NKG', 'GVR', 'BMP']},
    {'tid': 'fin-i1-pick-705', 'split': 'main', 'type': 'I1', 'sector': 'tiêu dùng và bán lẻ', 'cands': ['VNM', 'SAB', 'MSN', 'KDC', 'MWG', 'PNJ']},
    {'tid': 'fin-i2-maxgain-711', 'split': 'main', 'type': 'I2', 'cands': ['FPT', 'VJC', 'GAS', 'DGC', 'REE', 'PNJ']},
    {'tid': 'fin-i2-maxgain-712', 'split': 'main', 'type': 'I2', 'cands': ['STB', 'VPB', 'HDB', 'TPB', 'SHS', 'VND']},
    {'tid': 'fin-i2-maxgain-713', 'split': 'main', 'type': 'I2', 'cands': ['DCM', 'DPM', 'PVS', 'PVD', 'PLX', 'POW']},
    {'tid': 'fin-i2-maxgain-714', 'split': 'main', 'type': 'I2', 'cands': ['GMD', 'HAH', 'VHC', 'ANV', 'DBC', 'FRT']},
    {'tid': 'fin-i3-risk-721', 'split': 'main', 'type': 'I3', 'cands': ['DXG', 'NLG', 'KDH', 'VCG', 'CTD', 'PC1']},
    {'tid': 'fin-i3-risk-722', 'split': 'main', 'type': 'I3', 'cands': ['HSG', 'NKG', 'HPG', 'GEX', 'POW', 'VGS']},
    {'tid': 'fin-i3-risk-723', 'split': 'main', 'type': 'I3', 'cands': ['SSI', 'VCI', 'HCM', 'SHS', 'VND', 'STB']},
    {'tid': 'fin-i3-risk-724', 'split': 'main', 'type': 'I3', 'cands': ['FRT', 'DGW', 'MWG', 'PNJ', 'VJC', 'HAH']},
    {'tid': 'fin-i3-risk-725', 'split': 'main', 'type': 'I3', 'cands': ['PVD', 'PVS', 'GAS', 'PLX', 'DCM', 'DPM']},
    {'tid': 'fin-i4-port-731', 'split': 'main', 'type': 'I4', 'cands': ['VCB', 'TCB', 'MBB', 'FPT', 'HPG', 'MWG', 'GAS', 'VNM']},
    {'tid': 'fin-i4-port-732', 'split': 'main', 'type': 'I4', 'cands': ['SSI', 'VHM', 'VIC', 'DGC', 'REE', 'GMD', 'PNJ', 'POW']},
    {'tid': 'fin-i4-port-733', 'split': 'main', 'type': 'I4', 'cands': ['ACB', 'VPB', 'DXG', 'HSG', 'PVS', 'DCM', 'FRT', 'VJC']},
    {'tid': 'fin-i5-mem-741', 'split': 'main', 'type': 'I5', 'sub': 'exclude',
     'cands': ['VCB', 'MBB', 'VHM', 'KDH', 'FPT', 'HPG', 'GAS', 'MWG'],
     'rule': 'Tôi không mua cổ phiếu ngành ngân hàng và ngành bất động sản.', 'allowed': ['FPT', 'HPG', 'GAS', 'MWG']},
    {'tid': 'fin-i5-mem-742', 'split': 'main', 'type': 'I5', 'sub': 'update',
     'cands': ['HPG', 'HSG', 'GAS', 'PLX', 'PVS', 'SSI', 'VND', 'REE'],
     'rule': 'Tôi không mua cổ phiếu ngành thép.',
     'update': 'Cập nhật ghi nhớ của tôi: bỏ ràng buộc không mua ngành thép; thay vào đó tôi không mua cổ phiếu ngành dầu khí.',
     'allowed': ['HPG', 'HSG', 'SSI', 'VND', 'REE']},
    {'tid': 'fin-i5-mem-743', 'split': 'main', 'type': 'I5', 'sub': 'holdings',
     'cands': ['FPT', 'MWG', 'VCB', 'TCB', 'DGC', 'PNJ', 'SAB'],
     'rule': 'Tôi đang giữ FPT, MWG và VCB; tôi không mua thêm mã đang giữ.',
     'update': 'Cập nhật ghi nhớ của tôi: tôi đã bán hết VCB, hiện chỉ còn giữ FPT và MWG.',
     'allowed': ['VCB', 'TCB', 'DGC', 'PNJ', 'SAB']},
    # ---- pilot (5; one per type, symbols/sets not used as a whole by main)
    {'tid': 'fin-i1-pick-751', 'split': 'pilot', 'type': 'I1', 'sector': 'dầu khí', 'cands': ['GAS', 'PLX', 'PVS', 'PVD']},
    {'tid': 'fin-i2-maxgain-752', 'split': 'pilot', 'type': 'I2', 'cands': ['DHG', 'IMP', 'TRA', 'BMP', 'NTP', 'VGS']},
    {'tid': 'fin-i3-risk-753', 'split': 'pilot', 'type': 'I3', 'cands': ['VHM', 'VIC', 'DGC', 'GVR', 'REE', 'SAB']},
    {'tid': 'fin-i4-port-754', 'split': 'pilot', 'type': 'I4', 'cands': ['BID', 'CTG', 'HDB', 'TPB', 'VND', 'HCM', 'KDC', 'DBC']},
    {'tid': 'fin-i5-mem-755', 'split': 'pilot', 'type': 'I5', 'sub': 'exclude',
     'cands': ['SSI', 'VND', 'HCM', 'HPG', 'FPT', 'VNM'],
     'rule': 'Tôi không mua cổ phiếu ngành chứng khoán.', 'allowed': ['HPG', 'FPT', 'VNM']},
]
