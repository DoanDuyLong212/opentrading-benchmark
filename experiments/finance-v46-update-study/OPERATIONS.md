# V4.5 pause/resume operations

No command below changes a sealed prompt/source/task/grader. Run in this study directory.

```bash
python3 tools/v45_control.py status --out ABSOLUTE_SUPERVISOR_OUTPUT
python3 tools/v45_control.py pause --out ABSOLUTE_SUPERVISOR_OUTPUT
python3 tools/v45_control.py continue --out ABSOLUTE_SUPERVISOR_OUTPUT
python3 tools/v45_supervisor.py --seal ABSOLUTE_SEAL --out ABSOLUTE_SUPERVISOR_OUTPUT --resume
```

Soft pause finishes the current trial (up to registered900s), checkpoints atomically and stops before another trial/model/stage. A root pipeline pause is propagated to the active cohort; continue removes only its propagated flag. You may instead pause one cohort using its output path. A user-written cohort pause is not silently cleared by pipeline continue.

For immediate stop:

```bash
python3 tools/v45_control.py hard-stop --out ABSOLUTE_SUPERVISOR_OUTPUT
```

Hard stop verifies PID start/command and kills only the owned process tree. Resume retains the in-flight attempt as interrupted/DNF with unknown/partial usage, then continues pending scheduled cells; it never restarts that model request or retries the trial for quality. It cannot continue an upstream stream from the middle. Every timeout/interruption stays in primary denominators. Under a different PID namespace the command refuses to signal; run in the same host context as the supervisor. Never manually restart an apparently missing PID without checking state heartbeat/context.

Supervisor always runs an actual completed driver resume under an unconditional execute_trial interceptor after each cohort: zero calls and identical trial/manifest byte+size+mtime proof. Manual review then gates each cohort. At an await_root_*_review boundary use the frozen audit/raw files for independent all-arm review, write `financial-review.json` according to tools/v45_review.py; resume repeats completed driver analysis only. At pilot boundary deliver the reviewed PILOT-REPORT.md metrics to the user, then root writes `pilot-review-approval.json` with manifest_sha256, report_sha256, approved:true, independent_manual_financial_audit_pass:true, report_delivered_to_user:true and reviewer. Main is preauthorized only if the unchanged registered quality gate and this evidence boundary both pass.
