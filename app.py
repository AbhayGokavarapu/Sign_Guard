"""SignGuard document security workspace."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import streamlit as st
import config
from dashboard.components import inject_css,svg_icon
st.set_page_config(page_title='SignGuard | Document security',page_icon='assets/logo.svg',layout='wide',initial_sidebar_state='expanded')
inject_css()
from dashboard.navigation import PAGES, valid_page
# Reset legacy selections before the navigation widget is instantiated.
st.session_state['nav_page']=valid_page(st.session_state.get('nav_page'))
with st.sidebar:
    st.markdown(f'<div class="sg-brand"><span class="sg-brand-mark">{svg_icon()}</span><div><strong>SignGuard</strong><small>Document security</small></div></div><div class="sg-nav-label">WORKSPACE</div>',unsafe_allow_html=True)
    selected=st.radio('Navigation',list(PAGES),key='nav_page',label_visibility='collapsed')
    from dashboard.session_controls import clear_workspace
    st.button('Clear session',key='clear_workspace',on_click=clear_workspace,width='stretch',help='Clear this session’s uploads, previews and results. Downloads are not deleted; secure erasure is not guaranteed.')
    st.markdown('<div class="sg-sidebar-note"><strong>Evidence, before conclusions.</strong>Cryptographic verification and visual forensics in one workspace.<br><br>v3.2 &nbsp; / &nbsp; Research edition</div>',unsafe_allow_html=True)
mode='Public demo' if config.PUBLIC_DEMO else 'Local workspace'
st.markdown(f'<div class="sg-workspace-bar"><span>Document intelligence / Research workspace</span><span class="sg-workspace-status"><span class="sg-status-dot"></span>{mode}</span></div>',unsafe_allow_html=True)
if config.PUBLIC_DEMO:
    st.caption('Public demo · Documents are processed on the hosting server. Use synthetic or non-sensitive files.')
from importlib import import_module
import_module('dashboard.'+PAGES[selected]).render()
st.markdown('<div class="sg-note" style="border-top:1px solid #e0e5de;margin-top:2.5rem">SignGuard Research Edition &nbsp;·&nbsp; Findings support expert review and do not certify document authenticity.</div>',unsafe_allow_html=True)
