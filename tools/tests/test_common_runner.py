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
