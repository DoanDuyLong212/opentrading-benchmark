"""Independent joins for local per-intent rejections; no model/inference."""
import json,re
from pathlib import Path

def verify_v42_local_intent(event,all_events,provider,schemas):
    audit=event.get('financeIntent');local=event.get('localRejection') or {};call_id=event.get('callId')
    if not isinstance(audit,dict) or audit.get('sdk_call_id')!=call_id or not isinstance(audit.get('intent_id'),str):
        raise ValueError('C2 local rejection missing actual per-intent SDK metadata')
    if audit.get('correction_budget')!=1 or audit.get('correction_used') not in (0,1) or audit.get('phase') not in ('initial','correction','bounded_finance_correction','bounded_finance_acquisition'):
        raise ValueError('C2 intent budget/phase invalid')
    name=local.get('tool');original=audit.get('original_sdk_call_id')
    previous=[]
    for prior in all_events:
        if prior is event:break
        previous.append(prior)
    starts={e.get('callId'):e for e in previous if e.get('type')=='tool-start'}
    ends={e.get('callId'):e for e in previous if e.get('type')=='tool-end'}
    if local.get('code')=='invalid_tool_input' and original==call_id and audit['phase']=='initial':return
    reason=local.get('reason','')
    known={
      'Repeated or already pending/successful intent; do not replay this request.',
      'Tool correction exhausted or ineligible; do not replay this request.',
      'Bounded finance correction changed original entity/currency or temporal/financial scope, or targeted an unrelated intent; rejected without execution.',
    }
    if local.get('code')=='policy_guard_rejected' and (reason not in known or audit.get('reason')!=reason):
        raise ValueError('C2 unrecognized local per-intent guard reason')
    bounded=audit['phase']=='bounded_finance_correction'
    acquisition=audit['phase']=='bounded_finance_acquisition'
    phase_wire=False
    acquisition_wire=False
    for request in provider:
        if call_id not in request.get('response_tool_call_ids',[]):continue
        capture=request.get('native_request_capture') or {}
        if capture.get('path'):
            messages=json.loads(Path(capture['path']).read_text()).get('messages',[])
            phase_wire=any(m.get('role')=='user' and 'One bounded correction.' in str(m.get('content','')) for m in messages)
            acquisition_wire=any(m.get('role')=='user' and 'One bounded evidence acquisition opportunity before final.' in str(m.get('content','')) for m in messages)
    if acquisition:
        phases=[e for e in previous if e.get('type')=='finance-phase' and e.get('phase')=='bounded_finance_acquisition' and e.get('transition')=='enter']
        if not acquisition_wire or not phases or name not in phases[-1].get('availableToolNames',[]) or phases[-1].get('toolChoice')!='auto':
            raise ValueError('C2 acquisition phase lacks actual generating request/available-tool proof')
        if local.get('phase')!='bounded_finance_acquisition' or local.get('allowedTools')!=phases[-1].get('availableToolNames'):
            raise ValueError('C2 acquisition rejection differs from declared available-tool phase')
    if bounded and not phase_wire:raise ValueError('C2 bounded phase lacks actual generating request proof')
    if original==call_id:
        # A new unrelated call denied only inside explicit bounded correction.
        # It is a rejected new intent, never a successful correction of an old one.
        if not bounded or 'unrelated intent' not in reason:
            raise ValueError('C2 correction lacks original generated SDK call')
        failed=[e for e in previous if e.get('type')=='tool-end' and e.get('ok') is False
                and starts.get(e.get('callId'),{}).get('name')==name and not e.get('localRejection',{}).get('code')=='policy_guard_rejected']
        if not failed:raise ValueError('C2 unrelated-intent guard lacks actual prior failed tool')
        return
    prior_start=starts.get(original);prior_end=ends.get(original)
    # Duplicate same-batch call may be denied while the original is still pending.
    if not prior_start or prior_start.get('name')!=name:
        raise ValueError('C2 original SDK call absent or tool changed')
    previous_audit=(prior_end or {}).get('financeIntent')
    if previous_audit and (previous_audit.get('intent_id')!=audit['intent_id'] or previous_audit.get('original_sdk_call_id')!=original):
        raise ValueError('C2 local rejection crossed original intent identity')
    if local.get('code')=='invalid_tool_input':
        if not prior_end or prior_end.get('ok') is not False:
            raise ValueError('C2 corrected validation lacks failed original')
        return
    if 'Repeated or already' in reason:
        raw=local.get('rawInput');args=json.loads(raw) if isinstance(raw,str) else raw
        # Compare defaults, normalized selectors, and unordered arrays exactly as
        # public C2 equivalence; do not merely trust native intent_id labels.
        def norm(v):
            if isinstance(v,str):return v.strip().upper()
            if isinstance(v,list):return sorted([norm(x) for x in v],key=lambda x:json.dumps(x,sort_keys=True))
            if isinstance(v,dict):return {k:norm(x) for k,x in v.items()}
            return v
        schema=schemas[name]
        properties=schema.get('properties',{})
        defaults={k:p['default'] for k,p in properties.items() if 'default' in p}
        def scope(value):
            if not isinstance(value,dict):return value
            result={**defaults,**value}
            for field,item in list(result.items()):
                prop=properties.get(field,{})
                branches=[prop]+prop.get('anyOf',[])+prop.get('oneOf',[])
                types={kind for branch in branches for kind in (branch.get('type') if isinstance(branch.get('type'),list) else [branch.get('type')])}
                if re.search(r'symbol|ticker|currency|entity|peers',field,re.I):
                    result[field]=sorted(set(str(x).strip().upper() for x in (item if isinstance(item,list) else [item])))
                elif types & {'integer','number'} and isinstance(item,str) and re.fullmatch(r'[-+]?\d+',item.strip()) and abs(int(item))<=9007199254740991:
                    result[field]=int(item)
                elif 'array' in types and re.fullmatch(r'columns|metrics|statements',field,re.I) and isinstance(item,str):result[field]=[item]
            return norm(result)
        prior_args=prior_start.get('input',{})
        same_scope_starts=[start for start in starts.values() if start.get('name')==name and scope(start.get('input'))==scope(prior_args)]
        if not isinstance(args,dict) or not any(norm({**defaults,**args})==norm({**defaults,**start.get('input',{})}) for start in same_scope_starts):
            raise ValueError('C2 repeated guard arguments differ from original intent')
    elif not prior_end or prior_end.get('ok') is not False:
        raise ValueError('C2 exhausted/ineligible guard lacks original failed execution')
