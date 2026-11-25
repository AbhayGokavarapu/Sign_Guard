"""Shared visual language and accessible interface primitives for SignGuard."""
from __future__ import annotations
from html import escape
from pathlib import Path
from typing import Optional
import streamlit as st
from PIL import Image

C_PRIMARY='#172B28'; C_ACCENT='#276653'; C_BG='#F6F7F4'; C_CARD='#FFFFFF'
C_BORDER='#E0E5DE'; C_TEXT='#172B28'; C_MUTED='#6B7771'
C_SUCCESS='#276653'; C_WARNING='#98631E'; C_ERROR='#AD3939'


def svg_icon(name='shield', size=22):
    paths={
        'shield':'<path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z"/><path d="m8 12 3 3 5-6"/>',
        'file':'<path d="M14 2H5v20h14V7z"/><path d="M14 2v6h5M8 12h8M8 16h6"/>',
        'layers':'<path d="m12 3 10 6-10 6L2 9zM2 14l10 6 10-6M2 18l10 6 10-6"/>',
        'arrow':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
        'scan':'<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M7 12h10"/>',
        'chart':'<path d="M4 3v18h17M8 17v-5m5 5V7m5 10V4"/>',
        'check':'<path d="m5 12 4 4L19 6"/>',
    }
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths.get(name,paths["shield"])}</svg>'


def inject_css():
    st.markdown('<style>'+Path(__file__).with_name('theme.css').read_text()+'</style>',unsafe_allow_html=True)


def page_header(title, subtitle='', badge='WORKSPACE'):
    st.markdown(f'<div class="sg-page-head"><div class="sg-eyebrow">SIGNGUARD <span>/</span> {escape(badge)}</div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>',unsafe_allow_html=True)


def section_header(text, icon=''):
    st.markdown(f'<div class="sg-section"><h3>{escape(text)}</h3></div>',unsafe_allow_html=True)


def verdict_badge(verdict_value):
    value=verdict_value.replace('_',' ')
    kind={'TAMPERING DETECTED':'danger','REVIEW REQUIRED':'warning','INCONCLUSIVE':'neutral','UNSUPPORTED':'neutral'}.get(value,'neutral')
    st.markdown(f'<div class="sg-verdict sg-verdict-{kind}"><span class="sg-status-dot"></span><span>{escape(value.title())}</span></div>',unsafe_allow_html=True)


def status_pill(label,ok):
    state='pass' if ok is True else 'fail' if ok is False else 'unknown'
    symbol='Verified' if ok is True else 'Failed' if ok is False else 'Not established'
    st.markdown(f'<div class="sg-status-row"><span>{escape(label)}</span><span class="sg-pill sg-pill-{state}">{symbol}</span></div>',unsafe_allow_html=True)


def finding_card(code,severity,title,description):
    st.markdown(f'<div class="sg-finding sg-finding-{escape(severity.lower())}"><div class="sg-finding-meta"><span>{escape(severity)}</span><code>{escape(code)}</code></div><h4>{escape(title)}</h4><p>{escape(description)}</p></div>',unsafe_allow_html=True)


def metric_row(*items):
    cards=''.join(f'<div class="sg-metric-card"><div class="sg-metric-label">{escape(str(i[0]))}</div><div class="sg-metric-value">{escape(str(i[1]))}</div><div class="sg-metric-sub">{escape(str(i[2])) if len(i)>2 else ""}</div></div>' for i in items)
    st.markdown(f'<div class="sg-metric-grid">{cards}</div>',unsafe_allow_html=True)


def card(content_html):
    st.markdown(f'<div class="sg-card">{content_html}</div>',unsafe_allow_html=True)


def feature_card(number,title,description,icon='shield'):
    card(f'<div class="sg-feature-top"><span class="sg-feature-icon">{svg_icon(icon)}</span><span class="sg-index">{escape(number)}</span></div><h3>{escape(title)}</h3><p>{escape(description)}</p>')


def show_image(img,caption='',width=None):
    if img is not None: st.image(img,caption=caption,width=width or 'stretch')


def empty_state(message,icon='file'):
    st.markdown(f'<div class="sg-empty"><span class="sg-empty-icon">{svg_icon(icon if icon in ("shield","file","scan") else "file",30)}</span><h3>Ready when you are</h3><p>{escape(message)}</p></div>',unsafe_allow_html=True)


def download_button(label,data,filename,mime):
    st.download_button(label,data,file_name=filename,mime=mime,width='stretch')


def go_to(page):
    st.session_state['nav_page']=page


def navigation_button(label,page,key,primary=False):
    st.button(label,key=key,on_click=go_to,args=(page,),type='primary' if primary else 'secondary',width='stretch')


def result_summary(result):
    if result.processing_error: st.error(result.processing_error)
    if result.audit_error: st.warning('Audit record was not saved: '+result.audit_error)
    if result.fusion:
        verdict_badge(result.fusion.verdict.value)
        st.write(result.fusion.explanation)
        coverage=result.coverage
        integrity_label={"NO TAMPERING DETECTED":"Bytes intact","INTEGRITY FAILURE":"Failed","INTEGRITY NOT ESTABLISHED":"Not established","NOT APPLICABLE":"Not applicable"}.get(result.fusion.integrity_verdict.value,result.fusion.integrity_verdict.value.title())
        metric_row(('Integrity',integrity_label,'Signed-byte verification'),
                   ('Pages analysed',f'{coverage.get("pages_analysed",0)} / {coverage.get("page_count",0)}','Document coverage'),
                   ('Findings',len(result.fusion.findings),'Evidence requiring attention'),
                   ('Analysis time',f'{result.elapsed_sec:.2f}s','Processing duration'))
        for message in coverage.get('limitations',[]): st.warning(message)


def report_downloads(result,prefix='report'):
    from reporting.json_report import to_json
    from reporting.pdf_report import build_pdf_report
    a,b=st.columns(2)
    with a: st.download_button('Download PDF report',build_pdf_report(result),'signguard_report.pdf','application/pdf',key=prefix+'_pdf',width='stretch',type='primary')
    with b: st.download_button('Download JSON evidence',to_json(result).encode(),'signguard_report.json','application/json',key=prefix+'_json',width='stretch')


def evidence_package_controls(result,prefix='package'):
    from dashboard.case_review import reviews_for
    from reporting.evidence_bundle import build_bundle
    section_header('Verifiable evidence package')
    st.caption('Package the report, provenance, representative evidence images and human assessments. Retain the manifest hash independently to detect a complete rewrite.')
    include=st.checkbox('Include the original uploaded PDF in the package',value=False,key=prefix+'_source',help='Off by default. Including the PDF places its complete contents in the ZIP.')
    import hashlib,json
    reviews=reviews_for(result)
    token=(result.parsed.sha256 if result.parsed else '')+str(include)+hashlib.sha256(json.dumps(reviews,sort_keys=True).encode()).hexdigest()
    if st.button('Prepare evidence package',key=prefix+'_prepare'):
        try:
            bundle,reference=build_bundle(result=result,reviews=reviews,include_source=include)
            st.session_state[prefix+'_bundle']=(bundle,reference,token)
        except Exception as exc:st.error('Package could not be built: '+str(exc))
    stored=st.session_state.get(prefix+'_bundle')
    if stored and result.parsed and stored[2]==token:
        st.download_button('Download evidence ZIP',stored[0],'signguard-evidence.zip','application/zip',key=prefix+'_download',width='stretch')
        st.code(stored[1],language=None)
        st.caption('Manifest SHA-256 — retain this through an independent channel. Checksums alone do not certify authenticity.')
