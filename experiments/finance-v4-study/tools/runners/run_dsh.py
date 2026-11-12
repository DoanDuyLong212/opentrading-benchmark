"""DSH native headless profile composed from installed core bundles only."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import popen_run
from isolated import prepare, finish, SNAPSHOT

DSH_BIN = os.path.expanduser('~/.local/bin/dsh')
# Explicit allowlist of core services. Bundle updates do not silently add tools.
CORE = {'timer', 'llm', 'session', 'session-log-deepseek', 'typert', 'typert-loader',
 'typert-gateway', 'remote-access', 'session-title', 'agent', 'agent-default-model',
 'deepseek-llm-api-extensions', 'jobs', 'llm-pi-ai', 'session-persistence-jsonl', 'attachment-local', 'session-query-sqlite',
 'session-projection', 'storage', 'storage-json', 'storage-domain',
 'session-projection-cache', 'otel', 'token-meter', 'compaction-basic', 'timeout-policy',
 'spill-local', 'spill-policy', 'session-checkpoint-policy', 'tools', 'system-prompt',
 'agent-loop', 'headless-startup', 'headless-runner'}


def _events(text):
    for line in text.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict): yield event
        except ValueError: pass


def run(ws, instruction, task_dir, model, timeout_s, log_path, options=None):
    options = {**(options or {}), 'timeout_s': timeout_s}
    root, env, gateway, mcp_env = prepare(ws, task_dir, model, options)
    home = root / 'dsh-home'
    profile = home / 'profiles/benchmark'
    profile.mkdir(parents=True, exist_ok=True)
    bundles = ['@deepseek-ai/dsh-base', '@deepseek-ai/dsh-headless']
    (profile / 'package.json').write_text(json.dumps({'name': 'benchmark-isolated', 'private': True,
        'dependencies': {}, 'dsh': {'profile': {'bundles': bundles}}}))
    # Only module resolution is shared, never profiles, settings or plugin lists.
    installed = Path(DSH_BIN).resolve().parent.parent / 'node_modules'
    if not (profile / 'node_modules').exists(): (profile / 'node_modules').symlink_to(installed, target_is_directory=True)
    # Discover shipped entry ids locally and disable everything outside the frozen allowlist.
    # PyYAML cannot parse !!js tags; line-level id extraction is sufficient for bundle rows.
    import re
    ids = []
    for bundle in bundles:
        content = (installed / bundle / 'cordis.patch.yml').read_text()
        ids += re.findall(r'^\s*- id: ([\w-]+)', content, flags=re.M)
    patches = [{'id': name, 'disabled': True} for name in sorted(set(ids) - CORE)]
    patches += [{'id': 'llm-pi-ai', 'config': {'providers': {'nvidia': {'apiKeyEnv': 'NVIDIA_API_KEY',
        'api': 'openai-completions', 'baseURL': gateway.url, 'reasoning': 'off',
        'models': [{'id': gateway.model, 'contextWindow': 32000, 'maxTokens': 2048, 'reasoningEfforts': False}],
        'compat': {'supportsStore': False, 'supportsReasoningEffort': False}}}}},
        {'id': 'agent-default-model', 'config': {'provider': 'nvidia', 'model': gateway.model}},
        {'insert': [{'id': 'mcp-opentrading', 'name': '@deepseek-ai/dsh-mcp-client', 'config': {
            'serverName': 'opentrading', 'transport': 'stdio', 'command': sys.executable,
            'args': [str(SNAPSHOT)], 'env': mcp_env}}]}]
    (profile / 'cordis.patch.yml').write_text(json.dumps(patches, indent=2))
    (profile / 'cordis.yml').write_text('[]\n')
    env.update(DSH_HOME=str(home), NVIDIA_API_KEY=gateway.token, DSH_TELEMETRY_DISABLED='1', DSH_TOOLS_MODE='native')
    with gateway:
        rc, out, err, timed_out = popen_run([DSH_BIN, '--profile', 'benchmark', '--json', '-'],
            cwd=ws, env=env, timeout_s=timeout_s, log_path=log_path, stdin_text=instruction)
    texts, session = [], None
    for event in _events(out):
        if event.get('type') == 'final' and isinstance(event.get('text'), str): texts = [event['text']]
        session = event.get('sessionId') or event.get('session_id') or event.get('sessionID') or session
    return finish(root, gateway, {'status': 'timeout' if timed_out else 'ok' if rc == 0 else 'error',
        'final_text': '\n'.join(texts), 'session_id': session, 'notes': '' if rc == 0 else 'exit=%s' % rc},
        'dsh', {'bundles': bundles, 'core_entries': sorted(CORE), 'patches': patches})
