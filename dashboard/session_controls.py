"""Clear this session's retained document objects; no secure-erasure claim."""
import streamlit as st


def clear_mapping(state):
    epoch=state.get('_upload_epoch',0)+1
    for key in list(state):del state[key]
    state['_upload_epoch']=epoch
    state['nav_page']='Overview'


def clear_workspace():clear_mapping(st.session_state)
