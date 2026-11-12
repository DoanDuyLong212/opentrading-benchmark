import json,pathlib
p=pathlib.Path(__file__).resolve().parent;g=json.loads((p/'gold.json').read_text());payload=json.loads((p.parent/'environment/payloads.json').read_text())
rows=payload['tools']['peer:banks_p']['envelope']['data']['rows'];actual=sorted(r['symbol'] for r in rows if r['roe']>20);assert actual==g['solution']['pass']
print("ORACLE OK")
