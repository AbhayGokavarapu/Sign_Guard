"""A guided presentation that keeps the workspace navigation accessible."""
import streamlit as st
from dashboard.components import (page_header, section_header, empty_state, result_summary, show_image, finding_card, report_downloads)
from core.pipeline import run as run_pipeline
from simulation.controlled_scenarios import ALL_SCENARIOS
from simulation.security_fixtures import signed_control

STEPS=['Choose a document','Verify the baseline','Demonstrate a change','Inspect the evidence','Export the conclusion']


def _move(value):st.session_state['pres_step']=value


def render():
    page_header('Presentation','A guided walkthrough from a signed document to explainable forensic evidence.','GUIDED DEMO')
    step=st.session_state.get('pres_step',0)
    st.progress((step+1)/len(STEPS),text=f'Step {step+1} of {len(STEPS)} · {STEPS[step]}')
    a,b,c=st.columns([1,1,3])
    with a:st.button('← Previous',disabled=step==0,on_click=_move,args=(step-1,),width='stretch')
    with b:st.button('Next →',disabled=step==4,on_click=_move,args=(step+1,),width='stretch')
    with c:st.button('Restart walkthrough',on_click=_move,args=(0,))
    section_header(STEPS[step])
    if step==0:
        uploaded=st.file_uploader('Choose a PDF for the walkthrough',type=['pdf'],key='presentation_upload')
        if uploaded:
            digest=__import__('hashlib').sha256(uploaded.getvalue()).hexdigest()
            if st.session_state.get('pres_hash')!=digest:
                st.session_state['pres_raw']=uploaded.getvalue();st.session_state['pres_name']=uploaded.name
                st.session_state['pres_hash']=digest
                st.session_state.pop('pres_result',None);st.session_state.pop('pres_sc_result',None)
            st.success('Document ready. Continue to baseline verification.')
        st.caption('Or use a genuinely signed synthetic control, with a self-signed test certificate.')
        if st.button('Load signed demo document',type='primary'):
            st.session_state['pres_raw']=signed_control();st.session_state['pres_name']='signed_demo.pdf'
            st.session_state.pop('pres_result',None);st.session_state.pop('pres_sc_result',None)
            st.success('Signed demo document ready. Continue to step 2.')
    elif step==1:
        raw=st.session_state.get('pres_raw')
        if raw is None:empty_state('Choose a document in step 1 first.');return
        st.write(st.session_state.get('pres_name','document.pdf'))
        if st.button('Verify baseline →',type='primary'):
            with st.spinner('Verifying the document…'):st.session_state['pres_result']=run_pipeline(raw,st.session_state.get('pres_name','document.pdf'))
        result=st.session_state.get('pres_result')
        if result:result_summary(result)
    elif step==2:
        scenario=st.selectbox('Controlled demonstration',ALL_SCENARIOS,format_func=lambda s:s.name,key='pres_scenario')
        st.write(scenario.description)
        if st.button('Generate and analyse scenario →',type='primary'):
            with st.spinner('Preparing the scenario and collecting evidence…'):
                _,raw,truth=scenario.factory()
                st.session_state['pres_sc_result']=run_pipeline(raw,'scenario_'+scenario.id+'.pdf')
                st.session_state['pres_sc_gt']=truth
        result=st.session_state.get('pres_sc_result')
        if result:
            result_summary(result)
            with st.expander('Reveal scenario label'):st.write(st.session_state.get('pres_sc_gt','').replace('_',' '))
    elif step==3:
        result=st.session_state.get('pres_sc_result') or st.session_state.get('pres_result')
        if not result:empty_state('Complete baseline verification or a scenario first.');return
        tabs=st.tabs(['Revisions','Signature regions','Residuals','Geometric matches'])
        with tabs[0]:
            if result.revision and result.revision.diff_image:show_image(result.revision.diff_image,'Difference between signed and current content')
            else:st.info('No visible revision difference is available.')
        with tabs[1]:
            if result.localization:show_image(result.localization.annotated,'Representative signature regions')
        with tabs[2]:
            if result.ela:show_image(result.ela.amplified,'Amplified ELA residuals · Supporting evidence only')
        with tabs[3]:
            if result.ransac:show_image(result.ransac.inlier_vis,'RANSAC inliers and outliers')
            else:st.info('No matching candidate pair is available.')
    else:
        result=st.session_state.get('pres_sc_result') or st.session_state.get('pres_result')
        if not result:empty_state('Complete the previous steps to produce a conclusion.');return
        result_summary(result)
        if result.fusion:
            for finding in result.fusion.findings:finding_card(finding.code,finding.severity.value,finding.title,finding.description)
        report_downloads(result,'presentation')
        st.caption('Explain the limitations alongside the outcome. This report is not an authenticity certificate.')
