"""Document intake and focused analysis results."""
from html import escape
import hashlib
import json
from pathlib import Path
import config
import streamlit as st
from core.pipeline import run as run_pipeline
from dashboard.components import (page_header, section_header, result_summary, metric_row, status_pill, finding_card, report_downloads, show_image, card, feature_card, svg_icon)


def render_results(result,prefix='analysis'):
    section_header('Analysis outcome')
    result_summary(result)
    if not result.fusion:return
    tabs=st.tabs(['Findings','Digital signatures','Document revisions','Static content','Independent rendering','Coverage'])
    with tabs[0]:
        if result.fusion.findings:
            for finding in result.fusion.findings:
                finding_card(finding.code,finding.severity.value,finding.title,finding.description)
                if finding.page is not None: st.caption(f'Page {finding.page+1} · {finding.module}')
                if finding.limitation: st.caption(finding.limitation)
        else:
            st.info('No decisive forensic findings. This does not establish document authenticity or signer identity.')
    with tabs[1]:
        if result.crypto and result.crypto.total_sigs:
            for sig in result.crypto.results:
                with st.container(border=True):
                    st.markdown('**'+sig.field_name+'**')
                    a,b=st.columns(2)
                    with a:
                        status_pill('Signed-byte integrity',sig.integrity_ok)
                        status_pill('Mathematical signature',sig.math_valid)
                        status_pill('Certificate trust',sig.cert_trusted)
                    with b:
                        st.caption('SIGNER AND POLICY')
                        st.write(sig.trust_status)
                        st.caption('Identity: '+sig.identity_status)
                        st.caption('Modification policy: '+sig.modpolicy_status)
                    if sig.cert_info:
                        st.caption('Subject: '+sig.cert_info.subject)
                        st.caption('Issuer: '+sig.cert_info.issuer)
                    st.caption(f'Revocation: {sig.revocation_status} · Timestamp: {sig.timestamp_status}')
                    if sig.byte_range:
                        st.caption(f'ByteRange structural validity: {sig.byte_range.structurally_valid} · Covers current file: {sig.byte_range.covers_full_file}')
        else:st.info('No embedded digital signatures are available for verification.')
    with tabs[2]:
        if result.revision:
            rv=result.revision
            metric_row(('Revisions',len(rv.revisions),'Parsed PDF history'),('Visible change',f'{rv.changed_area_pct:.2f}%','Representative comparison page'))
            st.write(rv.summary)
            with st.expander('Consecutive revision timeline'):
                st.json(result.timeline)
            if rv.signed_rev_image and rv.current_image:
                a,b=st.columns(2)
                with a:show_image(rv.signed_rev_image,'Signed revision')
                with b:show_image(rv.current_image,'Current revision')
            if rv.diff_image:
                with st.expander('Inspect the pixel difference'):show_image(rv.diff_image,'Changed pixels')
        else:st.info('Revision comparison is not available for this result.')
    with tabs[3]:
        st.caption(result.active_content.get('note','Static inspection not available.'))
        if result.active_content.get('entries'):st.dataframe(result.active_content['entries'],hide_index=True,width='stretch')
        else:st.info('No listed action, embedded-file or external-link structures were found within the inspected objects.')
    with tabs[4]:
        if result.renderer_comparison:
            st.json(result.renderer_comparison)
        else:st.info('Enable the independent rendering check in analysis settings to compare MuPDF and Poppler.')
    with tabs[5]:
        st.json(result.coverage,expanded=True)
        with st.expander('Analysis limitations'):
            for limitation in result.fusion.limitations:st.write('• '+limitation)
    section_header('Keep the evidence')
    report_downloads(result,prefix)


