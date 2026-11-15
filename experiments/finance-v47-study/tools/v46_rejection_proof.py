"""Negative tool outcomes are accounting proofs, never financial evidence."""
import json

def objects(value):
    stack=[value];seen=set()
    while stack:
        x=stack.pop()
        if isinstance(x,dict):yield x;stack.extend(x.values())
        elif isinstance(x,list):stack.extend(x)
        elif isinstance(x,str) and x not in seen:
            seen.add(x)
            try:v=json.loads(x)
            except ValueError:continue
            if isinstance(v,(dict,list)):stack.append(v)

def rejected_context(content,record):
    expected=record.get('error_code')
    if expected not in ('invalid_request','unsupported_snapshot_query','invalid_derivation'):return False
    for obj in objects(content):
        if obj.get('benchmark_evidence') or obj.get('source_evidence'):return False
        if obj.get('request_rejected') is True and isinstance(obj.get('error'),dict) and obj['error'].get('code')==expected:return True
    # v4.6-update fix: the tool content may prefix the JSON ('Error: {...}');
    # objects() cannot extract embedded JSON from a non-JSON string. Fall back
    # to the authenticated marker pair in the raw tool output itself.
    return 'request_rejected' in content and expected in content

def unknown_context(content,name):
    # Actual native error output. The complete generated tool name must match;
    # typo repair/canonical fuzzy matching would disguise a model error.
    if not isinstance(content,str):return False
    text=content.strip()
    # v4.6-update fix: runtime tool_result error lines may carry an 'Error: '
    # prefix (same prefix class rejected_context already handles); strip only
    # that prefix. The generated tool name must still match completely.
    if text.startswith('Error: '):text=text[len('Error: '):].strip()
    # v4.6-update fix #11 (2026-11-10): OpenCode v2 permission/unknown-tool
    # rejections use this sentence form (pilot fin-l2-crypto-01 OC r2 — the
    # model hallucinated a shell tool outside the sealed inventory).
    sentence=f'No tool named "{name}" is currently available. Please use a tool from the available tool list.'
    if text==sentence:return True
    # fix #11b: the OC arm delivers the denial wrapped in a JSON envelope
    # ({"error":{"type":"tool.execution","message":<sentence>},"content":[]});
    # parse it and require the exact sentence with the exact tool name.
    if text.startswith('{') and 'No tool named' in text:
        try:
            parsed=json.loads(text)
            if isinstance(parsed,dict) and ((parsed.get('error') or {})).get('message')==sentence:return True
        except ValueError:pass
    return text in (
        f'unknown tool "{name}"',f'Unknown tool "{name}"',
        f'Không có tool "{name}".',
    )

def bind_source(bindings,record,proof):
    matches=[]
    for generated in bindings.pending():
        if generated['tool']!=record['tool'] or generated['arguments']!=record['arguments']:continue
        if record.get('started_at'):
            from datetime import datetime
            stamp=datetime.fromisoformat(record['started_at']).timestamp()
            request=generated['request'];rows=bindings.provider
            start=rows[request].get('started_at')
            stop=rows[request+1].get('started_at') if request+1<len(rows) else None
            if not isinstance(start,(int,float)) or stamp<start or (isinstance(stop,(int,float)) and stamp>=stop):continue
        if any(c['id']==generated['id'] and c['tool']==generated['tool'] and c['arguments']==generated['arguments'] and c.get('generation_keys')==[generated['key']] and proof(c) for c in bindings.contexts):matches.append(generated)
    if len(matches)!=1:return None
    g=matches[0]
    return bindings.claim(g['id'],g['tool'],g['arguments'],proof,scope=g['scope'],provider_index=g['provider_index'])


import re as _re
_LOOP = _re.compile(r'^Người dùng dừng vòng lặp: bạn đã gọi (?P<name>\S+) với cùng tham số (?P<count>\d+) lần liên tiếp\. '
                    r'Đừng gọi lại lời gọi này; đổi cách khác hoặc trả lời bằng dữ liệu đã có\.')


def loop_guard_count(content, name):
    """OpenTrading native LoopGuard denial (src/core/tools/loop-guard.ts loopDenied).

    Returns the reported consecutive count when the tool result is exactly that
    native denial for this exact tool name, else None. Accounting proof only:
    a denied call is never executed and never financial evidence.
    """
    if not isinstance(content, str):
        return None
    text = content.strip()
    if text.startswith('Error: '):
        text = text[len('Error: '):].strip()
    m = _LOOP.match(text)
    if not m or m.group('name') != name:
        return None
    count = int(m.group('count'))
    return count if count >= 3 else None


def schema_rejection_context(content, name, arguments):
    """OpenTrading client-side input-schema rejection (AI SDK "Type validation failed") of an MCP tool call.

    Amendment 2026-11-11 (d) audit: the call never reached the MCP server (no ledger row); the native sentence
    names the exact generated tool and echoes the exact rejected value. Accounting proof only, never evidence.
    """
    if not isinstance(content, str):
        return False
    import json as _json
    text = content.strip()
    head = 'Tham số không hợp lệ cho %s: Type validation failed: Value: ' % name
    if not text.startswith(head):
        return False
    rest = text[len(head):]
    try:
        value, _ = _json.JSONDecoder().raw_decode(rest)
    except ValueError:
        return False
    return value == arguments and 'invalid_argument' in rest
