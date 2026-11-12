"""Eight bounded first-response NVIDIA prompt ablations; not harness scores.

Only system text changes between conditions. The captured OpenTrading user
message (including its clock) and tool schema stay identical. No holdout calls.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'tools/runners'), str(ROOT/'tools')]
from provider import credential, NVIDIA_URL, DEFAULT_MODEL
from mcp_snapshot_server import load_entries, select_entry

FORMAT = '''
Ngoại lệ cho đầu ra có cấu trúc: khi người dùng yêu cầu JSON hoặc schema cụ thể,
hãy tuân thủ chính xác schema đó. Các quy tắc văn xuôi, bảng, đổi đơn vị hiển thị,
không dán JSON và không nêu tên tool chỉ là mặc định cho hội thoại thường;
không được ghi đè định dạng, đơn vị hay evidence mà người dùng yêu cầu.
'''
RECOVERY = '''
Quy tắc thực thi tool: đọc toàn bộ mô tả và mẫu request trước khi gọi. Khi mô tả
liệt kê snapshot_requests, dùng đúng một mẫu được hỗ trợ; không tự thêm tham số
tùy chọn để suy diễn cách lấy dữ liệu. Lỗi tham số hoặc request không được ghi
nhận không chứng minh dữ liệu không tồn tại. Sửa request theo mô tả rồi gọi lại.
Chỉ kết luận thiếu dữ liệu từ kết quả hợp lệ; không tự tạo provenance hay evidence.
'''

def main():
    source = json.loads((OUT/'capture/opentrading/requests.json').read_text())[0]
    original = source['messages'][0]['content']
    dsh = json.loads((OUT/'capture/dsh/requests.json').read_text())[0]['messages'][0]['content']
    systems = {'native':original, 'format_exception':original+'\n'+FORMAT,
               'tool_contract':original+'\n'+RECOVERY, 'dsh_system_only':dsh}
    entries, _ = load_entries(ROOT/'tasks/smoke/smoke-quote-01/environment/payloads.json')
    key = credential()
    rows = []
    total = 0
    dest = OUT/'prompt-ablation'
    dest.mkdir(exist_ok=True)
    for run in (1, 2):
        # Reverse order in the second repetition to limit ordering confounding.
        names = list(systems) if run == 1 else list(reversed(systems))
        for condition in names:
            if len(rows) >= 8 or total + 5500 > 48000:
                raise RuntimeError('diagnostic request/token budget exhausted')
            body = copy.deepcopy(source)
            body.update(model=DEFAULT_MODEL, stream=False, temperature=0, top_p=1, max_tokens=1024)
            body.pop('stream_options', None)
            body['messages'][0]['content'] = systems[condition]
            stem = '%s-r%d' % (condition, run)
            (dest/(stem+'-request.json')).write_text(json.dumps(body, ensure_ascii=False, indent=2))
            started = time.monotonic()
            request = urllib.request.Request(NVIDIA_URL+'/chat/completions', data=json.dumps(body).encode(),
                headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json',
                         'User-Agent':'vn-finance-benchmark-prompt-review/1'})
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = json.load(response)
            (dest/(stem+'-response.json')).write_text(json.dumps(raw, ensure_ascii=False, indent=2))
            usage = raw.get('usage') or {}
            if not all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('prompt_tokens','completion_tokens')):
                raise RuntimeError('unknown upstream usage; stopping diagnostics')
            total += usage['prompt_tokens']+usage['completion_tokens']
            if raw.get('model') != DEFAULT_MODEL:
                raise RuntimeError('provider model mismatch')
            message = raw['choices'][0]['message']
            calls = message.get('tool_calls') or []
            inspected = []
            for call in calls:
                f = call['function']
                args = json.loads(f['arguments'])
                try:
                    match, _ = select_entry(entries, f['name'].removeprefix('mcp__opentrading__'), args)
                    valid = True
                except (ValueError, KeyError):
                    match, valid = None, False
                inspected.append({'name':f['name'], 'arguments':args, 'replayable':valid, 'entry':match})
            row = {'condition':condition, 'run':run, 'usage':usage,
                   'seconds':round(time.monotonic()-started,3), 'calls':inspected,
                   'text':message.get('content'), 'finish_reason':raw['choices'][0].get('finish_reason'),
                   'system_sha256':hashlib.sha256(systems[condition].encode()).hexdigest(),
                   'user_sha256':hashlib.sha256(json.dumps(body['messages'][1:],sort_keys=True).encode()).hexdigest(),
                   'tools_sha256':hashlib.sha256(json.dumps(body['tools'],sort_keys=True).encode()).hexdigest()}
            rows.append(row)
            (dest/'summary.json').write_text(json.dumps({'kind':'first-response prompt diagnostic; not native harness evaluation',
                'model':DEFAULT_MODEL,'rows':rows,'total_tokens':total},ensure_ascii=False,indent=2))
            print(condition, run, inspected, flush=True)
            time.sleep(2)

if __name__ == '__main__':
    main()
