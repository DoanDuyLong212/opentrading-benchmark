import json,pathlib
p=pathlib.Path(__file__).resolve().parent;g=json.loads((p/'gold.json').read_text());payload=json.loads((p.parent/'environment/payloads.json').read_text())
assert payload['tools']['vnq:HPG']['envelope']['data']['last']==g['solution']['last'];assert payload['source_review_status'].startswith('synthetic')
print("ORACLE OK")