def render():
    page_header('Document analysis','Upload a PDF, verify its integrity, and review the evidence behind each finding.','ANALYSE')
    left,right=st.columns([2.3,1],gap='large')
    with left:
        uploaded=st.file_uploader('Choose a PDF document',type=['pdf'],key='document_upload_'+str(st.session_state.get('_upload_epoch',0)),help='PDF only. Maximum 50 MB. Encrypted and excessive rendering workloads are rejected.')
    with right:
        card('<div class="sg-eyebrow">BEFORE YOU UPLOAD</div><p>Use a document you are authorised to analyse. Public demo files are processed on the hosting server. Keep a copy of your exported report.</p>')
    kit_root=Path(config.BASE_DIR)/'samples'/'upload-kit'
    manifest=kit_root/'verified_results.json'
    if manifest.exists():
        with st.expander('Need a document? Download a verified sample',expanded=uploaded is None):
            samples=json.loads(manifest.read_text())
            sample=st.selectbox('Sample document',samples,format_func=lambda item:item['file']+' — '+item['title'],key='upload_sample_choice')
            st.caption(sample['description'])
            a,b=st.columns(2)
            with a:
                st.download_button('Download this PDF',(kit_root/sample['file']).read_bytes(),sample['file'],'application/pdf',key='download_sample_pdf',width='stretch')
            with b:
                archive=kit_root.parent/'signguard-upload-kit.zip'
                if archive.exists():st.download_button('Download all 7 samples (ZIP)',archive.read_bytes(),archive.name,'application/zip',key='download_sample_zip',width='stretch')
            st.caption('Download the PDF, then upload it above. Upload one numbered PDF at a time; extract the ZIP first. The expected outcomes are in START_HERE.txt inside the kit.')
    if uploaded is None:
        section_header('A clear view of document integrity')
        columns=st.columns(3)
        for col,args in zip(columns,[('01','Signature checks','Byte integrity, mathematical validity and certificate trust.','shield'),('02','Revision comparison','Discover changes between signed and current content.','layers'),('03','Visual evidence','Explore signature regions and possible duplication.','scan')]):
            with col:feature_card(*args)
        return
    raw=uploaded.getvalue();digest=hashlib.sha256(raw).hexdigest()
    if st.session_state.get('last_doc_hash')!=digest:
        st.session_state.pop('pipeline_result',None)
        st.session_state.pop('preview_result',None)
        st.session_state['last_doc_hash']=digest
    if st.session_state.get('preview_result') is None:
        with st.spinner('Reading document…'):
            st.session_state['preview_result']=run_pipeline(raw,uploaded.name,analysis_mode='crypto_only',record_audit=False)
    preview=st.session_state['preview_result'];parsed=preview.parsed
    if parsed is None or parsed.error:
        st.error(preview.processing_error or preview.validation.reason)
        if st.button('Retry reading this document'):
            st.session_state.pop('preview_result',None)
            st.rerun()
        return
    st.markdown(f'<div class="sg-document-id"><span class="sg-feature-icon">{svg_icon("file")}</span><div><strong>{escape(uploaded.name)}</strong><small>{parsed.page_count} pages &nbsp;·&nbsp; {len(raw)/1024:.1f} KB &nbsp;·&nbsp; SHA-256 {digest[:20]}…</small></div></div>',unsafe_allow_html=True)
    with st.expander('Document preview and analysis settings',expanded=st.session_state.get('pipeline_result') is None):
        a,b=st.columns([1.5,1],gap='large')
        with a:
            page=st.selectbox('Preview page',range(parsed.page_count),format_func=lambda p:f'Page {p+1}',key='preview_page_'+digest[:8])
            show_image(parsed.page_images[page],f'Page {page+1}')
        with b:
            st.markdown('**Analysis settings**')
            quality=st.slider('ELA recompression quality',50,95,75,key='ela_quality')
            amplification=st.slider('Heatmap brightness',5,30,15,key='ela_amplification',help='Display only. Does not change measurements or verdicts.')
            renderer_check=st.checkbox('Compare independent rendering engines',value=False,help='Compare MuPDF and Poppler on up to five pages. This can take longer; normal rendering differences are not proof of tampering.')
            st.caption('The full workflow verifies signatures and inspects all current pages. Candidate comparison limits are disclosed in coverage.')
            with st.expander('Document metadata'):st.json(parsed.metadata)
    current=(quality,amplification,renderer_check)
    if st.session_state.get('analysis_config')!=current:
        st.session_state.pop('pipeline_result',None)
        st.session_state['analysis_config']=current
    if st.button('Run document analysis →',type='primary',width='stretch'):
        with st.spinner('Verifying signatures and examining document evidence…'):
            result=run_pipeline(raw,uploaded.name,ela_quality=quality,ela_amp=amplification,renderer_check=renderer_check)
            st.session_state['pipeline_result']=result
        st.rerun()
    result=st.session_state.get('pipeline_result')
    if result:render_results(result)
