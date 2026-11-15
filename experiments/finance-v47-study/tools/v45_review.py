"""Preregistered independent all-arm financial claim adjudication, every split.
Preserves automatic rows/grades. Manual decisions are separate, hash-bound and
can only remove automatic wins; never rescue a failed answer or select retries.
"""
import json
from pathlib import Path
from run_manifest import hash_file,digest_json
REVIEW_CHECKS=('source','entity','period','unit','scope','arithmetic','narrative_claims')


def protected_artifacts(out):
    out=Path(out).resolve();files={}
    for name in ('manifest.json','trials.jsonl','completed-resume-proof.json'):
        path=out/name
        if path.is_file():files[name]=hash_file(path)
    for folder in ('trials',):
        root=out/folder
        if root.is_dir():
            for path in sorted(root.rglob('*')):
                if path.is_file() and not path.is_symlink():files[str(path.relative_to(out))]=hash_file(path)
    return digest_json(files)


def load_review(out,rows,manifest):
    out=Path(out);path=out/'financial-review.json'
    if not path.exists():return {'status':'pending','review_complete':False},None
    review=json.loads(path.read_text());expected={r['trial_id'] for r in rows if r.get('success') or r.get('grounded_financial_correctness')};decisions=review.get('decisions',{})
    if review.get('schema')!='independent-financial-review-v45' or review.get('manifest_sha256')!=manifest['fingerprint'] or review.get('protected_artifacts_sha256')!=protected_artifacts(out) or not review.get('reviewer') or review.get('independent') is not True or set(decisions)!=expected:raise ValueError('Manual financial review missing/changed all-win manifest/artifact/reviewer binding')
    auditpath=out/'audit-v45.json'
    if not auditpath.exists() or review.get('automatic_audit_sha256')!=hash_file(auditpath):raise ValueError('Manual review automatic audit endpoints changed')
    for tid,item in decisions.items():
        if type(item.get('pass')) is not bool or set(item.get('checks',{}))!=set(REVIEW_CHECKS) or any(type(v) is not bool for v in item['checks'].values()) or item['pass']!=all(item['checks'].values()) or not item.get('evidence_notes'):raise ValueError('Manual claim check incomplete: '+tid)
    return {'status':'complete','review_complete':True,'reviewer':review['reviewer'],'reviewed_automatic_wins':len(expected),'rejected_automatic_wins':sum(not x['pass'] for x in decisions.values()),'accepted_financial_fabrications':0,'review_sha256':hash_file(path)},review


def apply_review(out,rows,manifest):
    status,review=load_review(out,rows,manifest)
    if review is None:return rows,status
    copies=[]
    for original in rows:
        row=dict(original);decision=review['decisions'].get(row['trial_id'])
        row['automatic_success']=row.get('success');row['automatic_grounded_financial_correctness']=row.get('grounded_financial_correctness')
        if decision and not decision['pass']:
            row.update(success=False,grounded_financial_correctness=False,manual_financial_rejection=True,error_type='manual_financial_claim_rejection')
            if decision.get('fabricated_numeric_claim') and row.get('_scoring')=='refusal':row['fp']=1
        copies.append(row)
    return copies,status
