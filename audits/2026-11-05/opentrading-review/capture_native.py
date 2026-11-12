"""Capture native wire prompts against a LOCAL deterministic mock, no model inference.

This is inspection evidence only, never a benchmark or quality trial. Production
sources, frozen runners, model configuration, and existing receipts are unchanged.
"""
import importlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'tools/runners'), str(ROOT / 'tools')]
import provider

active = {'arm': None, 'requests': []}

class Mock(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        active['requests'].append(body)
        model = body['model']
        text = '{"inspection":"local capture only"}'
        usage = {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}
        if body.get('stream'):
            chunks = [dict(id='local-review', object='chat.completion.chunk', model=model,
                           choices=[dict(index=0, delta={'role': 'assistant', 'content': text}, finish_reason=None)]),
                      dict(id='local-review', object='chat.completion.chunk', model=model,
                           choices=[dict(index=0, delta={}, finish_reason='stop')], usage=usage)]
            payload = (''.join('data: '+json.dumps(c)+'\n\n' for c in chunks)+'data: [DONE]\n\n').encode()
            content_type = 'text/event-stream'
        else:
            payload = json.dumps(dict(id='local-review', object='chat.completion', model=model,
                choices=[dict(index=0, message={'role':'assistant','content':text}, finish_reason='stop')], usage=usage)).encode()
            content_type = 'application/json'
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Mock)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    # Override IN MEMORY only. No provider credential is loaded or transmitted.
    provider.NVIDIA_URL = 'http://127.0.0.1:%d/v1' % server.server_port
    provider.credential = lambda: 'local-mock-review-only'
    summary = {}
    try:
        for arm in ('opentrading', 'opencode', 'dsh'):
            active.update(arm=arm, requests=[])
            task = ROOT / 'tasks/smoke/smoke-quote-01'
            trial = OUT / 'capture' / arm
            ws = trial / 'ws'
            ws.mkdir(parents=True, exist_ok=True)
            instruction = (task / 'instruction.md').read_text()
            (ws / 'instruction.md').write_text(instruction)
            runner = importlib.import_module('run_'+arm)
            result = runner.run(str(ws), instruction, str(task),
                'nvidia/nvidia/nemotron-3.5-bolt-e4b', 120, str(trial/'run.log'),
                {'timeout_s':120, 'effort':'none', 'request_interval_s':0,
                 'mcp_ledger':str(trial/'mcp.jsonl')})
            (trial/'requests.json').write_text(json.dumps(active['requests'], ensure_ascii=False, indent=2))
            (trial/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
            summary[arm] = {'status':result['status'], 'captured_requests':len(active['requests']),
                            'real_model_calls':0, 'usage_is_synthetic':True}
            print(arm, summary[arm], flush=True)
    finally:
        server.shutdown()
        server.server_close()
    (OUT/'capture-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
