#!/bin/bash
set -u
B=/home/doanlong/extra/bench-v47-pin/runs/deepinfra-20261125
E=/home/doanlong/extra/bench-v47-pin/experiments
L=$B/judge-logs
set -a; . /home/doanlong/extra/benchmark/.env; set +a
export HTTPS_PROXY=http://127.0.0.1:25360 https_proxy=http://127.0.0.1:25360 NO_PROXY=localhost,127.0.0.1,::1 no_proxy=localhost,127.0.0.1,::1
export JUDGE_MODEL=anthropic/claude-haiku-5.5
export JUDGE_MAX_USD=10

log(){ echo "[$(date -Is)] $*" >> "$L/finalize.log"; }

log "waiting for benchmark and parallel judge"
while [ ! -f "$B/SUPERVISOR.DONE" ] && [ ! -f "$B/SUPERVISOR.ALERT" ]; do sleep 30; done
log "benchmark marker: $(ls "$B"/SUPERVISOR.* 2>/dev/null | tr '\n' ' ')"
while [ ! -f "$B/JUDGE-PARALLEL-DONE" ]; do sleep 30; done
log "parallel judge done"

# catch b2-ot trials that appeared after the parallel snapshot
cd "$E/finance-v47-supp2" || exit 1
log "b2-ot resume judge"
python3 tools/grade_run_llm.py "$B/b2-ot/run" --resume >> "$L/finalize.log" 2>&1 || log "b2-ot judge failed"

log "judge_primary all runs"
cd "$E/finance-v47-study" || exit 1
for d in "$B/../main-20261124/run" "$B/../main-20261124-shard2/run" "$B/a-ot/run" "$B/a-dsh/run" "$B/a-oc/run" "$B/a-dsh2/run" "$B/a-all/run"; do
  log "primary $d"
  python3 tools/judge_primary.py "$d" >> "$L/finalize.log" 2>&1 || log "primary failed $d"
done
cd "$E/finance-v47-supp" || exit 1
log "primary b-ot"
python3 tools/judge_primary.py "$B/b-ot/run" >> "$L/finalize.log" 2>&1 || log "primary failed b-ot"
cd "$E/finance-v47-supp2" || exit 1
log "primary b2-ot"
python3 tools/judge_primary.py "$B/b2-ot/run" >> "$L/finalize.log" 2>&1 || log "primary failed b2-ot"
cd "$E/finance-v46-update-study" || exit 1
log "primary old-v46u"
python3 tools/judge_primary.py "$B/old-v46u-selected/run" >> "$L/finalize.log" 2>&1 || log "primary failed old-v46u"

log "refresh deterministic composition"
cd "$B" || exit 1
python3 final_report.py >> "$L/finalize.log" 2>&1 || log "final_report failed"
log "aggregate haiku report"
python3 final_haiku_report.py >> "$L/finalize.log" 2>&1 || log "final_haiku_report failed"
log "DONE"
touch "$B/HAIKU-FINAL-300-DONE"
