import streamlit as st
from dotenv import load_dotenv
import os
import time
<<<<<<< HEAD
import base64
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
=======
import threading
from datetime import datetime
>>>>>>> b243754ea5fdb667d13f9cd6acdd96ccf1858bbe

# 환경변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="DealLens 전략분석 에이전트",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🚀"
)

<<<<<<< HEAD
# =============================================================================
# 유틸리티 함수
# =============================================================================

def get_base64_image(image_path):
    """이미지를 base64로 인코딩"""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

def generate_analysis_pdf():
    """분석 결과 PDF 생성"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    # 커스텀 스타일 정의
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1,  # 중앙 정렬
        textColor=colors.darkblue
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=colors.darkblue
    )
=======
# 커스텀 CSS 추가
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .step-container {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 10px;
    }
    .step {
        text-align: center;
        flex: 1;
        margin: 0 0.5rem;
    }
    .step-active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 15px 0 rgba(102, 126, 234, 0.3);
        transform: scale(1.05);
        transition: all 0.3s ease;
    }
    .step-completed {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 15px 0 rgba(17, 153, 142, 0.3);
    }
    .step-pending {
        background: #e9ecef;
        color: #6c757d;
        border-radius: 10px;
        padding: 1rem;
    }
    .analysis-stats {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
        padding: 1rem;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 10px;
        color: white;
    }
    .stat-item {
        text-align: center;
    }
    .pulse {
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown("""
<div class="main-header">
    <h1>🚀 DealLens: 전략분석 멀티에이전트</h1>
    <p>AI 기반 <strong>RFP 분석 → 내부 매칭 → 경쟁사 분석 → 전략 합성 → 리포트</strong> 파이프라인</p>
