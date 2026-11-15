import json,sys
r=json.load(open(sys.argv[1]))
msgs=r.get('messages',[])
def L(x): return len(json.dumps(x,ensure_ascii=False).encode()) if not isinstance(x,str) else len(x.encode())
sysb=sum(L(m['content']) if isinstance(m['content'],str) else sum(L(p.get('text','')) for p in m['content']) for m in msgs if m['role']=='system')
print('model',r.get('model'),'| system bytes',sysb,'| n msgs',len(msgs))
for m in msgs: print('  ',m['role'],L(m['content']))
tools=r.get('tools',[]); tot=0
for t in tools:
    f=t.get('function',t); b=L(t); tot+=b
    print(f"  tool {f['name']:40s} {b:6d}")
print('tools',len(tools),'bytes',tot,'| total body',L(r))
