"""Independent Decimal arithmetic for recorded native derivations; no JS runtime.
Never trusts a literal ref: checks every root leaf against actual source envelope.
"""
import ast,math,re,unicodedata
from decimal import Decimal,localcontext

def D(x):
    if isinstance(x,bool) or not isinstance(x,(int,float,str)):raise ValueError('Non-numeric input')
    d=Decimal(str(x))
    if not d.is_finite():raise ValueError('Nonfinite')
    return d

DIMENSIONLESS_ALIASES=frozenset(('', '1', 'lần', 'x', 'dimensionless', 'tỷ lệ', 'tỉ lệ', 'unitless', 'ratio', 'fraction'))

def factor(unit):
    text=unicodedata.normalize('NFC',str(unit or '')).lower();text=re.sub(r'\([^)]*\)','',text).strip()
    alias={'vndbn':'tỷ đồng','vndmn':'triệu đồng','vndk':'nghìn đồng','billion vnd':'tỷ đồng','million vnd':'triệu đồng'}
    def term(t):
        t=alias.get(t.strip(),t.strip())
        if t in DIMENSIONLESS_ALIASES:return D(1)
        power=re.fullmatch(r'(.*?)\^(-?\d+(?:\.\d+)?)',t)
        if power:return term(power[1])**D(power[2])
        if t in ('%','phần trăm','điểm %','điểm phần trăm'):return D('.01')
        if t=='bps':return D('.0001')
        for word,power in [('triệu tỷ',15),('nghìn tỷ',12),('ngàn tỷ',12),('nghìn',3),('ngàn',3),('triệu',6),('tỷ',9),('tỉ',9),('bn',9),('trăm',2),('k',3),('m',6)]:
            if t==word or t.startswith(word+' '):return D(10)**power*term(t[len(word):])
        if t in ('','1','lần','x','dimensionless','tỷ lệ','đồng','đ','vnd','vnđ','dong','cổ phiếu','cp','cổ','share','shares','điểm','point','points','usd','$','đô','đô la','usdt','eur','jpy','cny','ngày','day','days','năm','year','years','quý','quarter','quarters','tháng','month','months','lượt','hợp đồng'):return D(1)
        raise ValueError('Unverified unit: '+t)
    parts=text.split('/');out=D(1)
    for part in re.split('[*·×]',parts[0]):out*=term(part)
    for part in parts[1:]:out/=term(part)
    return out

def formula_constant(v):
    """Same set as OpenTrading isFormulaConstant (2026-11-11): listed constants, small counts, powers of ten."""
    if D(v) in map(D,[0,1,2,3,4,12,100,252,365]):return True
    if float(v).is_integer() and abs(v)<=31:return True
    if v==0:return False
    k=math.log10(abs(v));return abs(k-round(k))<1e-9 and abs(k)<=15

