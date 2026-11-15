"""Guarded workspace memory-only sync; leaves original200 MAIN and holdout untouched."""
import argparse,hashlib,json,shutil,time
from pathlib import Path
STUDY=Path(__file__).resolve().parents[1];ROOT=STUDY.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(d):return {str(p.relative_to(d)):sha(p)for p in sorted(d.rglob("*"))if p.is_file()and "__pycache__"not in p.parts}
def apply(review,execute=False):
 review=Path(review);r=json.loads(review.read_text());audit=ROOT/"audits/financial-memory-v45/corpus-audit.json";a=json.loads(audit.read_text())
 if not r.get("independent_review_pass")or r.get("corpus_audit_sha256")!=sha(audit)or not a.get("pass"):raise ValueError("Independent offline approval must bind the current memory corpus audit")
 before=json.loads((STUDY/"audits/MEMORY-ROOT-BEFORE.json").read_text());sources=[("main",f"fin-mem-{i}")for i in range(320,332)]+[("pilot","fin-mem-p01")]
 for relative,expected in before.items():
  p=ROOT/relative
  if not p.exists()or sha(p)!=expected:raise ValueError("User changes detected; no overwrite: "+relative)
 for split,tid in sources:
  d=STUDY/"tasks"/split/tid;item=next(x for x in a["rows"]if x["task"]==tid)
  if tree(d)!=item["task_tree"]:raise ValueError("Reviewed study memory task changed: "+tid)
  dest=ROOT/"tasks"/split/tid
  if tid in("fin-mem-329","fin-mem-330","fin-mem-331")and dest.exists():raise ValueError("New destination exists; preserve user content: "+tid)
 old200={p.name:tree(p)for p in sorted((ROOT/"tasks/main").iterdir())if p.is_dir()and not p.name.startswith("fin-mem-")}
 if len(old200)!=200:raise ValueError("Expected exactly200 retained nonmemory MAIN tasks")
 result={"schema":"guarded-memory-only-sync-v45","dry_run":not execute,"main_after":212,"source_tasks":13,"base200_sha256":hashlib.sha256(json.dumps(old200,sort_keys=True).encode()).hexdigest(),"holdout_access":"none","review_sha256":sha(review),"audit_sha256":sha(audit)}
 if execute:
  backup=ROOT/"audits/financial-memory-v45"/("canonical-root-backup-"+str(time.time_ns()));backup.mkdir()
  for split,tid in sources:
   source=STUDY/"tasks"/split/tid;dest=ROOT/"tasks"/split/tid
   if dest.exists():shutil.copytree(dest,backup/split/tid)
   dest.mkdir(parents=True,exist_ok=True)
   for p in sorted(source.rglob("*")):
    if not p.is_file()or "__pycache__"in p.parts:continue
    target=dest/p.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+".v45-sync-tmp");temp.write_bytes(p.read_bytes());temp.replace(target)
  after={p.name:tree(p)for p in sorted((ROOT/"tasks/main").iterdir())if p.is_dir()and not p.name.startswith("fin-mem-")}
  if old200!=after:raise RuntimeError("Unexpected base200 mutation")
  result["backup"]=str(backup);(backup/"receipt.json").write_text(json.dumps(result,indent=2)+"\n")
 return result
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--review",required=True);ap.add_argument("--execute",action="store_true");args=ap.parse_args();print(json.dumps(apply(args.review,args.execute),indent=2))