</div>
""", unsafe_allow_html=True)

# 사이드바 입력 영역
with st.sidebar:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 15px; color: white; text-align: center; margin-bottom: 2rem;'>
        <h2 style='margin: 0; color: white;'>⚙️ 분석 설정</h2>
        <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>파일과 경쟁사를 선택하세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 파일 업로드 섹션
    st.markdown("**📄 RFP 문서 업로드**")
    uploaded_file = st.file_uploader(
        "PDF 파일을 드래그하거나 클릭하여 업로드하세요",
        type=["pdf"],
        help="RFP 문서를 PDF 형태로 업로드해주세요. 최대 200MB까지 지원됩니다."
    )
    
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name} 업로드 완료")
        file_size = len(uploaded_file.getvalue()) / 1024 / 1024  # MB
        st.info(f"📊 파일 크기: {file_size:.1f} MB")
    
    st.markdown("---")
    
    # 경쟁사 선택 섹션
    st.markdown("**🏢 경쟁사 선택**")
    competitors = st.multiselect(
        "분석할 경쟁사를 선택하세요 (최대 5개 권장)",
        ["삼성SDS", "LG CNS", "포스코DX", "KT", "LG유플러스", "현대오토에버", "카카오엔터프라이즈", "CJ올리브네트웍스", "네이버클라우드", "SK C&C"],
        help="선택된 경쟁사에 대한 SWOT 분석이 수행됩니다."
    )
    
    if competitors:
        st.success(f"✅ {len(competitors)}개 경쟁사 선택됨")
        for comp in competitors:
            st.write(f"• {comp}")
    
    st.markdown("---")
    
    # 분석 실행 버튼
    run_button = st.button(
        "🚀 AI 분석 시작",
        use_container_width=True,
        type="primary",
        disabled=not (uploaded_file and competitors),
        help="PDF 파일과 경쟁사를 선택한 후 클릭하세요"
    )
    
    # 상태 표시
    if not uploaded_file:
        st.warning("📄 PDF 파일을 업로드해주세요")
    if not competitors:
        st.warning("🏢 경쟁사를 선택해주세요")
    if uploaded_file and competitors:
        st.success("✅ 분석 준비 완료!")

# 분석 단계 정의
ANALYSIS_STEPS = [
    {"id": "rfp_parsing", "name": "📄 RFP 분석", "desc": "문서 파싱 및 요구사항 추출"},
    {"id": "internal_matching", "name": "🔍 내부 매칭", "desc": "내부 역량 및 사례 매칭"},
    {"id": "competitor_analysis", "name": "🏢 경쟁사 분석", "desc": "경쟁사 SWOT 분석"},
    {"id": "strategy_synthesis", "name": "🎯 전략 수립", "desc": "전략 합성 및 제안"},
    {"id": "report_generation", "name": "📋 리포트 생성", "desc": "최종 보고서 작성"}
]

def show_progress_steps(current_step=None):
    """진행 단계 시각화"""
    st.markdown('<div class="step-container">', unsafe_allow_html=True)
    
    for i, step in enumerate(ANALYSIS_STEPS):
        if current_step and i < current_step:
            status_class = "step-completed"
            icon = "✅"
        elif current_step and i == current_step:
            status_class = "step-active pulse"
            icon = "⏳"
        else:
            status_class = "step-pending"
            icon = "⏸️"
            
        st.markdown(f"""
        <div class="step {status_class}">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
            <div style="font-weight: bold; margin-bottom: 0.25rem;">{step['name']}</div>
            <div style="font-size: 0.8rem; opacity: 0.8;">{step['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

def show_analysis_stats(elapsed_time, current_step_name, step_details=None):
    """분석 통계 표시"""
    st.markdown(f"""
    <div class="analysis-stats">
        <div class="stat-item">
            <div style="font-size: 2rem;">⏱️</div>
            <div><strong>{elapsed_time:.1f}초</strong></div>
            <div>경과 시간</div>
        </div>
        <div class="stat-item">
            <div style="font-size: 2rem;">🔄</div>
            <div><strong>{current_step_name}</strong></div>
            <div>현재 단계</div>
        </div>
        <div class="stat-item">
            <div style="font-size: 2rem;">🤖</div>
            <div><strong>AI 분석중</strong></div>
            <div>상태</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 단계별 상세 정보 표시
    if step_details:
        st.markdown(f"""
        <div style="background: rgba(102, 126, 234, 0.1); padding: 1rem; border-radius: 8px; margin: 1rem 0; border-left: 4px solid #667eea;">
            <strong>🔍 진행 상세:</strong> {step_details}
        </div>
        """, unsafe_allow_html=True)

# 세션 상태 초기화
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

# 메인 콘텐츠 영역
if run_button and uploaded_file and not st.session_state.analysis_complete:
    # PDF 저장을 위한 디렉토리 생성
    os.makedirs("data/samples", exist_ok=True)
>>>>>>> b243754ea5fdb667d13f9cd6acdd96ccf1858bbe
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # PDF 내용 구성
    story = []
    
    # 제목
    story.append(Paragraph("DealLens 전략 분석 보고서", title_style))
    story.append(Spacer(1, 20))
    
    # 분석 정보
    if st.session_state.get('previous_file'):
        story.append(Paragraph(f"<b>분석 파일:</b> {st.session_state.previous_file.name}", normal_style))
    story.append(Paragraph(f"<b>분석 시간:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 20))
    
    # 1. RFP 분석 결과
    story.append(Paragraph("① RFP 분석 결과", heading_style))
    story.append(Paragraph("🤖 Agent와 연결하면 RFP 문서 분석 결과가 표시됩니다.", normal_style))
    story.append(Spacer(1, 15))
    
    # 2. 내부 역량 매칭 결과
    story.append(Paragraph("② 내부 역량 매칭 결과", heading_style))
    story.append(Paragraph("🤖 Agent와 연결하면 내부 역량 매칭 결과가 표시됩니다.", normal_style))
    story.append(Spacer(1, 15))
    
    # 3. 경쟁사 분석 결과
    story.append(Paragraph("③ 경쟁사 분석 결과", heading_style))
    story.append(Paragraph("🤖 Agent와 연결하면 경쟁사 분석 결과가 표시됩니다.", normal_style))
    story.append(Spacer(1, 15))
    
    # 4. 전략 도출 결과
    story.append(Paragraph("④ 전략 도출 결과", heading_style))
    story.append(Paragraph("🤖 Agent와 연결하면 전략 도출 결과가 표시됩니다.", normal_style))
    story.append(Spacer(1, 20))
    
    # 푸터
    story.append(Paragraph("본 보고서는 DealLens 전략분석 멀티에이전트에 의해 생성되었습니다.", 
                          ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=1)))
    
    # PDF 생성
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def initialize_session_state():
    """세션 상태 초기화"""
    if 'show_history' not in st.session_state:
        st.session_state.show_history = False
    if 'analysis_running' not in st.session_state:
        st.session_state.analysis_running = False
    if 'analysis_completed' not in st.session_state:
        st.session_state.analysis_completed = False
    if 'analysis_history' not in st.session_state:
        st.session_state.analysis_history = []

<<<<<<< HEAD
def save_analysis_to_history():
    """현재 분석 결과를 히스토리에 저장"""
    if 'previous_file' in st.session_state and st.session_state.previous_file:
        file_content = None
        if hasattr(st.session_state.previous_file, 'getvalue'):
            file_content = st.session_state.previous_file.getvalue()
        elif hasattr(st.session_state.previous_file, 'read'):
            st.session_state.previous_file.seek(0)
            file_content = st.session_state.previous_file.read()
        
        analysis_record = {
            'filename': st.session_state.previous_file.name,
            'upload_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'file_content': file_content
        }
        st.session_state.analysis_history.append(analysis_record)

def reset_analysis_state():
    """분석 상태 초기화"""
    st.session_state.analysis_running = False
    st.session_state.analysis_completed = False
    st.session_state.previous_file = None

# =============================================================================
# CSS 스타일
# =============================================================================

st.markdown("""
<style>
    /* 메인 헤더 스타일 */
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
    
    .header-left {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
        position: relative;
        z-index: 1;
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        color: white;
        letter-spacing: -0.5px;
    }
    
    .main-header .subtitle {
        font-size: 0.9rem;
        margin: 0;
        color: #ccc;
        font-weight: 400;
        text-shadow: 0 0 10px rgba(138, 43, 226, 0.3);
    }
    
    .header-right {
        display: flex;
        align-items: center;
        gap: 1rem;
        position: relative;
        z-index: 1;
    }
    
    .nav-buttons {
        display: flex;
        gap: 0.5rem;
    }
    
    .nav-btn {
        background: transparent;
        border: 1px solid #333;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .nav-btn:hover {
        background: #333;
        border-color: #555;
    }
    
    /* 분석 진행 상태 스타일 */
    .step-container {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
        padding: 1rem;
        background-color: #f8f9fa;
        border-radius: 10px;
    }
    
    .step {
        text-align: center;
        flex: 1;
        margin: 0 0.5rem;
    }
    
    .step-active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 15px 0 rgba(102, 126, 234, 0.3);
        transform: scale(1.05);
        transition: all 0.3s ease;
    }
    
    .step-completed {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 15px 0 rgba(17, 153, 142, 0.3);
    }
    
    .step-pending {
        background: #e9ecef;
        color: #6c757d;
        border-radius: 10px;
        padding: 1rem;
    }
    
    .analysis-stats {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
        padding: 1rem;
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 10px;
        color: white;
    }
    
    .stat-item {
        text-align: center;
    }
    
    .pulse {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    @keyframes spin { 
        0% { transform: rotate(0deg); } 
        100% { transform: rotate(360deg); } 
    }
    
    /* 페이지 레이아웃 */
    .main .block-container {
        padding-top: 0 !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    .stApp > header {
        display: none !important;
    }
    
    .stApp {
        padding-top: 0 !important;
    }
    
    .main {
        padding-top: 0 !important;
    }
    
    .analysis-completed .main-header {
        display: none !important;
    }
    
    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #533483 100%) !important;
    }
    
    [data-testid="stSidebar"] > div {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #533483 100%) !important;
    }
    
    [data-testid="stSidebar"] * {
        background: transparent !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6 {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stButton > button {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.2) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
    }
    
    /* 다운로드 링크 스타일 */
    [data-testid="stSidebar"] .stDownloadButton > button,
    [data-testid="stSidebar"] button[data-testid="baseButton-secondary"],
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        border: none !important;
        color: #1a0dab !important;
        text-decoration: underline !important;
        font-weight: normal !important;
        padding: 0.5rem 0 !important;
        text-align: left !important;
    }
    
    [data-testid="stSidebar"] .stDownloadButton > button:hover,
    [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover,
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: transparent !important;
        color: #1509a0 !important;
        text-decoration: underline !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# JavaScript
# =============================================================================

st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const headerBtn = document.getElementById('header-history-btn');
    
    if (headerBtn) {
        headerBtn.onclick = function(e) {
            e.preventDefault();
            const url = new URL(window.location);
            url.searchParams.set('toggle_history', 'true');
            window.location.href = url.toString();
        };
    }
});

// 주기적으로 이벤트 리스너 재등록
setInterval(function() {
    const headerBtn = document.getElementById('header-history-btn');
    
    if (headerBtn && !headerBtn.onclick) {
        headerBtn.onclick = function(e) {
            e.preventDefault();
            const url = new URL(window.location);
            url.searchParams.set('toggle_history', 'true');
            window.location.href = url.toString();
        };
    }
}, 500);
</script>
""", unsafe_allow_html=True)

# =============================================================================
# 초기화
# =============================================================================

# 세션 상태 초기화
initialize_session_state()

# SKAX 로고 base64 인코딩
logo_base64 = get_base64_image("assets/sklogo.png")

# URL 쿼리 파라미터 처리
query_params = st.query_params
if query_params.get("toggle_history") == "true":
    st.session_state.show_history = not st.session_state.show_history
    try:
        del st.query_params["toggle_history"]
    except KeyError:
        pass
    st.rerun()

# =============================================================================
# 헤더 컴포넌트
# =============================================================================

def render_main_header():
    """메인 헤더 렌더링"""
    if logo_base64:
        st.markdown(f"""
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
    <div class="header-right">
        <div class="nav-buttons">
                    <button class="nav-btn" id="header-history-btn">📋 분석 History</button>
        </div>
</div>
    </div>
    """, unsafe_allow_html=True)
    else:
        st.markdown("""
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
            <div class="header-right">
                <div class="nav-buttons">
                    <button class="nav-btn" id="header-history-btn">📋 분석 History</button>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def render_sidebar_header():
    """사이드바 헤더 렌더링"""
    if logo_base64:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #533483 100%);
                    padding: 0.8rem 1rem; margin-bottom: 1rem; color: white; 
                    border-radius: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);">
            <div style="display: flex; flex-direction: column; align-items: center; gap: 0.3rem; margin-bottom: 0.3rem;">
                <img src="data:image/png;base64,{logo_base64}" style="height: 50px; width: auto;" alt="SKAX Logo">
                <h3 style="margin: 0; font-size: 1.2rem; color: white;">DealLens</h3>
            </div>
            <p style="margin: 0; font-size: 0.8rem; color: #ccc;">전략분석 멀티에이전트</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #533483 100%);
                    padding: 0.8rem 1rem; margin-bottom: 1rem; color: white; 
                    border-radius: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);">
            <div style="display: flex; flex-direction: column; align-items: center; gap: 0.3rem; margin-bottom: 0.3rem;">
                <div style="display: flex; align-items: center; gap: 0.2rem; background: rgba(255,255,255,0.1); padding: 0.2rem 0.4rem; border-radius: 4px;">
                    <span style="color: white; font-size: 0.7rem; font-weight: 600;">SKAX</span>
                </div>
                <h3 style="margin: 0; font-size: 1.2rem; color: white;">DealLens</h3>
            </div>
            <p style="margin: 0; font-size: 0.8rem; color: #ccc;">전략분석 멀티에이전트</p>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# 분석 히스토리 사이드바
