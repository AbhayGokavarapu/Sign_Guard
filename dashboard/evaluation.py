"""Measured research outcomes with comparisons and transparent failure cases."""
import json
from pathlib import Path
import subprocess
import sys
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import config
from dashboard.components import (page_header, empty_state, metric_row, section_header, card)


def render():
    page_header('Evaluation','Measured outcomes on held-out synthetic controls. Explore the trade-offs, not just the headline numbers.','RESEARCH')
    root=Path(config.BENCHMARKS_DIR);path=root/'evaluation_results.json'
    if not path.exists():
        empty_state('No benchmark results have been generated yet.')
        return
    data=json.loads(path.read_text())
    metric_row(('Alert precision',f'{data["precision"]:.0%}','How often an alert matches a positive control'),('Alert recall',f'{data["recall"]:.0%}','Positive controls that triggered an alert'),('Held-out controls',data['total'],'Synthetic evaluation files'),('F1 score',f'{data["f1"]:.0%}','Precision / recall balance'))
    tabs=st.tabs(['Method comparison','Failure cases','Localisation & runtime','Per-document results','External checks'])
    with tabs[0]:
        section_header('What each layer adds')
        modes=data.get('ablations',{})
        labels={'crypto_only':'Cryptography','crypto_revision':'Cryptography + revisions','full':'Full pipeline'}
        fig=go.Figure()
        for key,color in [('precision','#a3b88c'),('recall','#276653')]:
            fig.add_bar(name=key.title(),x=[labels.get(x,x) for x in modes],y=[modes[x][key]*100 for x in modes],marker_color=color)
        fig.update_layout(barmode='group',height=340,paper_bgcolor='#ffffff',plot_bgcolor='#ffffff',font={'color':'#53634e','family':'sans-serif'},margin=dict(t=20,l=20,r=20,b=20),legend=dict(orientation='h',y=1.15),yaxis=dict(range=[0,110],title='Percent',gridcolor='#edf0e9'))
        st.plotly_chart(fig,width='stretch')
        st.caption('The full pipeline finds more positive controls, but also produces more benign alerts. Higher recall does not imply higher accuracy.')
        st.dataframe(pd.DataFrame([{**{'Method':labels.get(k,k)},**v} for k,v in modes.items()]),hide_index=True,width='stretch')
    with tabs[1]:
        section_header('Detection outcomes')
        metric_row(('True positives',data['TP'],'Positive controls flagged'),('False positives',data['FP'],'Benign controls flagged'),('False negatives',data['FN'],'Positive controls missed'),('True negatives',data['TN'],'Benign controls without alerts'))
        card('<h3>Known limitations, made visible</h3><p>Pasted image edits were missed in this evaluation. Benign annotations, repeated logos and raster text can trigger review alerts. These cases are part of the evaluation, not excluded from it.</p>')
        categories=data.get('per_category',{})
        st.dataframe(pd.DataFrame([{'Control':k.replace('_',' ').title(),'Detected':v['TP'],'Benign alerts':v['FP'],'Missed':v['FN'],'Benign negatives':v['TN']} for k,v in categories.items()]),hide_index=True,width='stretch')
    with tabs[2]:
        loc=json.loads((root/'localization_metrics.json').read_text());runtime=json.loads((root/'runtime_metrics.json').read_text())
        section_header('Signature region localisation')
        metric_row(('IoU precision',f'{loc.get("precision",0):.0%}','On annotated signature pages'),('IoU recall',f'{loc.get("recall",0):.0%}','One-to-one box matching at IoU ≥ 0.5'),('Documents',loc['sig_documents'],'Annotated held-out documents'))
        st.caption(loc['note'])
        section_header('Processing performance')
        metric_row(('Mean',f'{runtime["mean_s"]:.2f}s','Worker analysis time'),('Median',f'{runtime["median_s"]:.2f}s','Worker analysis time'),('Slowest',f'{runtime["max_s"]:.2f}s','Measured control'))
        st.caption('Narrow synthetic localisation results do not establish real-world performance or performance on non-signature pages.')
    with tabs[3]:
        records=[r for r in data.get('records',[]) if r.get('split')=='held_out']
        frame=pd.DataFrame(records)
        if not frame.empty:
            frame['file']=frame['file'].map(lambda x:Path(x).name)
            st.dataframe(frame[['file','category','pred','elapsed','coverage_complete']],hide_index=True,width='stretch')
    with tabs[4]:
        external_path=root/'independent_validation.json'
        if external_path.exists():
            external=json.loads(external_path.read_text())
            metric_row(('External files',external['total'],'Licensed upstream fixtures'),
                       ('Upstream checks matched',external['upstream_checks_matched'],'Documented upstream assertions'),
                       ('Human adjudication','Pending','Independent examiner still required'))
            st.caption(external['scope'])
            st.dataframe([{'File':Path(r['file']).name,
                'SignGuard math':[s['math_valid'] for s in r['signatures']],
                'Coverage':[s['coverage'] for s in r['signatures']],
                'Poppler math':[s['valid'] for s in r['poppler'].get('signatures',[])],
                'Upstream checks match':r['upstream_checks_match']} for r in external['records']],hide_index=True,width='stretch')
            st.caption('Poppler is run without certificate/OCSP network validation. A mathematically valid signature can still have nonstandard coverage; inspect the coverage findings.')
            st.download_button('Download external validation evidence',external_path.read_bytes(),'independent_validation.json','application/json')
        audit_path=root/'dependency_audit.json'
        if audit_path.exists():
            with st.expander('Dependency audit and inventory'):
                audit=json.loads(audit_path.read_text());dependencies=audit.get('dependencies',[])
                st.write(f"{len(dependencies)} Python components; {sum(len(d.get('vulns',[])) for d in dependencies)} known vulnerabilities; {sum('skip_reason' in d for d in dependencies)} skipped.")
                st.caption(audit.get('run_metadata',{}).get('checked_at',''))
                st.caption('Time-specific known-vulnerability database results, not a security guarantee. OS/native packages are outside this Python inventory.')
                st.download_button('Download dependency audit',audit_path.read_bytes(),'dependency_audit.json','application/json')
                sbom=root/'python-sbom.json'
                if sbom.exists():st.download_button('Download CycloneDX inventory',sbom.read_bytes(),'python-sbom.json','application/json')

    section_header('Reproduce and export')
    a,b=st.columns(2)
    with a:st.download_button('Download evaluation JSON',path.read_bytes(),'evaluation_results.json','application/json',width='stretch')
    with b:st.download_button('Download evaluation CSV',(root/'evaluation_results.csv').read_bytes(),'evaluation_results.csv','text/csv',width='stretch')
    with st.expander('Re-run the synthetic benchmark'):
        st.caption('Regenerates the dataset and runs three analysis modes. This may take several minutes. Regeneration is disabled on the public demo.')
        if st.button('Re-run evaluation',disabled=config.PUBLIC_DEMO):
            with st.spinner('Running evaluation…'):
                ret=subprocess.run([sys.executable,str(root/'run_evaluation.py')],cwd=config.BASE_DIR,capture_output=True,text=True,timeout=1200)
            if ret.returncode:st.error('Benchmark failed. '+ret.stderr[-1200:])
            else:st.rerun()
    st.caption(data.get('note','Synthetic controls only; no real-world accuracy claim.'))
