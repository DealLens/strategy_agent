import streamlit as st

def reset_session_state():
    """Streamlit 세션 상태 초기화"""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
