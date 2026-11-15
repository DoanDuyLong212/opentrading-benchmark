"""Session-bound deterministic arithmetic over actually retrieved public records.

No task IDs, golds, inferred selector, data fetch, expression evaluator, or arbitrary
numeric operands. Source data is never rewritten; upstream receipts remain upstream.
"""
import copy
from decimal import Decimal, localcontext

NAME = 'analytics_compute'
REF = {'type':'object','properties':{'call_id':{'type':'string','minLength':1},'path':{'type':'string','pattern':'^/data/(?:[^~/]|~[01])+(?:/(?:[^~/]|~[01])+)*$' }},'required':['call_id','path'],'additionalProperties':False}
SCHEMA = {'type':'object','properties':{
    'entity_policy':{'type':'string','enum':['same_entity','cross_entity']},
    'operation':{'type':'string','enum':['sum','mean','growth_pct','margin_pct','ratio','scale','absolute_difference','relative_difference_pct']},
    'operands':{'type':'array','items':REF,'minItems':1,'maxItems':100},
    'input_unit':{'type':'string','enum':['VND','nghìn đồng/cổ phiếu','nghìn đồng','VND/cổ phiếu','tỷ đồng','triệu đồng','dimensionless','%']},
    'output_unit':{'type':'string','enum':['VND','nghìn đồng/cổ phiếu','nghìn đồng','VND/cổ phiếu','tỷ đồng','triệu đồng','dimensionless','%']},
},'required':['operation','operands','input_unit','output_unit'],'additionalProperties':False,'x-opentrading-schema-profile':'deterministic-derivation-v45'}
DEFINITION = {'name':NAME,'description':
    'DETERMINISTIC COMPUTATION over numeric leaves from successful source tools ALREADY retrieved in this session. '
    'No data lookup. JSON pointers escape ~ as ~0 and / inside a key as ~1. operands are {call_id: original benchmark_evidence.call_id, path: JSON pointer /data/...}. '
    'Operations: sum/mean equal-unit operands; growth_pct exactly [current,previous] => (current/previous-1)*100; '
    'margin_pct exactly [numerator,denominator] => numerator/denominator*100; scale exactly one operand, '
    'converts VND/nghìn đồng/cổ phiếu/triệu đồng/tỷ đồng. ratio [numerator,denominator] returns dimensionless. absolute_difference [a,b] returns abs(a-b); relative_difference_pct [a,b] returns abs(a-b)/abs(b)*100, for same entity, metric and period across sources. Read actual source units; never mix currencies, dates or metrics. '
    'entity_policy defaults same_entity for ratios; explicit cross_entity permits same-metric same-period ratio across named entities. Aggregates may combine entities. input_unit MUST match source metadata (VND, nghìn đồng/cổ phiếu, triệu đồng, tỷ đồng, dimensionless). '
    'VNDbn normalizes to tỷ đồng; table rows.values align by index with explicit periods. '
    'Returned derived_result is computed, not new upstream evidence: cite ORIGINAL source_evidence seven-field receipts. '
    'If inputs are absent, retrieve source tools first. No indicators/topN/profile capability.',
    'inputSchema':SCHEMA,'annotations':{'readOnlyHint':True,'destructiveHint':False,'idempotentHint':True,'openWorldHint':False}}


def traverse(env,path):
    import re
    if not re.fullmatch(REF['properties']['path']['pattern'],path):raise ValueError('numeric source path requires a nonempty leaf under /data/; inspect retrieved source, for example /data/last only when that numeric field exists')
    node=env;ancestors=[]
    for part in path.split('/')[1:]:
        if re.search(r'~(?![01])',part):raise ValueError('invalid JSON pointer escape')
        key=part.replace('~1','/').replace('~0','~')
        if isinstance(node,dict):ancestors.append(node);
        if isinstance(node,dict) and key not in node:raise ValueError('source pointer key absent: '+key)
        if isinstance(node,dict):node=node[key]
        elif isinstance(node,list):
            if not re.fullmatch(r'0|[1-9][0-9]*',key):raise ValueError('array index must be canonical nonnegative integer')
            node=node[int(key)]
        else:raise ValueError('pointer traverses a scalar')
    if isinstance(node,bool) or not isinstance(node,(int,float)):raise ValueError('source pointer must identify a numeric leaf')
    value=Decimal(str(node))
    if not value.is_finite():raise ValueError('source value must be finite')
    return value,ancestors


