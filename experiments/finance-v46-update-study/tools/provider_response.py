"""Strict JSON/SSE response decoding shared by gateway and offline provenance audit."""
import json,re

def response_chunks(payload, *, stream=None):
    text = payload.decode('utf-8-sig') if isinstance(payload, bytes) else payload.lstrip('\ufeff')
    if stream is None:
        first = text.lstrip()
        stream = first.startswith((':', 'data:', 'event:', 'id:', 'retry:'))
    if not stream:
        value = json.loads(text)
        if not isinstance(value, dict): raise ValueError('Provider JSON must be an object')
        return [value]
    chunks=[]; data=[]; done=False
    def event():
        nonlocal data,done
        if not data:return
        value='\n'.join(data);data=[]
        if value=='[DONE]':done=True;return
        if done:raise ValueError('Provider SSE data after DONE')
        item=json.loads(value)
        if not isinstance(item,dict):raise ValueError('Provider SSE data must be an object')
        chunks.append(item)
    lines=re.split(r'\r\n|\r|\n',text)
    if text.endswith(('\r','\n')):lines.pop()
    for line in lines:
        if not line:event();continue
        if line.startswith(':'):continue
        field,sep,value=line.partition(':')
        if sep and value.startswith(' '):value=value[1:]
        if field=='data':data.append(value)
        elif field in ('event','id','retry'):continue
        else:raise ValueError('Unexpected provider SSE field')
    # An unclosed last data event is a truncated provider response, never proof.
    if data:raise ValueError('Unterminated provider SSE event')
    if not chunks:raise ValueError('Provider SSE has no JSON events')
    return chunks
