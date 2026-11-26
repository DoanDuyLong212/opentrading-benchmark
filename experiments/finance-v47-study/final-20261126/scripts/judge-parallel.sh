#!/bin/bash
set -u
B=/home/doanlong/extra/bench-v47-pin/runs/deepinfra-20261125
E=/home/doanlong/extra/bench-v47-pin/experiments
L=$B/judge-logs
set -a; . /home/doanlong/extra/benchmark/.env; set +a
export HTTPS_PROXY=http://127.0.0.1:25360 https_proxy=http://127.0.0.1:25360 NO_PROXY=localhost,127.0.0.1,::1 no_proxy=localhost,127.0.0.1,::1
export JUDGE_MODEL=anthropic/claude-haiku-5.5
export JUDGE_MAX_USD=10
run() { echo "[$(date -Is)] start $*" >> "$L/jobs.log"; "$@" >> "$L/jobs.log" 2>&1; echo "[$(date -Is)] exit $? $*" >> "$L/jobs.log"; }
(
  cd "$E/finance-v47-study" || exit 1
  run python3 tools/grade_run_llm.py "$B/../main-20261124/run" --resume
  run python3 tools/grade_run_llm.py "$B/../main-20261124-shard2/run" --resume
) > "$L/job1.log" 2>&1 &
P1=$!
(
  cd "$E/finance-v47-study" || exit 1
  for d in a-ot a-dsh a-oc a-dsh2 a-all; do run python3 tools/grade_run_llm.py "$B/$d/run" --resume; done
) > "$L/job2.log" 2>&1 &
P2=$!
(
  cd "$E/finance-v47-supp" || exit 1
  run python3 tools/grade_run_llm.py "$B/b-ot/run" --resume
  cd "$E/finance-v47-supp2" || exit 1
  run python3 tools/grade_run_llm.py "$B/b2-ot/run" --resume
) > "$L/job3.log" 2>&1 &
P3=$!
(
  cd "$E/finance-v46-update-study" || exit 1
  run python3 tools/grade_run_llm.py "$B/old-v46u-selected/run" --resume
) > "$L/job4.log" 2>&1 &
P4=$!
wait $P1 $P2 $P3 $P4
echo "[$(date -Is)] parallel phase done" >> "$L/jobs.log"
touch "$B/JUDGE-PARALLEL-DONE"
