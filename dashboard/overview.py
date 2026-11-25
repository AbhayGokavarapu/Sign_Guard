"""Workspace overview: purposeful actions, current evidence and honest context."""
import json
from pathlib import Path
import streamlit as st
import config
from dashboard.components import (svg_icon, section_header, navigation_button, feature_card, card, empty_state, verdict_badge, metric_row)


def render():
    st.markdown(f'<div class="sg-hero"><div class="sg-hero-tag"><span class="sg-status-dot"></span>Clarity in every document</div><h1>Trust begins<br>with evidence.</h1><p>Look beyond the signature. Verify signed bytes, inspect document revisions, and uncover visual inconsistencies in a single forensic workspace.</p><div class="sg-hero-art">{svg_icon("shield",180)}</div><div class="sg-hero-footer"><span>Cryptographic integrity</span><span>Revision intelligence</span><span>Explainable findings</span></div></div>',unsafe_allow_html=True)
    a,b,c=st.columns([1,1,2])
    with a:navigation_button('Analyse a document →','Document analysis','home_analyse',True)
    with b:navigation_button('Explore the attack lab','Attack lab','home_lab')
    section_header('Three layers. One clear picture.')
    columns=st.columns(3,gap='medium')
    features=[('01','Verify the signature','Separate signed-byte integrity, mathematical validity and certificate trust.','shield'),
              ('02','Follow the revisions','Compare signed content with the current document, across every page.','layers'),
              ('03','Inspect visual evidence','Explore signature regions, recompression residuals and geometric duplication.','scan')]
    for col,args in zip(columns,features):
        with col:feature_card(*args)
    section_header('Your analysis workflow')
    st.markdown('<div class="sg-flow">'+''.join(f'<div class="sg-flow-step"><b>{n} &nbsp; {title}</b><span>{desc}</span></div>' for n,title,desc in [('01','Upload','Bring a PDF into the workspace.'),('02','Investigate','Review integrity and forensic findings.'),('03','Understand','Inspect measurements and visual evidence.'),('04','Export','Download a report for further review.')])+'</div>',unsafe_allow_html=True)
    left,right=st.columns([1.5,1])
    with left:
        section_header('Latest activity')
        result=st.session_state.get('pipeline_result')
        if result and result.parsed:
            card(f'<h3>{__import__("html").escape(result.parsed.file_name)}</h3><p>{result.parsed.page_count} pages · {result.elapsed_sec:.2f}s analysis</p>')
            verdict_badge(result.fusion.verdict.value)
            navigation_button('Open the evidence viewer →','Evidence viewer','home_evidence')
        else:empty_state('Your most recent document analysis will appear here. Start with a PDF or explore a controlled scenario.')
    with right:
        section_header('Research snapshot')
        path=Path(config.BENCHMARKS_DIR)/'evaluation_results.json'
        if path.exists():
            data=json.loads(path.read_text())
            metric_row(('Alert recall',f'{data["recall"]:.0%}','Held-out synthetic controls'),('Precision',f'{data["precision"]:.0%}','Review alerts include false positives'))
        st.caption('Synthetic results describe these controls, not real-world accuracy. View the complete evaluation, including missed cases and benign alerts.')
        navigation_button('View evaluation →','Evaluation','home_eval')
