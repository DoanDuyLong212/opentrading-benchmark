#!/usr/bin/env python3
"""Bounded NVIDIA-only model discovery and explicit real function-call canary."""
import argparse
import json
from pathlib import Path
import urllib.request
import urllib.error
from runners.provider import credential, NVIDIA_URL, DEFAULT_MODEL


def request(path, body=None):
    req = urllib.request.Request(NVIDIA_URL + path, data=None if body is None else json.dumps(body).encode(),
        headers={'Authorization': 'Bearer ' + credential(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, {'error': 'HTTP error (provider body withheld)'}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, {'error': type(exc).__name__}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='audits/2026-11-04/nvidia-function-probe.json')
    ap.add_argument('--model', default=DEFAULT_MODEL, choices=[DEFAULT_MODEL, 'ibm/granite-3.0-3b-a800m-instruct', 'meta/llama-3.1-8b-instruct', 'qwen/qwen3-4b', 'nvidia/nemotron-3.5-bolt-e4b', 'mistralai/mistral-7b-instruct-v0.3', 'deepseek-ai/deepseek-v4.1-flash'])
    args = ap.parse_args()
    status, catalog = request('/models')
    models = [m['id'] for m in catalog.get('data', [])]
    result = {'provider': 'nvidia', 'catalog_status': status, 'model': args.model,
              'small_candidates': [m for m in models if any(s in m for s in ('3b', '4b', '8b', 'nano'))]}
    if args.model not in models:
        result['error'] = 'requested model absent; no automatic fallback'
    else:
        body = {'model': args.model, 'messages': [{'role': 'user', 'content': 'Call get_quote for ticker FPT. Do not answer from memory.'}],
            'tools': [{'type': 'function', 'function': {'name': 'get_quote', 'description': 'Get frozen stock quote',
                'parameters': {'type': 'object', 'properties': {'ticker': {'type': 'string'}}, 'required': ['ticker']}}}],
            'tool_choice': 'auto', 'max_tokens': 128, 'temperature': 0}
        status, answer = request('/chat/completions', body)
        message = (answer.get('choices') or [{}])[0].get('message', {})
        calls = message.get('tool_calls', [])
        result.update(status=status, response_model=answer.get('model'), usage=answer.get('usage'), calls=calls)
        result['function_call_verified'] = bool(calls and calls[0].get('function', {}).get('name') == 'get_quote' and
            json.loads(calls[0]['function']['arguments']).get('ticker') == 'FPT')
        if result['function_call_verified']:
            body['messages'] += [message, {'role': 'tool', 'tool_call_id': calls[0]['id'], 'content': '{"ticker":"FPT","close":123400,"unit":"VND"}'},
                {'role': 'user', 'content': 'Return only JSON {"value":123400,"unit":"VND"}, using the quote result.'}]
            status2, second = request('/chat/completions', body)
            result['tool_loop'] = {'status': status2, 'usage': second.get('usage'),
                'message': (second.get('choices') or [{}])[0].get('message')}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('function_call_verified') and result.get('tool_loop', {}).get('status') == 200 else 2

if __name__ == '__main__': raise SystemExit(main())
