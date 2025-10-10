import streamlit as st
from dotenv import load_dotenv
import os
import time
import base64
import threading
import asyncio
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO

# Supervisor import
from workflow.supervisor import ParallelSupervisor, llm

# 환경변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="DealLens 전략분석 에이전트",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🚀"
)

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
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'supervisor' not in st.session_state:
        st.session_state.supervisor = ParallelSupervisor(llm) if llm else None
    if 'show_strategy_detail' not in st.session_state:
        st.session_state.show_strategy_detail = False

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
            'file_content': file_content,
            'analysis_results': st.session_state.get('analysis_results')
        }
        st.session_state.analysis_history.append(analysis_record)

def reset_analysis_state():
    """분석 상태 초기화"""
    st.session_state.analysis_running = False
    st.session_state.analysis_completed = False
    st.session_state.previous_file = None
    st.session_state.analysis_results = None
    st.session_state.show_strategy_detail = False

async def run_analysis_async(uploaded_file):
    """비동기 분석 실행"""
    if not st.session_state.supervisor:
        return {
            "error": "Supervisor가 초기화되지 않았습니다. API 키를 확인해주세요."
        }
    
    temp_path = None
    try:
        # 파일 내용 읽기
        file_content = uploaded_file.read()
        uploaded_file.seek(0)  # 파일 포인터 초기화
        
        # RFP 파일 경로 생성 (임시)
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(file_content)
        
        # Supervisor 실행 (수정된 형식)
        input_data = {
            "pdf_path": temp_path,
            "user_input": f"'{uploaded_file.name}' RFP 파일을 분석하여 전략 보고서를 작성해주세요."
        }
        results = await st.session_state.supervisor.invoke(input_data)
        
        return results
    except Exception as e:
        return {
            "error": f"분석 중 오류 발생: {str(e)}"
        }
    finally:
        # 임시 파일 삭제 (finally로 확실히 삭제)
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

def run_analysis(uploaded_file):
    """분석 실행 (동기 래퍼)"""
    return asyncio.run(run_analysis_async(uploaded_file))

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
logo_base64 = get_base64_image("data/sklogo.png")

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
                
                # 저장된 분석 결과 가져오기
                results = record.get('analysis_results')
                
                # 1. RFP 분석 결과
                with st.expander("① RFP 분석 결과", expanded=True):
                    if results and 'rfp_parser' in results:
                        rfp_data = results['rfp_parser']
                        if 'requirements' in rfp_data:
                            st.markdown("**📋 핵심 요구사항:**")
                            for req in rfp_data['requirements'][:10]:
                                st.markdown(f"- {req}")
                        if 'evaluation' in rfp_data:
                            st.markdown("\n**⚖️ 평가 기준:**")
                            for eval_item in rfp_data['evaluation'][:10]:
                                st.markdown(f"- {eval_item}")
                    else:
                        st.info("분석 결과가 없습니다.")
                
                # 2. 내부 역량 매칭 결과
                with st.expander("② 내부 역량 매칭 결과", expanded=False):
                    if results and 'internal_rag' in results:
                        internal_data = results['internal_rag']
                        matches = internal_data.get('internal_matches', [])
                        if matches:
                            for match in matches:
                                req = match.get('requirement', '요구사항 미지정')
                                st.markdown(f"**🔹 {req}**")
                                related = match.get('matches', [])
                                if related:
                                    for proj in related[:3]:
                                        st.markdown(f"- **{proj.get('title', '제목 없음')}**")
                                else:
                                    st.markdown("  ⚠️ 매칭된 사례 없음")
                        else:
                            st.warning("매칭된 내부 역량이 없습니다.")
                    else:
                        st.info("분석 결과가 없습니다.")
                
                # 3. 경쟁사 분석 결과
                with st.expander("③ 경쟁사 분석 결과", expanded=False):
                    if results and 'competitor_analysis' in results:
                        competitor_data = results['competitor_analysis']
                        profiles = competitor_data.get('competitor_profiles', {})
                        for company, profile in profiles.items():
                            st.markdown(f"### {company}")
                            if profile.get('company_summary'):
                                st.markdown(f"**📝 요약:** {profile['company_summary'][:200]}...")
                    else:
                        st.info("분석 결과가 없습니다.")
                
                # 4. 전략 도출 결과
                with st.expander("④ 전략 도출 결과", expanded=True):
                    if results and 'strategy' in results:
                        strategy_data = results['strategy'].get('strategy', {})
                        
                        if strategy_data.get('summary'):
                            st.markdown("### 💡 AI 전략 요약")
                            st.info(strategy_data['summary'])
                            st.markdown("---")
                        
                        if strategy_data.get('actions'):
                            st.markdown("**🎯 액션 플랜:**")
                            for action in strategy_data['actions']:
                                st.markdown(f"- {action}")
                        
                        if strategy_data.get('differentiation'):
                            st.markdown("\n**✨ 차별화 포인트:**")
                            for diff in strategy_data['differentiation']:
                                st.markdown(f"- {diff}")
                    else:
                        st.info("분석 결과가 없습니다.")
                
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
            "📊 분석 시작",
            use_container_width=True,
            type="primary",
            disabled=uploaded_file is None,
            help="RFP 파일을 업로드한 후 클릭하세요"
        )

    if run_button:
        if uploaded_file is not None:
            st.session_state.previous_file = uploaded_file
            st.session_state.analysis_running = True
            
            # 분석 진행 중 표시
            with st.spinner("🔄 AI 에이전트가 분석을 진행 중입니다..."):
                # 실제 분석 실행
                results = run_analysis(uploaded_file)
                st.session_state.analysis_results = results
                
            st.session_state.analysis_running = False
            st.session_state.analysis_completed = True
            st.rerun()

