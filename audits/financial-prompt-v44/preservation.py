"""Read-only preservation inventory for inherited files and fresh v43 scopes."""
import argparse,hashlib,json,subprocess
from pathlib import Path
WORK=Path('/home/doanlong/extra/benchmark');DEST=WORK/'audits/financial-prompt-v44'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(base):
    return {str(p.relative_to(base)):sha(p) for p in sorted(base.rglob('*')) if p.is_file() and not any(x in p.parts for x in ('node_modules','__pycache__','.pytest_cache','.git'))}
def compare(base,stored):return [p for p,h in stored.items() if not (base/p).is_file() or sha(base/p)!=h]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--final',action='store_true');a=ap.parse_args()
    previous=json.loads((WORK/'experiments/finance-v42-study/audits/original-before-inherited-v41.json').read_text())
    original=Path('/home/doanlong/OpenTrading');native=WORK/'experiments/finance-v43-study/experiments/opentrading-runtime'
    paths={'v42_results':WORK/'experiments/finance-v42-study/results','v43_tools':WORK/'experiments/finance-v43-study/tools','v43_tasks':WORK/'experiments/finance-v43-study/tasks','v43_plans':WORK/'experiments/finance-v43-study/plans','v43_native_src':native/'src','v43_native_test':native/'test','v43_native_prompts':native/'prompts','v43_native_test_artifacts':native/'test-artifacts','v43_prompts':WORK/'experiments/finance-v43-study/experiments'}
    # experiments includes native node_modules; restrict explicit compact prompt/config scopes separately.
    paths.pop('v43_prompts')
    for p in sorted((WORK/'experiments/finance-v43-study/experiments').iterdir()):
        if p.is_dir() and p.name!='opentrading-runtime':paths['v43_experiment_'+p.name]=p
    stored=DEST/'start-preservation-inventory.json'
    if a.final:
        state=json.loads(stored.read_text())
    else:
        state={'scope':'Fresh v44-start stored-path inventory of v42 results and v43 sources/logs; original production inherited Nov6 baseline, unrelated user changes reported not reverted. Excludes dependency trees/caches.','scopes':{k:{'path':str(p),'files':inventory(p)} for k,p in paths.items()},'v43_dependency_metadata':{p.name:sha(p) for p in [native/'package.json',native/'bun.lock'] if p.is_file()}}
        stored.write_text(json.dumps(state,indent=2)+'\n')
    inherited_changes=compare(original,previous['original_ot']['files']);head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=original,text=True).strip()
    checks={k:{'files':len(v['files']),'changed_or_missing':compare(Path(v['path']),v['files'])} for k,v in state['scopes'].items()}
    result={'scope':state['scope'],'original_stored_files':len(previous['original_ot']['files']),'original_changed_or_missing':inherited_changes,'original_head':head,'expected_original_head':previous['original_ot']['head'],'checks':checks,'passed':not inherited_changes and head==previous['original_ot']['head'] and all(not c['changed_or_missing'] for c in checks.values())}
    (DEST/('post-run-preservation.json' if a.final else 'start-preservation.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'original_changed_or_missing':inherited_changes,'counts':{k:c['files'] for k,c in checks.items()}}))
if __name__=='__main__':main()
