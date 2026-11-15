import json,pathlib,sys
p=pathlib.Path(__file__).resolve().parent
gold=json.loads((p/'gold.json').read_text());payload=json.loads((p.parent/'environment/payloads.json').read_text())
data={k:v.get('envelope',v) for k,v in payload['tools'].items()}
computed=data["fs:DCM"]["data"]["rows"][1]["values"]["Q3/2026"]/data["fs:DCM"]["data"]["rows"][0]["values"]["Q3/2026"]
assert abs(computed-gold["solution"]["value"])<1e-8
print("ORACLE OK")
