"""Second arithmetic implementation: reconstruct actual source leaves, without analytics_compute.compute."""
import hashlib,json,math
from decimal import Decimal,localcontext
FIELDS=('call_id','tool','matched_entry_id','payload_sha256','response_sha256','source','as_of')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def locate(env,path):
    import re
    if not isinstance(path,str) or not path.startswith('/data/'):raise ValueError('Nondata reference')
    node=env;chain=[]
    keys=[]
    for raw in path.split('/')[1:]:
        if re.search(r'~(?![01])',raw):raise ValueError('Malformed pointer escape')
        key=raw.replace('~1','/').replace('~0','~');keys.append(key)
        if isinstance(node,dict):chain.append((node,len(keys)-1));node=node[key]
        elif isinstance(node,list):
            if not re.fullmatch(r'0|[1-9][0-9]*',key):raise ValueError('Invalid array index')
            node=node[int(key)]
        else:raise ValueError('Pointer traverses a scalar')
    if isinstance(node,bool) or not isinstance(node,(int,float)):raise ValueError('Nonnumeric reference')
    return Decimal(str(node)),keys,chain

def selected_table(keys,chain):
    # Recover the public column index and enclosing table relation independently.
    if len(keys)<2 or keys[-2]!='values':return None
    for table,_ in reversed(chain):
        columns=table.get('periods');rows=table.get('rows')
        if not isinstance(columns,list) or not isinstance(rows,list):continue
        row=next((node for node,_ in chain if any(node is r for r in rows)),None)
        if row is None:continue
        values=row.get('values')
        if not isinstance(values,list) or len(values)!=len(columns):raise ValueError('Unaligned public table')
        column=int(keys[-1])
        if not 0<=column<len(columns) or not isinstance(columns[column],str):raise ValueError('Missing explicit table period')
        return table,row,columns[column]
    return None

def actual_unit(env,path,keys,chain):
    aliases={'vnd':'VND','đồng':'VND','vndbn':'tỷ đồng','nghìn đồng/cổ phiếu':'nghìn đồng/cổ phiếu','tỷ đồng':'tỷ đồng','triệu đồng':'triệu đồng','dimensionless':'dimensionless'}
    units=env.get('units');values=[]
    if isinstance(units,dict):values=[units[k] for k in (path,keys[-1]) if isinstance(units.get(k),str)]
    rows=[(row,index) for row,index in chain if isinstance(row.get('unit'),str)]
    if rows:
        row,index=rows[-1]
        if keys[index]=='values' or keys[-1] in ('value','amount'):values.append(row['unit'])
    table=selected_table(keys,chain)
    if table and isinstance(table[0].get('unit'),str):values.append(table[0]['unit'])
    normalized=[aliases.get(v.strip().lower()) for v in values]
    if not normalized or None in normalized or len(set(normalized))!=1:raise ValueError('Missing/ambiguous source units')
    return normalized[0]

def source_scope(env,keys,chain):
    import re
    entity=None;period=None;metric=keys[-1];table=selected_table(keys,chain)
    for row,index in chain:
        for k in ('symbol','ticker','entity'):
            if isinstance(row.get(k),str):entity=row[k].upper()
        for k in ('date','time','t','last_t','period'):
            if isinstance(row.get(k),(str,int)):period=str(row[k])
        if isinstance(row.get('norm_id'),(str,int)):metric='norm_id:'+str(row['norm_id'])
        elif isinstance(row.get('name'),str) and (isinstance(row.get('values'),dict) or table and row is table[1]):metric='name:'+row['name']
    if re.fullmatch(r'(?:Q[1-4]/[0-9]{4}|[0-9]{4}(?:-[0-9]{2}(?:-[0-9]{2})?)?)',keys[-1]):period=keys[-1]
    if table:period=table[2]
    if period is None:period=env.get('provenance',{}).get('data_time')
    return {'entity':entity,'period':period,'metric':metric}

