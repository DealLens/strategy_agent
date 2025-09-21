import streamlit as st
from app.utils.state_manager import init_session_state, reset_session_state, set_analysis_to_state
from main_mode import run_mode


def render_input_form():
    """사용자 입력 폼"""
    with st.form("analysis_form", border=False):
        topic = st.text_input(
            label="분석할 주제를 입력하세요:",
            value="스마트시티 구축 사업 RFP",
            key="ui_topic",
        )

        mode = st.selectbox(
            "분석 모드 선택",
            ["전략 분석", "경쟁사 분석", "RFP 파서", "내부 RAG", "리포터"],
            key="ui_mode",
        )

        submitted = st.form_submit_button("분석 시작")
        if submitted:
            if topic.strip():
                st.session_state.app_mode = "analysis"
            else:
                st.warning("주제를 입력하세요.")

def start_analysis():
    """분석 실행"""
    topic = st.session_state.ui_topic
    mode = st.session_state.ui_mode

    st.header(f"🔍 분석 모드: {mode}")
    st.write(f"**분석 주제:** {topic}")

    with st.spinner("에이전트가 전략을 분석 중입니다..."):
        result = run_mode(mode, topic)
        set_analysis_to_state(topic, result)

    st.success("분석이 완료되었습니다!")
    st.session_state.app_mode = "results"
    st.rerun()

def display_results():
    """분석 결과 출력"""
    st.header("분석 결과")
    st.subheader(f"주제: {st.session_state.analysis_topic}")
    st.text_area("분석 내용", st.session_state.analysis_result, height=400)

    if st.button("새 분석 시작"):
        reset_session_state()
        st.session_state.app_mode = "input"
        st.rerun()

def render_ui():
    """Streamlit UI"""
    st.set_page_config(page_title="DealLens 전략분석 에이전트", page_icon="📊")

    st.title("📊 DealLens: 전략분석 에이전트")
    st.markdown(
        """
        이 애플리케이션은 여러 AI 에이전트를 활용하여  
        RFP/사업 주제에 대해 전략 분석, 경쟁사 분석, 내부 역량 매칭 등을 수행합니다.
        """
    )

    current_mode = st.session_state.get("app_mode", "input")

    if current_mode == "input":
        render_input_form()
    elif current_mode == "analysis":
        start_analysis()
    elif current_mode == "results":
        display_results()

if __name__ == "__main__":
    # 세션 상태 초기화
    init_session_state()

    # 초기 앱 모드 설정
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "input"

    render_ui()