# =============================================================================
# 분석 단계 처리
# =============================================================================

def process_analysis_steps():
    """분석 단계 처리 (실제 분석은 render_analysis_button에서 처리됨)"""
    # 이제 실제 분석은 버튼 클릭 시 동기적으로 처리되므로
    # 이 함수는 더 이상 더미 프로그레스를 표시하지 않음
    pass

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
        
        # 분석 결과 확인
        results = st.session_state.get('analysis_results')
        
        if results and 'error' in results:
            st.error(f"❌ {results['error']}")
            st.info("💡 .env 파일에 API 키가 올바르게 설정되어 있는지 확인해주세요.")
        
        # 1. RFP 분석 결과
        with st.expander("① RFP 분석 결과", expanded=True):
            if results and 'rfp_parser' in results and not results.get('error'):
                rfp_data = results['rfp_parser']
                
                if 'requirements' in rfp_data:
                    st.markdown("**📋 핵심 요구사항:**")
                    for req in rfp_data['requirements'][:10]:
                        st.markdown(f"- {req}")
                
                if 'evaluation' in rfp_data:
                    st.markdown("\n**⚖️ 평가 기준:**")
                    for eval_item in rfp_data['evaluation'][:10]:
                        st.markdown(f"- {eval_item}")
                
                if 'risks' in rfp_data:
                    st.markdown("\n**⚠️ 리스크 요소:**")
                    for risk in rfp_data['risks'][:10]:
                        st.markdown(f"- {risk}")
            else:
                st.info("🤖 분석을 시작하면 RFP 문서 분석 결과가 표시됩니다.")
        
        # 2. 내부 역량 매칭 결과
        with st.expander("② 내부 역량 매칭 결과", expanded=False):
            if results and 'internal_rag' in results and not results.get('error'):
                internal_data = results['internal_rag']
                matches = internal_data.get('internal_matches', [])
                
                if matches:
                    for match in matches:
                        req = match.get('requirement', '요구사항 미지정')
                        st.markdown(f"**🔹 {req}**")
                        
                        related = match.get('matches', [])
                        if related:
                            for proj in related[:3]:
                                st.markdown(f"- **{proj.get('title', '제목 없음')}**")
                                if proj.get('summary'):
                                    st.markdown(f"  {proj['summary'][:200]}...")
                                if proj.get('url'):
                                    st.markdown(f"  [🔗 상세보기]({proj['url']})")
                        else:
                            st.markdown("  ⚠️ 매칭된 사례 없음")
                        st.markdown("---")
                else:
                    st.warning("매칭된 내부 역량이 없습니다.")
            else:
                st.info("🤖 분석을 시작하면 내부 역량 매칭 결과가 표시됩니다.")
        
        # 3. 경쟁사 분석 결과
        with st.expander("③ 경쟁사 분석 결과", expanded=False):
            if results and 'competitor_analysis' in results and not results.get('error'):
                competitor_data = results['competitor_analysis']
                profiles = competitor_data.get('competitor_profiles', {})
                
                for company, profile in profiles.items():
                    st.markdown(f"### {company}")
                    
                    # 회사 요약
                    if profile.get('company_summary'):
                        st.markdown(f"**📝 요약:** {profile['company_summary'][:300]}...")
                    
                    # SWOT
                    swot = profile.get('swot', {})
                    if swot:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**💪 강점 (S):**")
                            for s in swot.get('S', []):
                                st.markdown(f"- {s}")
                            st.markdown("**🌟 기회 (O):**")
                            for o in swot.get('O', []):
                                st.markdown(f"- {o}")
                        with col2:
                            st.markdown("**⚠️ 약점 (W):**")
                            for w in swot.get('W', []):
                                st.markdown(f"- {w}")
                            st.markdown("**⚡ 위협 (T):**")
                            for t in swot.get('T', []):
                                st.markdown(f"- {t}")
                    
                    # 최신 뉴스
                    recent_news = profile.get('recent_news', [])
                    if recent_news:
                        st.markdown("**📰 최신 뉴스:**")
                        for news in recent_news[:3]:
                            st.markdown(f"- [{news.get('title', '제목 없음')}]({news.get('url', '#')})")
                    
                    st.markdown("---")
            else:
                st.info("🤖 분석을 시작하면 경쟁사 분석 결과가 표시됩니다.")
        
        # 전략분석보고서 읽기 버튼
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📊 전략분석보고서 읽기", use_container_width=True, type="primary"):
                st.session_state.show_strategy_detail = True
                st.rerun()
        
        # PDF 다운로드 버튼
        st.markdown("")
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
# 전략 상세 보고서 페이지
# =============================================================================