def verify_derived(task,ledger):
    from mcp_snapshot_server import load_entries,select_envelope
    entries,_=load_entries(task/'environment/payloads.json');sources={};proofs=[]
    for record in ledger:
        if record.get('tool')!='analytics_compute':
            if record.get('status')=='ok':
                env=select_envelope(entries,record['tool'],record['arguments'])
                if digest(env)!=record['response_sha256']:raise ValueError('Source envelope hash mismatch')
                env['benchmark_evidence']={k:record[k] for k in FIELDS};sources[record['call_id']]=(env,record)
            continue
        if record.get('status')!='ok':
            if record.get('response_sha256') is not None or 'derivation' in record or 'source_evidence' in record:raise ValueError('Rejected compute carries synthetic successful derivation')
            continue
        if record.get('record_kind')!='deterministic_derivation' or any(record.get(k) is not None for k in ('source','as_of','matched_entry_id')):raise ValueError('Synthetic upstream evidence')
        args=record['arguments'];op=args['operation'];values=[];inputs=[];evidence=[];scopes=[]
        if op in ('sum','mean') and len({(r['call_id'],r['path']) for r in args['operands']})!=len(args['operands']):raise ValueError('Repeated aggregate dependency')
        for ref in args['operands']:
            env,source=sources[ref['call_id']]
            if source['ended_at']>record['started_at']:raise ValueError('Future/uncompleted dependency')
            number,keys,chain=locate(env,ref['path']);scopes.append(source_scope(env,keys,chain))
            if not number.is_finite() or actual_unit(env,ref['path'],keys,chain)!=args['input_unit']:raise ValueError('Wrong source unit or nonfinite number')
            receipt=env['benchmark_evidence'];values.append(number)
            if receipt not in evidence:evidence.append(receipt)
            inputs.append({**ref,'value_decimal':str(number),'unit':args['input_unit'],'source_response_sha256':source['response_sha256'],'source_payload_sha256':source['payload_sha256']})

        if op in ('sum','mean','margin_pct') and len(values)>1 and (any(not s['period'] for s in scopes) or len({s['period'] for s in scopes})!=1):raise ValueError('Selected periods differ or are missing')
        if op in ('sum','mean','growth_pct') and len({s['metric'] for s in scopes})!=1:raise ValueError('Selected metrics differ')
        if op in ('growth_pct','margin_pct') and (any(not s['entity'] for s in scopes) or len({s['entity'] for s in scopes})!=1):raise ValueError('Ratio entities differ or are missing')
        if op=='growth_pct' and (any(not x['period'] for x in scopes) or scopes[0]['period']==scopes[1]['period']):raise ValueError('Growth periods missing or identical')
        with localcontext() as ctx:
            ctx.prec=40
            if op in ('sum','mean'):
                if args['input_unit']!=args['output_unit']:raise ValueError('Aggregate unit/date mismatch')
                number=sum(values,Decimal(0));formula='sum(x)'
                if op=='mean':number=number/len(values);formula='sum(x)/count(x)'
            elif op in ('growth_pct','margin_pct'):
                if len(values)!=2 or values[1]==0 or (op=='growth_pct' and values[1]<0) or args['output_unit']!='%':raise ValueError('Invalid ratio operands')
                number=(values[0]/values[1]-(1 if op=='growth_pct' else 0))*100
                formula='(x[0]/x[1]-1)*100' if op=='growth_pct' else 'x[0]/x[1]*100'
            elif op=='scale':
                factors={'VND':Decimal(1),'triệu đồng':Decimal(1000000),'tỷ đồng':Decimal(1000000000)}
                if len(values)!=1:raise ValueError('Invalid scale cardinality')
                number=values[0]*factors[args['input_unit']]/factors[args['output_unit']];formula='x[0]*input_VND_factor/output_VND_factor'
            else:raise ValueError('Unknown operation')
        derived={'operation':op,'value':float(number),'value_decimal':str(number),'unit':args['output_unit'],'formula':formula,'inputs':inputs,'source_scopes':scopes}
        envelope={'derived_result':derived,'source_evidence':evidence,'availability':'derived_from_retrieved_sources','note':'Derived arithmetic, not new upstream evidence. Cite original source_evidence.'}
        if not number.is_finite() or not math.isfinite(float(number)) or record.get('derivation')!=derived or record.get('source_evidence')!=evidence or record['response_sha256']!=digest(envelope):raise ValueError('Derived arithmetic/dependency hash mismatch')
        proofs.append({'call_id':record['call_id'],'operation':op,'value_decimal':str(number),'source_dependencies':inputs,'reconstructed_response_sha256':digest(envelope),'upstream_evidence':False,'semantic_entity_metric_period_validation':'not implied by arithmetic; evaluate task gold and source coverage separately'})
    return proofs

