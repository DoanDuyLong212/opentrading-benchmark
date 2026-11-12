#!/usr/bin/env python3
"""Machine-readable task quality and overlap; holdout is hashes/counts only.

Does not claim financial facts have independent human verification. Original L1-L5
labels are retained as historical metadata; capability tags are separate.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',default='audits/contract-v2/task-quality.json');args=ap.parse_args()
    report={'version':2,'source_review_status':'not_independently_human_reviewed',
            'holdout_scope':'payload byte hashes, eligibility metadata and task counts only; no question/gold inspection',
            'capability_definition':'retrieval = value already returned; compute = arithmetic over inputs; aggregation = rank/filter/aggregate; evidence_check = refusal/consistency; synthesis = combine returned metrics; no task certified multi-hop by labels alone',
            'limitations':['holdout contains shared payloads with main; not an unseen-data generalization test',
                           'task-specific catalog narrows tool selection; does not measure full-catalog discovery',
                           'some pilot captures were manually trimmed/merged; original optional request parameters unavailable',
                           'scope is correctness relative to captured snapshots; original-source financial certification is outside this benchmark',
                           'CPI captures with ambiguous duplicate indicator/period/unit rows are diagnostic only and excluded from confirmatory scoring',
                           'narrative tasks requesting full close sequences but accepting incomplete evidence remain diagnostic only',
                           'valuation_run outputs multiples; these tasks do not measure independent fair-value valuation'],
            'splits':{},'tasks':[]}
    hashes=collections.defaultdict(list)
    for split in ['main','pilot','smoke','holdout']:
        tasks=sorted((ROOT/'tasks'/split).glob('*/task.toml'));report['splits'][split]={'n':len(tasks)}
        for p in tasks:
            payload=p.parent/'environment/payloads.json';h=hashlib.sha256(payload.read_bytes()).hexdigest();hashes[h].append({'split':split,'task':p.parent.name})
            meta=tomllib.loads(p.read_text())
            if not meta.get('confirmatory_eligible',True):
                report['splits'][split]['diagnostic_only']=report['splits'][split].get('diagnostic_only',0)+1
            if split=='holdout':continue
            tid=p.parent.name
            family=meta.get('family','')
            if any(x in tid for x in ['nonexist','future','trap','narrative','2src','2nguon']):cap='evidence_check'
            elif any(x in tid for x in ['growth','margin','gold','l2-crypto']):cap='compute' if 'l2-' in tid else 'retrieval'
            elif any(x in tid for x in ['agg','screen','top','index','multi']):cap='aggregation'
            elif any(x in tid for x in ['profile','compare']):cap='synthesis'
            else:cap='retrieval'
            row={'task':tid,'split':split,'original_level':meta.get('level'),'capability':cap,
                 'family':family,'payload_sha256':h,'source_review_status':'not_independently_human_reviewed',
                 'confirmatory_eligible':meta.get('confirmatory_eligible',True),
                 'exclusion_reason':meta.get('exclusion_reason'),
                 'multi_hop_verified':False}
            if 'valuation' in tid:row['limitation']='multiple extraction; no fair-value model'
            if 'l2-ratio' in tid or 'l2-tech' in tid:row['limitation']='precomputed ratio/indicator retrieval; historical L2 label overstates calculation'
            report['tasks'].append(row)
    report['overlap']={'main_holdout_shared_payload_groups':[], 'main_unique_payloads':sum(any(x['split']=='main' for x in group) for group in hashes.values())}
    for h,group in hashes.items():
        splits={x['split'] for x in group}
        if {'main','holdout'}<=splits:report['overlap']['main_holdout_shared_payload_groups'].append({'sha256':h,'members':group})
    report['overlap']['holdout_tasks_sharing_main_payload']=sum(sum(x['split']=='holdout' for x in g['members']) for g in report['overlap']['main_holdout_shared_payload_groups'])
    report['capability_counts']=dict(collections.Counter(row['capability'] for row in report['tasks']))
    path=ROOT/args.out;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'tasks_labeled':len(report['tasks']),'capability_counts':report['capability_counts'],'holdout_shared':report['overlap']['holdout_tasks_sharing_main_payload']}))


if __name__=='__main__':main()
