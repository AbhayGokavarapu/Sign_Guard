"""Controlled scenarios with a clear generate → inspect → analyse workflow."""
import hashlib
import streamlit as st
from simulation.controlled_scenarios import ALL_SCENARIOS
from core.pipeline import run as run_pipeline
from core.pdf_parser import render_page
from dashboard.components import (page_header, card, section_header, empty_state, show_image, navigation_button)
from dashboard.document_analysis import render_results


def render():
    page_header('Attack lab','Explore controlled scenarios and see which evidence the detector actually produces.','INVESTIGATE')
    left,right=st.columns([1.6,1],gap='large')
    with left:
        scenario=st.selectbox('Choose a scenario',ALL_SCENARIOS,format_func=lambda s:s.name,key='lab_scenario')
        st.write(scenario.description)
        st.caption('Synthetic documents · Ground-truth labels are withheld from the detector.')
        if st.button('Generate scenario',key='lab_generate',type='primary',width='stretch'):
            with st.spinner('Preparing controlled documents…'):
                try:
                    original,modified,truth=scenario.factory()
                    st.session_state['lab_'+scenario.id]=(original,modified,truth)
                    st.session_state.pop('lab_result_'+scenario.id,None)
                except Exception as exc:st.error(str(exc))
    with right:
        card('<div class="sg-eyebrow">HOW TO READ THE LAB</div><p>A cryptographic failure is different from a review alert. Compare the documents, run the detector, then reveal the known scenario label. Visual similarity alone never proves fraud.</p>')
    sample=st.session_state.get('lab_'+scenario.id)
    if sample is None:
        section_header('Your investigation starts here')
        empty_state('Choose a scenario and generate the documents to inspect their differences.','scan')
        return
    original,modified,truth=sample
    section_header('Compare the documents')
    same=original==modified
    st.caption('Identical files — baseline/control scenario.' if same else 'Different file hashes. A visible difference is not required for cryptographic tampering.')
    with st.expander('Original and scenario document',expanded=True):
        a,b=st.columns(2,gap='large')
        with a:
            st.markdown('**Original document**')
            show_image(render_page(original,dpi=96))
            st.caption('SHA-256 '+hashlib.sha256(original).hexdigest()[:24]+'…')
        with b:
            st.markdown('**Scenario document**')
            show_image(render_page(modified,dpi=96))
            st.caption('SHA-256 '+hashlib.sha256(modified).hexdigest()[:24]+'…')
    if st.button('Analyse scenario →',key='lab_analyse',type='primary',width='stretch'):
        with st.spinner('Running the detection workflow…'):
            result=run_pipeline(modified,'scenario_'+scenario.id+'.pdf')
            st.session_state['lab_result_'+scenario.id]=result
            st.session_state['evidence_result']=result
    result=st.session_state.get('lab_result_'+scenario.id)
    if result:
        render_results(result,prefix='lab_'+scenario.id)
        with st.expander('Reveal the ground-truth label'):
            st.write(truth.replace('_',' ').title())
            st.caption('Evaluation label only. This label was never passed to the detection engine.')
        navigation_button('Explore the visual evidence →','Evidence viewer','lab_view_evidence')
