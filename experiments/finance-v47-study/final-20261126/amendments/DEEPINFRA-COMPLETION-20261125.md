# Amendment 2026-11-25 ~23:00: single-run completion with v4.6u reuse and DeepInfra (owner decision)

Owner: "Tôi cần gấp nên review lại các task hiện tại và các task cũ đã chạy benchmark lần trước, thực hiện gộp,
OT sẽ dùng host deepinfra để chạy nốt, còn oc và dsh lấy bản đó gộp vào ..." and chose "1 lượt + thay 23 task".
Supersedes the two-replicate design and the shard plan. Registered before any trial below and before reading any
per-task v4.6u outcome. Composition file: FINAL-COMPOSITION-20261125.json.

## Final benchmark: 200 tasks x 3 arms x 1 run (stratum counts unchanged: compute 69, investor 36, lookup 30,
## memory 51, robustness 14)
1. 173 tasks: v4.7 replicate 1 (main-20261124, Pearl Research).
2. 4 tasks without replicate 1 (fin-c3-volshare-442, fin-l4-chain-657, fin-m2-port-548, fin-m5-revoke-545):
   v4.7 replicate 2 from main-20261124-shard2 (Pearl).
3. 4 tasks with no v4.6u equivalent (fin-i3-risk-725, fin-r1-call-775, fin-r1-call-778, fin-s2-times10-480):
   v4.7, all three arms on DeepInfra (run deepinfra-20261125/a-all).
4. 5 same-name tasks in their v4.6u versions (fin-c2-ann-414, fin-l4-2src-260, fin-l4-chain-305,
   fin-m4-port-525, fin-m5-revoke-530) and 14 replacement v4.6u tasks chosen by a fixed rule (same family, else
   same stratum; lowest sorted id): OC/DSH = v4.6u main run 1 (financial-v46u-main-final-or16-20261111, never the
   better of its two runs); OT = deepinfra-20261125/b-ot on the identical task files (supp tree), same per-task
   grader as the v4.6u arms. Public response contract and time-context preamble verified identical.
5. 14 single-run trials voided by the pre-registered infra rules (transport; infra-caused local limits) are
   re-run on DeepInfra per arm (a-dsh 5, a-oc 6, a-ot 3). The voided originals stay archived.
All other v4.7 replicate-2 trials (main indices >= 600 and the other 20 shard trials) are diagnostics only.

## Disclosed confounds
- Host: Pearl Research fp8 (sets 1-2) vs DeepInfra fp8 variants (sets 3-5, 45 trials).
- Set 4 compares OT v4.7 (runtime ae7ec48, Docker shell sandbox, clock shim) against OC 2.1.2 / DSH 0.2.1-rc.2
  from v4.6u (no sandbox, token cap 3.6M, timeout 240 s, host unpinned). Reported as a separate block.
- v4.6u answers survive only as excerpts: set 4 is scored by the deterministic per-task grader for all three
  arms (strict success) and kept out of the Haiku-primary pool.

## Addendum 2026-11-25 ~23:40: final 300-task benchmark (owner: "dùng cách 2 ... loại bỏ các tasks trùng lặp",
## then "cắt thẳng về 300 tasks đi, loại một số tasks tra cứu quá dễ đi")
- Block A = the 200 v4.7 tasks above (600 trials, 1 run).
- Block B = v4.6u tasks not duplicated in block A: 200 old tasks minus 62 duplicates (19 already in block A as old
  versions, 43 same-name as a v4.7 task) = 138, minus 38 easiest lookups by an outcome-blind rule (every L1, then L2
  by sorted id; level label from task.toml) = 100 tasks (lookup 82, compute 10, memory 8). See BLOCK-B-300-20261125.json.
  OC/DSH = v4.6u run 1; OT = new run on DeepInfra (deepinfra-20261125/b2-ot, supp2 tree with identical old task files).
- Total 300 tasks x 3 arms x 1 run = 900 trials. Primary report = block A; block B and the pooled 300 are reported
  separately (block B is lookup-heavy and mixes harness generations).
- The 2-of-2 stability metric is dropped from the primary results (one run per task per arm).
- Next (owner): rerun the same 300 tasks with google/gemma-4-26b-a4b-it:free after this completes.
