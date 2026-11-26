#!/bin/bash
# Sequential completion: one run at a time. Stops the chain on the first unexpected failure.
B=/home/doanlong/extra/bench-v47-pin/runs/deepinfra-20261125
for n in a-ot a-dsh a-oc a-all b-ot; do
  echo "$(date -Is) start $n" >> $B/chain.log
  $B/$n/run.sh
  rc=$?
  done_n=$(grep -c . $B/$n/run/trials.jsonl 2>/dev/null); sched=$(python3 -c "import json;print(len(json.load(open('$B/$n/run/manifest.json'))['plan']['schedule']))")
  echo "$(date -Is) end $n rc=$rc trials=$done_n/$sched" >> $B/chain.log
  [ "$done_n" = "$sched" ] || { echo "$(date -Is) CHAIN STOPPED at $n" >> $B/chain.log; exit 1; }
done
echo "$(date -Is) CHAIN COMPLETE" >> $B/chain.log