def expression(text,bindings):
    node=ast.parse(text.replace('^','**'),mode='eval')
    if sum(1 for _ in ast.walk(node))>512:raise ValueError('Expression too complex')
    def walk(n):
        if isinstance(n,ast.Expression):return walk(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)) and not isinstance(n.value,bool) and formula_constant(n.value):return D(n.value)
        if isinstance(n,ast.Name):return bindings[n.id]
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return walk(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        if isinstance(n,ast.BinOp):
            a,b=walk(n.left),walk(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,ast.Div):return a/b
            if isinstance(n.op,ast.Pow) and abs(b)<=100:return a**b
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and not n.keywords:
            vals=[walk(x) for x in n.args];name=n.func.id
            if name=='abs' and len(vals)==1:return abs(vals[0])
            if name=='min':return min(vals)
            if name=='max':return max(vals)
            if name=='sum':return sum(vals,D(0))
            if name=='avg':return sum(vals,D(0))/len(vals)
            if name=='sqrt' and len(vals)==1:return vals[0].sqrt()
            if name=='ln' and len(vals)==1:return vals[0].ln()
            if name=='log10' and len(vals)==1:return vals[0].log10()
            if name=='exp' and len(vals)==1:return vals[0].exp()
        raise ValueError('Unsupported expression grammar')
    with localcontext() as ctx:ctx.prec=40;return walk(node)

def pointer(env,path):
    cur=env
    for raw in path.split('/')[1:]:
        key=raw.replace('~1','/').replace('~0','~');cur=cur[int(key)] if isinstance(cur,list) else cur[key]
    return cur

def verify_native(record,sources,prior_derived=None):
    if record.get('status')!='ok' or record.get('kind')!='native_derived':return None
    result=record['result']['derived_result'];leaves=result['inputs'];prior_derived=prior_derived or {}
    if not leaves:raise ValueError('Derived result lacks actual source roots')
    for leaf in leaves:
        source=sources.get(leaf.get('call_id'))
        if not source:raise ValueError('Native root source not actually retrieved')
        value=pointer(source,leaf['path'])
        if D(value)!=D(leaf['value']):raise ValueError('Native root leaf value differs from source')
        # Independently resolve metadata from actual enclosing records/top units.
        current=source;ancestors=[];parts=leaf['path'].split('/')[1:]
        for raw in parts:
            if isinstance(current,dict):ancestors.append(current)
            key=raw.replace('~1','/').replace('~0','~');current=current[int(key)] if isinstance(current,list) else current[key]
        def nearest(keys):
            for ancestor in reversed(ancestors):
                for key in keys:
                    if isinstance(ancestor.get(key),str) and ancestor[key].strip():return ancestor[key].strip()
            return None
        publicunit=source.get('units',{}).get(leaf['path']) if isinstance(source.get('units',{}).get(leaf['path']),str) else nearest(['unit'])
        if publicunit is None:
            leafkey=parts[-1].replace('~1','/').replace('~0','~')
            choices=[u for field,u in source.get('units',{}).items() if field==leaf['path'] or leafkey in [x.strip() for x in re.split('[,;]',field)]]
            if not choices or len(set(choices))!=1:raise ValueError('Root unit is not published unambiguously')
            publicunit=choices[0]
        def canonical_unit(u):
            u=re.sub(r'\([^)]*\)','',str(u)).strip().lower();u={'vndbn':'tỷ đồng','vndmn':'triệu đồng','vndk':'nghìn đồng','vnd':'đồng','vnđ':'đồng','đ':'đồng','dong':'đồng'}.get(u,u)
            if u in DIMENSIONLESS_ALIASES:return 'dimensionless'
            return u.replace('vnd','đồng').replace('ngàn','nghìn').replace('tỉ','tỷ').replace('/share','/cổ phiếu').replace('/cp','/cổ phiếu')
        if factor(publicunit)!=factor(leaf['unit']) or canonical_unit(publicunit)!=canonical_unit(leaf['unit']):raise ValueError('Root unit differs from public source unit')
        entity=nearest(['symbol','ticker','entity','index','country','series','sector']);scope=nearest(['scope','statement_scope','consolidation','report_scope'])
        if scope is None:
            scope=next(('consolidated' if a['consolidated'] else 'separate' for a in reversed(ancestors) if isinstance(a.get('consolidated'),bool)),None)
        periodkey=parts[-1].replace('~1','/').replace('~0','~')
        period=periodkey if re.search(r'\d{4}|TTM|YTD|lũy kế',periodkey,re.I) else nearest(['period','date','last_t','t','time','timestamp'])
        if period is None:
            period=next((f"Q{a['quarter']}/{a['year']}" for a in reversed(ancestors) if isinstance(a.get('year'),int) and isinstance(a.get('quarter'),int)),None)
        array_column=re.search(r'/values/(\d+)$',leaf['path'])
        if array_column:
            columns=next((a['periods'] for a in ancestors if isinstance(a.get('periods'),list)),None)
            if columns is not None and int(array_column[1])<len(columns):period=columns[int(array_column[1])]
        if period is None and periodkey in ('o','h','l','c','v','open','high','low','close','last','volume','vol'):period=source.get('provenance',{}).get('data_time')
        query=source.get('_audit_source_request',{})
        if entity is None:entity=query.get('symbol') or query.get('ticker')
        if 'query_context' in leaf and leaf['query_context']!=query:raise ValueError('Root query_context differs from actual SDK/MCP arguments')
        if period is None:
            y=query.get('year');q=query.get('quarter')
            if isinstance(y,int) and 1900<=y<=2200:period=f'Q{q}/{y}' if isinstance(q,int) and 1<=q<=4 else str(y)
            elif isinstance(query.get('period'),str) and re.search(r'\d{4}|TTM|YTD|lũy kế',query['period'],re.I):period=query['period']
        if scope is None:
            if isinstance(query.get('consolidated'),bool):scope='consolidated' if query['consolidated'] else 'separate'
            else:scope=query.get('scope')
        metric=nearest(['metric','item'])
        if metric is None and (array_column or periodkey=='value' or re.search(r'\d{4}|TTM|YTD|lũy kế',periodkey,re.I)):metric=nearest(['name'])
        metric=metric or periodkey
        gotmetric=leaf.get('metric','')
        if isinstance(gotmetric,str) and gotmetric.startswith('name:'):gotmetric=gotmetric[5:]
        if isinstance(gotmetric,str) and gotmetric.startswith('norm_id:'):
            normid=next((str(a['norm_id']) for a in reversed(ancestors) if isinstance(a.get('norm_id'),(str,int))),None)
            metric='norm_id:'+str(normid)
        if gotmetric!=metric:raise ValueError('Root metric differs from public source metadata')
        for field,expected in [('entity',entity),('scope',scope),('period',period)]:
            got=leaf.get(field)
            if (str(got).upper() if field=='entity' and got is not None else got)!=(str(expected).upper() if field=='entity' and expected is not None else expected):raise ValueError('Root '+field+' differs from public source metadata')
        receipt=source.get('benchmark_evidence',{})
        if leaf.get('receipt')!=receipt or leaf.get('source_response_sha256')!=receipt.get('response_sha256') or leaf.get('source_payload_sha256')!=receipt.get('payload_sha256'):raise ValueError('Native root source receipt/hash mismatch')
    inputs=result.get('expression_inputs',leaves)
    names=[x.get('name') for x in inputs if 'name' in x]
    if len(names)!=len(set(names)):raise ValueError('Duplicate expression binding')
    for item in inputs:
        if item.get('derived_inputs'):
            prior=prior_derived.get(item.get('sdk_call_id'))
            if prior is None or D(prior['result']['derived_result']['value'])!=D(item['value']):raise ValueError('Derived chain lacks earlier verified execution')
            if item.get('unit')!=prior['result']['derived_result'].get('unit'):raise ValueError('Derived chain unit differs from verified execution')
            if item.get('derived_inputs')!=prior['result']['derived_result'].get('inputs'):raise ValueError('Derived chain roots differ')
        else:
            identity={k:v for k,v in item.items() if k!='name'}
            if not any(identity=={k:v for k,v in leaf.items() if k!='name'} for leaf in leaves):raise ValueError('Expression input is not a verified root source binding')
    rootkeys={(x.get('call_id'),x.get('path')) for x in leaves}
    usedkeys={(x.get('call_id'),x.get('path')) for item in inputs for x in (item.get('derived_inputs') or [item])}
    if rootkeys!=usedkeys:raise ValueError('Unused or extra root lineage')
    if record['tool']=='calculate':
        tree=ast.parse(result['expression'].replace('^','**'),mode='eval')
        function_names={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
        used_names={n.id for n in ast.walk(tree) if isinstance(n,ast.Name)}-function_names
        if used_names!={x['name'] for x in inputs}:raise ValueError('Unused or invented expression binding')
        values={x['name']:D(x['value'])*factor(x.get('unit')) for x in inputs}
        computed=expression(result['expression'],values)/factor(result.get('unit'))
        dims=expression_dimensions(result['expression'],{x['name']:dimensions(x.get('unit')) for x in inputs})
        if dims!=dimensions(result.get('unit')):raise ValueError('Independent output dimension mismatch')
    else:
        vals=[D(x['value']) for x in inputs];basevals=[D(x['value'])*factor(x.get('unit')) for x in inputs];op=result['expression'];args=record['arguments']
        if op in ('pct_change','share','relative_strength'):
            if dimensions(result.get('unit')) or factor(result.get('unit'))!=D('.01'):raise ValueError('Native percent output dimension/scale mismatch')
        elif op=='ratio':
            if dimensions(result.get('unit')) or factor(result.get('unit'))!=1:raise ValueError('Native ratio output dimension/scale mismatch')
        else:
            if dimensions(result.get('unit'))!=dimensions(inputs[0].get('unit')) or factor(result.get('unit'))!=factor(inputs[0].get('unit')):raise ValueError('Native output source unit mismatch')
        if op in ('mean','sum','annualize','rank','share') and any(dimensions(x.get('unit'))!=dimensions(inputs[0].get('unit')) or factor(x.get('unit'))!=factor(inputs[0].get('unit')) for x in inputs):raise ValueError('Native series source units differ')
        if op=='mean':computed=sum(vals,D(0))/len(vals)
        elif op=='sum':computed=sum(vals,D(0))
        elif op=='pct_change' and len(vals)==2:computed=(basevals[1]/basevals[0]-1)*100
        elif op=='ratio' and len(vals)==2:
            if dimensions(inputs[0].get('unit'))!=dimensions(inputs[1].get('unit')):raise ValueError('Ratio source dimensions differ')
            computed=basevals[0]/basevals[1]
        elif op=='annualize':computed=sum(vals,D(0))*D(args['periods_per_year'])/D(args['periods_done'])
        elif op=='relative_strength' and len(vals)==4:computed=((basevals[1]/basevals[0]-1)-(basevals[3]/basevals[2]-1))*100
        elif op in ('rank','share'):
            expected=[{'label':item.get('entity'),'value':v} for item,v in zip(inputs,vals)]
            if not all(x['label'] for x in expected):raise ValueError('Missing rank/share entity labels')
            if op=='rank':expected=sorted(expected,key=lambda x:-x['value'])
            else:
                total=sum(vals,D(0));expected=[{'label':x['label'],'value':x['value']/total*100} for x in expected]
            reported=result['value']
            if not isinstance(reported,list) or len(reported)!=len(expected):raise ValueError('Vector computation shape mismatch')
            for actual,want in zip(reported,expected):
                if not isinstance(actual,dict) or actual.get('label')!=want['label'] or abs(D(actual.get('value'))-want['value'])>D('.00000051'):raise ValueError('Vector computation differs from independent Decimal')
            return {'computed':[{'label':x['label'],'value':str(x['value'])} for x in expected],'reported':reported,'roots':len(leaves)}
        else:raise ValueError('Unsupported native financial op')
    # Native round6 default or explicit decimals; independent Decimal value tolerance.
    decimals=record.get('arguments',{}).get('decimals',6);tol=D(10)**-int(decimals)/2+D('1e-9')*max(D(1),abs(computed))
    if abs(D(result['value'])-computed)>tol:raise ValueError('Native arithmetic differs from independent Decimal')
    return {'computed':str(computed),'reported':result['value'],'tolerance':str(tol),'roots':len(leaves)}


def verify_common(record,sources,prior_common=None):
    """Independent Decimal check of common utility using same audited source roots.
The execution engine may be shared with OT; this arithmetic auditor is Python.
"""
    if record.get('tool')!='analytics_calculate' or record.get('status')!='ok':return None
    import copy
    result=copy.deepcopy(record['derivation']);prior_common=prior_common or {};prior_native={}
    for item in result.get('expression_inputs',[]):
        if item.get('derived_id'):
            reference=item['derived_id'];prior=prior_common.get(reference)
            if prior is None:raise ValueError('Common chain lacks earlier verified derivation')
            item['derived_inputs']=copy.deepcopy(prior['derivation']['inputs']);item['sdk_call_id']=reference
            prior_native[reference]={'result':{'derived_result':prior['derivation']}}
    return verify_native({'kind':'native_derived','tool':'calculate','status':'ok','arguments':{'decimals':record['arguments'].get('precision',6)},'result':{'derived_result':result}},sources,prior_native)


def dimensions(unit):
    text=unicodedata.normalize('NFC',str(unit or '')).lower();text=re.sub(r'\([^)]*\)','',text).strip()
    aliases={'vndbn':'tỷ đồng','vndmn':'triệu đồng','vndk':'nghìn đồng','billion vnd':'tỷ đồng','million vnd':'triệu đồng'}
    def term(t):
        t=aliases.get(t.strip(),t.strip())
        if t in DIMENSIONLESS_ALIASES:return {}
        power=re.fullmatch(r'(.*?)\^(-?\d+(?:\.\d+)?)',t)
        if power:return {k:v*D(power[2]) for k,v in term(power[1]).items()}
        for word in ['triệu tỷ','nghìn tỷ','ngàn tỷ','nghìn','ngàn','triệu','tỷ','tỉ','bn','trăm','k','m']:
            if t==word:return {}
            if t.startswith(word+' '):return term(t[len(word):])
        if t in ('','1','lần','x','dimensionless','tỷ lệ','%','phần trăm','điểm %','điểm phần trăm','bps'):return {}
        for base,names in [('VND',['đồng','đ','vnd','vnđ','dong']),('share',['cổ phiếu','cp','cổ','share','shares']),('point',['điểm','point','points']),('USD',['usd','$','đô','đô la']),('USDT',['usdt']),('EUR',['eur']),('JPY',['jpy']),('CNY',['cny']),('day',['ngày','day','days']),('year',['năm','year','years']),('quarter',['quý','quarter','quarters']),('month',['tháng','month','months']),('contract',['hợp đồng']),('turn',['lượt'])]:
            if t in names:return {base:D(1)}
        raise ValueError('Unverified dimension unit '+t)
    result={};parts=text.split('/')
    for i,part in enumerate(parts):
        for component in re.split('[*·×]',part):
            for base,power in term(component).items():result[base]=result.get(base,D(0))+power*(1 if i==0 else -1)
    return {k:v for k,v in result.items() if v}


def expression_dimensions(text,units):
    tree=ast.parse(text.replace('^','**'),mode='eval')
    def combine(a,b,sign=1):
        c=dict(a)
        for k,v in b.items():c[k]=c.get(k,D(0))+sign*v
        return {k:v for k,v in c.items() if v}
    def walk(n):
        if isinstance(n,ast.Expression):return walk(n.body)
        if isinstance(n,ast.Constant):return {}
        if isinstance(n,ast.Name):return units[n.id]
        if isinstance(n,ast.UnaryOp):return walk(n.operand)
        if isinstance(n,ast.BinOp):
            a,b=walk(n.left),walk(n.right)
            if isinstance(n.op,(ast.Add,ast.Sub)):
                if a!=b:raise ValueError('Independent dimension mismatch in addition')
                return a
            if isinstance(n.op,ast.Mult):return combine(a,b)
            if isinstance(n.op,ast.Div):return combine(a,b,-1)
            if isinstance(n.op,ast.Pow):
                if b:raise ValueError('Dimensional exponent')
                exponent=expression(ast.unparse(n.right),{})
                return {k:v*exponent for k,v in a.items() if v*exponent}
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name):
            args=[walk(a) for a in n.args];name=n.func.id
            if name in ('min','max','sum','avg'):
                if any(x!=args[0] for x in args):raise ValueError('Independent function dimension mismatch')
                return args[0]
            if name=='abs':return args[0]
            if name=='sqrt':return {k:v/2 for k,v in args[0].items()}
            if name in ('ln','log10','exp'):
                if any(args):raise ValueError('Transcendental function needs dimensionless input')
                return {}
        raise ValueError('Unsupported dimensional grammar')
    return walk(tree)
