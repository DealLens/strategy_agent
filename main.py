import streamlit as st
from app.utils.state_manager import init_session_state, reset_session_state, set_analysis_to_state
from main_mode import run_mode


def render_input_form():
    """사용자 입력 폼"""
    with st.form("analysis_form", border=False):
        # 파일 업로드 섹션
        st.subheader("📄 RFP 파일 업로드")
        uploaded_file = st.file_uploader(
            "RFP PDF 파일을 업로드하세요",
            type=['pdf'],
            help="분석할 RFP 문서를 PDF 형태로 업로드하세요"
        )
        
        # 주제 입력 섹션
        st.subheader("📝 분석 주제 및 프롬프트")
        topic = st.text_input(
            label="분석할 주제를 입력하세요:",
            value="스마트시티 구축 사업 RFP",
            key="ui_topic",
            help="RFP 제목이나 프로젝트 주제를 입력하세요"
        )
        
        # 사용자 프롬프트 입력
        user_prompt = st.text_area(
            label="추가 분석 요청사항 (선택사항):",
            placeholder="예: 특별히 중점을 두고 분석하고 싶은 부분이나 추가로 고려해야 할 사항을 입력하세요...",
            key="ui_prompt",
            height=100,
            help="분석에 특별한 요구사항이 있다면 입력하세요"
        )

        mode = st.selectbox(
            "분석 모드 선택",
            ["전체 파이프라인", "전략 분석", "경쟁사 분석", "RFP 파서", "내부 RAG", "리포터"],
            key="ui_mode",
        )

        submitted = st.form_submit_button("분석 시작")
        if submitted:
            if uploaded_file is not None or topic.strip():
                # 업로드된 파일을 임시 저장
                if uploaded_file is not None:
                    # 업로드된 파일을 저장
                    import tempfile
                    import os
                    
                    # 임시 디렉토리에 파일 저장
                    temp_dir = tempfile.mkdtemp()
                    file_path = os.path.join(temp_dir, uploaded_file.name)
                    
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    st.session_state.uploaded_file_path = file_path
                    st.session_state.uploaded_file_name = uploaded_file.name
                else:
                    st.session_state.uploaded_file_path = None
                    st.session_state.uploaded_file_name = None
                
                st.session_state.user_prompt = user_prompt
                st.session_state.app_mode = "analysis"
            else:
                st.warning("RFP 파일을 업로드하거나 주제를 입력하세요.")

def start_analysis():
    """분석 실행"""
    topic = st.session_state.ui_topic
    mode = st.session_state.ui_mode
    user_prompt = st.session_state.get("user_prompt", "")
    uploaded_file_path = st.session_state.get("uploaded_file_path")
    uploaded_file_name = st.session_state.get("uploaded_file_name")

    st.header(f"🔍 분석 모드: {mode}")
    
    # 분석 정보 표시
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**분석 주제:** {topic}")
        if uploaded_file_name:
            st.write(f"**업로드된 파일:** {uploaded_file_name}")
    with col2:
        if user_prompt:
            st.write(f"**추가 요청사항:** {user_prompt}")

    # 분석 실행
    with st.spinner("에이전트가 전략을 분석 중입니다..."):
        # 파일이 업로드된 경우 파일 경로를 사용, 그렇지 않으면 주제만 사용
        if uploaded_file_path:
            analysis_input = uploaded_file_path
        else:
            analysis_input = topic
            
        # 사용자 프롬프트가 있으면 함께 전달
        if user_prompt:
            analysis_input = f"{analysis_input}\n\n사용자 추가 요청사항: {user_prompt}"
            
        result = run_mode(mode, analysis_input)
        set_analysis_to_state(topic, result)

    st.success("분석이 완료되었습니다!")
    st.session_state.app_mode = "results"
    st.rerun()

def display_results():
    """분석 결과 출력"""
    st.header("분석 결과")
    
    # 분석 정보 표시
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"주제: {st.session_state.analysis_topic}")
        if st.session_state.get("uploaded_file_name"):
            st.write(f"**업로드된 파일:** {st.session_state.uploaded_file_name}")
    with col2:
        if st.session_state.get("user_prompt"):
            st.write(f"**추가 요청사항:** {st.session_state.user_prompt}")
    
    # 분석 결과 표시
    st.markdown("---")
    st.markdown(st.session_state.analysis_result)

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
        
        **전체 파이프라인**: RFP 파서 → 내부 RAG → 경쟁사 분석 → 전략 수립 → 보고서 생성의 순차 실행
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
