#!/bin/bash
B=/home/doanlong/extra/bench-v47-pin/runs/deepinfra-20261125
until grep -q "CHAIN COMPLETE\|CHAIN STOPPED" $B/chain.log; do sleep 30; done
grep -q "CHAIN STOPPED" $B/chain.log && { echo "$(date -Is) chain2 not started: chain1 stopped" >> $B/chain.log; exit 1; }
echo "$(date -Is) start b2-ot" >> $B/chain.log
$B/b2-ot/run.sh
n=$(grep -c . $B/b2-ot/run/trials.jsonl 2>/dev/null)
echo "$(date -Is) end b2-ot trials=$n/100" >> $B/chain.log
[ "$n" = 100 ] && echo "$(date -Is) CHAIN2 COMPLETE" >> $B/chain.log || echo "$(date -Is) CHAIN2 STOPPED" >> $B/chain.log
