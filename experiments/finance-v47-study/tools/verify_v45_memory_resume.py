#!/usr/bin/env python3
"""Run exact completed memory CLI with gateway/episode constructors forbidden."""
import argparse,json,sys
from pathlib import Path
from run_manifest import hash_file

def snapshot(out):
 out=Path(out);paths=[out/'manifest.json']+[p for p in(out/'episodes').rglob('*')if p.is_file()and not p.is_symlink()]
 return {str(p.relative_to(out)):{'sha256':hash_file(p),'size':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns}for p in sorted(paths)}
def verify(command):
 if not isinstance(command,list)or len(command)<3 or Path(command[1]).name!='run_memory_benchmark.py'or'--execute'not in command:raise ValueError('Exact approved completed memory CLI required')
 out=Path(command[command.index('--out')+1]).resolve();manifest=json.loads((out/'manifest.json').read_text())
 for cell in manifest['schedule']:
  result=out/'episodes'/cell['trial_id']/'result.json'
  if not result.exists()or json.loads(result.read_text()).get('status')not in('completed','ok','dnf','interrupted'):raise ValueError('Every scheduled episode must be terminal before completed resume proof')
 before=snapshot(out);calls=[]
 import run_memory_benchmark as driver
 from runners import provider
 class ForbiddenInference(BaseException):pass
 def blocked(*args,**kwargs):calls.append('constructor');raise ForbiddenInference('Completed resume attempted gateway/episode construction')
 old_episode=driver.MemoryEpisode;old_gateway=provider.ProviderGateway.__init__;argv=sys.argv
 driver.MemoryEpisode=blocked;provider.ProviderGateway.__init__=blocked;sys.argv=[command[1],*command[2:]]
 try:driver.main()
 finally:driver.MemoryEpisode=old_episode;provider.ProviderGateway.__init__=old_gateway;sys.argv=argv
 after=snapshot(out);proof={'schema':'completed-memory-resume-v45','pass':not calls and before==after,'new_model_calls':0,'new_episode_or_gateway_constructors':len(calls),'manifest_sha256':hash_file(out/'manifest.json'),'before':before,'after':after,'method':'exact actual completed driver CLI with BaseException constructors interceptor; all episode and capture SHA/size/mtime preserved'}
 (out/'completed-resume-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 if not proof['pass']:raise ValueError('Completed resume changed protected files or constructed inference')
 return proof
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--command-json',required=True);a=ap.parse_args();r=verify(json.loads(a.command_json));print(json.dumps({k:v for k,v in r.items()if k not in('before','after')}))
