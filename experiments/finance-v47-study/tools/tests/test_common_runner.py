# -*- coding: utf-8 -*-
"""Test common.popen_run — bất biến: PWD env khớp cwd (opencode resolve directory từ PWD)."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runners"))
from common import popen_run
import tempfile

def test_pwd_matches_cwd(tmp_path):
    cwd = str(tmp_path / "ws"); os.makedirs(cwd)
    log = str(tmp_path / "log.txt")
    rc, out, err, to = popen_run(["pwd"], cwd=cwd, env=dict(os.environ), timeout_s=10, log_path=log)
    assert os.path.realpath(out.strip()) == os.path.realpath(cwd)
    assert to is False and rc == 0

def test_pwd_env_override(tmp_path):
    cwd = str(tmp_path / "ws2"); os.makedirs(cwd)
    log = str(tmp_path / "log2.txt")
    rc, out, err, to = popen_run([sys.executable, "-c", "import os;print(os.environ.get('PWD',''))"],
                                 cwd=cwd, env={"PATH": os.environ["PATH"], "PWD": "/sai/duong/dan"},
                                 timeout_s=10, log_path=log)
    assert out.strip() == cwd, "PWD env phải bị override thành cwd thật"


def test_parent_exit_cannot_leave_pipe_holding_descendant(tmp_path):
    import time
    script = "import subprocess,sys; p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);print(p.pid,flush=True)"
    start = time.monotonic()
    rc, out, err, timed_out = popen_run([sys.executable, '-c', script], str(tmp_path), dict(os.environ), 2, str(tmp_path / 'log'))
    assert time.monotonic() - start < 3
    assert rc == 0 and not timed_out
    child = int(out.strip())
    proc = '/proc/%d/stat' % child
    # It may briefly remain a zombie waiting for init to reap it.
    for _ in range(100):
        if not os.path.exists(proc) or open(proc).read().split()[2] == 'Z': break
        time.sleep(0.01)
    else: raise AssertionError('descendant survived the runner process group cleanup')