def aligned_table(env,path):
    """Explicit public row/column relation; never infer a missing period/unit."""
    _,ancestors=traverse(env,path)
    parts=path.split('/')
    if len(parts)<3 or parts[-2]!='values':return None
    for table in reversed(ancestors):
        periods=table.get('periods');rows=table.get('rows')
        if not isinstance(periods,list) or not isinstance(rows,list):continue
        selected=next((row for row in ancestors if any(row is item for item in rows)),None)
        if selected is None or not isinstance(selected.get('values'),list):continue
        if len(selected['values'])!=len(periods):raise ValueError('table row values and explicit periods must align exactly')
        index=int(parts[-1])
        if not 0<=index<len(periods) or not isinstance(periods[index],str):raise ValueError('table selected period must be explicit text')
        return table,selected,periods[index]
    return None


def unit_for(env,path):
    _,ancestors=traverse(env,path)
    leaf=path.split('/')[-1].replace('~1','/').replace('~0','~')
    candidates=[]
    # Exact field/pointer metadata, or an explicit nearest row unit applying to its values.
    units=env.get('units')
    if isinstance(units,dict):
        candidates=[units[key] for key in (path,leaf) if isinstance(units.get(key),str)]
    rows=[row for row in ancestors if isinstance(row.get('unit'),str)]
    if rows and (any(ancestor is rows[-1].get('values') for ancestor in ancestors) or leaf in ('value','amount')):candidates.append(rows[-1]['unit'])
    aligned=aligned_table(env,path)
    if aligned and isinstance(aligned[0].get('unit'),str):candidates.append(aligned[0]['unit'])
    aliases={'vnd':'VND','đồng':'VND','vndbn':'tỷ đồng','nghìn đồng':'nghìn đồng','nghìn vnd':'nghìn đồng','vndk':'nghìn đồng','vnd/cổ phiếu':'VND/cổ phiếu','vnd/share':'VND/cổ phiếu','đồng/cổ phiếu':'VND/cổ phiếu','%':'%','nghìn đồng/cổ phiếu':'nghìn đồng/cổ phiếu',
'tỷ đồng':'tỷ đồng','triệu đồng':'triệu đồng',
             'dimensionless':'dimensionless'}
    normalized=[aliases.get(item.strip().lower()) for item in candidates]
    if not normalized or None in normalized or len(set(normalized))!=1:
        raise ValueError('explicit unambiguous field unit metadata required for selected source field')
    return normalized[0]


def scope_for(env,path):
    import re
    _,ancestors=traverse(env,path)
    entity=None;period=None;metric=path.split('/')[-1]
    aligned=aligned_table(env,path)
    for row in ancestors:
        for field in ('symbol','ticker','entity','index','country','series','sector'):
            if isinstance(row.get(field),str):entity=row[field].upper()
        for field in ('date','time','t','last_t','period'):
            if isinstance(row.get(field),(str,int)):period=str(row[field])
        if isinstance(row.get('year'),int) and not isinstance(row.get('year'),bool) and isinstance(row.get('quarter'),int) and not isinstance(row.get('quarter'),bool):period='Q'+str(row['quarter'])+'/'+str(row['year'])
        if isinstance(row.get('norm_id'),(str,int)):metric='norm_id:'+str(row['norm_id'])
        elif isinstance(row.get('name'),str) and (isinstance(row.get('values'),dict) or aligned and row is aligned[1]):metric='name:'+row['name']
    leaf=path.split('/')[-1].replace('~1','/').replace('~0','~')
    if re.fullmatch(r'(?:Q[1-4]/[0-9]{4}|[0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?)',leaf):period=leaf
    if aligned:period=aligned[2]
    query=(env.get('_benchmark_request') or {}).get('arguments',{})
    if entity is None:
        query_entity=query.get('symbol') or query.get('ticker')
        if isinstance(query_entity,str):entity=query_entity.upper()
    if period is None and re.fullmatch(r'last|close|open|high|low|price|c|o|h|l|v|volume',leaf,re.I):period=env.get('provenance',{}).get('data_time')
    if period is None:
        year=query.get('year');quarter=query.get('quarter')
        if isinstance(year,int) and not isinstance(year,bool) and 1900<=year<=2200:period=('Q'+str(quarter)+'/' if isinstance(quarter,int) and not isinstance(quarter,bool) and 1<=quarter<=4 else '')+str(year)
        elif isinstance(query.get('period'),str) and re.search(r'[0-9]{4}|TTM|YTD',query['period']):period=query['period']
    return {'entity':entity,'period':period,'metric':metric}


