"""Hash-bound all-arm memory financial review. Only removes immutable auto wins."""
import json
from pathlib import Path
from run_manifest import hash_file,digest_json
CHECKS=('user_facts','current_rule','source','entity','period','unit','scope','arithmetic','narrative_claims','native_persistence')
def protected_artifacts(out):
 out=Path(out);files={}
 for name in ('manifest.json','completed-resume-proof.json'):
  if (out/name).is_file():files[name]=hash_file(out/name)
 for p in sorted((out/'episodes').rglob('*')):
  if p.is_file()and not p.is_symlink():files[str(p.relative_to(out))]=hash_file(p)
 return digest_json(files)
def apply_review(out,rows,manifest):
 out=Path(out);path=out/'memory-financial-review.json'
 if not path.exists():return rows,{'review_complete':False,'status':'pending'}
 review=json.loads(path.read_text());expected={r['trial_id']for r in rows if r.get('success')or r.get('episode_grounded_financial_success')or r.get('memory_state_correctness')};decisions=review.get('decisions',{})
 audit=out/'memory-audit.json'
 if review.get('schema')!='independent-memory-financial-review-v45'or review.get('manifest_sha256')!=hash_file(out/'manifest.json')or review.get('protected_artifacts_sha256')!=protected_artifacts(out)or not audit.exists()or review.get('automatic_audit_sha256')!=hash_file(audit)or not review.get('reviewer')or review.get('independent')is not True or set(decisions)!=expected:raise ValueError('Incomplete/changed independent all-arm memory review binding')
 for tid,item in decisions.items():
  if type(item.get('pass'))is not bool or set(item.get('checks',{}))!=set(CHECKS)or any(type(v)is not bool for v in item['checks'].values())or item['pass']!=all(item['checks'].values())or not item.get('evidence_notes'):raise ValueError('Incomplete memory/source/narrative review: '+tid)
 copies=[]
 for original in rows:
  row=dict(original)
  for key in ('success','episode_grounded_financial_success','memory_state_correctness'):row['automatic_'+key]=row.get(key)
  decision=decisions.get(row['trial_id']);row['manual_financial_reviewed']=True
  if decision and not decision['pass']:
   row.update(success=False,episode_grounded_financial_success=False,grounded_financial_correctness=False,memory_state_correctness=False,manual_financial_rejection=True)
  copies.append(row)
 return copies,{'status':'complete','review_complete':True,'review_sha256':hash_file(path),'reviewed_automatic_wins':len(expected),'rejected_automatic_wins':sum(not x['pass']for x in decisions.values()),'accepted_financial_fabrications':0,'automatic_artifacts_preserved':True}
