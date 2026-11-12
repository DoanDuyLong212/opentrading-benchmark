# Gold/task audit — 2026-11-10 (pre-inference, v4.6-update corpus)

Scope: study corpus `experiments/finance-v46-update-study/tasks` (main 230, pilot 25, smoke 3,
devsmoke 12, holdout fin-mem 10, memorydev 2) + root `tasks/holdout` (50 financial, user-approved
review before any holdout inference). Method: (1) all 342 oracles re-run (all OK — only proves
payload⇄gold self-consistency); (2) independent checks from payloads (period ordering, latest
period, row names, resolver emptiness, weekday/holiday, recomputation of every task without an
oracle body: chain-303..306, 2src-302, breadth-301, devsmoke 01-12); (3) manual semantic read of
every question vs gold vs grader behaviour (`tests/grader.py` executed on probe strings).

Verdict: arithmetic of golds is correct everywhere checked. Defects are in **question/grader
alignment**, not numbers. Items marked FIX change scoring; WORDING items are clarifications.

## A. Scoring defects (FIX)

| # | Tasks | Defect | Fix |
|---|---|---|---|
| A1 | pilot fin-l2-tech-01, fin-l3-tech-multi-01, fin-l3-top-01; main fin-l2-tech-162..165, fin-l3-tech-multi-203..207, fin-l3-top-197..202, fin-l4-chain-303; root holdout 916, 917, 927 | `period` must equal 30/10 but the tools (`signals_technical`, `market_movers`) return no session date (only data_time 2026-11-01). Accept list contains "phiên gần nhất"/"gần nhất", but `period_hit` rejects them (date branch requires exact date set). Model cannot derive the date from data. | State the session in the question ("phiên 30/10"), as breadth-301/agg-181..188 already do; shared grader untouched. Root holdout items deferred to holdout migration (C1). |
| A2 | main fin-l5-compare-288, 289, 290 | Asks 5-session % (26/10→30/10) of NG=F/HG=F/BZ=F, but `yf_commodities` has only price/prev (1 session). Gold sym_pct = 1-session change; oracle never checks it. `source` accepts only `vn_msn_fx_gold` although the commodity lives in `yf_commodities`. Unanswerable as written. | Rewrite to 1-session change for both assets (commodity price/prev vs USDVND 30/10 vs 29/10 = +0.0116%), `source` = str_all[yf_commodities, vn_msn_fx_gold], required keys + yf. |
| A3 | main fin-l2-gf-compare-174, 175 | GC=F / SI=F exist only in `yf_commodities`; schema example says `vn_msn_fx_gold`; grader requires BOTH tools (str_all). Correct answer citing yf only fails. | `source` = str `yf_commodities`; schema example fixed. |
| A4 | main fin-l4-2src-257, 258; root holdout 940 | Needs 3 source tools (yf, vn_crypto_ohlcv, USDVND from vn_msn_fx_gold) but grader set-equality demands exactly 2. A model obeying the common v4.6u rule "list every needed source tool" fails. | Accept the 3-tool set; schema example lists 3. |
| A5 | main fin-l3-top-202 | Root 202 asked "5 mã giảm" but gold was volume leaders; migration fixed gold → now an exact duplicate of 201 (double weight). | Rewrite 202 as "5 mã khối lượng khớp lệnh lớn nhất" (HPG, TCB, NVL, VPB, SSI; vol + close). |
| A7 | pilot fin-l2-gold-01; main fin-l2-gf-compare-172..175; root holdout 919 | Found by judge calibration on superseded or9: question asks the change vs the previous session (in `note`); all 3 arms wrote "phiên 30/10/2026 (so với phiên 29/10/2026)" in `period`, rejected by the exact date-set check (3/3 false fails). | Schema example: `period` = asked session only; comparison session goes in `note`. |
| A6 | crypto-multi winner fields (main 208–215, root holdout 928/929, pilot fin-l3-crypto-01) | Winner accept tokens are substring phrases ("dầu", "crude", "gas"); in 211 (BZ=F, NG=F, CL=F) the answer "dầu Brent BZ=F" passes. No reject list → multi-ticker answers pass. | Add `reject` = other tickers in the set (+ "Brent" for CL=F). |

| A8 (open, found in or10 pilot) | any `period` check with a single date (pilot tech-01, tech-multi-01, …) | `period_hit` requires the set of dates in the answer to equal the accepted set; answers "phiên 30/10/2026 (… snapshot 2026-11-01)" are rejected because the snapshot date is counted. Observed 3/3 arms on fin-l3-tech-multi-01 and DSH on fin-l2-tech-01. | Not fixable inside the sealed or10 cohort. For main: either ignore dates explicitly labelled snapshot/as_of in `period_hit`, or state in the schema that `period` holds only the session date. Pilot review reports strict and period-normalized views. |

