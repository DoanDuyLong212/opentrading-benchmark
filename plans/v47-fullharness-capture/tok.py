import json,sys,tiktoken
e=tiktoken.get_encoding('o200k_base')
def T(x): return len(e.encode(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False)))
def text(c): return c if isinstance(c,str) else ''.join(p.get('text','') for p in c)
rows=[]
for label,path in [a.split('=',1) for a in sys.argv[1:]]:
    r=json.load(open(path)); msgs=r.get('messages',[])
    s=sum(T(text(m['content'])) for m in msgs if m['role'] in('system','developer'))
    u=sum(T(text(m['content'])) for m in msgs if m['role']=='user')
    tools=r.get('tools',[]); t=sum(T(x) for x in tools)
    rows.append((label,s,len(tools),t,u,s+t+u))
print(f"{'':28}{'system':>8}{'tools':>12}{'user':>8}{'total':>8}")
for l,s,n,t,u,tot in rows: print(f"{l:28}{s:8,}{n:5} /{t:6,}{u:8,}{tot:8,}")