# =============================================================================

def render_analysis_history():
    """분석 히스토리 사이드바 렌더링"""
    if st.session_state.show_history:
        with st.sidebar:
            st.markdown("### 📋 분석 History")
            st.markdown("---")

            if st.session_state.analysis_history:
                for i, record in enumerate(reversed(st.session_state.analysis_history)):
                    with st.expander(f"📄 {record['filename']}", expanded=False):
                        st.write(f"**업로드 시간:** {record['upload_time']}")
                        
                        if st.button(f"📊 분석 결과 보기", key=f"view_result_{i}"):
                            st.session_state.selected_analysis = i
                            st.session_state.show_analysis_detail = True

                        if record.get('file_content'):
                            st.download_button(
                                label="📥 PDF 다운로드",
                                data=record['file_content'],
                                file_name=record['filename'],
                                mime="application/pdf",
                                key=f"download_{i}"
                            )
                        else:
                            st.warning("파일 내용을 찾을 수 없습니다.")
            else:
                st.info("아직 분석 기록이 없습니다.")

            # 사이드바 닫기 버튼
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("닫기"):
                    st.session_state.show_history = False
                    st.rerun()

# =============================================================================
# 분석 결과 상세 보기
# =============================================================================

def render_analysis_detail():
    """선택된 분석 결과 상세 보기"""
    if st.session_state.get('show_analysis_detail'):
        if 'selected_analysis' in st.session_state:
            selected_idx = len(st.session_state.get('analysis_history', [])) - 1 - st.session_state.selected_analysis
            if 0 <= selected_idx < len(st.session_state.get('analysis_history', [])):
                record = st.session_state.analysis_history[selected_idx]

                st.markdown("---")
                st.markdown(f"### 📊 분석 결과: {record['filename']}")
                st.markdown(f"**분석 시간:** {record['upload_time']}")
                
                # 전략 보고서 표시
                st.markdown("---")
                st.markdown("## 📊 전략 분석 결과")
                
                # 1. RFP 분석 결과
                with st.expander("① RFP 분석 결과", expanded=True):
                    st.write("**핵심 요약**: RFP 문서에서 추출한 핵심 요구사항과 제약 조건을 분석했습니다.")
                    st.write("**핵심 요구사항:**")
                    st.write("- 기술적 요구사항: 클라우드 기반 솔루션 구축")
                    st.write("- 사업적 요구사항: 3년간 유지보수 지원")
                    st.write("- 제약 조건: 보안 인증 및 규정 준수")
                
                # 2. 내부 역량 매칭 결과
                with st.expander("② 내부 역량 매칭 결과", expanded=False):
                    st.write("**강점:**")
                    st.write("- 관련 레퍼런스 3건 보유")
                    st.write("- 동일 업종 솔루션 경험")
                    st.write("- 전문 인력 5명 확보")
                    st.write("**보완 필요:**")
                    st.write("- 추가 보안 인증 취득 필요")
                    st.write("- 특정 기술 스택 교육 필요")
                
                # 3. 경쟁사 분석 결과
                with st.expander("③ 경쟁사 분석 결과", expanded=False):
                    st.write("주요 경쟁사 3곳과의 가격/기술 비교 분석을 완료했습니다.")
                    st.write("**SWOT:**")
                    st.write("- 강점: 고객기반 및 브랜드 인지도")
                    st.write("- 약점: 맞춤형 솔루션 개발 역량 부족")
                    st.write("- 기회: 신규 규제에 따른 시장 확대")
                    st.write("- 위협: 저가 공세 및 신규 진입자")
                
                # 4. 전략 도출 결과
                with st.expander("④ 전략 도출 결과", expanded=True):
                    st.write("**전략 기둥(Pillars):**")
                    st.write("- 차별화된 기술 제안")
                    st.write("- 리스크 완화 전략")
                    st.write("- 레퍼런스 스토리텔링")
                    st.write("**전술(Tactics):**")
                    st.write("- PoC(Proof of Concept) 번들 제공")
                    st.write("- 단계별 견적안 제시")
                    st.write("- 상호운영성 강조")
                
                if st.button("🔙 목록으로 돌아가기"):
                    st.session_state.show_analysis_detail = False
                    st.rerun()

