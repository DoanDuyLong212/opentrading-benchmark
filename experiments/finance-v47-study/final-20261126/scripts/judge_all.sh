#!/bin/bash
# Haiku 5.5 judge (key OPENROUTER_KEY = judge key) + judge_primary for every run feeding the 300-task table.
set -a; . /home/doanlong/extra/benchmark/.env; set +a
export HTTPS_PROXY=http://127.0.0.1:25360 https_proxy=http://127.0.0.1:25360 NO_PROXY=localhost,127.0.0.1,::1
R=/home/doanlong/extra/bench-v47-pin/runs; E=/home/doanlong/extra/bench-v47-pin/experiments
L=$R/deepinfra-20261125/judge.log
for pair in "finance-v47-study $R/main-20261124/run" "finance-v47-study $R/main-20261124-shard2/run" \
            "finance-v47-study $R/deepinfra-20261125/a-ot/run" "finance-v47-study $R/deepinfra-20261125/a-dsh/run" \
            "finance-v47-study $R/deepinfra-20261125/a-oc/run" "finance-v47-study $R/deepinfra-20261125/a-dsh2/run" \
            "finance-v47-study $R/deepinfra-20261125/a-all/run" "finance-v47-supp $R/deepinfra-20261125/b-ot/run" \
            "finance-v47-supp2 $R/deepinfra-20261125/b2-ot/run"; do
  set -- $pair
  echo "$(date -Is) judge $2" >> $L
  (cd $E/$1 && python3 tools/grade_run_llm.py $2 --batch 5 --resume >> $L 2>&1) || echo "$(date -Is) JUDGE FAIL $2" >> $L
  (cd $E/$1 && python3 tools/judge_primary.py $2 >> $L 2>&1) || echo "$(date -Is) PRIMARY FAIL $2" >> $L
done
echo "$(date -Is) JUDGE ALL DONE" >> $L