def smoke_financial_canary(task,answer,ledger):
    """Secondary preregistered financial canary, NOT primary grading or hidden gold.

    Only inspected on primary-accepted quote/aggregation smoke. Actual received
    source leaves determine all values/periods/units. No gold/solution is read.
    """
    import datetime,re
    from mcp_snapshot_server import load_entries,select_envelope
    entries,_=load_entries(task/'environment/payloads.json');records=[];issues=[]
    for row in ledger:
        if row.get('status')=='ok' and row.get('tool')=='vn_quote_history':
            env=select_envelope(entries,row['tool'],row['arguments']);data=env.get('data') or {}
            unit_metadata=env.get('units') or {};unit_candidates=[]
            for fields,unit in unit_metadata.items():
                if isinstance(fields,str) and 'last' in [f.strip() for f in fields.split(',')] and isinstance(unit,str):unit_candidates.append(unit.split('(')[0].strip())
            selected_unit=unit_candidates[0] if unit_candidates and len(set(unit_candidates))==1 else None
            records.append({'call_id':row['call_id'],'symbol':data.get('symbol'),'last':data.get('last'),'last_t':data.get('last_t'),'unit':selected_unit,'unit_metadata':unit_metadata,'provenance_data_time':(env.get('provenance') or {}).get('data_time')})
    sources={r['symbol']:r for r in records}
    # Recognize the explicit ISO/public Vietnamese date representations, preserving
    # full year. Other/unparseable representations fail closed as unverified.
    period=str(answer.get('period') or '');dates=set(re.findall(r'(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)',period))
    for d,m,y in re.findall(r'(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)',period):
        try:dates.add(datetime.date(int(y),int(m),int(d)).isoformat())
        except ValueError:issues.append('Invalid calendar date in answer period')
    for d,m,y in re.findall(r'(\d{1,2})\s*tháng\s*(\d{1,2})\s*năm\s*(\d{4})',period,re.I):
        try:dates.add(datetime.date(int(y),int(m),int(d)).isoformat())
        except ValueError:issues.append('Invalid localized calendar date in answer period')
    from public_response_contract import public_success_example
    declared_period=str(public_success_example((task/'instruction.md').read_text()).get('period') or '')
    requested_dates=set(re.findall(r'(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)',declared_period))
    if requested_dates and dates!=requested_dates:issues.append('Answer period differs from explicit public task period')
    needed=['HPG'] if task.name=='smoke-quote-01' else ['VCB','BID','CTG','TCB','MBB']
    for symbol in needed:
        if symbol not in sources:issues.append('Required actual source entity missing: '+symbol);continue
        r=sources[symbol]
        if r['unit']!='nghìn đồng/cổ phiếu':issues.append('Source unit not verified per-share thousand VND: '+symbol)
        if not r['last_t'] or r['last_t']!=r['provenance_data_time']:issues.append('Source selected date/provenance not aligned: '+symbol)
        if dates!={r['last_t']}:issues.append('Answer period differs from the selected source trading date: '+symbol)
    if str(answer.get('unit') or '').strip().lower() not in ('nghìn đồng','nghìn đồng/cổ phiếu'):issues.append('Answer unit differs from task/source scale')
    if answer.get('source')!='vn_quote_history':issues.append('Answer canonical source differs')
    values={k:Decimal(str(sources[k]['last'])) for k in needed if k in sources}
    observed_values={}
    if len(values)==len(needed):
        if len(needed)==1:
            observed_values={'value':str(values['HPG'])}
            if isinstance(answer.get('value'),bool) or not isinstance(answer.get('value'),(int,float)) or Decimal(str(answer['value']))!=values['HPG']:issues.append('Quote value differs from actual retrieved leaf')
        else:
            mean=sum(values.values(),Decimal(0))/len(values);expected={**values,'mean':mean};actual=answer.get('values')
            observed_values={k:str(v) for k,v in expected.items()}
            if not isinstance(actual,dict):issues.append('Missing aggregate values map')
            else:
                for key,value in expected.items():
                    candidate=actual.get(key)
                    if isinstance(candidate,bool) or not isinstance(candidate,(int,float)) or abs(Decimal(str(candidate))-value)>Decimal('0.000001'):issues.append('Aggregate value differs from actual retrieved leaves: '+key)
    return {'pass':not issues,'scope':'secondary smoke financial source/date/unit/numeric canary, does not change primary/frozen grades','issues':issues,'actual_source_leaves':records,'parsed_answer_dates':sorted(dates),'public_requested_dates':sorted(requested_dates),'independently_recomputed_values':observed_values,'answer_period':answer.get('period'),'answer_unit':answer.get('unit')}
