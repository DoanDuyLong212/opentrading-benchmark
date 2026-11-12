"""Independent raw-output contract regressions; no inference or implementation edits."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'experiments/finance-v43-study'
sys.path.insert(0,str(STUDY/'tools'))
from public_response_contract import append_public_contract,validate_public_response_contract,public_success_example

instruction=append_public_contract((STUDY/'tasks/smoke/smoke-quote-01/instruction.md').read_text())
good={'value':123.45,'unit':'nghìn đồng','period':'phiên 2026-10-30','source':'vn_quote_history','evidence':[]}
cases=[]
def add(label,value,wanted,raw=False):
    result=validate_public_response_contract(instruction,value if raw else json.dumps(value,ensure_ascii=False),['vn_quote_history'])
    cases.append({'label':label,'expected':wanted,**result})
add('public success shape with arbitrary ungraded numeric value',good,True)
for field in ['period','source','evidence']:
    value=copy.deepcopy(good);value.pop(field);add('missing '+field,value,False)
for field,value in [('period',20261030),('value',True),('evidence',{}),('source','vnstock'),('source','mcp__opentrading__vn_quote_history'),('source','stock_overview')]:
    changed=copy.deepcopy(good);changed[field]=value;add('wrong '+field+': '+repr(value),changed,False)
add('markdown fence','```json\n'+json.dumps(good)+'\n```',False,True)
add('surrounding prose','Answer: '+json.dumps(good),False,True)
add('two objects',json.dumps(good)+json.dumps(good),False,True)
add('surrounding whitespace',' \n'+json.dumps(good)+'\n ',True,True)
add('public refusal branch',{'value':None,'reason':'Specific honest reason.','evidence':[]},True)
add('refusal missing reason',{'value':None,'evidence':[]},False)
add('refusal mixed financial success',{'value':None,'reason':'Absent.','evidence':[],'values':{'VCB':999}},False)
inventory=[]
for path in sorted((STUDY/'tasks').glob('*/*/instruction.md')):
    try:example=public_success_example(append_public_contract(path.read_text()))
    except Exception as exc:inventory.append({'path':str(path.relative_to(STUDY)),'error':str(exc)})
errors=[case for case in cases if case['valid']!=case['expected']]
result={'pass':not errors and not inventory,'cases':cases,'errors':errors,
        'public_instruction_count':len(list((STUDY/'tasks').glob('*/*/instruction.md'))),
        'unsupported_public_instructions':inventory,
        'source_sha256':hashlib.sha256((STUDY/'tools/public_response_contract.py').read_bytes()).hexdigest()}
Path(__file__).with_suffix('.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='cases'},ensure_ascii=False))
sys.exit(0 if result['pass'] else 1)
