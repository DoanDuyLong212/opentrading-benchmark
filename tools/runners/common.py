# -*- coding: utf-8 -*-
"""Dùng chung cho các runner: chạy subprocess có timeout + kill cả process group."""
import os
import signal
import subprocess


def popen_run(cmd, cwd, env, timeout_s, log_path, stdin_text=None):
    """Chạy cmd; ghi stdout+stderr vào log_path; trả (rc, stdout, stderr, timed_out)."""
    with open(log_path, "w", encoding="utf-8") as log:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             start_new_session=True)
        timed_out = False
        try:
            out, err = p.communicate(input=stdin_text, timeout=timeout_s)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                p.kill()
            out, err = p.communicate()
            rc = p.returncode
        log.write("--- CMD ---\n%s\n\n--- STDOUT ---\n%s\n\n--- STDERR ---\n%s\n" % (
            " ".join(cmd), out or "", err or ""))
    return rc, out or "", err or "", timed_out