def render_strategy_detail_page():
    """전략 도출 결과 상세 페이지"""
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
        if st.button("🔙 분석 결과로 돌아가기", use_container_width=True):
            st.session_state.show_strategy_detail = False
            st.rerun()
        
        if st.button("📋 분석 History", use_container_width=True):
            st.session_state.show_history = not st.session_state.show_history
            st.rerun()
        
        if st.button("🔄 새로운 분석", use_container_width=True):
            save_analysis_to_history()
            reset_analysis_state()
            st.rerun()
    
    # 전략 도출 결과 표시
    st.markdown("# 📈 전략 분석 보고서")
    st.markdown("---")
    
    # 분석 결과 가져오기
    results = st.session_state.get('analysis_results')
    
    if results and 'strategy' in results and not results.get('error'):
        strategy_data = results['strategy'].get('strategy', {})
        
        # 1️⃣ 전략 요약 (핵심 방향성)
        st.markdown("## 1️⃣ 전략 요약 (핵심 방향성)")
        if strategy_data.get('summary'):
            st.info(strategy_data['summary'])
        
        # Focus 영역 표시
        focus = strategy_data.get('focus', {})
        if focus:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**🔧 내부 역량 관점**")
                st.markdown(focus.get('internal', 'N/A'))
            with col2:
                st.markdown("**🥊 경쟁사 대응 관점**")
                st.markdown(focus.get('competitor', 'N/A'))
            with col3:
                st.markdown("**📊 시장/정책 관점**")
                st.markdown(focus.get('market', 'N/A'))
        st.markdown("---")
        
        # 2️⃣ 요구사항 대비 내부 갭 분석
        st.markdown("## 2️⃣ 요구사항 대비 내부 갭 분석")
        appendix = strategy_data.get('appendix', {})
        gaps = appendix.get('gaps', [])
        
        if gaps:
            for gap in gaps:
                gap_level = gap.get('gap', 'unknown').upper()
                gap_color = {
                    'HIGH': '🔴',
                    'MEDIUM': '🟡',
                    'LOW': '🟢',
                    'UNKNOWN': '⚪'
                }.get(gap_level, '⚪')
                
                gap_id = gap.get('id', '')
                st.markdown(f"**{gap_color} [{gap_id}] {gap.get('requirement', '요구사항 미지정')}**")
                st.markdown(f"- **갭 수준:** {gap_level}")
                st.markdown(f"- **보완 액션:** {gap.get('suggested_action', 'N/A')}")
                
                # 연결된 액션 표시
                action_ids = gap.get('action_ids', [])
                if action_ids:
                    st.markdown(f"- **연결된 액션:** {', '.join(action_ids)}")
                st.markdown("")
        else:
            st.info("갭 분석 데이터가 없습니다.")
        st.markdown("---")
        
        # 3️⃣ 경쟁사 대응 전략
        st.markdown("## 3️⃣ 경쟁사 대응 전략")
        competitor_counters = appendix.get('competitor_counters', [])
        
        if competitor_counters:
            for counter in competitor_counters:
                st.markdown(f"### 🏢 {counter.get('company', '경쟁사')}")
                st.markdown(counter.get('counter', 'N/A'))
                st.markdown("")
        
        # 차별화 포인트
        differentiation = strategy_data.get('differentiation', [])
        if differentiation:
            st.markdown("### ✨ 당사 차별화 포인트")
            for i, diff in enumerate(differentiation, 1):
                st.markdown(f"{i}. {diff}")
        
        if not competitor_counters and not differentiation:
            st.info("경쟁사 대응 전략 데이터가 없습니다.")
        st.markdown("---")
        
        # 4️⃣ 핵심 액션 플랜
        st.markdown("## 4️⃣ 핵심 액션 플랜")
        actions = strategy_data.get('prioritized_actions', [])
        
        if actions:
            for i, action in enumerate(actions, 1):
                if isinstance(action, dict):
                    # 우선순위 표시
                    impact = action.get('impact', 'medium').upper()
                    urgency = action.get('urgency', 'medium').upper()
                    effort = action.get('effort', 'medium').upper()
                    
                    priority_badge = "🔥" if impact == "HIGH" and urgency == "HIGH" else "⚡" if urgency == "HIGH" else "📌"
                    action_id = action.get('id', f'A{i}')
                    
                    st.markdown(f"### {priority_badge} [{action_id}] {action.get('action', '액션 항목')}")
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**📝 선정 근거:** {action.get('why', 'N/A')}")
                        st.markdown(f"**👤 담당:** {action.get('owner', 'N/A')}")
                        
                        # 기대 결과 (수치화)
                        expected_result = action.get('expected_result', '')
                        if expected_result:
                            st.markdown(f"**📊 기대 결과:** {expected_result}")
                    
                    with col2:
                        st.markdown(f"**Impact:** `{impact}`")
                        st.markdown(f"**Urgency:** `{urgency}`")
                        st.markdown(f"**Effort:** `{effort}`")
                        st.markdown(f"**기한:** {action.get('due_hint', 'N/A')}")
                    
                    # 연결 관계
                    related_gaps = action.get('related_gaps', [])
                    related_risks = action.get('related_risks', [])
                    if related_gaps or related_risks:
                        st.markdown("**🔗 연결:**")
                        if related_gaps:
                            st.markdown(f"  - 해결하는 갭: {', '.join(related_gaps)}")
                        if related_risks:
                            st.markdown(f"  - 완화하는 리스크: {', '.join(related_risks)}")
                    
                    st.markdown("")
                else:
                    st.markdown(f"{i}. {action}")
        else:
            st.info("액션 플랜 데이터가 없습니다.")
        st.markdown("---")
        
        # 5️⃣ 당사 SWOT
        st.markdown("## 5️⃣ 당사 SWOT 분석")
        # focus를 활용하여 SWOT 형태로 재구성
        if focus:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 💪 강점 (Strengths)")
                st.markdown(focus.get('internal', 'N/A'))
                st.markdown("")
                st.markdown("### 🌟 기회 (Opportunities)")
                st.markdown(focus.get('market', 'N/A'))
            with col2:
                st.markdown("### ⚠️ 약점 (Weaknesses)")
                # gaps에서 HIGH/MEDIUM 갭 추출
                high_gaps = [g.get('requirement', '') for g in gaps if g.get('gap', '').upper() in ['HIGH', 'MEDIUM']]
                if high_gaps:
                    st.markdown('\n'.join([f"- {g}" for g in high_gaps[:3]]))
                else:
                    st.markdown("식별된 주요 갭 없음")
                
                st.markdown("")
                st.markdown("### ⚡ 위협 (Threats)")
                st.markdown(focus.get('competitor', 'N/A'))
        else:
            st.info("SWOT 분석 데이터가 없습니다.")
        st.markdown("---")
        
        # 6️⃣ 3단계 실행 로드맵
        st.markdown("## 6️⃣ 3단계 실행 로드맵")
        roadmap = strategy_data.get('roadmap', {})
        
        if roadmap:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("### 📋 Phase 0: Pre-Bid")
                prebid = roadmap.get('phase_0_prebid', [])
                if prebid:
                    for item in prebid:
                        if isinstance(item, dict):
                            st.markdown(f"**• {item.get('task', 'N/A')}**")
                            if item.get('expected_outcome'):
                                st.markdown(f"  📊 {item.get('expected_outcome')}")
                            if item.get('related_actions'):
                                st.markdown(f"  🔗 {', '.join(item.get('related_actions', []))}")
                        else:
                            st.markdown(f"- {item}")
                        st.markdown("")
                else:
                    st.markdown("_항목 없음_")
            
            with col2:
                st.markdown("### 🧪 Phase 1: PoC")
                poc = roadmap.get('phase_1_poc', [])
                if poc:
                    for item in poc:
                        if isinstance(item, dict):
                            st.markdown(f"**• {item.get('task', 'N/A')}**")
                            if item.get('expected_outcome'):
                                st.markdown(f"  📊 {item.get('expected_outcome')}")
                            if item.get('related_actions'):
                                st.markdown(f"  🔗 {', '.join(item.get('related_actions', []))}")
                        else:
                            st.markdown(f"- {item}")
                        st.markdown("")
                else:
                    st.markdown("_항목 없음_")
            
            with col3:
                st.markdown("### 📄 Phase 2: Proposal")
                proposal = roadmap.get('phase_2_proposal', [])
                if proposal:
                    for item in proposal:
                        if isinstance(item, dict):
                            st.markdown(f"**• {item.get('task', 'N/A')}**")
                            if item.get('expected_outcome'):
                                st.markdown(f"  📊 {item.get('expected_outcome')}")
                            if item.get('related_actions'):
                                st.markdown(f"  🔗 {', '.join(item.get('related_actions', []))}")
                        else:
                            st.markdown(f"- {item}")
                        st.markdown("")
                else:
                    st.markdown("_항목 없음_")
        else:
            st.info("로드맵 데이터가 없습니다.")
        st.markdown("---")
        
        # 7️⃣ 리스크 및 KPI
        st.markdown("## 7️⃣ 리스크 및 KPI")
        
        # 리스크
        st.markdown("### ⚠️ 주요 리스크")
        risks = strategy_data.get('risks', [])
        
        if risks:
            for i, risk in enumerate(risks, 1):
                if isinstance(risk, dict):
                    likelihood = risk.get('likelihood', 'medium').upper()
                    impact = risk.get('impact', 'medium').upper()
                    
                    risk_level = "🔴" if likelihood == "HIGH" and impact == "HIGH" else "🟡" if likelihood == "HIGH" or impact == "HIGH" else "🟢"
                    risk_id = risk.get('id', f'R{i}')
                    
                    st.markdown(f"**{risk_level} [{risk_id}] {risk.get('risk', '리스크 항목')}**")
                    st.markdown(f"- **가능성:** {likelihood} | **영향도:** {impact}")
                    st.markdown(f"- **대응 방안:** {risk.get('mitigation', 'N/A')}")
                    
                    # 대응 액션 매핑
                    mitigation_action_ids = risk.get('mitigation_action_ids', [])
                    if mitigation_action_ids:
                        st.markdown(f"- **🔗 대응 액션:** {', '.join(mitigation_action_ids)}")
                    st.markdown("")
                else:
                    st.markdown(f"{i}. {risk}")
        else:
            st.info("리스크 데이터가 없습니다.")
        
        st.markdown("")
        
        # KPI
        st.markdown("### 📊 핵심 KPI")
        kpis = strategy_data.get('kpis', [])
        
        if kpis:
            for i, kpi in enumerate(kpis, 1):
                if isinstance(kpi, dict):
                    st.markdown(f"**{i}. {kpi.get('name', 'KPI 항목')}**")
                    st.markdown(f"- **목표치:** {kpi.get('target', 'N/A')}")
                    st.markdown(f"- **현재/기준:** {kpi.get('baseline', 'N/A')}")
                    
                    # 연결된 액션
                    related_actions = kpi.get('related_actions', [])
                    if related_actions:
                        st.markdown(f"- **🔗 관련 액션:** {', '.join(related_actions)}")
                    st.markdown("")
                else:
                    st.markdown(f"{i}. {kpi}")
        else:
            st.info("KPI 데이터가 없습니다.")
        
    else:
        st.warning("전략 분석 결과를 찾을 수 없습니다.")
    
    # 하단 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔙 분석 결과로 돌아가기", use_container_width=True, type="primary", key="back_bottom"):
            st.session_state.show_strategy_detail = False
            st.rerun()

# =============================================================================
# 메인 실행 로직
# =============================================================================

def main():
    """메인 실행 함수"""
    # 전략 상세 페이지로 이동했는지 확인
    if st.session_state.get('show_strategy_detail', False):
        render_strategy_detail_page()
        return
    
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