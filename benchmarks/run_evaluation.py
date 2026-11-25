"""Measure held-out security outcomes, benign controls, ablations and localisation IoU."""
import csv
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from core.pipeline import run
from core.signature_localizer import localize
from simulation.evaluation_dataset import generate_evaluation_dataset


def metrics(rows):
    tp=fp=fn=tn=unsupported=0
    for row in rows:
        positive = row['positive']
        predicted = row['pred'] in ('TAMPERING DETECTED','REVIEW REQUIRED')
        unsupported += row['pred']=='UNSUPPORTED'
        if positive and predicted: tp+=1
        elif not positive and predicted: fp+=1
        elif positive: fn+=1
        else: tn+=1
    n=len(rows); p=tp/max(tp+fp,1); r=tp/max(tp+fn,1)
    # Unsupported negative controls are not counted as correct decisions.
    correct=sum(row['pred']!='UNSUPPORTED' and row['positive']==(row['pred'] in ('TAMPERING DETECTED','REVIEW REQUIRED')) for row in rows)
    return dict(total=n,evaluated=n,unsupported=unsupported,TP=tp,FP=fp,FN=fn,TN=tn,
        accuracy=round(correct/max(n,1),4),precision=round(p,4),recall=round(r,4),f1=round(2*p*r/max(p+r,1e-12),4))


def wilson(success,n):
    if not n:return [0,1]
    z=1.96; p=success/n; d=1+z*z/n
    center=(p+z*z/(2*n))/d
    margin=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [round(max(0,center-margin),4),round(min(1,center+margin),4)]


def iou(a,b):
    x,y,w,h=a; u,v,s,t=b
    inter=max(0,min(x+w,u+s)-max(x,u))*max(0,min(y+h,v+t)-max(y,v))
    return inter/max(w*h+s*t-inter,1)


def main():
    start=time.perf_counter(); manifest=generate_evaluation_dataset()
    records=[]; ablations={mode:[] for mode in ('crypto_only','crypto_revision','full')}
    loc_tp=loc_fp=loc_fn=0; sig_docs=found=0
    for entry in manifest['files']:
        raw=(Path(config.BASE_DIR)/entry['file']).read_bytes()
        outputs={}
        modes=ablations if entry['split']=='held_out' else ('full',)
        for mode in modes:
            result=run(raw,Path(entry['file']).name,analysis_mode=mode,record_audit=False)
            outputs[mode]=result
            row={**entry,'pred':result.fusion.verdict.value,'elapsed':result.elapsed_sec,
                'cls_pred':result.classification.doc_class.value if result.classification else 'Unsupported',
                'n_cands':result.coverage.get('candidates_found',0),
                'finding_codes':sorted({f.code for f in result.fusion.findings}),
                'coverage_complete':result.coverage.get('complete',False),
                'processing_error':result.processing_error}
            if entry['split']=='held_out':ablations[mode].append(row)
            if mode=='full':records.append(row)
        if entry['signature_boxes'] and entry['split']=='held_out':
            sig_docs+=1; detected=False
            # IoU matching uses actual per-page detector boxes and independent annotations.
            for page in sorted({b['page'] for b in entry['signature_boxes']}):
                candidates=localize(raw,page).candidates
                truth=[b['bbox'] for b in entry['signature_boxes'] if b['page']==page]
                matched=set()
                for box in truth:
                    scored=sorted(((iou(box,c.bbox),i) for i,c in enumerate(candidates) if i not in matched),reverse=True)
                    if scored and scored[0][0]>=.5:
                        matched.add(scored[0][1]);loc_tp+=1;detected=True
                    else:loc_fn+=1
                loc_fp+=len(candidates)-len(matched)
            found+=detected
        print(entry['split'],entry['category'],outputs['full'].fusion.verdict.value,flush=True)
    held=[r for r in records if r['split']=='held_out']; task=metrics(held)
    groups={kind:metrics([r for r in held if r['category']==kind]) for kind in sorted({r['category'] for r in held})}
    for name,m in groups.items():m['recall_95pct_wilson']=wilson(m['TP'],m['TP']+m['FN'])
    full={'generated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'total_files':len(records),'total_time_s':round(time.perf_counter()-start,3),
        'note':manifest['note'],'evaluation_split':'held_out','records':records,**task,
        'per_category':groups,'ablations':{mode:metrics(rows) for mode,rows in ablations.items()},
        'confirmed_integrity_failures':sum('CRYPTO-001' in r['finding_codes'] for r in held),
        'review_alerts':sum(r['pred']=='REVIEW REQUIRED' for r in held)}
    cls_correct=sum(r['expected_class']==r['cls_pred'] for r in held)
    classes=sorted({r['expected_class'] for r in held})
    cls={'total':len(held),'correct':cls_correct,'incorrect':len(held)-cls_correct,'accuracy':cls_correct/len(held),
        'note':'Held-out synthetic classification; repeated logos/image regions are candidate heuristics.',
        'per_class':{c:{'precision':sum(r['cls_pred']==c and r['expected_class']==c for r in held)/max(sum(r['cls_pred']==c for r in held),1),
                        'recall':sum(r['cls_pred']==c and r['expected_class']==c for r in held)/max(sum(r['expected_class']==c for r in held),1)} for c in classes}}
    loc={'sig_documents':sig_docs,'at_least_one_found':found,'none_found':sig_docs-found,'detection_rate':found/max(sig_docs,1),
         'TP':loc_tp,'FP':loc_fp,'FN':loc_fn,'iou_threshold':.5,'precision':loc_tp/max(loc_tp+loc_fp,1),'recall':loc_tp/max(loc_tp+loc_fn,1),
         'note':'IoU >= 0.5 one-to-one matching on annotated held-out signature pages; FP counts only those pages.'}
    times=[r['elapsed'] for r in held]
    runtime={'n_files':len(held),'mean_s':statistics.mean(times),'median_s':statistics.median(times),'max_s':max(times),
             'environment':{'python':sys.version,'platform':sys.platform},'note':'Worker analysis time; total evaluation time also includes process startup and dataset generation.'}
    dest=Path(config.BENCHMARKS_DIR)
    for filename,data in [('evaluation_results.json',full),('tampering_metrics.json',task),('classification_metrics.json',cls),
                          ('localization_metrics.json',loc),('runtime_metrics.json',runtime),('dataset_manifest.json',manifest)]:
        (dest/filename).write_text(json.dumps(data,indent=2))
    fields=['file','category','split','label','pred','cls_pred','n_cands','elapsed','coverage_complete']
    with (dest/'evaluation_results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(records)
    print(json.dumps({'held_out':task,'ablations':full['ablations'],'localisation':loc},indent=2))


if __name__=='__main__':main()
