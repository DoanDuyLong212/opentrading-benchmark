"""Common C2 admission: every adapter must preserve finite constraints on wire."""
def schema_constraints(value):
    if isinstance(value,dict):
        out={}
        for key,item in value.items():
            if key in {'description','title','$schema','$id','examples','default'} or key.startswith('x-'):continue
            if key in {'properties','patternProperties','$defs','definitions','dependentSchemas'} and isinstance(item,dict):
                # Mapping keys are user argument names, never schema annotations.
                out[key]={name:schema_constraints(schema) for name,schema in item.items()}
            elif key in {'const','enum','required','dependentRequired'}:
                # Literal values are data, including keys named description/default.
                out[key]=item
            else:out[key]=schema_constraints(item)
        return out
    if isinstance(value,list):return [schema_constraints(v) for v in value]
    return value


def verify_c2_wire_contracts(body,definitions):
    byname={d['name']:d for d in definitions if d.get('inputSchema',{}).get('x-opentrading-schema-profile') in ('finite-replay-c2','deterministic-derivation-v44','deterministic-derivation-v45','grounded-calculation-v45')}
    if not byname:return
    observed={}
    for item in body.get('tools',[]):
        function=item.get('function',{});name=function.get('name','')
        canonical=next((name[len(prefix):] for prefix in ('opentrading_','mcp__opentrading__','mcp_opentrading_') if name.startswith(prefix)),None)
        if canonical in byname:
            observed[canonical]=function.get('parameters')
    if set(observed)!=set(byname):raise ValueError('C2 wire catalog missing finite contracts')
    for name,definition in byname.items():
        if schema_constraints(observed[name])!=schema_constraints(definition['inputSchema']):
            raise ValueError('C2 wire schema constraints changed by adapter: '+name)


def verify_c2_public_cues(body,definitions):
    """Separate prose proof: constraints alone cannot establish visible common action cues."""
    expected={d['name']:d['description'] for d in definitions}
    observed={}
    for item in body.get('tools',[]):
        f=item.get('function',{});name=f.get('name','')
        canonical=next((name[len(p):] for p in ('opentrading_','mcp__opentrading__','mcp_opentrading_') if name.startswith(p)),None)
        if canonical in expected:observed[canonical]=f.get('description','')
    if set(observed)!=set(expected):raise ValueError('Common C2 public cue catalog missing')
    for name,description in observed.items():
        if description!=expected[name]:raise ValueError('Common C2 public description changed by adapter: '+name)
