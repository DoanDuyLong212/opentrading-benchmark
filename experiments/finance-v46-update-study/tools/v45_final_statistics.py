#!/usr/bin/env python3
"""Final main-only two-model family correction. Does not pool model outcomes."""
import argparse,json
from pathlib import Path

def combine(summaries):
    comparisons=[];models=[];notes=[]
    for summary in summaries:
        model=summary['model']
        if model in models:raise ValueError('Duplicate model cohort')
        models.append(model);data=summary['financial_v45']
        if not data.get('complete'):raise ValueError('Incomplete main schedule')
        for row in data.get('paired_task_cluster',[]):
            if row.get('candidate')!='opentrading' or row.get('control') not in ('opencode','dsh'):raise ValueError('Only final main OT/OC/DSH comparisons')
            comparisons.append({**row,'model':model})
    if len(comparisons)>8:raise ValueError('More than eight registered comparisons')
    running=0
    for rank,row in enumerate(sorted(comparisons,key=lambda x:x['p_one_sided_task_signflip'])):
        # Missing comparisons are implicitly p=1; never shrink multiplicity family.
        running=max(running,min(1,(8-rank)*row['p_one_sided_task_signflip']));row['p_holm_registered_eight']=running
        row['practical_statistical_superiority']=row['difference']>=.05 and row['ci95_task_cluster'][0]>0 and running<=.05
    for summary in summaries:
        arms=summary['financial_v45']['arms'];ot=arms['opentrading']
        operational=ot['fabricated_evidence_accepted']==0 and all(ot[f]<=arms[c][f] for c in ('opencode','dsh') for f in ('dnf','false_refusals','false_positives')) and all(ot['evidence_grounded']>=arms[c]['evidence_grounded'] for c in ('opencode','dsh'))
        relevant=[r for r in comparisons if r['model']==summary['model']]
        notes.append({'model':summary['model'],'operational_nonregression':operational,'superior_on_defined_benchmark':len(relevant)==4 and all(r['practical_statistical_superiority'] for r in relevant) and operational})
    return {'schema':'main-v45-eight-comparison-family','registered_comparisons':8,'observed_comparisons':len(comparisons),'models_analyzed_separately':models,'no_model_pooling':True,'comparisons':comparisons,'per_model':notes,'note':'Quality statistical screen; final claim additionally requires independent manual finance/audit PASS and preserved raw results. Missing cohort comparisons do not count as wins.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--summary',action='append',required=True);p.add_argument('--out',required=True);a=p.parse_args();result=combine([json.loads(Path(x).read_text()) for x in a.summary]);Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
