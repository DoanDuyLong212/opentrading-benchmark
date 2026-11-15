import json, sys, time, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
n = [0]
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        body = json.dumps({"object":"list","data":[{"id":"mock-model","object":"model"}]}).encode()
        self.send_response(200); self.send_header('content-type','application/json'); self.send_header('content-length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get('content-length',0)))
        n[0]+=1
        open(f"{OUT}/{n[0]:03d}{self.path.replace('/','_')}.json","wb").write(raw)
        try: req=json.loads(raw)
        except Exception: req={}
        text="ok"
        if req.get('stream'):
            self.send_response(200); self.send_header('content-type','text/event-stream'); self.end_headers()
            base={"id":"x","object":"chat.completion.chunk","created":int(time.time()),"model":"mock-model"}
            for ch in [{"index":0,"delta":{"role":"assistant","content":text},"finish_reason":None},{"index":0,"delta":{},"finish_reason":"stop"}]:
                self.wfile.write(b"data: "+json.dumps({**base,"choices":[ch]}).encode()+b"\n\n")
            self.wfile.write(b"data: "+json.dumps({**base,"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}).encode()+b"\n\n")
            self.wfile.write(b"data: [DONE]\n\n"); self.wfile.flush()
        else:
            body=json.dumps({"id":"x","object":"chat.completion","created":int(time.time()),"model":"mock-model","choices":[{"index":0,"message":{"role":"assistant","content":text},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}).encode()
            self.send_response(200); self.send_header('content-type','application/json'); self.send_header('content-length',str(len(body))); self.end_headers(); self.wfile.write(body)
ThreadingHTTPServer(('127.0.0.1',int(sys.argv[1])),H).serve_forever()
