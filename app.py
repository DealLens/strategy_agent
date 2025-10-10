import streamlit as st 
from dotenv import load_dotenv
import os
import base64
import time
from datetime import datetime
import tempfile

# Agent imports
from workflow.agents.rfp_parser import rfp_parser
from workflow.agents.internal_rag import internal_rag
from workflow.agents.competitor_analysis import competitor_analysis
from workflow.agents.strategy_synthesizer import strategy_synthesizer
from workflow.agents.reporter import reporter

load_dotenv()

st.set_page_config(
    page_title="DealLens 전략분석 에이전트",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🚀",
)


def get_base64_image(image_path: str) -> str | None:
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return None


def initialize_session_state():
    if "analysis_completed" not in st.session_state:
        st.session_state.analysis_completed = False
    if "previous_file_saved" not in st.session_state:
        st.session_state.previous_file_saved = False
    if "previous_file" not in st.session_state:
        st.session_state.previous_file = None
    if "analysis_timestamp" not in st.session_state:
        st.session_state.analysis_timestamp = None
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = {}
    if "analysis_section_order" not in st.session_state:
        st.session_state.analysis_section_order = []
    if "view" not in st.session_state:
        st.session_state.view = "analysis"
    if "analysis_in_progress" not in st.session_state:
        st.session_state.analysis_in_progress = False


def reset_analysis_state():
    st.session_state.analysis_completed = False
    st.session_state.previous_file = None
    st.session_state.previous_file_saved = False
    st.session_state.analysis_timestamp = None
    st.session_state.analysis_results = {}
    st.session_state.analysis_section_order = []
    st.session_state.view = "analysis"
    st.session_state.analysis_in_progress = False


initialize_session_state()
logo_base64 = get_base64_image("assets/sklogo.png")

