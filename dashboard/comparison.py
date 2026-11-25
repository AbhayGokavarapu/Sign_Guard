"""Two-document investigation independent of whether either file is signed."""
import json
import streamlit as st
from core.document_diff import compare,public_comparison
from dashboard.components import page_header,section_header,metric_row,show_image,empty_state
from reporting.evidence_bundle import comparison_pdf,build_bundle


def render():
    page_header('Document comparison','Compare a known original with a suspect copy—even when neither PDF is digitally signed.','COMPARE')
    epoch=st.session_state.get('_upload_epoch',0)
    a,b=st.columns(2)
    with a:original=st.file_uploader('Known original PDF',type=['pdf'],key=f'comparison_original_{epoch}')
    with b:suspect=st.file_uploader('Suspect or revised PDF',type=['pdf'],key=f'comparison_suspect_{epoch}')
    st.caption('Pages are compared by position. Differences are evidence for review; they do not by themselves prove forgery.')
    if original is None or suspect is None:
        if original is None and suspect is None:
            from pathlib import Path
            import config
            folder=Path(config.BASE_DIR)/'samples'/'upload-kit'
            if (folder/'01_signed_original.pdf').exists() and st.button('Compare the supplied sample original and modified PDF',key='comparison_demo'):
                with st.spinner('Comparing the sample documents…'):
                    st.session_state['comparison_result']=compare((folder/'01_signed_original.pdf').read_bytes(),(folder/'03_changed_after_signing.pdf').read_bytes(),'01_signed_original.pdf','03_changed_after_signing.pdf')
                    st.session_state['comparison_identity']=('sample','sample')
                    st.session_state.pop('comparison_bundle',None)
            result=st.session_state.get('comparison_result') if st.session_state.get('comparison_identity')==('sample','sample') else None
            if not result:
                empty_state('Upload both PDFs, or compare the supplied samples, to inspect text, images, metadata and page changes.')
                return
        else:
            empty_state('Upload the second PDF to complete this comparison.')
            return
    else:
        import hashlib
        identity=(hashlib.sha256(original.getvalue()).hexdigest(),hashlib.sha256(suspect.getvalue()).hexdigest())
        if st.session_state.get('comparison_identity')!=identity:
            st.session_state.pop('comparison_result',None)
            st.session_state.pop('comparison_bundle',None)
            st.session_state['comparison_identity']=identity
        if st.button('Compare documents →',type='primary',width='stretch'):
            with st.spinner('Comparing document text and visible content…'):
                st.session_state['comparison_result']=compare(original.getvalue(),suspect.getvalue(),original.name,suspect.name)
        result=st.session_state.get('comparison_result')
    if not result:return
    if result.get('error'):st.error(result['error']);return
    metric_row(('Original pages',result['original']['page_count'],'Known original'),('Suspect pages',result['suspect']['page_count'],'Compared copy'),
               ('Changed pages',len(result['changed_pages']),'Aligned by page position'),('File bytes','Identical' if result['identical_bytes'] else 'Different','SHA-256 comparison'))
    tabs=st.tabs(['Page changes','Visual differences','Metadata','Export'])
    with tabs[0]:
        st.dataframe([{'Page':r['page']+1,'Change':r['change'],'Changed area %':r.get('changed_area_pct')} for r in result['pages']],hide_index=True,width='stretch')
        for row in result['pages']:
            if row.get('text_changes'):
                with st.expander(f"Page {row['page']+1}: ordered text changes"):
                    for change in row['text_changes']:
                        a,b=st.columns(2)
                        with a:st.code('\n'.join(change['removed']) or '(no removed lines)',language=None)
                        with b:st.code('\n'.join(change['added']) or '(no added lines)',language=None)
    with tabs[1]:
        for row in result.get('images',[]):
            section_header(f"Page {row['page']+1}")
            a,b,c=st.columns(3)
            with a:st.image(row['original'],caption='Original',width='stretch')
            with b:st.image(row['suspect'],caption='Suspect',width='stretch')
            with c:st.image(row['difference'],caption='Pixel difference',width='stretch')
        if not result.get('images'):st.info('No representative modified-page images are available.')
    with tabs[2]:st.json(result['metadata_changes'])
    with tabs[3]:
        st.download_button('Download comparison JSON',json.dumps(public_comparison(result),indent=2),'comparison.json','application/json')
        st.download_button('Download comparison PDF',comparison_pdf(result),'comparison.pdf','application/pdf')
        if st.button('Prepare comparison evidence package'):
            st.session_state['comparison_bundle']=build_bundle(comparison=result)
        bundle=st.session_state.get('comparison_bundle')
        if bundle:
            st.download_button('Download comparison package ZIP',bundle[0],'comparison-evidence.zip','application/zip')
            st.caption('Retain this manifest SHA-256 independently: '+bundle[1])
    for limitation in result.get('limitations',[]):st.caption(limitation)
