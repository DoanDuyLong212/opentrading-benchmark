"""Reference-guided LLM judge (secondary, diagnostic metric).

Rewritten 2026-11-10 after the gold audit. The previous version cached verdicts by
the first 200 prompt characters (the task header), so every trial of a task got
the first trial's verdict; it also referenced undefined names, saw only the first
question line and only gold['solution'] (refusal tasks looked like {"query":...}).

Design (MT-Bench reference-guided single-answer grading; FinanceBench-style value
tolerance):
  * Judge model: OpenRouter ``nvidia/nemotron-3-ultra-550b-a55b`` (different family
    from the DeepSeek agent under test), temperature 0.
  * Judge sees the full public question + answer schema, the scoring type, every
    expected field with its tolerance/accept/reject lists, refusal tokens, verdict
    tokens and the gold notes, plus the full final answer text.
  * A deterministic numeric pre-pass (same tolerance rule as tests/grader.py) is a
    separate signal; it never overrides the judge or the sealed grader.
  * Cache key = sha256(model + system + user prompt); persisted by the caller.
The judge is a secondary metric: it may flag a sealed pass for manual review, it
never rescues a sealed failure. Gold is never shown to the agent under test.
"""
import hashlib
import json
import os
import re
import time
import http.client
import urllib.error
import urllib.request
from pathlib import Path

JUDGE_MODEL_PAID = 'nvidia/nemotron-3-ultra-550b-a55b'
# User 2026-11-10: use the free variant (same checkpoint family, free_model_daily_requests quota)
# until exhausted; on quota/rate-limit errors the call falls back to the paid id.
JUDGE_MODEL = os.environ.get('JUDGE_MODEL', JUDGE_MODEL_PAID + ':free')
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
PRICE_PER_1M = {'prompt_usd': 0.6, 'completion_usd': 2.4,
                'source': 'OpenRouter /api/v1/models 2026-11-10'}
MAX_ANSWER_CHARS = 24000
VERDICTS = ('correct', 'partial', 'incorrect')

SYSTEM = (
    'Bạn là giám khảo tài chính độc lập, chấm một câu trả lời so với ĐÁP ÁN CHUẨN (gold) của benchmark '
    'hỏi đáp tài chính trên snapshot dữ liệu đóng băng ngày 2026-11-01. Gold được tính từ dữ liệu snapshot; '
    'coi gold là đúng, không dùng kiến thức thị trường bên ngoài.\n'
    'Chỉ đánh giá NỘI DUNG: giá trị số của từng trường được hỏi (trong tolerance cho sẵn), đơn vị và quy mô '
    '(đồng/nghìn đồng/tỷ đồng, %, lần), kỳ/ngày, mã/thứ hạng/tập hợp, kết luận đúng/sai, và tính đúng của việc '
    'từ chối: với scoring=refusal, câu trả lời ĐÚNG khi đặt value null và nêu lý do dữ liệu không có/chưa công bố; '
    'đưa ra con số cho đại lượng được hỏi là SAI (bịa số). Với câu có đáp án, từ chối là SAI.\n'
    'Cách đọc ĐÁP ÁN CHUẨN: mỗi danh sách accept/reject là các CÁCH VIẾT TƯƠNG ĐƯƠNG, chỉ cần khớp MỘT phần tử về nghĩa '
    '(không cần chứa mọi phần tử). Ngày/kỳ cùng giá trị nhưng khác định dạng là ĐÚNG (30/10/2026 = 30/10 = 2026-10-30; '
    'Q3/2026 = quý 3/2026). Chỉ chấm các trường có trong expected_fields (cùng value/refusal theo scoring); trường không có '
    'trong expected_fields (ví dụ period khi gold không kiểm period) thì bỏ qua.\n'
    'BỎ QUA hoàn toàn: định dạng (markdown, code fence, chữ bao quanh), thứ tự trường, trường evidence/receipt, '
    'tên tool trong source, và ghi chú thừa không mâu thuẫn. Không phạt làm tròn nằm trong tolerance.\n'
    'correct = mọi trường được hỏi đúng; partial = có ít nhất một trường đúng và ít nhất một trường sai/thiếu; '
    'incorrect = còn lại.\n'
    'Kết thúc bằng ĐÚNG MỘT dòng JSON: {"verdict":"correct|partial|incorrect","reason":"<một câu>",'
    '"failed_fields":["<path>", ...]}'
)


# --------------------------------------------------------------------- inputs
def public_question(task_dir):
    """Question + answer schema as shown to the agent, without the shared contract boilerplate."""
    text = (Path(task_dir) / 'instruction.md').read_text(encoding='utf-8')
    return text.split('## Ràng buộc chung')[0].strip()


