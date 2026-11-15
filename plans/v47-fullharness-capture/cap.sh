#!/bin/bash
# usage: cap.sh <src-root> <home> <outdir>
cp /tmp/claude-1000/-home-doanlong-extra-benchmark/5b5479c8-64e9-4a07-b3f2-4a530a8d4374/scratchpad/fullcap/catalog.json $2/cache/models.json
mkdir -p $3; python3 /tmp/claude-1000/-home-doanlong-extra-benchmark/5b5479c8-64e9-4a07-b3f2-4a530a8d4374/scratchpad/fullcap/mock.py 18434 $3 > /dev/null 2>&1 & MP=$!; sleep 1
cd /tmp/claude-1000/-home-doanlong-extra-benchmark/5b5479c8-64e9-4a07-b3f2-4a530a8d4374/scratchpad/fullcap/otws; OPENTRADING_MODELS_URL=http://127.0.0.1:9/none OPENTRADING_HOME=$2 NVIDIA_API_KEY=tok timeout 120 bun $1/src/index.tsx -p "$(cat /home/doanlong/extra/benchmark/experiments/finance-v46-update-study/tasks/main/fin-c4-rebal-426/instruction.md)" > $3.log 2>&1; echo exit=$?
kill $MP
