"""Evidence viewer: focused images and measurements, separated by method."""
import streamlit as st
from dashboard.components import (page_header, empty_state, navigation_button, show_image, metric_row)


def render():
    page_header('Evidence viewer','Inspect the measurements and intermediate images behind your analysis.','EVIDENCE')
    sources={}
    if st.session_state.get('pipeline_result'):sources['Uploaded document']=st.session_state['pipeline_result']
    if st.session_state.get('evidence_result'):sources['Latest lab scenario']=st.session_state['evidence_result']
    if not sources:
        empty_state('Analyse a document or run a lab scenario to populate this workspace.','scan')
        a,b=st.columns(2)
        with a:navigation_button('Analyse a document →','Document analysis','evidence_analyse',True)
        with b:navigation_button('Open the attack lab','Attack lab','evidence_lab')
        return
    selected=st.selectbox('Evidence source',list(sources));result=sources[selected]
    if result.parsed:st.caption(result.parsed.file_name+' · SHA-256 '+result.parsed.sha256[:24]+'…')
    tabs=st.tabs(['Signature regions','ELA residuals','Feature matching','Revision changes','Evidence ledger'])
    with tabs[0]:
        loc=result.localization
        if loc:
            st.caption(f'Representative page {loc.page_index+1} · Scores are heuristic, not probabilities. All-page summaries are in the evidence ledger.')
            show_image(loc.annotated,'Detected signature-like regions')
            with st.expander('Inspect localisation stages'):
                a,b,c=st.columns(3)
                with a:show_image(loc.gray,'Grayscale')
                with b:show_image(loc.text_masked,'Text suppressed')
                with c:show_image(loc.thresholded,'Thresholded regions')
            for i,candidate in enumerate(loc.candidates):
                with st.expander(f'Region {i+1} · Page {candidate.page+1} · Heuristic score {candidate.confidence:.2f}'):
                    show_image(candidate.crop)
        else:empty_state('Signature localisation is not available for this analysis.')
    with tabs[1]:
        ela=result.ela
        if ela and not ela.error:
            selected_q=st.selectbox('JPEG quality',sorted(ela.multi_quality),key='viewer_ela_quality')
            sample=ela.multi_quality[selected_q]
            metric_row(('Mean residual',f'{sample.mean_residual:.2f}','Unamplified measurement'),('High-energy pixels',f'{sample.high_pct:.2f}%','Raw residual threshold'))
            a,b=st.columns(2)
            with a:show_image(ela.original,'Analysed image')
            with b:show_image(sample.amplified,'Amplified residual · Display only')
            with st.expander('Raw residual image'):show_image(sample.raw_diff)
            st.caption('Recompression residuals can result from ordinary text, edges and textures. ELA alone does not establish manipulation.')
        else:empty_state('ELA evidence is not available for this result.')
    with tabs[2]:
        if result.orb:
            orb=result.orb;rs=result.ransac
            metric_row(('Keypoints A',orb.n_kp_a,'First region'),('Keypoints B',orb.n_kp_b,'Second region'),('Filtered matches',orb.n_filtered,'Reciprocal ratio matches'))
            if rs:
                show_image(rs.inlier_vis,'Geometric consistency · Green inliers / red outliers')
                st.write(rs.summary)
            st.caption('Repeated legitimate artwork can match. This evidence does not establish unauthorised signature reuse.')
        else:empty_state('Feature matching needs at least two suitable candidate regions.')
    with tabs[3]:
        rv=result.revision
        if rv:
            st.write(rv.summary)
            if rv.signed_rev_image:
                a,b=st.columns(2)
                with a:show_image(rv.signed_rev_image,'Earliest signed revision')
                with b:show_image(rv.current_image,'Current revision')
            if rv.diff_image:show_image(rv.diff_image,'Pixel difference')
            st.dataframe([{'Revision':r.index+1,'Signed':r.is_signed,'End offset':r.end_offset,'Pages':r.page_count} for r in rv.revisions],hide_index=True,width='stretch')
        else:empty_state('No revision comparison is available.')
    with tabs[4]:
        st.markdown('**Analysis coverage**');st.json(result.coverage)
        with st.expander('Per-page measurements'):st.json(result.page_results)
        with st.expander('Compared candidate pairs'):st.json(result.pair_results)