def gold_reference(gold):
    ref = {'scoring': gold.get('scoring'), 'solution': gold.get('solution')}
    fields = []
    for e in gold.get('expects', []):
        if e.get('path') == 'source' or e.get('type') == 'evidence':
            continue  # tool-name / receipt checks belong to the sealed grader, not content
        item = {k: e[k] for k in ('path', 'type', 'gold', 'tol', 'accept', 'reject') if k in e}
        fields.append(item)
    if fields:
        ref['expected_fields'] = fields
    for k in ('refusal_tokens', 'refusal_assertions', 'bonus_numbers', 'verdict_accept', 'verdict_reject', 'notes'):
        if gold.get(k):
            ref[k] = gold[k]
    return ref


def build_prompt(question, gold, answer_text):
    answer = (answer_text or '').strip() or '(không có câu trả lời)'
    if len(answer) > MAX_ANSWER_CHARS:
        answer = answer[:MAX_ANSWER_CHARS] + '\n...[cắt bớt]'
    return ('CÂU HỎI (nguyên văn, kèm schema trả lời):\n' + question +
            '\n\nĐÁP ÁN CHUẨN (gold, JSON):\n' + json.dumps(gold_reference(gold), ensure_ascii=False, indent=1) +
            '\n\nCÂU TRẢ LỜI CẦN CHẤM:\n' + answer)