st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #533483 100%);
        padding: 1rem 2rem;
        margin: 0 0 0.5rem 0;
        color: white;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-radius: 15px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg,
            transparent 30%,
            rgba(0, 191, 255, 0.1) 40%,
            rgba(138, 43, 226, 0.2) 50%,
            rgba(0, 191, 255, 0.1) 60%,
            transparent 70%);
        animation: flow 8s ease-in-out infinite;
        z-index: 0;
    }
    .main-header::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: radial-gradient(ellipse at center, rgba(0, 191, 255, 0.05) 0%, transparent 70%);
        z-index: 0;
    }
    @keyframes flow {
        0%, 100% { transform: translateX(-100%) translateY(-100%) rotate(0deg); }
        50% { transform: translateX(0%) translateY(0%) rotate(180deg); }
    }
    .header-left { position: relative; z-index: 1; }
    .main-header h1 { font-size: 2.5rem; font-weight: 700; margin: 0; letter-spacing: -0.5px; }
    .main-header .subtitle { font-size: 0.9rem; margin: 0; color: #ccc; text-shadow: 0 0 10px rgba(138, 43, 226, 0.3); }

    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #533483 100%) !important;
        display: flex;
        flex-direction: column;
    }
    [data-testid="stSidebar"] .sidebar-header-card {
        position: sticky;
        top: 0;
        z-index: 5;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #533483 100%);
        padding: 0.8rem 1rem;
        margin-bottom: 1rem;
        color: white;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    [data-testid="stSidebar"] * { background: transparent !important; color: white !important; }
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stDownloadButton > button {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: white !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] .stDownloadButton > button:hover {
        background-color: rgba(255, 255, 255, 0.2) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
    }
    .stApp > header { display: none !important; }
    .stApp { padding-top: 0 !important; }
    .main .block-container { padding-top: 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_main_header():
    if logo_base64:
        st.markdown(
            f"""
<div class="main-header">
    <div class="header-left">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <img src="data:image/png;base64,{logo_base64}" style="height: 60px; width: auto;" alt="SKAX Logo">
            <div>
                <h1>DealLens</h1>
                <div class="subtitle">전략분석 멀티에이전트</div>
            </div>
        </div>
    </div>
</div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="main-header">
                <div class="header-left">
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <div style="display: flex; align-items: center; gap: 0.3rem; background: rgba(255,255,255,0.1); padding: 0.3rem 0.6rem; border-radius: 6px;">
                            <span style="color: white; font-size: 0.8rem; font-weight: 600;">SKAX</span>
                        </div>
                        <div>
                            <h1>DealLens</h1>
                            <div class="subtitle">전략분석 멀티에이전트</div>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar_header():
    if logo_base64:
        st.markdown(
            f"""
        <div class="sidebar-header-card">
            <div style="display: flex; flex-direction: column; align-items: center; gap: 0.3rem; margin-bottom: 0.3rem;">
                <img src="data:image/png;base64,{logo_base64}" style="height: 50px; width: auto;" alt="SKAX Logo">
                <h3 style="margin: 0; font-size: 1.2rem; color: white;">DealLens</h3>
            </div>
            <p style="margin: 0; font-size: 0.8rem; color: #ccc;">전략분석 멀티에이전트</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="sidebar-header-card">
                <div style="display: flex; flex-direction: column; align-items: center; gap: 0.3rem; margin-bottom: 0.3rem;">
                    <div style="display: flex; align-items: center; gap: 0.2rem; background: rgba(255,255,255,0.1); padding: 0.2rem 0.4rem; border-radius: 4px;">
                        <span style="color: white; font-size: 0.7rem; font-weight: 600;">SKAX</span>
                    </div>
                    <h3 style="margin: 0; font-size: 1.2rem; color: white;">DealLens</h3>
                </div>
                <p style="margin: 0; font-size: 0.8rem; color: #ccc;">전략분석 멀티에이전트</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def current_file_section():
    file_obj = st.session_state.get("previous_file")
    if not file_obj:
        st.markdown("**현재 분석 파일:** -")
        return

    if hasattr(file_obj, "getvalue"):
        file_content = file_obj.getvalue()
    elif hasattr(file_obj, "read"):
        file_obj.seek(0)
        file_content = file_obj.read()
    else:
        file_content = None

    if file_content:
        b64_file = base64.b64encode(file_content).decode()
        st.markdown(
            f"""
            <div style="margin: 0.5rem 0;">
                <strong>현재 분석 파일:</strong><br>
                <a href="data:application/pdf;base64,{b64_file}"
                   download="{file_obj.name}"
                   style="color: #ffffff; text-decoration: underline; font-size: 0.9rem;"
                   onmouseover="this.style.color='#dfe4ff'"
                   onmouseout="this.style.color='#ffffff'">
                    {file_obj.name}
                </a>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"**현재 분석 파일:** {file_obj.name}")
        st.warning("파일 내용을 찾을 수 없습니다.")


def render_sidebar_base():
    with st.sidebar:
        render_sidebar_header()
        current_file_section()
        timestamp = st.session_state.get("analysis_timestamp")
        if timestamp:
            st.markdown(f"**분석 시간:** {timestamp}")
        else:
            st.markdown("**분석 시간:** -")
        st.markdown("---")

        if st.button(
            "🔄 새로운 분석",
            use_container_width=True,
            key="sidebar_new_analysis_button",
        ):
            reset_analysis_state()
            st.rerun()


def render_file_upload():
    if st.session_state.get("analysis_completed", False):
        return None

    st.markdown(
        """
        <div style="text-align: left; margin: 0.5rem 0 0.5rem 0;">
            <h3 style="font-size: 1.5rem; font-weight: 600; color: #333; margin-bottom: 0.5rem;">
                📄 RFP 파일을 업로드해주세요
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return st.file_uploader(
        "",
        type=["pdf"],
        help="RFP 문서를 PDF 형태로 업로드해주세요. 최대 200MB까지 지원됩니다.",
        label_visibility="collapsed",
    )


def render_analysis_button(uploaded_file):
    if st.session_state.get("analysis_completed", False):
        return

    col_left, col_center, col_right = st.columns([1, 2, 1])
    run_button = col_center.button(
        "📄 RFP 업로드",
        use_container_width=True,
        type="primary",
        disabled=uploaded_file is None,
        help="RFP 파일을 업로드한 후 클릭하세요",
    )

    if run_button and uploaded_file is not None:
        st.session_state.previous_file = uploaded_file
        st.session_state.previous_file_saved = True
        st.session_state.analysis_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.analysis_completed = True
        st.session_state.analysis_results = {}
        st.session_state.analysis_section_order = []
        st.session_state.view = "analysis"
        st.rerun()


def process_analysis_steps():
    """
    분석이 완료된 상태에서 실제 AI agent를 실행하여 결과를 생성합니다.
    """
    if not st.session_state.get("analysis_completed", False):
        return
    
    # 이미 분석이 실행된 경우 (결과가 있으면) 다시 실행하지 않음
    # strategy까지 있으면 완전히 완료된 것으로 간주
    if st.session_state.analysis_results.get("strategy"):
        return
    
    uploaded_file = st.session_state.get("previous_file")
    if not uploaded_file:
        st.error("업로드된 파일이 없습니다.")
        return
    
    # 이미 진행 중인지 확인 (중복 실행 방지)
    if st.session_state.get("analysis_in_progress", False):
        return
    
    # 진행 중 플래그 설정
    st.session_state.analysis_in_progress = True
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # ========== 1단계: RFP 분석 ==========
        status_text.markdown("### 🔍 1단계: RFP 분석 중...")
        progress_bar.progress(10)
        
        # PDF 파일을 임시로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            pdf_path = tmp_file.name
        
        try:
            # RFP 분석 실행
            rfp_result = rfp_parser.invoke({"pdf_path": pdf_path})
            
            # 결과 포맷팅
            rfp_content = "### 📋 RFP 분석 결과\n\n"
            
            if "error" in rfp_result:
                rfp_content += f"⚠️ 오류 발생: {rfp_result['error']}\n"
            else:
                if rfp_result.get("requirements"):
                    rfp_content += "#### 🎯 핵심 요구사항\n"
                    for req in rfp_result["requirements"][:10]:
                        rfp_content += f"- {req}\n"
                    rfp_content += "\n"
                
                if rfp_result.get("evaluation"):
                    rfp_content += "#### 📊 평가 기준\n"
                    for eval_item in rfp_result["evaluation"][:10]:
                        rfp_content += f"- {eval_item}\n"
                    rfp_content += "\n"
                
                if rfp_result.get("risks"):
                    rfp_content += "#### ⚠️ 잠재적 리스크\n"
                    for risk in rfp_result["risks"][:10]:
                        rfp_content += f"- {risk}\n"
                    rfp_content += "\n"
                
                if rfp_result.get("schedule"):
                    rfp_content += "#### 📅 일정\n"
                    for schedule in rfp_result["schedule"][:5]:
                        rfp_content += f"- {schedule}\n"
                    rfp_content += "\n"
            
            st.session_state.analysis_results["rfp_analysis"] = rfp_content
            st.session_state.analysis_results["rfp_raw"] = rfp_result
            
        finally:
            # 임시 파일 삭제
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        
        progress_bar.progress(30)
        
        # ========== 2단계: 내부 역량 매칭 ==========
        status_text.markdown("### 🔍 2단계: 내부 역량 매칭 중...")
        
        # RFP에서 추출한 요구사항 사용
        requirements = rfp_result.get("requirements", [])[:5]  # 상위 5개만
        
        if requirements:
            internal_result = internal_rag.invoke({"requirements": requirements})
            
            # 결과 포맷팅
            internal_content = "### 🔍 내부 역량 매칭 결과\n\n"
            
            if "error" in internal_result:
                internal_content += f"⚠️ 오류 발생: {internal_result['error']}\n"
            else:
                matches = internal_result.get("internal_matches", [])
                for match in matches:
                    req = match.get("requirement", "")
                    related_projects = match.get("matches", [])
                    
                    internal_content += f"#### 📌 {req}\n"
                    if related_projects:
                        for idx, proj in enumerate(related_projects, 1):
                            internal_content += f"{idx}. **{proj.get('title', 'N/A')}**\n"
                            if proj.get('summary'):
                                internal_content += f"   - {proj['summary'][:200]}...\n"
                            if proj.get('url'):
                                internal_content += f"   - [링크]({proj['url']})\n"
                        internal_content += "\n"
                    else:
                        internal_content += "   - 매칭된 사례가 없습니다.\n\n"
            
            st.session_state.analysis_results["internal_matching"] = internal_content
            st.session_state.analysis_results["internal_raw"] = internal_result
        else:
            st.session_state.analysis_results["internal_matching"] = "⚠️ 요구사항을 추출할 수 없어 내부 매칭을 수행하지 못했습니다."
        
        progress_bar.progress(50)
        
        # ========== 3단계: 경쟁사 분석 ==========
        status_text.markdown("### ⚔️ 3단계: 경쟁사 분석 중...")
        
        competitor_result = competitor_analysis.invoke({"update_data": True})
        
        # 경쟁사 분석 결과 저장 (dict 형태로)
        competitor_profiles = competitor_result.get("competitor_profiles", {})
        st.session_state.analysis_results["competitor_analysis"] = competitor_profiles
        st.session_state.analysis_results["competitor_raw"] = competitor_result
        
        progress_bar.progress(70)
        
        # ========== 4단계: 전략 도출 ==========
        status_text.markdown("### 🚀 4단계: 전략 도출 중...")
        
        # 전략 합성 실행
        strategy_input = {
            "requirements": requirements,
            "internal_matches": st.session_state.analysis_results.get("internal_raw", {}).get("internal_matches", []),
            "competitor_profiles": competitor_profiles
        }
        
        strategy_result = strategy_synthesizer.invoke(strategy_input)
        
        # 전략 결과 저장
        st.session_state.analysis_results["strategy"] = strategy_result.get("strategy", {})
        st.session_state.analysis_results["strategy_raw"] = strategy_result
        
        progress_bar.progress(90)
        
        # ========== 5단계: 최종 보고서 생성 ==========
        status_text.markdown("### 📋 5단계: 최종 보고서 생성 중...")
        
        reporter_input = {
            "requirements": rfp_result.get("requirements", []),
            "evaluation": rfp_result.get("evaluation", []),
            "risks": rfp_result.get("risks", []),
            "internal_matches": st.session_state.analysis_results.get("internal_raw", {}).get("internal_matches", []),
            "competitor_profiles": competitor_profiles,
            "strategy": strategy_result.get("strategy", {})
        }
        
        reporter_result = reporter.invoke({"data": reporter_input})
        
        st.session_state.analysis_results["report"] = reporter_result
        
        progress_bar.progress(100)
        status_text.markdown("### ✅ 분석 완료!")
        
        # 진행 중 플래그 해제
        st.session_state.analysis_in_progress = False
        
        time.sleep(1)
        
        # UI 새로고침
        progress_bar.empty()
        status_text.empty()
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ 분석 중 오류 발생: {str(e)}")
        import traceback
        with st.expander("오류 상세 정보"):
            st.code(traceback.format_exc())
        # 진행 중 플래그 해제
        st.session_state.analysis_in_progress = False
        progress_bar.empty()
        status_text.empty()


def render_strategy_report():
    if not st.session_state.get("analysis_completed", False):
        return

    st.markdown("## 전략 분석 결과")

    results_state = st.session_state.get("analysis_results", {})

    with st.expander("① RFP 분석 결과", expanded=True):
        rfp_content = results_state.get("rfp_analysis")
        if rfp_content:
            st.markdown(rfp_content)
        else:
            st.info("RFP 분석 결과가 아직 준비되지 않았습니다.")

    section_definitions = [
        {
            "key": "internal_matching",
            "title": "② 내부 역량 매칭 결과",
            "empty_msg": "내부 역량 매칭 결과가 아직 준비되지 않았습니다.",
        },
        {
            "key": "competitor_analysis",
            "title": "③ 경쟁사 분석 결과",
            "empty_msg": "경쟁사 분석 결과가 아직 준비되지 않았습니다.",
        },
    ]

    dynamic_order = sorted(
        section_definitions,
        key=lambda section: (
            0 if results_state.get(section["key"]) else 1,
            section["title"],
        ),
    )

    new_order_keys = [section["key"] for section in dynamic_order]
    if new_order_keys != st.session_state.get("analysis_section_order", []):
        st.session_state.analysis_section_order = new_order_keys
    else:
        persisted_order = st.session_state.get("analysis_section_order", [])
        if persisted_order:
            dynamic_order = sorted(
                section_definitions,
                key=lambda section: persisted_order.index(section["key"])
                if section["key"] in persisted_order
                else len(persisted_order),
            )

    for idx, section in enumerate(dynamic_order, start=2):
        title = section["title"]
        if idx == 3:
            title = title.replace("②", "③") if "②" in title else title
        elif idx == 2:
            title = title.replace("③", "②") if "③" in title else title

        with st.expander(title, expanded=False):
            content = results_state.get(section["key"])
            if section["key"] == "competitor_analysis":
                competitor_data = content if isinstance(content, dict) else {}
                
                if not competitor_data:
                    st.info("경쟁사 분석 결과가 아직 준비되지 않았습니다.")
                else:
                    for company_name, profile in competitor_data.items():
                        with st.expander(f"🏢 {company_name}", expanded=False):
                            if isinstance(profile, dict):
                                # 회사 개요
                                if profile.get("company_summary"):
                                    st.markdown("##### 📝 회사 개요")
                                    st.markdown(profile["company_summary"][:500] + "..." if len(profile.get("company_summary", "")) > 500 else profile["company_summary"])
                                    st.markdown("---")
                                
                                # 핵심 기술
                                if profile.get("key_technologies"):
                                    st.markdown("##### 💡 핵심 기술")
                                    for tech in profile["key_technologies"]:
                                        st.markdown(f"- {tech}")
                                    st.markdown("---")
                                
                                # 차별화 포인트
                                if profile.get("differentiation_points"):
                                    st.markdown("##### 🎯 차별화 포인트")
                                    for point in profile["differentiation_points"]:
                                        st.markdown(f"- {point}")
                                    st.markdown("---")
                                
                                # SWOT 분석
                                if profile.get("swot"):
                                    st.markdown("##### 📊 SWOT 분석")
                                    swot = profile["swot"]
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if swot.get("S"):
                                            st.markdown("**💪 강점 (Strengths)**")
                                            for s in swot["S"]:
                                                st.markdown(f"- {s}")
                                        if swot.get("W"):
                                            st.markdown("**⚠️ 약점 (Weaknesses)**")
                                            for w in swot["W"]:
                                                st.markdown(f"- {w}")
                                    
                                    with col2:
                                        if swot.get("O"):
                                            st.markdown("**🌟 기회 (Opportunities)**")
                                            for o in swot["O"]:
                                                st.markdown(f"- {o}")
                                        if swot.get("T"):
                                            st.markdown("**🚨 위협 (Threats)**")
                                            for t in swot["T"]:
                                                st.markdown(f"- {t}")
                                    st.markdown("---")
                                
                                # 최신 뉴스
                                if profile.get("recent_news"):
                                    st.markdown("##### 📰 최신 뉴스")
                                    for idx, news in enumerate(profile["recent_news"][:3], 1):
                                        if isinstance(news, dict):
                                            st.markdown(f"**{idx}. {news.get('title', 'N/A')}**")
                                            if news.get('summary'):
                                                st.caption(news['summary'])
                                            if news.get('url'):
                                                st.markdown(f"   [링크]({news['url']})")
                                        else:
                                            st.markdown(f"{idx}. {news}")
                            else:
                                st.markdown(str(profile))
            else:
                if content:
                    st.markdown(content)
                else:
                    st.info(section["empty_msg"])

    stage_ready = all(results_state.get(key) for key in ["rfp_analysis", "internal_matching", "competitor_analysis"])
    navigate_button = st.button(
        "🚀 전략 도출 결과 보기",
        disabled=not stage_ready,
        use_container_width=True,
    )

    if navigate_button and stage_ready:
        st.session_state.view = "strategy"
        st.rerun()


def render_strategy_view():
    st.markdown("## 🚀 전략 도출 결과")
    results_state = st.session_state.get("analysis_results", {})
    strategy_data = results_state.get("strategy") or results_state.get("strategy_output")

    if not strategy_data:
        st.info("전략 도출 결과가 아직 준비되지 않았습니다.")
    else:
        if isinstance(strategy_data, dict):
            # 실행 계획 (Actions)
            if strategy_data.get("actions"):
                st.markdown("### 📋 실행 계획")
                for idx, action in enumerate(strategy_data["actions"], 1):
                    if isinstance(action, dict):
                        priority_emoji = "🔴" if action.get("priority") == "High" else "🟡" if action.get("priority") == "Medium" else "🟢"
                        st.markdown(f"#### {priority_emoji} {idx}. {action.get('action', 'N/A')}")
                        st.markdown(f"**유형:** {action.get('type', 'N/A')}")
                        st.markdown(f"**우선순위:** {action.get('priority', 'N/A')}")
                        st.markdown(f"**설명:** {action.get('description', 'N/A')}")
                        st.markdown(f"**일정:** {action.get('timeline', 'N/A')}")
                        st.markdown("---")
                    else:
                        st.markdown(f"{idx}. {action}")
                st.markdown("")
            
            # SWOT 분석
            if strategy_data.get("swot"):
                st.markdown("### 📊 당사 SWOT 분석")
                swot = strategy_data["swot"]
                
                col1, col2 = st.columns(2)
                with col1:
                    if swot.get("S"):
                        st.markdown("#### 💪 강점 (Strengths)")
                        for s in swot["S"]:
                            st.markdown(f"- {s}")
                    st.markdown("")
                    if swot.get("W"):
                        st.markdown("#### ⚠️ 약점 (Weaknesses)")
                        for w in swot["W"]:
                            st.markdown(f"- {w}")
                
                with col2:
                    if swot.get("O"):
                        st.markdown("#### 🌟 기회 (Opportunities)")
                        for o in swot["O"]:
                            st.markdown(f"- {o}")
                    st.markdown("")
                    if swot.get("T"):
                        st.markdown("#### 🚨 위협 (Threats)")
                        for t in swot["T"]:
                            st.markdown(f"- {t}")
                
                st.markdown("---")
            
            # 차별화 전략
            if strategy_data.get("differentiation"):
                st.markdown("### 🎯 경쟁사 대비 차별화 전략")
                for idx, diff in enumerate(strategy_data["differentiation"], 1):
                    if isinstance(diff, dict):
                        impact_emoji = "⭐⭐⭐" if diff.get("impact") == "High" else "⭐⭐" if diff.get("impact") == "Medium" else "⭐"
                        st.markdown(f"#### {idx}. {diff.get('differentiation', 'N/A')} {impact_emoji}")
                        st.markdown(f"**vs.** {diff.get('vs_competitor', 'N/A')}")
                        st.markdown(f"**전략:** {diff.get('strategy', 'N/A')}")
                        st.markdown(f"**영향도:** {diff.get('impact', 'N/A')}")
                        st.markdown(f"**실행 방안:** {diff.get('implementation', 'N/A')}")
                        st.markdown("---")
                    else:
                        st.markdown(f"{idx}. {diff}")
                st.markdown("")
            
            # 경쟁 우위 요소
            if strategy_data.get("competitive_advantages"):
                st.markdown("### 💎 경쟁 우위 요소")
                for adv in strategy_data["competitive_advantages"]:
                    st.markdown(f"- ✅ {adv}")
                st.markdown("")
            
            # 역량 갭
            if strategy_data.get("capability_gaps"):
                st.markdown("### ⚠️ 보완 필요 역량")
                for gap in strategy_data["capability_gaps"]:
                    st.markdown(f"- 🔸 {gap}")
                st.markdown("")
            
            # 전략적 권장사항
            if strategy_data.get("strategic_recommendations"):
                st.markdown("### 💡 전략적 권장사항")
                recommendations = strategy_data["strategic_recommendations"]
                
                for key, value in recommendations.items():
                    key_display = key.replace("_", " ").title()
                    st.markdown(f"**{key_display}:**")
                    st.info(value)
                st.markdown("")
            
            # 기타 섹션 (위에서 다루지 않은 것들)
            handled_keys = {"actions", "swot", "differentiation", "competitive_advantages", 
                          "capability_gaps", "strategic_recommendations"}
            for section_title, content in strategy_data.items():
                if section_title not in handled_keys:
                    st.markdown(f"### {section_title}")
                    if isinstance(content, list):
                        for item in content:
                            st.markdown(f"- {item}")
                    elif isinstance(content, dict):
                        for key, value in content.items():
                            st.markdown(f"**{key}:** {value}")
                    else:
                        st.markdown(str(content))
                    st.markdown("")
        else:
            st.markdown(str(strategy_data))

    st.markdown("---")
    if st.button("↩ 전략 분석 화면으로 돌아가기", key="strategy_back_button"):
        st.session_state.view = "analysis"
        st.rerun()


def main():
    if st.session_state.view == "strategy":
        render_sidebar_base()
        render_strategy_view()
        return

    render_main_header()

    if st.session_state.get("analysis_completed", False):
        render_sidebar_base()
    else:
        with st.sidebar:
            render_sidebar_header()

    uploaded_file = render_file_upload()

    if uploaded_file:
        st.session_state.previous_file = uploaded_file
        st.session_state.previous_file_saved = False

    render_analysis_button(uploaded_file)
    process_analysis_steps()
    render_strategy_report()


if __name__ == "__main__":
    main()
