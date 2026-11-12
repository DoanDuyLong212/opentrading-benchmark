"""Offline memory-construct audit; no model calls and no holdout access."""
import hashlib,json,re,subprocess,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def tasks(root=ROOT):
 return [*sorted((root/"tasks/main").glob("fin-mem-*")),*sorted((root/"tasks/pilot").glob("fin-mem-*")),*sorted((root/"tasks/memorydev").glob("*"))]
def validate_task(d,run_oracle=True):
 failures=[]; gold=json.loads((d/"solution/gold.json").read_text());payload=json.loads((d/"environment/payloads.json").read_text());turns=json.loads((d/"environment/turns.json").read_text());meta=tomllib.loads((d/"task.toml").read_text());active={};ops=[]
 def check(ok,name):
  if not ok:failures.append(name)
 check(meta.get("track")=="memory_multiturn" and meta.get("multiturn") is True,"memory track")
 check("memory_policy" not in turns,"guessed executable permission policy")
 check(turns.get("execution_contract")=="v45-controlled-shared-user-notebook-v1","execution contract")
 check(sha(d/"environment/payloads.json")==gold.get("payload_sha256"),"raw payload hash")
 final=[]
 for session in turns["sessions"]:
  for index,turn in enumerate(session["turns"]):
   if turn.get("final"):final.append((session["id"],index))
   for op in turn.get("memory_operations",[]):
    source=op.get("source_text","");text=op.get("text","")
    check(bool(source) and source in turn["text"] and (not text or text in turn["text"]),"verbatim public user operation")
    check(op.get("consent")=="explicit_user_request","explicit user consent")
    check(bool(re.search(r"nhớ|lưu|cập nhật|quên|xóa|hủy|remember|update|forget|delete",source,re.I)),"operation intent")
    check(op.get("op") in ("put","delete"),"operation enum")
    if op.get("kind")=="thesis":check(op.get("subject",{}).get("alias","") in source and op.get("subject",{}).get("kind") in ("ticker","sector","market"),"thesis subject")
    if op["op"]=="put":active[op["id"]]=op
    else:active.pop(op["id"],None)
    ops.append(op)
 check(len(final)==1,"exactly one graded final turn")
 instruction=(d/"instruction.md").read_text()
 for block in re.findall(r"```json\s*(.*?)```",instruction,re.S):
  try:json.loads(block)
  except ValueError:failures.append("invalid public JSON schema")
 tools=payload.get("tools",{});contract=gold.get("provenance_contract",[])
 for c in contract:
  entry=tools.get(c["matched_entry_id"]);check(bool(entry),"receipt source exists")
  if entry:check(digest(entry["envelope"])==c["response_sha256"],"canonical source response hash")
 checks=gold.get("memory_checks",{})
 if checks.get("revoked_id"):check(checks["revoked_id"] not in active,"revoked user fact absent")
 if checks.get("active_ids"):check(set(checks["active_ids"])==set(active),"exact active fact IDs")
 if checks.get("no_market_assertion"):check(not tools and not contract,"no fabricated market receipt for absent user preference")
 oracle=None
 if run_oracle:
  r=subprocess.run(["python3",str(d/"solution/oracle.py")],capture_output=True,text=True,timeout=20);oracle={"exit":r.returncode,"stdout":r.stdout,"stderr":r.stderr};check(r.returncode==0,"offline oracle consistency")
 return {"task":d.name,"construct":gold.get("memory_construct"),"active_fact_ids":sorted(active),"operations":len(ops),"pass":not failures,"failures":failures,"oracle":oracle,"task_tree":{str(p.relative_to(d)):sha(p) for p in sorted(d.rglob("*")) if p.is_file() and "__pycache__" not in str(p)}}
def audit(root=ROOT):
 rows=[validate_task(d) for d in tasks(root)];main=list((root/"tasks/main").glob("*/task.toml"));count=len(main)
 return {"schema":"memory-corpus-audit-v45","pass":all(x["pass"] for x in rows) and count<=250,"main_total":count,"main_cap":250,"memory_tasks":len(rows),"external_model_calls":0,"scope":"Oracle consistency, explicit operation source binding and construct inventory. Not external source authenticity or learned/persistent memory efficacy.","rows":rows}
if __name__=="__main__":
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,required=True);a=ap.parse_args();result=audit();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n");print(json.dumps({k:v for k,v in result.items() if k!="rows"}));raise SystemExit(0 if result["pass"] else 1)