def compute(args,sources):
    import jsonschema
    jsonschema.Draft7Validator(SCHEMA).validate(args)
    operation=args['operation'];refs=args['operands']
    if operation in ('growth_pct','margin_pct','ratio','absolute_difference','relative_difference_pct') and len(refs)!=2:raise ValueError('ratio requires exactly two ordered operands')
    if operation=='scale' and len(refs)!=1:raise ValueError('scale requires exactly one operand')
    if operation in ('sum','mean') and len({(x['call_id'],x['path']) for x in refs})!=len(refs):
        raise ValueError('duplicate source operands rejected')
    values=[];receipts=[];inputs=[];scopes=[]
    for ref in refs:
        if ref['call_id'] not in sources:raise ValueError('source call_id not a successful retrieved call in this session')
        env=sources[ref['call_id']]
        value,_=traverse(env,ref['path'])
        scopes.append(scope_for(env,ref['path']))
        if unit_for(env,ref['path'])!=args['input_unit']:raise ValueError('input_unit differs from explicit source units')
        values.append(value);receipt=env['benchmark_evidence']
        if receipt not in receipts:receipts.append(copy.deepcopy(receipt))
        inputs.append({**ref,'value_decimal':str(value),'unit':args['input_unit'],'source_response_sha256':receipt['response_sha256'],'source_payload_sha256':receipt['payload_sha256']})
    if operation in ('sum','mean','margin_pct','ratio','absolute_difference','relative_difference_pct') and len(values)>1:
        if any(not x['period'] for x in scopes) or len({x['period'] for x in scopes})!=1:
            raise ValueError('selected operands require identical explicit recorded period')
    if operation in ('sum','mean') and len({x['metric'] for x in scopes})!=1:
        raise ValueError('aggregate operands must select the same recorded metric')
    if args.get('entity_policy')=='cross_entity' and operation not in ('sum','mean','ratio'):raise ValueError('cross_entity policy supported for aggregates and explicit same-metric ratio only')
    if operation in ('growth_pct','margin_pct','ratio','absolute_difference','relative_difference_pct'):
        if operation=='ratio' and args.get('entity_policy')=='cross_entity':
            if any(not x['entity'] for x in scopes) or len({x['metric'] for x in scopes})!=1:raise ValueError('cross-entity ratio requires explicit entities and same metric')
        elif any(not x['entity'] for x in scopes) or len({x['entity'] for x in scopes})!=1:
            raise ValueError('ratio operands require same explicit recorded entity')
    if operation=='growth_pct':
        if len({x['metric'] for x in scopes})!=1:raise ValueError('growth operands require same recorded metric')
        if any(not x['period'] for x in scopes) or scopes[0]['period']==scopes[1]['period']:raise ValueError('growth requires two distinct explicit recorded periods; caller orders current then previous')
    if operation in ('absolute_difference','relative_difference_pct') and len({x['metric'] for x in scopes})!=1:raise ValueError('cross-source disagreement requires identical recorded metric')
    explicit_scopes=[]
    for ref in refs:
        _,ancestors=traverse(sources[ref['call_id']],ref['path'])
        found=[str(row[key]).lower() for row in ancestors for key in ('scope','statement_scope','consolidated') if key in row]
        explicit_scopes.append(found[-1] if found else None)
    if len(set(explicit_scopes))>1:raise ValueError('source statement scope mismatch or missing scope')
    with localcontext() as context:
        context.prec=40
        if operation in ('sum','mean'):
            if args['output_unit']!=args['input_unit']:raise ValueError('aggregate output_unit must equal input_unit')
            result=sum(values,Decimal(0));formula='sum(x)'
            if operation=='mean':result/=len(values);formula='sum(x)/count(x)'
        elif operation in ('absolute_difference','relative_difference_pct'):
            if operation=='absolute_difference':
                if args['output_unit']!=args['input_unit']:raise ValueError('difference output unit must match input')
                result=abs(values[0]-values[1]);formula='abs(x[0]-x[1])'
            else:
                if args['output_unit']!='%':raise ValueError('relative difference output unit must be %')
                if values[1]==0:raise ValueError('zero denominator')
                result=abs(values[0]-values[1])/abs(values[1])*100;formula='abs(x[0]-x[1])/abs(x[1])*100'
        elif operation in ('growth_pct','margin_pct','ratio'):
            if args['output_unit']!=('dimensionless' if operation=='ratio' else '%'):raise ValueError('ratio output_unit must be dimensionless for ratio, % for percentage')
            if values[1]==0:raise ValueError('zero denominator')
            if operation=='growth_pct' and values[1]<0:raise ValueError('growth_pct requires positive previous value; negative-base growth convention unspecified')
            result=(values[0]/values[1]-(1 if operation=='growth_pct' else 0))*(1 if operation=='ratio' else 100)
            formula='x[0]/x[1]' if operation=='ratio' else '(x[0]/x[1]-1)*100' if operation=='growth_pct' else 'x[0]/x[1]*100'
        else:
            factors={'VND':Decimal(1),'nghìn đồng':Decimal(1000),'VND/cổ phiếu':Decimal(1),'nghìn đồng/cổ phiếu':Decimal(1000),'triệu đồng':Decimal(1000000),'tỷ đồng':Decimal(1000000000)}
            if args['input_unit'] not in factors or args['output_unit'] not in factors:raise ValueError('scale supports explicit VND, triệu đồng, tỷ đồng only')
            price_units={'nghìn đồng/cổ phiếu','VND/cổ phiếu'}
            if (args['input_unit'] in price_units)!=(args['output_unit'] in price_units):raise ValueError('scale cannot change price per share into currency or reverse; price final VND convention requires derived VND/cổ phiếu')
            result=values[0]*factors[args['input_unit']]/factors[args['output_unit']]
            formula='x[0]*input_VND_factor/output_VND_factor'
    import math
    if not result.is_finite() or not math.isfinite(float(result)):raise ValueError('result cannot be represented as a finite JSON number')
    return {'derived_result':{'operation':operation,'value':float(result),'value_decimal':str(result),
                             'unit':args['output_unit'],'formula':formula,'inputs':inputs,'source_scopes':scopes},
            'source_evidence':receipts,'availability':'derived_from_retrieved_sources',
            'note':'Derived arithmetic, not new upstream evidence. Cite original source_evidence.'}


def numeric_candidates(args,sources,limit=16):
    """Public correction hints from retrieved sources only; never task/gold lookup."""
    found=[]
    def walk(value,path,call_id):
        if len(found)>=limit:return
        if isinstance(value,dict):
            for key,item in value.items():walk(item,path+'/'+str(key).replace('~','~0').replace('/','~1'),call_id)
        elif isinstance(value,list):
            for index,item in enumerate(value):walk(item,path+'/'+str(index),call_id)
        elif isinstance(value,(int,float)) and not isinstance(value,bool):
            try:unit=unit_for(sources[call_id],path)
            except (ValueError,IndexError,KeyError,TypeError):return
            found.append({'call_id':call_id,'path':path,'unit':unit})
    for ref in args.get('operands',[]) if isinstance(args,dict) else []:
        if not isinstance(ref,dict):continue
        call_id=ref.get('call_id')
        if call_id in sources and not any(x['call_id']==call_id for x in found):walk(sources[call_id].get('data'),'/data',call_id)
    return found
