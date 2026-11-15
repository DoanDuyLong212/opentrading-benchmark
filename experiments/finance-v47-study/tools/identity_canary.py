"""v4.6-update identity canary — 3-probe fingerprint per cohort (item 3 decision).

Super endpoint returns a private alias (checkpoint UNVERIFIED per route-v2). This
canary binds each cohort to (a) the exact returned response identity, (b) the
declared context-window behavior, (c) the tool-call wire format — so a silent
checkpoint/route change mid-study stops the cohort instead of contaminating it.
Zero financial content. Run before each cohort; store beside the cohort manifest.
"""
import json, os, sys, time, urllib.request


def probe(key_env, base_url, model, timeout=90):
    key = os.environ.get(key_env, '')
    if not key:
        return {'pass': False, 'error': f'missing env {key_env}'}

    def chat(messages, tools=None):
        body = {'model': model, 'messages': messages, 'temperature': 0, 'max_tokens': 512, 'stream': False}
        if tools:
            body['tools'] = tools
            body['tool_choice'] = 'auto'
        req = urllib.request.Request(base_url.rstrip('/') + '/chat/completions',
                                     data=json.dumps(body).encode(),
                                     headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read().decode())
        return d, time.time() - t0

    out = {'model_requested': model, 'probes': []}

    # P1 identity + minimal latency
    d, dt = chat([{'role': 'user', 'content': 'Reply with exactly: OK'}])
    p1 = {'probe': 'identity', 'wall_s': round(dt, 1), 'response_model': d.get('model'),
          'finish': d['choices'][0].get('finish_reason'),
          'content_ok': d['choices'][0]['message'].get('content', '').strip().endswith('OK'),
          'usage_present': bool(d.get('usage', {}).get('prompt_tokens'))}
    out['returned_model'] = d.get('model')
    out['probes'].append(p1)

    # P2 Vietnamese instruction-following (1 turn, strict one-liner)
    d, dt = chat([{'role': 'user', 'content': 'Trả lời đúng một dòng, không giải thích: 2+2=? (chỉ số)'}])
    out['probes'].append({'probe': 'vn_follow', 'wall_s': round(dt, 1),
                          'content_head': (d['choices'][0]['message'].get('content') or '')[:60]})

    # P3 tool-call wire format (function call round-trip shape)
    tools = [{'type': 'function', 'function': {'name': 'echo_probe', 'description': 'Echo probe tool.',
              'parameters': {'type': 'object', 'properties': {'v': {'type': 'string'}},
                              'required': ['v'], 'additionalProperties': False}}}]
    d, dt = chat([{'role': 'user', 'content': 'Call echo_probe with v="ping"'}], tools=tools)
    tcs = d['choices'][0].get('message', {}).get('tool_calls') or []
    out['probes'].append({'probe': 'tool_wire', 'wall_s': round(dt, 1),
                          'tool_called': bool(tcs) and tcs[0]['function']['name'] == 'echo_probe',
                          'args_ok': bool(tcs) and json.loads(tcs[0]['function']['arguments']).get('v') == 'ping'})

    out['pass'] = all(p.get('content_ok', p.get('tool_called', True)) for p in out['probes'] if 'probe' in p) \
        and bool(out.get('returned_model'))
    return out


if __name__ == '__main__':
    cfg = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
    result = probe(cfg.get('key_env', 'NVIDIA_API_KEY'), cfg.get('base_url', 'https://integrate.api.nvidia.com/v1'),
                   cfg.get('model', 'nvidia/nemotron-3.5-super-vl-120b-a12b'))
    print(json.dumps(result, ensure_ascii=False, indent=1))
    out_path = cfg.get('out')
    if out_path:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        json.dump(result, open(out_path, 'w'), ensure_ascii=False, indent=1)
    sys.exit(0 if result['pass'] else 1)
