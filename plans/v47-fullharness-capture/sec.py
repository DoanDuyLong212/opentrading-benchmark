import json,sys,re
m=json.load(open(sys.argv[1]))['messages'][0]['content']
pos=[(mm.start(),mm.group(1)) for mm in re.finditer(r'^<(\w+)>',m,re.M)]
tot=0
for i,(p,n) in enumerate(pos):
    end=pos[i+1][0] if i+1<len(pos) else len(m)
    b=len(m[p:end].encode()); tot+=b; print(f'  {n:16s}{b:6d}')
print('  pre',len(m[:pos[0][0]].encode()) if pos else 0,'total',len(m.encode()))