# ------------------------------------------------------------ numeric pre-pass
def extract_answer_object(text):
    if not isinstance(text, str):
        return None
    candidates = [text.strip()]
    candidates += re.findall(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
    start = text.rfind('{')
    while start >= 0:
        candidates.append(text[start:])
        start = text.rfind('{', 0, start)
    for c in candidates:
        try:
            obj = json.loads(c)
        except (ValueError, TypeError):
            try:
                obj, _ = json.JSONDecoder().raw_decode(c)
            except (ValueError, TypeError):
                continue
        if isinstance(obj, dict):
            return obj
    return None


def _get(obj, path):
    cur = obj
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def numeric_prepass(answer_text, gold):
    """Per value-field check with the grader's tolerance rule. None = no value fields / no JSON."""
    specs = [e for e in gold.get('expects', []) if e.get('type') == 'value']
    if not specs:
        return None
    obj = extract_answer_object(answer_text)
    if obj is None:
        return {'parsed': False, 'fields': {}, 'all_ok': False}
    fields = {}
    for e in specs:
        v = _get(obj, e['path'])
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            fields[e['path']] = False
            continue
        tol = e.get('tol') or {'rel': 0.005}
        g = float(e['gold'])
        bound = abs(g) * tol['rel'] if 'rel' in tol else tol.get('abs', 0)
        fields[e['path']] = abs(float(v) - g) <= bound + 1e-9
    return {'parsed': True, 'fields': fields, 'all_ok': all(fields.values())}


# ------------------------------------------------------------------- the call
def openrouter_key():
    """Same credential the OpenRouter runner uses (OPENROUTER_KEY, also read from benchmark/.env)."""
    if os.environ.get('OPENROUTER_KEY'):
        return os.environ['OPENROUTER_KEY']
    env_file = Path(__file__).resolve().parents[3] / '.env'
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            m = re.match(r'\s*(?:export\s+)?OPENROUTER_KEY\s*=\s*["\']?([^"\'\s]+)', line)
            if m:
                return m.group(1)
    if os.environ.get('OPENROUTER_API_KEY'):
        return os.environ['OPENROUTER_API_KEY']
    for path in ('~/.opentrading/auth.json', '~/.local/share/opencode/auth.json'):
        try:
            entry = json.loads(Path(path).expanduser().read_text()).get('openrouter', {})
            key = entry.get('key') or entry.get('apiKey')
            if key:
                return key
        except (OSError, ValueError):
            pass
    raise RuntimeError('OpenRouter key missing (OPENROUTER_API_KEY)')


def _post(body, key, timeout):
    req = urllib.request.Request(OPENROUTER_URL, data=json.dumps(body).encode(), headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
        'X-Title': 'snapshot-finance-benchmark-judge'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def parse_verdict(text):
    """Last JSON object that carries a valid verdict (reasoning text may contain other braces)."""
    for m in reversed(list(re.finditer(r'\{[^{}]*"verdict"[^{}]*\}', text or ''))):
        try:
            obj = json.loads(m.group(0))
        except ValueError:
            continue
        verdict = str(obj.get('verdict', '')).strip().lower()
        if verdict in VERDICTS:
            failed = obj.get('failed_fields') if isinstance(obj.get('failed_fields'), list) else []
            return verdict, str(obj.get('reason', ''))[:400], failed
    return None


def call_judge(user, *, model=JUDGE_MODEL, key=None, max_tokens=8000, timeout=300, retries=3, post=_post,
               deny_data_collection=False, system=None, parser=None):
    """Free variant first; on 402/429 (free quota or rate limit) retry once on the paid id.

    deny_data_collection (used for the sealed holdout): paid id only, OpenRouter provider
    preference data_collection=deny, never the free endpoint."""
    if deny_data_collection:
        model = model[:-len(':free')] if model.endswith(':free') else model
        return _call_once(user, model=model, key=key, max_tokens=max_tokens, timeout=timeout, retries=retries,
                          post=post, provider={'data_collection': 'deny'}, system=system, parser=parser)
    result = _call_once(user, model=model, key=key, max_tokens=max_tokens, timeout=timeout, retries=retries, post=post,
                        system=system, parser=parser)
    if model.endswith(':free') and result.get('verdict') == 'judge_error' and result.get('reason') in ('http_402', 'http_429'):
        result = _call_once(user, model=model[:-len(':free')], key=key, max_tokens=max_tokens, timeout=timeout,
                            retries=retries, post=post, system=system, parser=parser)
        result['fallback_from'] = model
    return result


def _call_once(user, *, model, key, max_tokens, timeout, retries, post, provider=None, system=None, parser=None):
    body = {'model': model, 'temperature': 0, 'max_tokens': max_tokens, 'stream': False,
            'messages': [{'role': 'system', 'content': system or SYSTEM}, {'role': 'user', 'content': user}]}
    if provider:
        body['provider'] = provider
    key = key or openrouter_key()
    last_error = None
    for attempt in range(retries + 1):
        try:
            data = post(body, key, timeout)
        except urllib.error.HTTPError as exc:
            last_error = 'http_%d' % exc.code
            if exc.code not in (408, 409, 425, 429, 500, 502, 503, 504) or attempt == retries:
                break
            time.sleep(min(60, 5 * 2 ** attempt))
            continue
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException, ValueError) as exc:
            last_error = type(exc).__name__
            if attempt == retries:
                break
            time.sleep(min(60, 5 * 2 ** attempt))
            continue
        choice = (data.get('choices') or [{}])[0]
        message = choice.get('message') or {}
        text = message.get('content') or ''
        usage = data.get('usage') or {}
        result = {'returned_model': data.get('model'), 'provider': data.get('provider'),
                  'finish_reason': choice.get('finish_reason'), 'usage': usage, 'attempts': attempt + 1}
        if parser is not None:
            batch = parser(text) or parser(message.get('reasoning') or '')
            if batch:
                result.update(verdict='batch', batch=batch)
                return result
            last_error = 'unparseable_batch:' + (choice.get('finish_reason') or '') + ':' + text[-160:]
            result.update(verdict='unparseable', reason=last_error, failed_fields=[])
            if attempt == retries:
                return result
            continue
        parsed = parse_verdict(text) or parse_verdict(message.get('reasoning') or '')
        if parsed:
            result.update(verdict=parsed[0], reason=parsed[1], failed_fields=parsed[2])
            return result
        last_error = 'unparseable:' + (choice.get('finish_reason') or '') + ':' + text[-160:]
        result.update(verdict='unparseable', reason=last_error, failed_fields=[])
        if attempt == retries:
            return result
    return {'verdict': 'judge_error', 'reason': last_error, 'failed_fields': [], 'returned_model': None,
            'usage': {}, 'attempts': retries + 1}


def judge_answer(task_dir, gold, answer_text, *, cache=None, model=JUDGE_MODEL, call=call_judge):
    """Judge one answer. Returns verdict dict incl. cache_key and numeric pre-pass."""
    user = build_prompt(public_question(task_dir), gold, answer_text)
    cache_key = hashlib.sha256((model + '\n' + SYSTEM + '\n' + user).encode()).hexdigest()
    if cache is not None and cache_key in cache:
        result = dict(cache[cache_key], cached=True)
    else:
        result = call(user, model=model)
        result['cached'] = False
        if cache is not None and result.get('verdict') in VERDICTS:
            cache[cache_key] = {k: v for k, v in result.items() if k != 'cached'}
    result['cache_key'] = cache_key
    result['numeric_prepass'] = numeric_prepass(answer_text, gold)
    return result


def usage_cost(usage):
    p = usage.get('prompt_tokens') or 0
    c = usage.get('completion_tokens') or 0
    return p * PRICE_PER_1M['prompt_usd'] / 1e6 + c * PRICE_PER_1M['completion_usd'] / 1e6


# ----------------------------------------------------------------- batched judging (2026-11-11, user)
SYSTEM_BATCH = SYSTEM.rsplit('Kết thúc bằng', 1)[0] + (
    'Bạn nhận NHIỀU MỤC, mỗi mục có id, câu hỏi, đáp án chuẩn và câu trả lời riêng. Chấm TỪNG MỤC ĐỘC LẬP theo đúng '
    'các quy tắc trên; không để mục này ảnh hưởng mục khác.\n'
    'Kết thúc bằng ĐÚNG MỘT dòng JSON: {"results":[{"id":"<id>","verdict":"correct|partial|incorrect",'
    '"reason":"<một câu>","failed_fields":["<path>", ...]}, ...]} với đủ mọi id.'
)
BATCH_ANSWER_CHARS = 8000


def compact_answer(answer_text):
    """The judge ignores evidence/receipts; drop them so a batch fits. Falls back to the raw text."""
    obj = extract_answer_object(answer_text)
    if isinstance(obj, dict):
        obj = {k: v for k, v in obj.items() if k not in ('evidence', 'memory_evidence')}
        text = json.dumps(obj, ensure_ascii=False)
    else:
        text = (answer_text or '').strip()
    text = text or '(không có câu trả lời)'
    return text if len(text) <= BATCH_ANSWER_CHARS else text[:BATCH_ANSWER_CHARS] + '\n...[cắt bớt]'


def parse_batch(text):
    for m in reversed(list(re.finditer(r'\{\s*"results"\s*:', text or ''))):
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[m.start():])
        except ValueError:
            continue
        out = {}
        for r in obj.get('results') or []:
            verdict = str(r.get('verdict', '')).strip().lower()
            if isinstance(r, dict) and verdict in VERDICTS and r.get('id') is not None:
                out[str(r['id'])] = (verdict, str(r.get('reason', ''))[:400],
                                     r.get('failed_fields') if isinstance(r.get('failed_fields'), list) else [])
        if out:
            return out
    return None


