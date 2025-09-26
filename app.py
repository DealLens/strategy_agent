import streamlit as st
from dotenv import load_dotenv
import os

# ✅ 환경변수 로드 (맨 위에서 실행 1번만 해주면 됨)
load_dotenv()

from workflow.supervisor import supervisor

# 페이지 설정
st.set_page_config(
    page_title="DealLens 전략분석 에이전트",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 헤더
st.title("🚀 DealLens: 전략분석 멀티에이전트")
st.markdown("AI 기반 **RFP 분석 → 내부 매칭 → 경쟁사 분석 → 전략 합성 → 리포트** 파이프라인")

# 사이드바 입력 영역
with st.sidebar:
    st.header("⚙️ 입력 설정")
    uploaded_file = st.file_uploader("📄 RFP PDF 업로드", type=["pdf"])
    
    competitors = st.multiselect(
        "🏢 경쟁사 선택",
        ["삼성 SDS", "LG CNS", "포스코DX", "KT", "현대 오토에버", "카카오", "CJ 올리브네트웍스"]
    )
    
    run_button = st.button("🔍 분석 실행", use_container_width=True)

# 메인 콘텐츠 영역
if run_button and uploaded_file:
    # PDF 저장을 위한 디렉토리 생성
    os.makedirs("data/samples", exist_ok=True)
    
    # PDF 저장
    pdf_path = f"data/samples/{uploaded_file.name}"
    with open(pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    query = f"RFP 파일: {pdf_path}\n경쟁사: {competitors}\n이 정보를 기반으로 전략 보고서를 생성해줘."

    with st.spinner("⏳ 전략 보고서 생성 중..."):
        result = supervisor.invoke({"input": query})

    st.success("✅ 분석이 완료되었습니다!")

    # Deal Brief (요약)
    st.subheader("📋 Deal Brief")
    st.info(result["output"])  # 강조 블록

    # 상세 결과 (탭으로 구분)
    st.subheader("📑 상세 분석")
    tab1, tab2, tab3 = st.tabs(["요구사항", "경쟁사 분석", "전략 제안"])

    with tab1:
        st.write("🔹 요구사항 및 평가 기준 상세 내용")
        # st.json(result["sections"].get("요구사항", {}))

    with tab2:
        st.write("🏢 경쟁사 SWOT 분석")
        # st.json(result["sections"].get("경쟁사", {}))

    with tab3:
        st.write("🎯 전략 제안 / 보완책")
        # st.json(result["sections"].get("전략", {}))

else:
    st.info("좌측 사이드바에서 📄 PDF를 업로드하고 경쟁사를 선택한 후 '🔍 분석 실행'을 눌러주세요.")
