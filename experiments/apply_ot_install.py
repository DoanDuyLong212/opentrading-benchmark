"""Apply a sealed, reviewed payload after conflict checks; retain backups and a receipt.

Run explicitly only after smoke/pilot review. This script needs filesystem permission
for the original project. runtime_only leaves the existing default prompts intact.
"""
import argparse,datetime,hashlib,json,os,shutil
from pathlib import Path

def digest(path):
 return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['runtime_only','finance_default'],required=True)
 args=parser.parse_args();root=Path(__file__).resolve().parent.parent
 manifest=json.loads((root/'experiments/opentrading-install-manifest.json').read_text());dst=Path(manifest['destination'])
 selected={p:v for p,v in manifest['files'].items() if args.mode=='finance_default' or p.startswith('src/')}
 # Verify every input and destination before writing any destination bytes.
 for name,record in selected.items():
  src=root/'experiments/opentrading-runtime'/name;target=dst/name
  if digest(src)!=record['after_sha256']: raise SystemExit('Payload changed after review: '+name)
  if target.is_symlink() or any(p.is_symlink() for p in target.parents if p!=dst): raise SystemExit('Refusing symlink destination: '+name)
  if digest(target)!=record['before_sha256']: raise SystemExit('Original changed since baseline; preserve user changes: '+name)
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
 backup=root/'experiments/installed-backups'/stamp;backup.mkdir(parents=True,exist_ok=False)
 receipt={'mode':args.mode,'destination':str(dst),'backup':str(backup),'files':selected,'completed':False}
 for name in selected:
  target=dst/name
  if target.exists():
   saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
 receipt_path=backup/'receipt.json';receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
 for name,record in selected.items():
  target=dst/name;target.parent.mkdir(parents=True,exist_ok=True)
  temporary=target.with_name(target.name+'.finance-install.tmp')
  if temporary.exists():raise SystemExit('Temporary file already exists: '+str(temporary))
  try:
   with temporary.open('xb') as out:
    out.write((root/'experiments/opentrading-runtime'/name).read_bytes());out.flush();os.fsync(out.fileno())
   os.replace(temporary,target)
  finally:
   if temporary.exists(): temporary.unlink()
  if digest(target)!=record['after_sha256']:raise SystemExit('Installed checksum mismatch: '+name)
 receipt['completed']=True;receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'installed_files':len(selected),'mode':args.mode,'receipt':str(receipt_path)},indent=2))

if __name__=='__main__':main()
