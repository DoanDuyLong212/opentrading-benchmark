#!/usr/bin/env python3
"""Guarded 21-path v45 product installation. Default is a read-only product dry run."""
import argparse,hashlib,json,os,subprocess,tempfile,shutil,fcntl
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def command(root,*args):return subprocess.check_output(['git','-C',str(root),*args]).decode().strip()
def inventory(root):
 names=subprocess.check_output(['git','-C',str(root),'ls-files','-z','--cached','--others','--exclude-standard']).decode().split('\0')
 result={}
 for name in sorted(set(names)-{''}):
  p=root/name
  if p.is_symlink():result[name]={'symlink':os.readlink(p)}
  elif p.is_file():result[name]={'sha256':sha(p),'bytes':p.stat().st_size}
  elif not p.exists():result[name]={'missing':True}
 return result
def ancestor_symlink(path,root):
 current=path
 while current!=root:
  if current.is_symlink():return True
  current=current.parent
 return root.is_symlink()
def verify(manifest,root):
 if command(root,'rev-parse','HEAD')!=manifest['expected_product_head']:raise ValueError('Product HEAD differs from approved base')
 candidate=Path(manifest['candidate_root']).resolve();rows=manifest['files'];names=[r['path']for r in rows]
 if len(rows)!=21 or len(set(names))!=21 or manifest.get('delete_paths')!=[]or manifest.get('preserve_unlisted_paths')is not True:raise ValueError('Expected exactly21 unique nondeleting paths with preserve guard')
 for row in rows:
  name=Path(row['path'])
  if name.is_absolute()or'..'in name.parts or name.parts[0]in('.git',):raise ValueError('Unsafe install path')
  src=candidate/name;dest=root/name
  if ancestor_symlink(src,candidate)or ancestor_symlink(dest,root)or not dest.resolve().is_relative_to(root)or not src.resolve().is_relative_to(candidate):raise ValueError('Symlink/path escape is not allowed')
  if not src.is_file()or sha(src)!=row['candidate_sha256']:raise ValueError('Candidate changed: '+str(name))
  current=sha(dest)if dest.is_file()else None
  if current!=row['expected_product_sha256']:raise ValueError('Existing product/user change conflicts: '+str(name))
 return candidate

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--manifest',required=True);ap.add_argument('--product',default='/home/doanlong/OpenTrading');ap.add_argument('--out',required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--approved-dry-run-sha256');ap.add_argument('--engineering-approval');a=ap.parse_args()
 root=Path(a.product).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);manifestpath=Path(a.manifest).resolve();manifest=json.loads(manifestpath.read_text());candidate=verify(manifest,root)
 before=inventory(root);paths={r['path']for r in manifest['files']}
 report={'installer_sha256':sha(Path(__file__).resolve()),'schema':'v45-product-install-dry-run-v1','status':'ready_for_independent_review','manifest':str(manifestpath),'manifest_sha256':sha(manifestpath),'product_root':str(root),'expected_product_head':manifest['expected_product_head'],'candidate_root':str(candidate),'paths':manifest['files'],'delete_paths':[],'preserve_unlisted_paths':True,'before_inventory':before}
 dry=out/'dry-run.json'
 if not a.execute:
  if dry.exists()and json.loads(dry.read_text())!=report:raise ValueError('Preserve previous dry run; use a new output directory')
  if not dry.exists():write(dry,report)
  print(json.dumps({'status':'dry_run_pass','dry_run':str(dry),'sha256':sha(dry),'paths':len(paths),'preserved_unlisted_files':len(set(before)-paths)}));return
 if not dry.exists()or sha(dry)!=a.approved_dry_run_sha256 or json.loads(dry.read_text())!=report:raise ValueError('Exact current dry-run hash and inventory required')
 if not a.engineering_approval:raise ValueError('Independent engineer approval artifact required')
 approval=json.loads(Path(a.engineering_approval).read_text())
 if approval.get('status')!='approved'or approval.get('install_dry_run_sha256')!=a.approved_dry_run_sha256:raise ValueError('Approval does not bind exact installation dry run')
 lock=(out/'install.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if (out/'installation.json').exists()or(out/'backup').exists():raise ValueError('Prior installation/backup exists; preserve it')
 # Backup each overwritten path, plus complete hash-only user inventory. No personal research/auth copied.
 backup=out/'backup';backup.mkdir();absent=[]
 for row in manifest['files']:
  source=root/row['path'];dest=backup/row['path']
  if source.is_file():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
  else:absent.append(row['path'])
 write(out/'backup-receipt.json',{'original_head':manifest['expected_product_head'],'original_inventory':before,'originally_absent_paths':absent,'backup_sha256':{r['path']:sha(backup/r['path'])for r in manifest['files']if(backup/r['path']).exists()},'rollback':'Restore only listed backup paths; remove only originally absent installed paths after checking their installed hashes. Preserve unrelated user changes.'})
 verify(manifest,root)
 if inventory(root)!=before:raise ValueError('Product changed while preparing backup; no install performed')
 installed=[]
 try:
  for row in manifest['files']:
   dest=root/row['path'];dest.parent.mkdir(parents=True,exist_ok=True)
   data=(candidate/row['path']).read_bytes()
   if hashlib.sha256(data).hexdigest()!=row['candidate_sha256']:raise ValueError('Candidate changed before staging: '+row['path'])
   if (sha(dest)if dest.is_file()else None)!=row['expected_product_sha256']:raise ValueError('User changed install path before replace: '+row['path'])
   with tempfile.NamedTemporaryFile(dir=dest.parent,prefix='.v45-install-',delete=False)as tmp:
    temp=Path(tmp.name);tmp.write(data);tmp.flush();os.fsync(tmp.fileno())
   if sha(temp)!=row['candidate_sha256']or sha(candidate/row['path'])!=row['candidate_sha256']:
    temp.unlink();raise ValueError('Candidate changed after staging: '+row['path'])
   if ancestor_symlink(dest,root)or(sha(dest)if dest.is_file()else None)!=row['expected_product_sha256']:
    temp.unlink();raise ValueError('Install destination changed after staging: '+row['path'])
   shutil.copymode(candidate/row['path'],temp);os.replace(temp,dest);installed.append(row['path'])
  after=inventory(root)
  if command(root,'rev-parse','HEAD')!=manifest['expected_product_head']:raise ValueError('HEAD changed during installation')
  if any(after.get(name)!=value for name,value in before.items()if name not in paths):raise ValueError('Unlisted user file changed during installation')
  if any(sha(root/r['path'])!=r['candidate_sha256']for r in manifest['files']):raise ValueError('Installed source hash mismatch')
  write(out/'installation.json',{'status':'installed','dry_run_sha256':a.approved_dry_run_sha256,'manifest_sha256':sha(manifestpath),'head_unchanged':True,'installed_paths':installed,'after_inventory':after,'unlisted_user_changes_preserved':True,'source_matches_candidate':True})
 except BaseException as exc:
  write(out/'installation-failure.json',{'status':'partial_install_preserved_for_recovery','installed_paths':installed,'error':str(exc),'backup_receipt':str(out/'backup-receipt.json')});raise
 print(json.dumps({'status':'installed','receipt':str(out/'installation.json')}))
if __name__=='__main__':main()
