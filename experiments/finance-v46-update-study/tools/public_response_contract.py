"""Uniform caller-visible contract. No task gold or task-ID inference."""
import json
import re
from pathlib import Path
PUBLIC_RESPONSE_CONTRACT = {
    'version':'4.2',
    'refusalSchema':{'type':'object','required':['value','reason','evidence'],
                     'properties':{'value':{'type':'null'},'reason':{'type':'string','minLength':1},
                                   'evidence':{'type':'array'}},'additionalProperties':True},
    'success':'Use the success schema already shown in this public task instruction; evidence is always an array.'}
PUBLIC_CONTRACT_TEXT = '''\n\n## Common public response contract v4.2\nThe final response must be exactly one JSON object. The success shape is the public task example above, with evidence always an array. A legitimate refusal is an alternative branch for EVERY task, including tasks whose success example uses values/ranking/items: {"value":null,"reason":"specific honest reason","evidence":[]}. For refusal omit incompatible nonempty success fields (values/ranking/items). A refusal is a completed response, not a correct numerical answer to an answerable question. An unsupported/rejected query does NOT establish missing financial data; inspect the public allowed request variants and correct only without changing the requested financial meaning. Never invent a receipt. Return only the requested structured numerical fields; do not add unrequested numerical claims. Include every actual successful response receipt needed for your assertion; evidence may be empty only when no successful response supports it. No tool rejection is financial evidence.\nPUBLIC_RESPONSE_CONTRACT_V42=''' + json.dumps(PUBLIC_RESPONSE_CONTRACT,ensure_ascii=False,separators=(',',':')) + '\n'

def append_public_contract(instruction):
    return instruction + PUBLIC_CONTRACT_TEXT


def _shape(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    return 'string'


def public_success_example(instruction):
    """Only the public fenced example is a shape declaration, never hidden gold.

    This intentionally is not a general natural-language schema compiler. Reject
    unsupported/ambiguous declarations explicitly instead of silently dropping them.
    """
    blocks = re.findall(r'```json\s*([\s\S]*?)```', instruction)
    if len(blocks) != 1:
        raise ValueError('Expected exactly one public success JSON example')
    value = json.loads(blocks[0])
    if not isinstance(value, dict):
        raise ValueError('Public success example must be an object')
    return value


def validate_public_response_contract(instruction, final_text, catalog_names=None):
    """Common v4.2 endpoint for every arm; financial/receipt grading is separate.

    Mirrors the native finance policy's public example type/optional/null and
    canonical-source checks. Checks top-level shape, not period/date contents or
    arbitrary nested example values. No task identity, gold or ledger is read.
    """
    errors = []
    try:
        example = public_success_example(instruction)
    except (ValueError, TypeError) as exc:
        return {'valid': False, 'errors': ['unsupported_public_contract: '+str(exc)], 'branch': None}
    try:
        def reject_constant(value):
            raise ValueError('Non-JSON numeric constant: '+value)
        value = json.loads(final_text, parse_constant=reject_constant)
    except (ValueError, TypeError):
        # v4.6-update: a SOLE fenced JSON with whitespace outside is equivalent
        # to the bare object — matches the grounded metric's fence acceptance
        # (the endpoint contract previously enforced the strict bare-object form,
        # killing grounded-acceptable fenced answers from fence-style models).
        value = None
        m = re.fullmatch(r'\s*```(?:json)?\s*(.+?)\s*```\s*', final_text or '', re.S)
        if m:
            try:
                value = json.loads(m.group(1), parse_constant=reject_constant)
            except (ValueError, TypeError):
                value = None
        if value is None:
            return {'valid': False, 'errors': ['Final response must be exactly one JSON object, without markdown or surrounding prose.'], 'branch': None}
    if not isinstance(value, dict):
        return {'valid': False, 'errors': ['Final response must be a JSON object.'], 'branch': None}
    refusal = 'value' in value and value['value'] is None
    if refusal:
        if not isinstance(value.get('reason'), str) or len(value['reason']) == 0:
            errors.append('Refusal requires a nonempty reason string.')
        for field in ('values', 'ranking', 'items'):
            if field in value and value[field] is not None and value[field] != [] and value[field] != {}:
                errors.append('Refusal cannot contain incompatible nonempty success field: '+field)
    else:
        nullable = set(re.findall(r'["`]?([A-Za-z_]\w*)["`]?\s*(?::|=|(?:với|là|as)\s+(?:JSON\s+)?)\s*["`]?null\b', instruction))
        for field, declared in example.items():
            optional = isinstance(declared, str) and re.search(r'tuỳ chọn|tùy chọn|optional', declared, re.I)
            if field not in value:
                if not optional:
                    errors.append('Missing requested field: '+field)
            elif not (value[field] is None and field in nullable) and _shape(value[field]) != _shape(declared):
                errors.append('Requested field has wrong JSON type: '+field+'; expected '+_shape(declared))
        if catalog_names is None:
            catalog = json.loads(Path(__file__).with_name('tool_contracts_v4.json').read_text())
            catalog_names = [item['name'] for item in catalog['tools']]
        names = set(catalog_names)
        source_contract = re.search(r'source[^\n]{0,160}(?:tên tool|tool name|catalog|namespace tool)', instruction, re.I)
        source_contract = source_contract or (isinstance(example.get('source'), str) and example['source'] in names)
        source = value.get('source')
        sources = [s.strip() for s in re.split(r'[,;+|]+', source)] if isinstance(source, str) else source if isinstance(source, list) else []
        if source_contract and not (source is None and 'source' in nullable) and (not sources or any(not isinstance(s, str) or s not in names for s in sources)):
            errors.append('source must use exact registered tool names, not provider names or invented aliases.')
    if not isinstance(value.get('evidence'), list):
        errors.append('Required evidence must be an array.')
    return {'valid': not errors, 'errors': list(dict.fromkeys(errors)), 'branch': 'refusal' if refusal else 'success'}