# =============================================================================
    # 파일 업로드 섹션
# =============================================================================

def render_file_upload():
    """파일 업로드 섹션 렌더링"""
    if st.session_state.get('analysis_completed', False):
        # 분석이 완료된 상태에서는 업로드 컴포넌트를 숨김
        return None

    st.markdown("""
    <div style="text-align: left; margin: 0.5rem 0 0.5rem 0;">
        <h3 style="font-size: 1.5rem; font-weight: 600; color: #333; margin-bottom: 0.5rem;">
            📄 RFP 파일을 업로드해주세요
        </h3>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "",
        type=["pdf"],
        help="RFP 문서를 PDF 형태로 업로드해주세요. 최대 200MB까지 지원됩니다.",
        label_visibility="collapsed"
    )
    return uploaded_file

# =============================================================================
# 분석 버튼 UI
# =============================================================================

def render_analysis_button(uploaded_file):
    """분석 버튼 UI 렌더링"""
    if st.session_state.get('analysis_completed', False):
        return

    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        run_button = st.button(
            "📄 RFP 업로드",
            use_container_width=True,
            type="primary",
            disabled=uploaded_file is None,
            help="RFP 파일을 업로드한 후 클릭하세요"
        )

    if run_button:
        if uploaded_file is not None:
            st.session_state.previous_file = uploaded_file
        st.session_state.analysis_running = False
        st.session_state.analysis_completed = True
        st.rerun()

# =============================================================================
# 분석 단계 처리
# =============================================================================

def process_analysis_steps():
    """분석 단계 처리"""
    if not st.session_state.get('analysis_completed', False) and st.session_state.analysis_running:
        # 현재 단계 초기화
        if 'current_step_index' not in st.session_state:
            st.session_state.current_step_index = 0
            st.session_state.start_time = time.time()
            st.session_state.step_status = {
                'step1_completed': False,
                'step2_completed': False,
                'step3_completed': False,
                'step4_completed': False
            }
        
        steps = [
            "1/4 RFP 문서 분석 중...",
            "2/4 핵심 요구사항 추출 중...",
            "3/4 전략 분석 수행 중...",
            "4/4 결과 정리 중...",
            "AI 분석 완료"
        ]
        
        # 현재는 시뮬레이션으로 시간 기반 진행
        elapsed_time = time.time() - st.session_state.start_time
        current_index = min(int(elapsed_time), len(steps) - 1)
        
        # 현재 단계 업데이트
        st.session_state.current_step = steps[current_index]
        st.session_state.current_step_index = current_index
        
        # 모든 단계 완료 시 (5초 후)
        if elapsed_time >= 5.0:
            st.session_state.analysis_completed = True
            st.session_state.analysis_running = False
            # 세션 상태 정리
            for key in ['current_step_index', 'start_time', 'step_status']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        else:
            # 아직 진행 중이면 0.1초 후 다시 실행
            time.sleep(0.1)
            st.rerun()

# =============================================================================
# 전략 분석 보고서
# =============================================================================

def render_strategy_report():
    """전략 분석 보고서 렌더링"""
    if st.session_state.get('analysis_completed', False):
        # 사이드바에 헤더 표시
        with st.sidebar:
            render_sidebar_header()
            
            # 분석 정보 표시
            if st.session_state.get('previous_file'):
                file_content = None
                if hasattr(st.session_state.previous_file, 'getvalue'):
                    file_content = st.session_state.previous_file.getvalue()
                elif hasattr(st.session_state.previous_file, 'read'):
                    st.session_state.previous_file.seek(0)
                    file_content = st.session_state.previous_file.read()
                
                if file_content:
                    b64_file = base64.b64encode(file_content).decode()
                    st.markdown(f"""
                    <div style="margin: 0.5rem 0;">
                        <strong>분석 파일:</strong><br>
                        <a href="data:application/pdf;base64,{b64_file}" 
                           download="{st.session_state.previous_file.name}"
                           style="color: #1a0dab; text-decoration: underline; font-size: 0.9rem;"
                           onmouseover="this.style.color='#1509a0'"
                           onmouseout="this.style.color='#1a0dab'">
                            {st.session_state.previous_file.name}
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"**분석 파일:** {st.session_state.previous_file.name}")
                    st.warning("파일 내용을 찾을 수 없습니다.")
                    
            st.markdown(f"**분석 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            st.markdown("---")
            
            # 사이드바 버튼들
            if st.button("📋 분석 History", use_container_width=True):
                st.session_state.show_history = not st.session_state.show_history
                st.rerun()
            
            if st.button("🔄 새로운 분석", use_container_width=True):
                save_analysis_to_history()
                reset_analysis_state()
                st.rerun()
        
        # 전략 분석 보고서 표시
        st.markdown("## 전략 분석 결과")
        
        # TODO: Agent와 연결하면 실제 분석 결과가 표시됩니다
        # 1. RFP 분석 결과
        with st.expander("① RFP 분석 결과", expanded=True):
            st.info("🤖 Agent와 연결하면 RFP 문서 분석 결과가 표시됩니다.")
        
        # 2. 내부 역량 매칭 결과
        with st.expander("② 내부 역량 매칭 결과", expanded=False):
            st.info("🤖 Agent와 연결하면 내부 역량 매칭 결과가 표시됩니다.")
        
        # 3. 경쟁사 분석 결과
        with st.expander("③ 경쟁사 분석 결과", expanded=False):
            st.info("🤖 Agent와 연결하면 경쟁사 분석 결과가 표시됩니다.")
        
        # 4. 전략 도출 결과
        with st.expander("④ 전략 도출 결과", expanded=True):
            st.info("🤖 Agent와 연결하면 전략 도출 결과가 표시됩니다.")
        
        # PDF 다운로드 버튼
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            try:
                pdf_data = generate_analysis_pdf()
                filename = f"DealLens_분석보고서_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                
                st.download_button(
                    label="📄 분석 결과 PDF 다운로드",
                    data=pdf_data,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF 생성 중 오류가 발생했습니다: {str(e)}")
                st.info("reportlab 라이브러리가 설치되어 있는지 확인해주세요: pip install reportlab")

# =============================================================================
# 메인 실행 로직
# =============================================================================

def main():
    """메인 실행 함수"""
    # 헤더 렌더링 (분석 완료 시에는 숨김)
    if not st.session_state.get('analysis_completed', False):
        render_main_header()
    
    # 분석 히스토리 사이드바
    render_analysis_history()
    
    # 분석 결과 상세 보기
    render_analysis_detail()
    
    # 파일 업로드 섹션
    uploaded_file = render_file_upload()
    
    # 새로운 파일 업로드 시 분석 완료 상태 초기화
    if uploaded_file and st.session_state.get('analysis_completed', False):
        save_analysis_to_history()
        st.session_state.analysis_running = False
        st.session_state.analysis_completed = False
        st.session_state.previous_file = uploaded_file
        st.rerun()
    elif uploaded_file:
        st.session_state.previous_file = uploaded_file
    
    # 분석 버튼 UI
    render_analysis_button(uploaded_file)
    
    # 분석 단계 처리
    process_analysis_steps()
    
    # 전략 분석 보고서
    render_strategy_report()

# =============================================================================
# 앱 실행
# =============================================================================

if __name__ == "__main__":
    main()
=======
    # 진행률 표시 영역 생성
    progress_container = st.container()
    stats_container = st.container()
    
    with progress_container:
        st.markdown("### 🚀 분석 진행 상황")
        progress_placeholder = st.empty()
        
    with stats_container:
        stats_placeholder = st.empty()
    
    # 분석 시작
    start_time = time.time()
    
    # 각 단계별 진행률 표시
    for i, step in enumerate(ANALYSIS_STEPS):
        with progress_placeholder.container():
            show_progress_steps(current_step=i)
        
        with stats_placeholder.container():
            elapsed = time.time() - start_time
            show_analysis_stats(elapsed, step['name'])
        
        # 각 단계별 상세 메시지와 함께 더 긴 딜레이
        step_details = None
        if i == 0:  # RFP 분석
            step_details = "PDF 문서에서 텍스트를 추출하고 요구사항, 평가기준, 리스크를 분석하고 있습니다"
            st.info("📄 PDF 문서를 파싱하고 요구사항을 추출하고 있습니다...")
            
            # 세부 진행률 표시
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for percent in range(0, 101, 10):
                progress_bar.progress(percent)
                if percent < 30:
                    status_text.text("📖 PDF 문서 읽는 중...")
                elif percent < 70:
                    status_text.text("🔍 요구사항 추출 중...")
                else:
                    status_text.text("✅ 분석 완료!")
                time.sleep(0.3)
                
        elif i == 1:  # 내부 매칭
            step_details = "내부 사례 데이터베이스에서 관련 프로젝트와 역량을 매칭하고 있습니다"
            st.info("🔍 내부 역량 데이터베이스와 매칭하고 있습니다...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for percent in range(0, 101, 15):
                progress_bar.progress(percent)
                if percent < 40:
                    status_text.text("🗃️ 내부 데이터베이스 검색 중...")
                elif percent < 80:
                    status_text.text("🔗 관련 사례 매칭 중...")
                else:
                    status_text.text("✅ 매칭 완료!")
                time.sleep(0.25)
                
        elif i == 2:  # 경쟁사 분석
            step_details = f"{len(competitors)}개 경쟁사의 강점, 약점, 기회, 위협 요소를 분석하고 있습니다"
            st.info("🏢 선택된 경쟁사들의 SWOT 분석을 수행하고 있습니다...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for percent in range(0, 101, 12):
                progress_bar.progress(percent)
                if percent < 25:
                    status_text.text("🏢 경쟁사 정보 수집 중...")
                elif percent < 50:
                    status_text.text("💪 강점 분석 중...")
                elif percent < 75:
                    status_text.text("⚠️ 약점 및 위협 분석 중...")
                else:
                    status_text.text("✅ SWOT 분석 완료!")
                time.sleep(0.35)
                
        elif i == 3:  # 전략 수립
            step_details = "분석 결과를 종합하여 차별화 전략과 액션 플랜을 수립하고 있습니다"
            st.info("🎯 분석 결과를 바탕으로 전략을 수립하고 있습니다...")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for percent in range(0, 101, 20):
                progress_bar.progress(percent)
                if percent < 40:
                    status_text.text("📊 데이터 종합 분석 중...")
                elif percent < 80:
                    status_text.text("🎯 전략 수립 중...")
                else:
                    status_text.text("✅ 전략 완성!")
                time.sleep(0.2)
                
        elif i == 4:  # 리포트 생성
            step_details = "최종 보고서를 작성하고 AI 분석을 실행하고 있습니다"
            st.info("📋 최종 보고서를 생성하고 있습니다...")
            with st.spinner("🔄 AI 분석 실행 중... 잠시만 기다려주세요"):
                result = supervisor.invoke({"input": query})
        
        # 단계별 상세 정보 업데이트
        if step_details:
            with stats_placeholder.container():
                elapsed = time.time() - start_time
                show_analysis_stats(elapsed, step['name'], step_details)
    
    # 완료 상태 표시
    with progress_placeholder.container():
        show_progress_steps(current_step=len(ANALYSIS_STEPS))
    
    with stats_placeholder.container():
        total_time = time.time() - start_time
        st.markdown(f"""
        <div class="analysis-stats">
            <div class="stat-item">
                <div style="font-size: 2rem;">✅</div>
                <div><strong>완료</strong></div>
                <div>분석 상태</div>
            </div>
            <div class="stat-item">
                <div style="font-size: 2rem;">⏱️</div>
                <div><strong>{total_time:.1f}초</strong></div>
                <div>총 소요 시간</div>
            </div>
            <div class="stat-item">
                <div style="font-size: 2rem;">📊</div>
                <div><strong>5단계</strong></div>
                <div>완료된 분석</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 완료 메시지와 함께 결과 페이지로 전환 안내
    st.success("🎉 분석이 성공적으로 완료되었습니다!")
    
    # 결과를 세션 상태에 저장
    st.session_state.analysis_result = result
    st.session_state.analysis_complete = True
    
    # 자동 페이지 전환을 위한 카운트다운
    countdown_placeholder = st.empty()
    for i in range(3, 0, -1):
        countdown_placeholder.info(f"🔄 {i}초 후 결과 페이지로 이동합니다...")
        time.sleep(1)
    countdown_placeholder.empty()
    
    # 페이지 새로고침으로 결과 페이지 표시
    st.rerun()

# 분석 완료 후 결과 페이지 표시
elif st.session_state.analysis_complete and st.session_state.analysis_result:
    result = st.session_state.analysis_result
    
    # 결과 페이지 헤더
    st.markdown("# 📊 분석 결과")
    st.balloons()  # 축하 효과
    
    # Deal Brief (요약) - 더 매력적인 디자인
    st.markdown("## 📋 Deal Brief")
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; margin: 1rem 0; box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);'>
        <h3 style='margin-top: 0; color: white;'>💼 전략 요약</h3>
        <p style='font-size: 1.1rem; line-height: 1.6; margin-bottom: 0;'>
            {result.get("output", result.get("deal_brief", "분석 결과를 불러오는 중입니다..."))}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 상세 결과 (탭으로 구분) - 개선된 디자인
    st.markdown("## 📑 상세 분석 결과")
    tab1, tab2, tab3, tab4 = st.tabs(["📋 요구사항", "⚖️ 평가기준/리스크", "🏢 경쟁사 분석", "🎯 전략 제안"])

    with tab1:
        st.markdown("#### 🔹 요구사항 분석")
        requirements = result.get("sections", {}).get("요구사항", [])
        if requirements:
            for idx, req in enumerate(requirements, 1):
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 1rem; border-left: 4px solid #667eea; margin: 0.5rem 0; border-radius: 0 8px 8px 0;'>
                    <strong>{idx}.</strong> {req}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("요구사항 데이터를 불러오는 중입니다...")

    with tab2:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🛡️ 평가 기준")
            criteria = result.get("sections", {}).get("평가기준", [])
            if criteria:
                for idx, crit in enumerate(criteria, 1):
                    st.markdown(f"""
                    <div style='background: #e8f5e8; padding: 1rem; border-left: 4px solid #28a745; margin: 0.5rem 0; border-radius: 0 8px 8px 0;'>
                        <strong>{idx}.</strong> {crit}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("평가기준 데이터를 불러오는 중입니다...")
        
        with col2:
            st.markdown("#### ⚠️ 리스크 분석")
            risks = result.get("sections", {}).get("리스크", [])
            if risks:
                for idx, risk in enumerate(risks, 1):
                    st.markdown(f"""
                    <div style='background: #fff3cd; padding: 1rem; border-left: 4px solid #ffc107; margin: 0.5rem 0; border-radius: 0 8px 8px 0;'>
                        <strong>{idx}.</strong> {risk}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("리스크 데이터를 불러오는 중입니다...")

    with tab3:
        st.markdown("#### 🏢 경쟁사 SWOT 분석")
        competitors_data = result.get("sections", {}).get("경쟁사", {})
        if competitors_data:
            for name, swot in competitors_data.items():
                with st.expander(f"🏢 {name}", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**💪 강점 (Strengths)**")
                        st.success(swot.get('S', '-'))
                        st.markdown("**🎯 기회 (Opportunities)**")
                        st.info(swot.get('O', '-'))
                    with col2:
                        st.markdown("**⚠️ 약점 (Weaknesses)**")
                        st.warning(swot.get('W', '-'))
                        st.markdown("**🚫 위협 (Threats)**")
                        st.error(swot.get('T', '-'))
        else:
            st.info("경쟁사 분석 데이터를 불러오는 중입니다...")

    with tab4:
        st.markdown("#### 🎯 전략 제안")
        strategy = result.get("sections", {}).get("전략", {})
        
        if strategy:
            # 전략 요약
            if "actions" in strategy:
                st.markdown("**📌 핵심 액션 플랜**")
                for idx, action in enumerate(strategy["actions"], 1):
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; padding: 1rem; margin: 0.5rem 0; border-radius: 10px;'>
                        <strong>{idx}.</strong> {action}
                    </div>
                    """, unsafe_allow_html=True)
            
            # SWOT 요약
            if "swot" in strategy:
                st.markdown("**📊 SWOT 요약**")
                with st.expander("SWOT 분석 상세", expanded=False):
                    st.json(strategy["swot"])
            
            # 차별화 포인트
            if "differentiation" in strategy:
                st.markdown("**✨ 차별화 포인트**")
                for idx, diff in enumerate(strategy["differentiation"], 1):
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 1rem; margin: 0.5rem 0; border-radius: 10px;'>
                        <strong>💎 {idx}.</strong> {diff}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("전략 제안 데이터를 불러오는 중입니다...")
    
    # 새로운 분석 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 새로운 분석 시작", use_container_width=True, type="secondary"):
            # 세션 상태 초기화
            st.session_state.analysis_complete = False
            st.session_state.analysis_result = None
            st.rerun()

else:
    # 대기 화면 - 더 매력적인 디자인
    st.markdown("""
    <div style='text-align: center; padding: 3rem 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; color: white; margin: 2rem 0;'>
        <h2 style='margin-top: 0; color: white;'>🚀 DealLens 전략분석 시작하기</h2>
        <p style='font-size: 1.2rem; margin: 1.5rem 0;'>AI 기반 RFP 분석으로 경쟁력 있는 전략을 수립하세요</p>
        <div style='background: rgba(255, 255, 255, 0.2); padding: 1.5rem; border-radius: 15px; margin: 2rem 0;'>
            <h3 style='color: white; margin-top: 0;'>📋 분석 프로세스</h3>
            <div style='display: flex; justify-content: space-around; flex-wrap: wrap;'>
                <div style='margin: 0.5rem; text-align: center;'>
                    <div style='font-size: 2rem;'>📄</div>
                    <div>RFP 분석</div>
                </div>
                <div style='margin: 0.5rem; text-align: center;'>
                    <div style='font-size: 2rem;'>🔍</div>
                    <div>내부 매칭</div>
                </div>
                <div style='margin: 0.5rem; text-align: center;'>
                    <div style='font-size: 2rem;'>🏢</div>
                    <div>경쟁사 분석</div>
                </div>
                <div style='margin: 0.5rem; text-align: center;'>
                    <div style='font-size: 2rem;'>🎯</div>
                    <div>전략 수립</div>
                </div>
                <div style='margin: 0.5rem; text-align: center;'>
                    <div style='font-size: 2rem;'>📋</div>
                    <div>리포트 생성</div>
                </div>
            </div>
        </div>
        <p style='font-size: 1rem; opacity: 0.8; margin-bottom: 0;'>👈 좌측 사이드바에서 PDF를 업로드하고 경쟁사를 선택한 후 분석을 시작하세요</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 기능 소개 섹션
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; height: 200px; display: flex; flex-direction: column; justify-content: center;'>
            <div style='font-size: 3rem; margin-bottom: 1rem;'>🤖</div>
            <h3 style='margin: 0; color: white;'>AI 기반 분석</h3>
            <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>최신 AI 기술로 정확한 분석</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; height: 200px; display: flex; flex-direction: column; justify-content: center;'>
            <div style='font-size: 3rem; margin-bottom: 1rem;'>⚡</div>
            <h3 style='margin: 0; color: white;'>빠른 처리</h3>
            <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>몇 분 내에 완성되는 전략 보고서</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 15px; color: white; text-align: center; height: 200px; display: flex; flex-direction: column; justify-content: center;'>
            <div style='font-size: 3rem; margin-bottom: 1rem;'>📊</div>
            <h3 style='margin: 0; color: white;'>상세 분석</h3>
            <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>요구사항부터 전략까지 한번에</p>
        </div>
        """, unsafe_allow_html=True)
>>>>>>> b243754ea5fdb667d13f9cd6acdd96ccf1858bbe
