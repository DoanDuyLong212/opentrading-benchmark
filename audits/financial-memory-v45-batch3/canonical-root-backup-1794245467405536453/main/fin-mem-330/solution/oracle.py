import json,pathlib
p=pathlib.Path(__file__).resolve().parent;g=json.loads((p/'gold.json').read_text());payload=json.loads((p.parent/'environment/payloads.json').read_text())
turns=json.loads((p.parent/'environment/turns.json').read_text());ops=[o for s in turns['sessions'] for t in s['turns'] for o in t.get('memory_operations',[])];assert ops[-1]['op']=='delete' and g['solution']['active_threshold'] is None
print("ORACLE OK")
