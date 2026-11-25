"""Append human assessments without replacing automated security findings."""
import json
import streamlit as st
from core.review import finding_id,record_review,verify_reviews,STATUSES
from dashboard.components import page_header,empty_state,navigation_button,finding_card


def reviews_for(result):
    if not result or not result.parsed:return []
    return st.session_state.get('human_reviews',{}).get(result.parsed.sha256,[])


def render():
    page_header('Case review','Record an examiner’s assessment separately from the automated findings.','HUMAN REVIEW')
    sources={}
    for key,label in [('pipeline_result','Uploaded document'),('evidence_result','Latest lab scenario')]:
        result=st.session_state.get(key)
        if result and result.parsed and result.fusion:sources[label]=result
    if not sources:
        empty_state('Analyse a document or scenario before reviewing its findings.')
        navigation_button('Start an analysis →','Document analysis','review_start',True)
        return
    selected=st.selectbox('Review source',list(sources));result=sources[selected]
    st.caption('Document SHA-256: '+result.parsed.sha256)
    st.info('Reviewer names are self-asserted. Assessments do not change the detector’s verdict and are retained only in this session until exported.')
    if not result.fusion.findings:st.info('There are no automated findings to assess for this document.');return
    finding=st.selectbox('Finding to review',result.fusion.findings,format_func=lambda f:f.code+' — '+f.title)
    finding_card(finding.code,finding.severity.value,finding.title,finding.description)
    with st.form('human_review_form'):
        status=st.selectbox('Assessment',STATUSES,index=2)
        reviewer=st.text_input('Examiner name or reference (optional)',max_chars=120)
        reason=st.text_area('Reason and supporting observations',max_chars=4000)
        submit=st.form_submit_button('Save assessment',type='primary')
    if submit:
        try:
            all_reviews=dict(st.session_state.get('human_reviews',{}))
            history=all_reviews.get(result.parsed.sha256,[])
            all_reviews[result.parsed.sha256]=record_review(history,result.parsed.sha256,finding,status,reason,reviewer)
            st.session_state['human_reviews']=all_reviews
            st.success('Assessment added. The machine finding and verdict remain unchanged.')
        except ValueError as exc:st.error(str(exc))
    history=reviews_for(result)
    if history:
        st.caption(f'{len(history)} review events · Chain consistent: {verify_reviews(history)}')
        st.dataframe([{'Assessment':r['assessment'],'Finding':r['finding_code'],'Reason':r['reason'],'Examiner':r['reviewer_claimed_name'],'Time':r['timestamp']} for r in history],hide_index=True,width='stretch')
        st.download_button('Export review history JSON',json.dumps(history,indent=2),'human-review.json','application/json')
        st.caption('The complete history is also included when exporting this document’s evidence package.')
