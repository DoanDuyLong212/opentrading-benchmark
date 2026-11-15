import json,pathlib,sys
p=pathlib.Path(__file__).resolve().parent
gold=json.loads((p/'gold.json').read_text());payload=json.loads((p.parent/'environment/payloads.json').read_text())
data={k:v.get('envelope',v) for k,v in payload['tools'].items()}
computed=sum(data[k]["data"]["last"] for k in ["q:DGC","q:DCM","q:DPM"])/3
assert abs(computed-gold["solution"]["value"])<1e-8
print("ORACLE OK")