## B. Wording / ambiguity (clarify; same gold)

| # | Tasks | Issue | Fix |
|---|---|---|---|
| B1 | all instructions | NOTE ONLY. Contract asks ≥6 decimals / abs ≤1e-6 while most golds are 2 dp with tol rel 0.5% / abs 0.05–0.1. Registered v4.6u repair aimed at devsmoke (true abs 1e-6); over-precision can never cause a false fail. | No change. |
| B2 | main fin-l5-profile-261 (CTD) | Payload labels CTD fiscal quarters Q1–Q4/2026 (FY ends June); question says "quý gần nhất: Q4/2026" before calendar Q4 ends → invites a false "future" refusal. | Add: "nhãn kỳ theo niên độ tài chính của nguồn (CTD)". |
| B3 | main fin-l5-compare-285 | BTC 0.5924% vs ETH 0.5936% — equal at 2 dp; winner decided by unrounded value, not stated (214 already states it). | Add the 214 sentence. |
| B4 | main fin-l5-compare-277 | POM ROE 392.86 with negative equity (P/B −2.34) ranked #1 — financially meaningless; a careful analyst may exclude it. | State: rank by the ROE value returned, including anomalies; mention anomaly in note. |
| B5 | main fin-l1-quote-crypto-125, fin-l4-2src-257/258, fin-l5-compare-287; holdout 940 | "close gần nhất" of a 24/7 pair = the open 01/11 daily bar; prior full bar 31/10 differs 0.3–0.9% (257 would fail on 31/10). | Specify "nến ngày mới nhất trong dữ liệu (01/11)". |
| B6 | root holdout fin-l3-top-925 | "%%" format leftovers in question. | Fix text. |
| B7 | main fin-mem-349 | User alias "Vietcap" → HT1 collides with the real company (Vietcap = VCI; HT1 = Vicem Hà Tiên); note calls it "domain-TRUE". | Use a neutral private label. Note cosmetic: fin-mem-345 notes contain stray Cyrillic. |

Any change to `source`/required tools (A2–A5) must regenerate `provenance_contract`,
`provenance_catalog`, `required_payload_keys` and the oracle body with existing tooling, and add
oracle checks for every graded field. Low-risk alternative for A2 and A5: quarantine
(`confirmatory_eligible=false` + `exclusion_reason`) before inference.

Pilot impact: A1 (fin-l2-tech-01, fin-l3-tech-multi-01, fin-l3-top-01) and A6 (fin-l3-crypto-01).
Everything else is main-only.

## C. Methodology

- C1 RESOLVED 2026-11-10 (user chose "replace"): the 11 replicas were rewritten by
  tools/build_holdout_replacements_20261110.py — same ids/payloads, new questions no main task asks
  (921 max/min spread, 922 strict >15k filter, 928/929 new yf trios, 923/924 new P/B filters, 927 max RSI,
  940 1-session % by two sources, 938 ETHUSDT 10-day min/date/range (now eligible value task),
  944/945 P/B and P/E rankings). Oracles OK, synthesized correct pass / mutants fail, 0 holdout
  questions identical to main. Receipt: holdout-replacements.json. Original history below.
- C1 (original) Holdout: 11/50 root holdout questions are verbatim copies of main (921≡181, 922≡182, 928≡208,
  929≡209, 923≡189, 924≡190, 927≡203, 940≡258, 938≡248, 944≡275, 945≡276); others reuse the same
  payload. Root holdout also still uses the old root grader/instructions (md5 d1a4030d), not the
  v4.6u contract. Before any holdout use: migrate to the study contract and replace or separately
  report the 11 replicas.
- C2 README eligible counts (178/43/22/3) are stale; task.toml gives main 183 financial + 30 memory.
- C3 Oracles are generator-coupled; 5 tasks had no oracle body (chain-303..305, 2src-302,
  breadth-301) — verified independently here.

## Verified correct (no change)

bctc (period = last column, line names, hợp nhất = Tổng LNST / LNST thu nhập DN), growth, margin,
ratio, macro GDP (quarterly, not cumulative), index (10 bars 19/10–30/10), agg, screen, top ranks
incl. MSN/BCM tie (−2.9126 vs −2.9077), L4 future (Q4 not ended; 31/10 Sat, 01/11 Sun, 02/09
holiday; HDB/POM lack Q3), nonexist (resolver null + empty candidates), narrative verdicts,
valuation, profile arithmetic, chain/2src recomputation, devsmoke fixtures, fin-mem arithmetic.
