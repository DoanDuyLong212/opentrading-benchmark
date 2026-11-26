# Amendment 2026-11-25: two-stream execution (replicate-2 tail shard)

Owner decision (chat, 2026-11-25): "Đồng ý và watcher đặt theo dõi thường xuyên hơn ngừa limit liên tục"
in reply to the two-stream plan. Registered BEFORE the first shard trial.

## Split
- Main `runs/main-20261124/run` (seal `main-20261124/seal.json`, unchanged code/manifest) executes its frozen
  schedule only up to index S = 837 (exclusive): the rest of replicate 1 (indices < 600) plus the replicate-2
  blocks of the first m = 79 tasks in main's replicate-2 order (indices 600..836).
- Shard `runs/main-20261124-shard2/run` (seal `main-20261124-shard2/seal.json`, approval V47-MAIN-20261125-SHARD2)
  executes replicate 2 of the remaining 121 tasks (`SHARD-SPLIT.json` `shard_tasks`, main replicate-2 order
  positions 79..199), `--runs 1`, seed 20261104 (its own seeded task order and arm permutations), 363 trials.
- Same code (42 protected files, identical hashes), harnesses, protocol, task fingerprints, model, host pin
  (Pearl Research), key (OPENROUTER_KEY_2), network path (NETWORK-PATH-20261125.md), timeouts and caps.
  Only the paid receipt/allocation and budget differ (shard cap 2.9; main cap 6 unchanged).

## Identity and merge
- A shard trial `<task>__<arm>__r1` is replicate 2 of `<task>` for `<arm>`. Main's `__r2` ids at indices
  >= 837 are never executed by main.
- Each directory is graded separately; the merge relabels shard `__r1` -> `__r2` in the analysis table only.
  No row is ever written into another run's trials.jsonl.

## Guards
- A detached boundary guard pauses main so that it never starts index >= 837 (including after re-runs of
  voided trials). Overshoot rule: if main ever executes an index >= 837, main's copy of that trial is void and
  the shard's copy counts.
- The transport-void rule (VOID-RECEIPT-20261125) applies to both directories, plus one final sweep each.
- If the shard sees OpenRouter 402 in_flight_budget_exhausted or repeated 429/529, only the shard is paused
  and execution falls back to one stream (main continues; leftover shard trials resume later).

## Notes
- Concurrency check: per-attempt HOME/XDG/TMPDIR/ot-home/dsh-home, dynamic ports, randomly named shell
  containers with per-attempt mounts; only the 2 s inter-request rate lock is shared (intended).
- Latency metrics are slightly noisier under two streams; both streams interleave all three arms.

## Addendum 2026-11-25 19:10: infra-caused local-limit failures (registered before any sweep)
Observed after two streams: Pearl upstream 429 ("temporarily rate-limited upstream") 4/232 requests (1.7%) vs
3/2509 (0.12%) single-stream. Gateway retries recover most, but each failed transport attempt reserves
failed_attempt_token_reservation (1441792) tokens and counts as an upstream attempt.
Rule (mechanical, outcome-blind, all arms): in the final sweep a non-ok trial is ALSO voided and re-run when its
terminal provider row is `local_token_budget_exhausted` or `upstream_attempt_cap_exceeded` AND the limit would not
have been reached without the trial's failed upstream_transport attempts (429/529/5xx), i.e.
  token case: observed usage tokens + next-attempt reservation <= max_total_tokens when the failed-attempt
              reservations are removed;
  cap case:   (upstream attempts - failed transport attempts) < max_requests (48 for memory tasks, 24 otherwise).
Applies to both main and shard, including trials before this note. Pure agent overruns stay recorded failures.
Watcher: if 429/529 >= 3% of requests (and >= 5 events) in the last 30 min, the shard is paused (one stream).

## Addendum 2026-11-25 22:30: shard cancelled by owner ("Huỷ luồng phụ đi, từ giờ chỉ chạy 1 luồng thôi")
- The shard (main-20261124-shard2) is cancelled after 24/363 trials; it will not be resumed. Its 24 trials
  (journal ~$0.19) are excluded from the confirmatory analysis and kept as diagnostics only.
- The boundary guard is stopped: main runs its complete frozen schedule (all 1200 trials, both replicates)
  in a single stream. The merge/relabel rule above no longer applies.
- The infra-caused local-limit void rule (19:10 addendum) and the transport-void rule still apply to main.
- If main's journal cap ($6) is reached before completion, the leftover trials run afterwards (never in
  parallel) in a separately sealed continuation run, per the owner's 18:50 instruction.

## Addendum 2026-11-25 22:45: shard kept, executed sequentially (supersedes the 22:30 cancellation)
Owner: "Ở luồng phụ những trial nào chạy thành công thì giữ lại, tránh chạy lại lãng phí".
- One stream at a time: main runs to S = 837 (boundary guard restarted), then the shard continues its remaining
  339 trials. Never both alive at once (watch3.py refuses and pauses).
- ALL 24 recorded shard trials are kept (23 ok + 1 failure). Keeping only successes and re-running failures would
  be outcome-dependent selection; the only re-runs are the pre-registered infra rules (transport void and the
  19:10 infra-caused local-limit rule), applied identically to main and shard.
- The split, identity, merge/relabel and overshoot rules of this amendment apply again.
