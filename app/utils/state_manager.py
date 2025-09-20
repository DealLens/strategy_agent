import streamlit as st

def init_session_state():
    """앱 시작 시 세션 스테이트 초기화"""
    if "initialized" not in st.session_state:
        reset_session_state()

def reset_session_state():
    """세션 스테이트 리셋"""
    st.session_state.initialized = True
    st.session_state.app_mode = "input"        # 현재 UI 모드
    st.session_state.analysis_topic = None     # 분석 주제
    st.session_state.analysis_result = None    # 분석 결과
    st.session_state.docs = {}                 # RAG 문서 저장소
    st.session_state.viewing_history = False   # 과거 분석 조회 여부

def set_analysis_to_state(topic: str, result: str, docs: dict = None):
    """
    분석 결과를 세션 스테이트에 저장
    Args:
        topic (str): 분석 주제
        result (str): 분석 결과 텍스트
        docs (dict): 선택적으로 RAG 결과 같은 추가 데이터
    """
    st.session_state.analysis_topic = topic
    st.session_state.analysis_result = result
    st.session_state.docs = docs or {}
    st.session_state.viewing_history = True
