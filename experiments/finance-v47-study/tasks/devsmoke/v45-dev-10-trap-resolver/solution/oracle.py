import json,pathlib,sys
p=pathlib.Path(__file__).resolve().parent
gold=json.loads((p/'gold.json').read_text());payload=json.loads((p.parent/'environment/payloads.json').read_text())
data={k:v.get('envelope',v) for k,v in payload['tools'].items()}
assert gold["solution"]["value"] is None
assert any(e["availability"]=="empty" for e in data.values()) or all("Q4/2026" not in str(e["data"]) for e in data.values())
print("ORACLE OK")
