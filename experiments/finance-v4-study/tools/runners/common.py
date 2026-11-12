"""Bounded subprocess execution; terminate the complete fresh process group."""
import os
import signal
import subprocess
import tempfile


def kill_group(process, sig=signal.SIGKILL):
    # start_new_session makes this group id stable even after its leader exits.
    try:
        os.killpg(process.pid, sig)
    except (ProcessLookupError, PermissionError):
        pass


def popen_run(cmd, cwd, env, timeout_s, log_path, stdin_text=None):
    env = dict(env)
    env['PWD'] = os.path.abspath(cwd)
    # File capture avoids an orphan retaining a PIPE and hanging communicate().
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as stdout, tempfile.TemporaryFile(mode='w+', encoding='utf-8') as stderr:
        process = subprocess.Popen(cmd, cwd=cwd, env=env,
            stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, text=True, start_new_session=True)
        timed_out = False
        try:
            process.communicate(input=stdin_text, timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_group(process)
            try:
                process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
        finally:
            # Native CLI may finish while its MCP child still lives.
            kill_group(process)
        stdout.seek(0)
        stderr.seek(0)
        out, err = stdout.read(), stderr.read()
    with open(log_path, 'w', encoding='utf-8') as log:
        log.write('--- CMD ---\n%s\n\n--- STDOUT ---\n%s\n\n--- STDERR ---\n%s\n' % (' '.join(cmd), out, err))
    return process.returncode, out, err, timed_out