def item_key(model, task_dir, gold, answer_text):
    user = build_prompt(public_question(task_dir), gold, compact_answer(answer_text))
    return hashlib.sha256((model + '\nBATCH\n' + SYSTEM_BATCH + '\n' + user).encode()).hexdigest()


def judge_batch(items, *, cache=None, model=JUDGE_MODEL, call=call_judge):
    """items: [(id, task_dir, gold, answer_text)]. One request for all uncached items; any item missing from the
    reply is judged alone with the single-item prompt. Returns {id: result} incl. cache_key and numeric pre-pass."""
    out, todo = {}, []
    for iid, tdir, gold, text in items:
        key = item_key(model, tdir, gold, text)
        if cache is not None and key in cache:
            out[iid] = dict(cache[key], cached=True, cache_key=key)
        else:
            todo.append((iid, tdir, gold, text, key))
    if todo:
        blocks = ['### MỤC id=%s\n%s' % (iid, build_prompt(public_question(tdir), gold, compact_answer(text)))
                  for iid, tdir, gold, text, _ in todo]
        user = ('Chấm %d mục dưới đây.\n\n' % len(todo)) + '\n\n'.join(blocks)
        res = call(user, model=model, system=SYSTEM_BATCH, parser=parse_batch, max_tokens=16000)
        got = res.get('batch') or {}
        meta = {k: res.get(k) for k in ('returned_model', 'provider', 'finish_reason', 'attempts')}
        meta['usage_batch'] = res.get('usage') or {}
        meta['batch_size'] = len(todo)
        for iid, tdir, gold, text, key in todo:
            if iid in got:
                verdict, reason, failed = got[iid]
                r = dict(meta, verdict=verdict, reason=reason, failed_fields=failed, mode='batch')
                if cache is not None:
                    cache[key] = dict(r)
                out[iid] = dict(r, cached=False, cache_key=key)
            else:
                single = judge_answer(tdir, gold, text, cache=cache, model=model,
                                      call=lambda u, model=model: call(u, model=model))
                out[iid] = dict(single, mode='single_fallback')
                if cache is not None and single.get('verdict') in VERDICTS:
                    cache[key] = {k: v for k, v in out[iid].items() if k not in ('cached', 'cache_key', 'numeric_prepass')}
    for iid, tdir, gold, text in items:
        out[iid]['numeric_prepass'] = numeric_prepass(text, gold)
    return out
