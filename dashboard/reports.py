"""Evidence exports and optional local audit custody."""
import json
import pandas as pd
import streamlit as st
import config
from dashboard.components import (page_header, card, section_header, feature_card, report_downloads, empty_state, navigation_button)
from core.audit_logger import verify_chain,get_records,export_checkpoint


def render():
    page_header('Reports & audit','Keep a reviewable record of the document, findings, measurements and analysis coverage.','EXPORT')
    result=st.session_state.get('pipeline_result')
    if result:
        if result.parsed:
            card(f'<div class="sg-eyebrow">CURRENT DOCUMENT</div><h3>{__import__("html").escape(result.parsed.file_name)}</h3><p>Analysed {result.analysis_ts} · {result.elapsed_sec:.2f}s processing time</p>')
        section_header('Choose your export')
        a,b=st.columns(2)
        with a:feature_card('PDF','Forensic report','A readable summary of verification states, findings and limitations.','file')
        with b:feature_card('JSON','Structured evidence','Document identity, measurements, per-page results and checked candidate pairs.','layers')
        report_downloads(result,'reports')
        from reporting.json_report import build_report
        with st.expander('Preview structured evidence'):st.json(build_report(result))
    else:
        empty_state('Analyse a document to generate downloadable evidence and a forensic report.')
        navigation_button('Start a document analysis →','Document analysis','reports_start',True)
    section_header('Audit custody')
    if config.PUBLIC_DEMO:
        st.info('Shared audit history is disabled for the public demo. Download your reports before leaving; hosted storage is temporary.')
        return
    ok,message=verify_chain()
    (st.success if ok else st.error)(message)
    st.caption('Hash linking can reveal inconsistent records. Detecting a full rewrite or truncation requires an independently retained checkpoint.')
    if ok:
        st.download_button('Export independent audit checkpoint',json.dumps(export_checkpoint(),indent=2),'audit_checkpoint.json','application/json')
    try:records=get_records()
    except ValueError as exc:st.error(str(exc));return
    if records:
        with st.expander(f'Inspect {len(records)} audit records'):
            frame=pd.DataFrame(records)
            for name in ('doc_hash','prev_hash','record_hash'):
                if name in frame:frame[name]=frame[name].str[:20]+'…'
            st.dataframe(frame,hide_index=True,width='stretch')
