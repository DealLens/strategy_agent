import streamlit as st
from dotenv import load_dotenv
import os
import base64
import time
from datetime import datetime

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


def reset_analysis_state():
    st.session_state.analysis_completed = False
    st.session_state.previous_file = None
    st.session_state.previous_file_saved = False
    st.session_state.analysis_timestamp = None
    st.session_state.analysis_results = {}
    st.session_state.analysis_section_order = []
    st.session_state.view = "analysis"


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
    return


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
                for competitor in ["A사", "B사", "C사"]:
                    data = competitor_data.get(competitor) or competitor_data.get(competitor.lower()) if competitor_data else None
                    with st.expander(f"{competitor}", expanded=False):
                        if data:
                            if isinstance(data, list):
                                for item in data:
                                    st.markdown(f"- {item}")
                            elif isinstance(data, dict):
                                for key, value in data.items():
                                    st.markdown(f"**{key}**")
                                    if isinstance(value, list):
                                        for element in value:
                                            st.markdown(f"- {element}")
                                    else:
                                        st.markdown(str(value))
                            else:
                                st.markdown(str(data))
                        else:
                            st.info(f"{competitor}에 대한 분석 결과가 아직 준비되지 않았습니다.")
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
    st.markdown("## 전략 도출 결과")
    results_state = st.session_state.get("analysis_results", {})
    strategy_data = results_state.get("strategy") or results_state.get("strategy_output")

    if not strategy_data:
        st.info("전략 도출 결과가 아직 준비되지 않았습니다.")
    else:
        if isinstance(strategy_data, dict):
            for section_title, content in strategy_data.items():
                st.subheader(str(section_title))
                if isinstance(content, list):
                    for item in content:
                        st.markdown(f"- {item}")
                elif isinstance(content, dict):
                    for key, value in content.items():
                        st.markdown(f"**{key}**")
                        if isinstance(value, list):
                            for element in value:
                                st.markdown(f"- {element}")
                        else:
                            st.markdown(str(value))
                else:
                    st.markdown(str(content))
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
