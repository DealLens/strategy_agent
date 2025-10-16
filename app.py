import streamlit as st
from dotenv import load_dotenv
import os
import time
import base64
import threading
import asyncio
import re
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO

# Supervisor import
from workflow.supervisor import ParallelSupervisor, llm
from workflow.agents.strategy_synthesizer import _clean_text

# 환경변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="DealLens 전략분석 에이전트",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="▸"
)

# =============================================================================
# 유틸리티 함수
# =============================================================================

def get_base64_image(image_path):
    """이미지를 base64로 인코딩"""
    try:
        # 절대 경로와 상대 경로 모두 시도
        paths_to_try = [
            image_path,
            os.path.join(os.getcwd(), image_path),
            os.path.abspath(image_path)
        ]
        
        for path in paths_to_try:
            if os.path.exists(path):
                with open(path, "rb") as img_file:
                    return base64.b64encode(img_file.read()).decode()
        
        # 파일이 없으면 None 반환
        print(f"이미지 파일을 찾을 수 없습니다: {image_path}")
        return None
    except Exception as e:
        print(f"이미지 인코딩 오류: {e}")
        return None

def register_korean_font():
    """한글 폰트 등록 (개선된 버전)"""
    font_candidates = [
        ("C:/Windows/Fonts/malgun.ttf", "MalgunGothic", "맑은 고딕"),
        ("C:/Windows/Fonts/malgunbd.ttf", "MalgunGothicBold", "맑은 고딕 Bold"),
        ("C:/Windows/Fonts/gulim.ttc", "Gulim", "굴림"),
        ("C:/Windows/Fonts/batang.ttc", "Batang", "바탕"),
        ("C:/Windows/Fonts/dotum.ttc", "Dotum", "돋움"),
        ("C:/Windows/Fonts/arial.ttf", "Arial", "Arial"),
    ]
    
    for font_path, font_name, display_name in font_candidates:
        try:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                print(f"폰트 등록 성공: {display_name} ({font_name})")
                return font_name
        except Exception as e:
            print(f"폰트 등록 실패 ({font_path}): {e}")
            continue
    
    print("한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다.")
    return 'Helvetica'  # 폴백

def _clean_text(text):
    """텍스트 정리 함수 (PDF 생성용)"""
    if not text:
        return ""
    
    # HTML 태그 제거
    import re
    text = re.sub(r'<[^>]+>', '', str(text))
    
    # 특수 문자 정리
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # 연속된 공백 정리
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def generate_analysis_pdf():
    """분석 결과 PDF 생성 (한글 지원 개선)"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    
    # 한글 폰트 등록
    korean_font = register_korean_font()
    
    # 커스텀 스타일 정의 (한글 폰트 적용)
    title_style = ParagraphStyle(
        'CustomTitle',
        fontName=korean_font,
        fontSize=24,
        spaceAfter=30,
        alignment=1,  # 중앙 정렬
        textColor=colors.HexColor('#1e3a8a'),
        leading=28
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        fontName=korean_font,
        fontSize=12,
        spaceAfter=20,
        alignment=1,  # 중앙 정렬
        textColor=colors.HexColor('#64748b'),
        leading=16
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        fontName=korean_font,
        fontSize=18,
        spaceAfter=15,
        spaceBefore=15,
        textColor=colors.HexColor('#1e3a8a'),
        leading=22
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        fontName=korean_font,
        fontSize=14,
        spaceAfter=10,
        spaceBefore=10,
        textColor=colors.HexColor('#2563eb'),
        leading=18
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        fontName=korean_font,
        fontSize=11,
        spaceAfter=8,
        leading=16
    )
    
    bullet_style = ParagraphStyle(
        'CustomBullet',
        fontName=korean_font,
        fontSize=10,
        spaceAfter=5,
        leftIndent=20,
        leading=15
    )
    
    info_style = ParagraphStyle(
        'CustomInfo',
        fontName=korean_font,
        fontSize=10,
        spaceAfter=5,
        textColor=colors.HexColor('#64748b'),
        leading=14
    )
    
    # PDF 내용 구성
    story = []
    
    # 제목 및 부제목
    story.append(Paragraph("전략 분석 보고서", title_style))
    story.append(Paragraph("DealLens 전략분석 AI 에이전트", subtitle_style))
    story.append(Spacer(1, 20))
    
    # 분석 정보
    story.append(Paragraph("분석 개요", heading1_style))
    if st.session_state.get('previous_file'):
        story.append(Paragraph(f"분석 파일: {st.session_state.previous_file.name}", info_style))
    story.append(Paragraph(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", info_style))
    story.append(Paragraph("본 보고서는 DealLens 전략분석 AI 에이전트에 의해 생성되었습니다.", info_style))
    story.append(Spacer(1, 30))
    
    # 실제 분석 결과 가져오기
    results = st.session_state.get('analysis_results')
    
    if results and not results.get('error'):
        # === RFP 분석 결과 ===
        rfp_data = results.get('rfp_parser', {})
        if rfp_data:
            story.append(Paragraph("RFP 분석 결과", heading1_style))
            
            # 주제 표시
            subject = rfp_data.get('subject', '')
            if subject:
                story.append(Paragraph(f"주제: {_clean_text(subject)}", heading2_style))
                story.append(Spacer(1, 15))
            
            # 핵심 요구사항
            requirements = rfp_data.get('requirements', [])
            if requirements:
                story.append(Paragraph("핵심 요구사항", heading2_style))
                for i, req in enumerate(requirements[:8], 1):
                    story.append(Paragraph(f"{i}. {_clean_text(req)[:300]}", bullet_style))
                story.append(Spacer(1, 15))
            
            # 평가 기준
            evaluation = rfp_data.get('evaluation', [])
            if evaluation:
                story.append(Paragraph("평가 기준", heading2_style))
                for i, eval_item in enumerate(evaluation[:6], 1):
                    story.append(Paragraph(f"{i}. {_clean_text(eval_item)[:300]}", bullet_style))
                story.append(Spacer(1, 15))
        
        # === 내부 역량 매칭 결과 ===
        internal_data = results.get('internal_rag', {})
        internal_matches = internal_data.get('internal_matches', [])
        if internal_matches:
            story.append(PageBreak())
            story.append(Paragraph("내부 역량 매칭 결과", heading1_style))
            
            for i, match in enumerate(internal_matches[:5], 1):
                requirement = match.get('requirement', '')
                match_score = match.get('match_score', 0)
                matches = match.get('matches', [])
                
                story.append(Paragraph(f"매칭 {i}: {_clean_text(requirement)[:200]}", heading2_style))
                story.append(Paragraph(f"매칭 점수: {match_score}", bullet_style))
                
                if matches:
                    story.append(Paragraph("매칭된 내부 역량:", bullet_style))
                    for j, m in enumerate(matches[:3], 1):
                        # 딕셔너리 형태의 데이터를 깔끔하게 처리
                        if isinstance(m, dict):
                            title = m.get('title', '')
                            summary = m.get('summary', '')
                            if title:
                                story.append(Paragraph(f"  {j}. <b>{_clean_text(title)[:100]}</b>", bullet_style))
                                if summary:
                                    # 요약에서 핵심 내용만 추출
                                    clean_summary = _clean_text(summary)[:200]
                                    story.append(Paragraph(f"     {clean_summary}...", bullet_style))
                        else:
                            story.append(Paragraph(f"  {j}. {_clean_text(str(m))[:250]}", bullet_style))
                story.append(Spacer(1, 10))
        
        # === [1] 전략 요약 ===
        # supervisor에서 반환되는 구조에 맞게 수정
        strategy_result = results.get('strategy', {})
        strategy_data = strategy_result.get('strategy', {}) if strategy_result else {}
        
        if strategy_data:
            story.append(PageBreak())
            story.append(Paragraph("1. 전략 요약", heading1_style))
            
            # 전략 요약
            summary = strategy_data.get('summary', '')
            if summary:
                story.append(Paragraph(f"<b>핵심 전략:</b> {_clean_text(summary)[:800]}", normal_style))
                story.append(Spacer(1, 15))
            
            # Focus 영역
            focus = strategy_data.get('focus', {})
            if focus:
                story.append(Paragraph("주요 포커스 영역", heading2_style))
                for key, value in focus.items():
                    if value:
                        story.append(Paragraph(f"• <b>{key}:</b> {_clean_text(value)[:300]}", bullet_style))
                story.append(Spacer(1, 15))
        
        # === [2] 핵심 액션 플랜 ===
        actions = strategy_data.get('prioritized_actions', [])
        if actions:
            story.append(PageBreak())
            story.append(Paragraph("2. 핵심 액션 플랜", heading1_style))
            
            for i, action in enumerate(actions[:6], 1):  # 상위 6개만
                if isinstance(action, dict):
                    action_title = action.get('action', f'액션 {i}')
                    story.append(Paragraph(f"<b>액션 {i}:</b> {action_title}", heading2_style))
                    
                    why = action.get('why', '')
                    if why:
                        story.append(Paragraph(f"<b>실행 이유:</b> {_clean_text(why)[:400]}", bullet_style))
                    
                    how = action.get('how', '')
                    if how:
                        story.append(Paragraph(f"<b>실행 방법:</b> {_clean_text(how)[:400]}", bullet_style))
                    
                    story.append(Spacer(1, 12))
        
        # === 경쟁사 분석 결과 ===
        competitor_data = results.get('competitor_analysis', {})
        competitor_profiles = competitor_data.get('competitor_profiles', {})
        if competitor_profiles:
            story.append(PageBreak())
            story.append(Paragraph("경쟁사 분석 결과", heading1_style))
            
            for company, profile in list(competitor_profiles.items())[:3]:  # 상위 3개만
                story.append(Paragraph(f"<b>{company}</b>", heading2_style))
                
                # 회사 요약
                company_summary = profile.get('company_summary', '')
                if company_summary:
                    story.append(Paragraph(f"회사 개요: {_clean_text(company_summary)[:400]}", bullet_style))
                
                # 핵심 기술
                key_technologies = profile.get('key_technologies', [])
                if key_technologies:
                    story.append(Paragraph("핵심 기술:", bullet_style))
                    for tech in key_technologies[:4]:
                        story.append(Paragraph(f"  • {_clean_text(tech)[:200]}", bullet_style))
                
                # SWOT 분석
                swot = profile.get('swot', {})
                if swot:
                    story.append(Paragraph("SWOT 분석:", bullet_style))
                    for key, value in swot.items():
                        if value:
                            story.append(Paragraph(f"  <b>{key}:</b> {_clean_text(value)[:200]}", bullet_style))
                
                story.append(Spacer(1, 12))
        
        # === [3] 경쟁사 대응 전략 ===
        appendix = strategy_data.get('appendix', {})
        competitor_counters = appendix.get('competitor_counters', [])
        
        if competitor_counters:
            story.append(PageBreak())
            story.append(Paragraph("3. 경쟁사 대응 전략", heading1_style))
            
            # 경쟁사별로 그룹화
            companies = {}
            for counter in competitor_counters:
                company = counter.get('company', '경쟁사')
                if company not in companies:
                    companies[company] = []
                companies[company].append(counter.get('counter', 'N/A'))
            
            for company, counters in companies.items():
                story.append(Paragraph(f"<b>{company}</b> 대응 전략", heading2_style))
                for j, counter_text in enumerate(counters[:3], 1):  # 상위 3개만
                    story.append(Paragraph(f"{j}. {_clean_text(counter_text)[:500]}", bullet_style))
                story.append(Spacer(1, 10))
        
        # === [4] 리스크 ===
        risks = strategy_data.get('risks', [])
        if risks:
            story.append(PageBreak())
            story.append(Paragraph("4. 주요 리스크 및 대응방안", heading1_style))
            
            for i, risk in enumerate(risks[:5], 1):  # 상위 5개만
                if isinstance(risk, dict):
                    risk_text = risk.get('risk', '리스크 항목')
                    story.append(Paragraph(f"<b>리스크 {i}:</b> {_clean_text(risk_text)[:400]}", bullet_style))
                    
                    mitigation = risk.get('mitigation', '')
                    if mitigation:
                        story.append(Paragraph(f"<b>대응방안:</b> {_clean_text(mitigation)[:400]}", bullet_style))
                    story.append(Spacer(1, 10))
        
        # === [5] KPI ===
        kpis = strategy_data.get('kpis', [])
        if kpis:
            story.append(PageBreak())
            story.append(Paragraph("5. 핵심 성과지표 (KPI)", heading1_style))
            
            for i, kpi in enumerate(kpis[:6], 1):  # 상위 6개만
                if isinstance(kpi, dict):
                    kpi_name = kpi.get('name', 'KPI')
                    baseline = kpi.get('baseline', 'N/A')
                    target = kpi.get('target', 'N/A')
                    story.append(Paragraph(f"<b>{kpi_name}:</b> {baseline} → {target}", bullet_style))
                    story.append(Spacer(1, 6))
        
        # 마무리 섹션
        story.append(PageBreak())
        story.append(Paragraph("결론 및 권고사항", heading1_style))
        story.append(Paragraph("본 분석을 통해 도출된 전략적 방향성을 바탕으로 체계적인 실행 계획을 수립하고, 정기적인 모니터링을 통해 목표 달성을 보장할 것을 권고합니다.", normal_style))
        story.append(Spacer(1, 20))
    
    else:
        story.append(Paragraph("※ 분석 결과가 없거나 오류가 발생했습니다.", normal_style))
        story.append(Paragraph("분석을 다시 시도해주세요.", normal_style))
    
    # 푸터
    footer_style = ParagraphStyle(
        'Footer',
        fontName=korean_font,
        fontSize=9,
        alignment=1,
        textColor=colors.HexColor('#64748b'),
        spaceBefore=20
    )
    story.append(Paragraph("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", footer_style))
    story.append(Paragraph("본 보고서는 DealLens 전략분석 AI 에이전트에 의해 생성되었습니다.", footer_style))
    story.append(Paragraph(f"생성일시: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}", footer_style))
    
    # PDF 생성
    try:
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"PDF 생성 오류: {e}")
        # 오류 시 기본 PDF 반환
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        error_story = [Paragraph(f"PDF 생성 중 오류 발생: {str(e)}", normal_style)]
        doc.build(error_story)
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
                    <button class="nav-btn" id="header-history-btn">■ 분석 History</button>
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
                    <button class="nav-btn" id="header-history-btn">■ 분석 History</button>
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
            st.markdown("### ■ 분석 History")
            st.markdown("---")

            if st.session_state.analysis_history:
                for i, record in enumerate(reversed(st.session_state.analysis_history)):
                    with st.expander(f"■ {record['filename']}", expanded=False):
                        st.write(f"**업로드 시간:** {record['upload_time']}")
                        
                        if st.button(f"▶ 분석 결과 보기", key=f"view_result_{i}"):
                            st.session_state.selected_analysis = i
                            st.session_state.show_analysis_detail = True

                        if record.get('file_content'):
                            st.download_button(
                                label="■ 원본 RFP 다운로드",
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
                st.markdown(f"### ▶ 분석 결과: {record['filename']}")
                st.markdown(f"**분석 시간:** {record['upload_time']}")
                
                # 전략 보고서 표시
                st.markdown("---")
                st.markdown("## ▶ 전략 분석 결과")
                
                # 저장된 분석 결과 가져오기
                results = record.get('analysis_results')
                
                # 1. RFP 분석 결과
                with st.expander("① RFP 분석 결과", expanded=True):
                    if results and 'rfp_parser' in results:
                        rfp_data = results['rfp_parser']
                        
                        # 주제 표시
                        if 'subject' in rfp_data:
                            st.markdown(f"**주제:** {rfp_data['subject']}")
                        
                        if 'requirements' in rfp_data:
                            st.markdown("**■ 핵심 요구사항:**")
                            for req in rfp_data['requirements'][:10]:
                                st.markdown(f"- {req}")
                        if 'evaluation' in rfp_data:
                            st.markdown("\n**▣ 평가 기준:**")
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
                            # 기술 스택 관련 키워드 (필터링용) - 정확히 일치하는 경우만 필터링
                            tech_keywords = ['개발 언어 및 환경', '기본 개발 언어', '개발 프레임워크', 
                                            '데이터 연동', '기술 스택 및 개발 환경']
                            
                            # 모든 매칭 결과를 하나의 리스트로 통합
                            all_projects = []
                            for match in matches:
                                req = match.get('requirement', '요구사항 미지정')
                                
                                # 기술 스택 관련 요구사항 필터링 (정확히 일치하거나 시작하는 경우만)
                                is_tech_stack = any(req.strip().startswith(keyword) for keyword in tech_keywords)
                                if is_tech_stack:
                                    continue
                                
                                related = match.get('matches', [])
                                for proj in related:
                                    proj_copy = proj.copy()
                                    proj_copy['matched_requirement'] = req
                                    # 구분선 제거
                                    if 'summary' in proj_copy:
                                        proj_copy['summary'] = proj_copy['summary'].replace('=' * 50, '').replace('=' * 40, '').strip()
                                    all_projects.append(proj_copy)
                            
                            # 상위 3개만 표시
                            if all_projects:
                                for i, proj in enumerate(all_projects[:3], 1):
                                    st.markdown(f"**{i}. {proj.get('title', '제목 없음')}**")
                                    
                                    # summary 파싱
                                    summary = proj.get('summary', '')
                                    
                                    # 구분자 찾기
                                    challenges_markers = ['Challenges:', 'Business Challenges:', '▶ 사업 환경']
                                    solutions_markers = ['Solutions:', 'Solutions :', '▶ Win 전략']
                                    benefits_markers = ['Benefits:', 'Benefits :', '▶ 성과']
                                    
                                    # 사업배경 추출
                                    challenges_start = -1
                                    for marker in challenges_markers:
                                        pos = summary.find(marker)
                                        if pos != -1:
                                            challenges_start = pos
                                            break
                                    
                                    solutions_start = -1
                                    for marker in solutions_markers:
                                        pos = summary.find(marker)
                                        if pos != -1:
                                            solutions_start = pos
                                            break
                                    
                                    if challenges_start != -1 and solutions_start != -1:
                                        background = summary[challenges_start:solutions_start]
                                        for marker in challenges_markers:
                                            background = background.replace(marker, '')
                                        background = background.strip()
                                        # 처음 2-3문장만 추출
                                        sentences = background.split('.')
                                        background = '. '.join(sentences[:2]).strip() + '.'
                                        st.markdown(f"**• 사업배경:** {background}")
                                    
                                    # 솔루션 추출
                                    benefits_start = -1
                                    for marker in benefits_markers:
                                        pos = summary.find(marker)
                                        if pos != -1:
                                            benefits_start = pos
                                            break
                                    
                                    if solutions_start != -1:
                                        if benefits_start != -1:
                                            solution = summary[solutions_start:benefits_start]
                                        else:
                                            solution = summary[solutions_start:]
                                        for marker in solutions_markers:
                                            solution = solution.replace(marker, '')
                                        solution = solution.strip()
                                        # 처음 2-3문장만 추출
                                        sentences = solution.split('.')
                                        solution = '. '.join(sentences[:2]).strip() + '.'
                                        if solution and solution != '.':
                                            st.markdown(f"**• 솔루션:** {solution}")
                                    
                                    # 성과 추출
                                    if benefits_start != -1:
                                        benefits = summary[benefits_start:]
                                        for marker in benefits_markers:
                                            benefits = benefits.replace(marker, '')
                                        benefits = benefits.strip()
                                        # 처음 2-3문장만 추출
                                        sentences = benefits.split('.')
                                        benefits = '. '.join(sentences[:2]).strip() + '.'
                                        if benefits and benefits != '.':
                                            st.markdown(f"**• 성과 및 효과:** {benefits}")
                                    
                                    if proj.get('url'):
                                        st.markdown(f"[🔗 상세보기]({proj['url']})")
                                    st.markdown("")
                            else:
                                st.info("유의미한 내부 역량 매칭 결과가 없습니다.")
                        else:
                            st.warning("매칭된 내부 역량이 없습니다.")
                    else:
                        st.info("분석 결과가 없습니다.")
                
                # 3. 경쟁사 분석 결과
                with st.expander("③ 경쟁사 분석 결과", expanded=False):
                    if results and 'competitor_analysis' in results:
                        competitor_data = results['competitor_analysis']
                        profiles = competitor_data.get('competitor_profiles', {})
                        
                        # ABC 순서로 정렬하기 위한 함수
                        def get_company_order(company_name):
                            """회사명을 ABC 순서로 정렬하기 위한 순서 반환"""
                            if "A사" in company_name or "삼성SDS" in company_name or "삼성 SDS" in company_name or "SAMSUNG SDS" in company_name or "SDS" in company_name:
                                return 1
                            elif "B사" in company_name or "LG CNS" in company_name or "LG C&S" in company_name or "LGCNS" in company_name or "CNS" in company_name:
                                return 2
                            elif "C사" in company_name or "현대오토에버" in company_name or "현대 오토에버" in company_name or "HYUNDAI AUTOEVER" in company_name or "AutoEver" in company_name or "오토에버" in company_name:
                                return 3
                            else:
                                return 999  # 기타 회사는 마지막에 배치
                        
                        # ABC 순서로 정렬하여 출력
                        for company, profile in sorted(profiles.items(), key=lambda x: get_company_order(x[0])):
                            # 이미 익명화된 이름이므로 그대로 사용
                            st.markdown(f"### {company}")
                            if profile.get('company_summary'):
                                st.markdown(f"**▲ 요약:** {profile['company_summary'][:200]}...")
                    else:
                        st.info("분석 결과가 없습니다.")
                
                # 4. 전략 도출 결과
                with st.expander("④ 전략 도출 결과", expanded=True):
                    if results and 'strategy' in results:
                        # 상태 메시지 표시
                        strategy_result = results['strategy']
                        status = strategy_result.get('status', 'unknown')
                        message = strategy_result.get('message', '')
                        
                        if status == 'success':
                            st.success(message)
                        elif status == 'fallback':
                            st.warning(message)
                        elif status == 'error':
                            st.error(message)
                        
                        strategy_data = strategy_result.get('strategy', {})
                        
                        if strategy_data.get('summary'):
                            st.markdown("### ○ 전략 요약")
                            st.info(strategy_data['summary'])
                            st.markdown("---")
                        
                        if strategy_data.get('actions'):
                            st.markdown("**• 액션 플랜:**")
                            for action in strategy_data['actions']:
                                st.markdown(f"- {action}")
                        
                        if strategy_data.get('differentiation'):
                            st.markdown("\n**○ 차별화 포인트:**")
                            for diff in strategy_data['differentiation']:
                                # "차별화포인트 X:", "차별화 포인트 X:" 같은 접두어 제거
                                cleaned_diff = re.sub(r'^차별화\s*포인트\s*\d+\s*[:：]\s*', '', str(diff), flags=re.IGNORECASE)
                                st.markdown(f"- {cleaned_diff}")
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
            ■ RFP 파일을 업로드해주세요
        </h3>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "RFP 파일 업로드",
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
            "▶ 분석 시작",
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
            with st.spinner(" AI 에이전트가 분석을 진행 중입니다... \n더 자세한 분석을 위해 최소 1분에서 최대 5분까지 소요될 수 있습니다. "):
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
            if st.button("■ 분석 History", use_container_width=True):
                st.session_state.show_history = not st.session_state.show_history
                st.rerun()
            
            if st.button("◎ 새로운 분석", use_container_width=True):
                save_analysis_to_history()
                reset_analysis_state()
                st.rerun()
        
        # DealLens 로고와 제목을 중앙 정렬로 배치 (로고를 글자 위에)
        # 로고를 base64로 인코딩해서 사용
        logo_base64 = get_base64_image("data/DealLens_logo2.png")
        if logo_base64:
            st.markdown(f"""
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center; margin-top: 20px;">
            <img src="data:image/png;base64,{logo_base64}" alt="DealLens Logo" style="height: 90px; margin-bottom: 5px;">
    <h1 style="font-size: 2.2rem; font-weight: 700; color: #1E293B; margin: 0; text-align: center; white-space: nowrap;">
          최종 전략 분석 보고서
    </h1>
</div>
<hr style="margin: 20px 0 30px 0; border: 0.5px solid #e2e2e2;">
""", unsafe_allow_html=True)
        else:
            st.markdown("""
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center; margin-top: 20px;">
        <div style="height: 90px; width: 90px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-bottom: 5px;">
            <span style="color: white; font-size: 2.25rem; font-weight: bold;">DL</span>
    </div>
    <h1 style="font-size: 2.2rem; font-weight: 700; color: #1E293B; margin: 0; text-align: center; white-space: nowrap;">
          최종 전략 분석 보고서
    </h1>
</div>
<hr style="margin: 20px 0 30px 0; border: 0.5px solid #e2e2e2;">
""", unsafe_allow_html=True)
        
        # 여백 추가
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # 분석 결과 확인
        results = st.session_state.get('analysis_results')
        
        if results and 'error' in results:
            st.error(f"✗ {results['error']}")
            st.info("※ .env 파일에 API 키가 올바르게 설정되어 있는지 확인해주세요.")
        
        # 1. RFP 분석 결과
        with st.expander("① RFP 분석 결과", expanded=True):
            if results and 'rfp_parser' in results and not results.get('error'):
                rfp_data = results['rfp_parser']
                
                # 주제 표시
                if 'subject' in rfp_data:
                    st.markdown(f"**주제:** {rfp_data['subject']}")
                
                if 'requirements' in rfp_data:
                    st.markdown("**▲ 핵심 요구사항:**")
                    for req in rfp_data['requirements'][:10]:
                        st.markdown(f"- {req}")
                
                if 'evaluation' in rfp_data:
                    st.markdown("\n**▲ 평가 기준:**")
                    for eval_item in rfp_data['evaluation'][:10]:
                        st.markdown(f"- {eval_item}")
                
                if 'risks' in rfp_data:
                    st.markdown("\n**▲ 리스크 요소:**")
                    for risk in rfp_data['risks'][:10]:
                        st.markdown(f"- {risk}")
            else:
                st.info("※ 분석을 시작하면 RFP 문서 분석 결과가 표시됩니다.")
        
        # 2. 내부 역량 매칭 결과
        with st.expander("② 내부 역량 매칭 결과", expanded=False):
            if results and 'internal_rag' in results and not results.get('error'):
                internal_data = results['internal_rag']
                matches = internal_data.get('internal_matches', [])
                
                if matches:
                    # 기술 스택 관련 키워드 (필터링용) - 정확히 일치하는 경우만 필터링
                    tech_keywords = ['개발 언어 및 환경', '기본 개발 언어', '개발 프레임워크', 
                                    '데이터 연동', '기술 스택 및 개발 환경']
                    
                    # 모든 매칭 결과를 하나의 리스트로 통합
                    all_projects = []
                    for match in matches:
                        req = match.get('requirement', '요구사항 미지정')
                        
                        # 기술 스택 관련 요구사항 필터링 (정확히 일치하거나 시작하는 경우만)
                        is_tech_stack = any(req.strip().startswith(keyword) for keyword in tech_keywords)
                        if is_tech_stack:
                            continue
                        
                        related = match.get('matches', [])
                        for proj in related:
                            proj_copy = proj.copy()
                            proj_copy['matched_requirement'] = req
                            # 구분선 제거
                            if 'summary' in proj_copy:
                                proj_copy['summary'] = proj_copy['summary'].replace('=' * 50, '').replace('=' * 40, '').strip()
                            all_projects.append(proj_copy)
                    
                    # 상위 3개만 표시
                    if all_projects:
                        for i, proj in enumerate(all_projects[:3], 1):
                            st.markdown(f"**{i}. {proj.get('title', '제목 없음')}**")
                            
                            # summary 파싱
                            summary = proj.get('summary', '')
                            
                            # 구분자 찾기
                            challenges_markers = ['Challenges:', 'Business Challenges:', '▶ 사업 환경']
                            solutions_markers = ['Solutions:', 'Solutions :', '▶ Win 전략']
                            benefits_markers = ['Benefits:', 'Benefits :', '▶ 성과']
                            
                            # 사업배경 추출
                            challenges_start = -1
                            for marker in challenges_markers:
                                pos = summary.find(marker)
                                if pos != -1:
                                    challenges_start = pos
                                    break
                            
                            solutions_start = -1
                            for marker in solutions_markers:
                                pos = summary.find(marker)
                                if pos != -1:
                                    solutions_start = pos
                                    break
                            
                            if challenges_start != -1 and solutions_start != -1:
                                background = summary[challenges_start:solutions_start]
                                for marker in challenges_markers:
                                    background = background.replace(marker, '')
                                background = background.strip()
                                # 처음 2-3문장만 추출
                                sentences = background.split('.')
                                background = '. '.join(sentences[:2]).strip() + '.'
                                st.markdown(f"**• 사업배경:** {background}")
                            
                            # 솔루션 추출
                            benefits_start = -1
                            for marker in benefits_markers:
                                pos = summary.find(marker)
                                if pos != -1:
                                    benefits_start = pos
                                    break
                            
                            if solutions_start != -1:
                                if benefits_start != -1:
                                    solution = summary[solutions_start:benefits_start]
                                else:
                                    solution = summary[solutions_start:]
                                for marker in solutions_markers:
                                    solution = solution.replace(marker, '')
                                solution = solution.strip()
                                # 처음 2-3문장만 추출
                                sentences = solution.split('.')
                                solution = '. '.join(sentences[:2]).strip() + '.'
                                if solution and solution != '.':
                                    st.markdown(f"**• 솔루션:** {solution}")
                            
                            # 성과 추출
                            if benefits_start != -1:
                                benefits = summary[benefits_start:]
                                for marker in benefits_markers:
                                    benefits = benefits.replace(marker, '')
                                benefits = benefits.strip()
                                # 처음 2-3문장만 추출
                                sentences = benefits.split('.')
                                benefits = '. '.join(sentences[:2]).strip() + '.'
                                if benefits and benefits != '.':
                                    st.markdown(f"**• 성과 및 효과:** {benefits}")
                            
                            if proj.get('url'):
                                st.markdown(f"[🔗 상세보기]({proj['url']})")
                            st.markdown("")
                    else:
                        st.info("유의미한 내부 역량 매칭 결과가 없습니다.")
                else:
                    st.warning("매칭된 내부 역량이 없습니다.")
            else:
                st.info("※ 분석을 시작하면 내부 역량 매칭 결과가 표시됩니다.")
        
        # 3. 경쟁사 분석 결과
        with st.expander("③ 경쟁사 분석 결과", expanded=False):
            if results and 'competitor_analysis' in results and not results.get('error'):
                competitor_data = results['competitor_analysis']
                profiles = competitor_data.get('competitor_profiles', {})
                
                # ABC 순서로 정렬하기 위한 함수
                def get_company_order(company_name):
                    """회사명을 ABC 순서로 정렬하기 위한 순서 반환"""
                    if "A사" in company_name or "삼성SDS" in company_name or "삼성 SDS" in company_name or "SAMSUNG SDS" in company_name or "SDS" in company_name:
                        return 1
                    elif "B사" in company_name or "LG CNS" in company_name or "LG C&S" in company_name or "LGCNS" in company_name or "CNS" in company_name:
                        return 2
                    elif "C사" in company_name or "현대오토에버" in company_name or "현대 오토에버" in company_name or "HYUNDAI AUTOEVER" in company_name or "AutoEver" in company_name or "오토에버" in company_name:
                        return 3
                    else:
                        return 999  # 기타 회사는 마지막에 배치
                
                # ABC 순서로 정렬하여 출력
                for company, profile in sorted(profiles.items(), key=lambda x: get_company_order(x[0])):
                    # 이미 익명화된 이름이므로 그대로 사용
                    st.markdown(f"### {company}")
                    
                    # 회사 요약
                    if profile.get('company_summary'):
                        st.markdown(f"**◆ 요약:** {profile['company_summary']}")
                    
                    # SWOT
                    swot = profile.get('swot', {})
                    if swot:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**▲ 강점 (S):**")
                            for s in swot.get('S', []):
                                st.markdown(f"- {s}")
                            st.markdown("**▲ 기회 (O):**")
                            for o in swot.get('O', []):
                                st.markdown(f"- {o}")
                        with col2:
                            st.markdown("**▲ 약점 (W):**")
                            for w in swot.get('W', []):
                                st.markdown(f"- {w}")
                            st.markdown("**▲ 위협 (T):**")
                            for t in swot.get('T', []):
                                st.markdown(f"- {t}")
                    
                    # 최신 뉴스
                    recent_news = profile.get('recent_news', [])
                    if recent_news:
                        st.markdown("**◆ 최신 뉴스:**")
                        for news in recent_news[:3]:
                            st.markdown(f"- [{news.get('title', '제목 없음')}]({news.get('url', '#')})")
                    
                    st.markdown("---")
            else:
                st.info("※ 분석을 시작하면 경쟁사 분석 결과가 표시됩니다.")
        
        # 전략분석보고서 읽기 버튼
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("▶ 전략분석보고서 읽기", use_container_width=True, type="primary"):
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
                    label="■ 분석 결과 PDF 다운로드",
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
        if st.button("◀ 분석 결과로 돌아가기", use_container_width=True):
            st.session_state.show_strategy_detail = False
            st.rerun()
        
        # PDF 다운로드 버튼 추가
        st.markdown("---")
        try:
            pdf_data = generate_analysis_pdf()
            filename = f"전략분석보고서_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            st.download_button(
                label="■ PDF 다운로드",
                data=pdf_data,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                type="primary"
            )
        except Exception as e:
            st.error(f"PDF 생성 중 오류: {e}")
        
        st.markdown("---")
        
        if st.button("■ 분석 History", use_container_width=True):
            st.session_state.show_history = not st.session_state.show_history
            st.rerun()
        
        if st.button("◎ 새로운 분석", use_container_width=True):
            save_analysis_to_history()
            reset_analysis_state()
            st.rerun()
    
    # DealLens 로고와 제목을 중앙 정렬로 배치 (로고를 글자 위에)
    # 로고를 base64로 인코딩해서 사용
    logo_base64 = get_base64_image("data/DealLens_logo2.png")
    if logo_base64:
        st.markdown(f"""
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center; margin-top: 20px;">
            <img src="data:image/png;base64,{logo_base64}" alt="DealLens Logo" style="height: 90px; margin-bottom: 5px;">
    <h1 style="font-size: 2.2rem; font-weight: 700; color: #1E293B; margin: 0; text-align: center; white-space: nowrap;">
          최종 전략 분석 보고서
    </h1>
</div>
<hr style="margin: 20px 0 30px 0; border: 0.5px solid #e2e2e2;">
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="display: flex; flex-direction: column; justify-content: center; align-items: center; margin-top: 20px;">
        <div style="height: 90px; width: 90px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-bottom: 5px;">
            <span style="color: white; font-size: 2.25rem; font-weight: bold;">DL</span>
    </div>
    <h1 style="font-size: 2.2rem; font-weight: 700; color: #1E293B; margin: 0; text-align: center; white-space: nowrap;">
          최종 전략 분석 보고서
    </h1>
</div>
<hr style="margin: 20px 0 30px 0; border: 0.5px solid #e2e2e2;">
""", unsafe_allow_html=True)
    
    # # 여백 추가
    # st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
    
    # 분석 결과 가져오기
    results = st.session_state.get('analysis_results')
    
    if results and 'strategy' in results and not results.get('error'):
        # 상태 메시지 표시
        strategy_result = results['strategy']
        status = strategy_result.get('status', 'unknown')
        message = strategy_result.get('message', '')
        
        if status == 'success':
            st.success(message)
        elif status == 'fallback':
            st.warning(message)
        elif status == 'error':
            st.error(message)
        
        strategy_data = strategy_result.get('strategy', {})
        appendix = strategy_data.get('appendix', {})
        
        # ● 임원 요약 (Executive Summary)
        executive_summary = appendix.get('executive_summary', {})
        if executive_summary:
            st.markdown("## ● 임원 요약 (Executive Summary)")
            
            # 핵심 메시지 3가지
            key_messages = executive_summary.get('핵심 메시지 3가지', [])
            if key_messages:
                st.markdown("### ○ 핵심 메시지 (Top 3)")
                for msg in key_messages:
                    st.success(msg)
            
            col1, col2 = st.columns(2)
            with col1:
                # 투자 대비 효과
                roi_value = executive_summary.get('투자 대비 효과', '')
                if roi_value:
                    st.markdown("### 💰 투자 대비 효과")
                    st.info(roi_value)
            
            with col2:
                # 위험 요소 TOP 3
                top_risks = executive_summary.get('위험 요소 TOP 3', '')
                if top_risks:
                    st.markdown("### ▲ 주요 위험 요소")
                    st.warning(top_risks)
            
            st.markdown("---")
        
        # ▶ 경쟁사 비교 요약 테이블
        comparison_table = appendix.get('competitor_comparison_table', [])
        if comparison_table:
            st.markdown("## ▶ 경쟁사 비교 요약")
            
            for row in comparison_table:
                category = row.get('category', '')
                st.markdown(f"### {category}")
                
                col1, col2, col3, col4, col5 = st.columns([1.5, 2, 2, 2, 2.5])
                
                with col1:
                    st.markdown("**구분**")
                with col2:
                    st.markdown("**당사**")
                with col3:
                    st.markdown("**A사**")
                with col4:
                    st.markdown("**B사**")
                with col5:
                    st.markdown("**C사**")
                
                st.markdown("---")
                
                col1, col2, col3, col4, col5 = st.columns([1.5, 2, 2, 2, 2.5])
                
                with col1:
                    st.markdown("지표")
                with col2:
                    st.success(row.get('당사', '-'))
                with col3:
                    st.markdown(row.get('A사', '-'))
                with col4:
                    st.markdown(row.get('B사', '-'))
                with col5:
                    st.markdown(row.get('C사', '-'))
                
                # 당사 우위 강조
                advantage = row.get('당사 우위', '')
                if advantage:
                    st.info(f"**{advantage}**")
                
                st.markdown("")
            
            st.markdown("---")
        
        # [1] 전략 요약 (핵심 방향성)
        st.markdown("## [1] 전략 요약 (핵심 방향성)")
        if strategy_data.get('summary'):
            with st.expander("■ 전체 전략 요약 보기", expanded=False):
                st.info(strategy_data['summary'])
        
        # Focus 영역 표시
        focus = strategy_data.get('focus', {})
        if focus:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**◇ 내부 역량 관점**")
                st.markdown(focus.get('internal', 'N/A'))
            with col2:
                st.markdown("**▶ 경쟁사 대응 관점**")
                st.markdown(focus.get('competitor', 'N/A'))
            with col3:
                st.markdown("**▶ 시장/정책 관점**")
                st.markdown(focus.get('market', 'N/A'))
        st.markdown("---")
                
        # [2] 요구사항 대비 내부 적합도 분석 (그룹화)
        st.markdown("## [2] 요구사항 대비 내부 적합도 분석")
        appendix = strategy_data.get('appendix', {})
        fit_table = appendix.get('fit_table', [])
        
        if fit_table:
            # 적합도 차이 원인별로 그룹화
            from collections import defaultdict
            gap_groups = defaultdict(list)
            
            for fit_row in fit_table:
                gap_cause = fit_row.get('gap_root_cause', '기타')
                # 같은 적합도 차이 원인을 가진 항목들을 그룹화
                gap_groups[gap_cause].append(fit_row)
            
            # 그룹별로 출력
            group_idx = 1
            for gap_cause, items in gap_groups.items():
                # 첫 번째 항목의 정보 사용 (같은 보완 필요 원인이므로 동일한 영향/솔루션)
                first_item = items[0]
                fit_level = first_item.get('fit_level', 'unknown').upper()
                fit_color = {
                    'HIGH_FIT': '🟢',
                    'PARTIAL_FIT': '🟡',
                    'LOW_FIT': '🔴',
                    'UNKNOWN': '⚪'
                }.get(fit_level, '⚪')
                
                # 그룹 제목 (대표 키워드 추출)
                if "레거시 기술 스택" in gap_cause or "Java" in gap_cause or "Spring" in gap_cause:
                    group_title = "레거시 기술 스택 현대화"
                elif "AI" in gap_cause or "MLOps" in gap_cause or "모델" in gap_cause:
                    group_title = "AI/ML 운영 체계"
                elif "보안 인증" in gap_cause or "ISMS" in gap_cause:
                    group_title = "보안 인증 및 컴플라이언스"
                elif "내부 역량 부족" in gap_cause:
                    group_title = "내부 역량 보완 (파트너 협업)"
                else:
                    group_title = f"적합도 분석 그룹 {group_idx}"
                
                st.markdown(f"### {fit_color} {group_title}")
                
                # 관련 요구사항 리스트
                requirements = [item.get('requirement', '') for item in items]
                st.markdown(f"**■ 관련 요구사항 ({len(items)}건):**")
                for req in requirements:
                    st.markdown(f"  • {req}")
                
                st.markdown(f"**▶ 적합도 수준:** {fit_level.replace('_', ' ').title()}")
                
                # 적합도 차이 원인 분석 (공통)
                if gap_cause:
                    st.markdown(f"**▷ 보완 필요 원인:** {gap_cause}")
                
                # 정량적 영향 (공통)
                quantitative_impact = first_item.get('quantitative_impact', '')
                if quantitative_impact:
                    st.markdown(f"**△ 정량적 영향:** {quantitative_impact}")
                
                # 정성적 영향 (공통)
                qualitative_impact = first_item.get('qualitative_impact', '')
                if qualitative_impact:
                    st.markdown(f"**○ 정성적 영향:** {qualitative_impact}")
                
                # 보완 액션 (공통)
                suggested_action = first_item.get('suggested_action', 'N/A')
                st.markdown(f"**◇ 통합 솔루션:** {suggested_action}")
                
                st.markdown("---")
                group_idx += 1
        else:
            st.info("적합도 분석 데이터가 없습니다.")
        st.markdown("---")
        
        # [3] 경쟁사 대응 전략
        st.markdown("## [3] 경쟁사 대응 전략")
        competitor_counters = appendix.get('competitor_counters', [])
        
        if competitor_counters:
            # 경쟁사별로 그룹화 ([2] 개선 - 기술 특성 기반)
            companies = {}
            for counter in competitor_counters:
                company = counter.get('company', '경쟁사')
                if company not in companies:
                    companies[company] = []
                companies[company].append(counter.get('counter', 'N/A'))
            
            for company, counters in companies.items():
                # 이미 익명화된 이름이므로 그대로 사용
                st.markdown(f"### ■ {company}")
                
                # 중복 제거: 같은 유형(강점/약점) 전략이 중복되면 제거
                filtered_counters = []
                seen_types = set()
                
                for counter_text in counters:
                    # 강점/약점 유형 판별
                    if '[강점 대응]' in counter_text or '강점 대응:' in counter_text:
                        strategy_type = 'strength'
                    elif '[약점 활용]' in counter_text or '약점 활용:' in counter_text:
                        strategy_type = 'weakness'
                    else:
                        strategy_type = 'other'
                    
                    # 같은 유형이 이미 있으면 스킵
                    if strategy_type in seen_types and strategy_type != 'other':
                        continue
                    
                    seen_types.add(strategy_type)
                    filtered_counters.append(counter_text)
                    
                    # 최대 2개까지만
                    if len(filtered_counters) >= 2:
                        break
                
                for counter_text in filtered_counters:
                    # "3." 같은 번호 문장 완전 필터링 (더 강력하게)
                    if (counter_text.strip() in ['1.', '2.', '3.', '4.', '5.'] or 
                        counter_text.strip().startswith(('1.', '2.', '3.', '4.', '5.')) or
                        '3.' in counter_text.strip() or
                        counter_text.strip().startswith('3.') or
                        '3.\n' in counter_text or
                        '\n3.' in counter_text):
                        continue
                    
                    # _clean_text 적용
                    cleaned_counter = _clean_text(counter_text)
                    
                    # cleaned_counter가 비어있거나 "3."이 포함되어 있으면 스킵
                    if (not cleaned_counter or 
                        len(cleaned_counter.strip()) < 10 or
                        '3.' in cleaned_counter.strip()):
                        continue
                    
                    # 이미 이모지/헤더가 포함된 텍스트인지 확인
                    has_prefix = (counter_text.strip().startswith(('▶', '▲', '△', '○', '[강점 대응]', '[약점 활용]')) or
                                 '[강점 대응]' in counter_text or '[약점 활용]' in counter_text or
                                 '▶' in counter_text or '▲' in counter_text)
                    
                    # 번호 표시하지 않음 (깔끔한 표시를 위해)
                    
                    # 텍스트 변환: "강점 대응:" → "▶ **강점 대응**:", "약점 활용:" → "▲ **약점 활용**:"
                    display_text = cleaned_counter
                    if display_text.startswith("강점 대응:") and not display_text.startswith("▶"):
                        display_text = "▶ **강점 대응**: " + display_text.replace("강점 대응: ", "")
                    elif display_text.startswith("약점 활용:") and not display_text.startswith("▲"):
                        display_text = "▲ **약점 활용**: " + display_text.replace("약점 활용: ", "")
                    elif display_text.startswith("▶ 강점 대응:") and not "**" in display_text:
                        display_text = display_text.replace("▶ 강점 대응:", "▶ **강점 대응**:")
                    elif display_text.startswith("▲ 약점 활용:") and not "**" in display_text:
                        display_text = display_text.replace("▲ 약점 활용:", "▲ **약점 활용**:")
                    
                    st.markdown(display_text)
                    st.markdown("")
                st.markdown("---")
        
        # 차별화 포인트
        differentiation = strategy_data.get('differentiation', [])
        if differentiation:
            st.markdown("### 당사 차별화 포인트 (정량 검증)")
            for i, diff in enumerate(differentiation, 1):
                # "차별화포인트 X:", "차별화 포인트 X:" 같은 접두어 제거
                cleaned_diff = re.sub(r'^차별화\s*포인트\s*\d+\s*[:：]\s*', '', str(diff), flags=re.IGNORECASE)
                st.markdown(f"**{i}.** {_clean_text(cleaned_diff)}")
        
        if not competitor_counters and not differentiation:
            st.info("경쟁사 대응 전략 데이터가 없습니다.")
        st.markdown("---")
        
        # [4] 핵심 액션 플랜
        st.markdown("## [4] 핵심 액션 플랜")
        actions = strategy_data.get('prioritized_actions', [])
        
        if actions:
            for i, action in enumerate(actions, 1):
                if isinstance(action, dict):
                    # 우선순위 표시
                    impact = action.get('impact', 'medium').upper()
                    urgency = action.get('urgency', 'medium').upper()
                    effort = action.get('effort', 'medium').upper()
                    
                    priority_badge = "▲" if impact == "HIGH" and urgency == "HIGH" else "▸" if urgency == "HIGH" else "◆"
                    
                    st.markdown(f"### {priority_badge} {action.get('action', '액션 항목')}")
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**▷ 이유(Why):** {_clean_text(action.get('why', 'N/A'))}")
                        
                        # 방법(How)
                        how = action.get('how', '')
                        if how:
                            st.markdown(f"**◇ 방법(How):** {_clean_text(how)}")
                        
                        # 전략 접근법
                        strategy_approach = action.get('strategy_approach', '')
                        if strategy_approach:
                            approach_emoji = {
                                'Defensive': '◈',
                                'Offensive': '▶',
                                'Differentiation': '○',
                                'Partnership': '◎',
                                'Innovative': '○'
                            }.get(strategy_approach, '■')
                            st.markdown(f"**{approach_emoji} 전략 접근:** {strategy_approach}")
                        
                        st.markdown(f"**◇ 담당:** {action.get('owner', 'N/A')}")
                        
                        # 기대 결과 (수치화)
                        expected_result = action.get('expected_result', '')
                        if expected_result:
                            st.markdown(f"**▶ 기대 결과:** {_clean_text(expected_result)}")
                    
                    with col2:
                        st.markdown(f"**Impact:** `{impact}`")
                        st.markdown(f"**Urgency:** `{urgency}`")
                        st.markdown(f"**Effort:** `{effort}`")
                    
                    st.markdown("")
                else:
                    st.markdown(f"{i}. {action}")
        else:
            st.info("액션 플랜 데이터가 없습니다.")
        st.markdown("---")
        
        # [5] 당사 SWOT
        st.markdown("## [5] 당사 SWOT 분석")
        
        # focus를 활용하여 SWOT 형태로 재구성
        if focus:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### ▲ 강점 (Strengths)")
                
                # 강점 데이터 가공
                internal_strength = focus.get('internal', '')
                if internal_strength and internal_strength != 'N/A':
                    # 강점을 더 구체적으로 재구성
                    strength_items = []
                    
                    # 기존 내부 역량 관련 내용 분석
                    if '기술' in internal_strength or '역량' in internal_strength:
                        strength_items.append("• **기술 역량 우위**: 검증된 개발 프레임워크 및 풍부한 프로젝트 경험을 바탕으로 한 기술적 신뢰성 확보")
                    
                    if '사례' in internal_strength or '경험' in internal_strength:
                        strength_items.append("• **실증된 성과**: 유사 도메인 프로젝트 성공 사례를 통한 고객 신뢰도 및 프로젝트 성공률 향상")
                    
                    if '전문성' in internal_strength or '노하우' in internal_strength:
                        strength_items.append("• **도메인 전문성**: 산업별 특화 솔루션 및 비즈니스 프로세스 이해를 통한 맞춤형 솔루션 제공")
                    
                    if not strength_items:
                        strength_items.append(f"• {internal_strength}")
                    
                    for item in strength_items:
                        st.markdown(item)
                else:
                    st.markdown("• **기술 역량 우위**: 검증된 개발 프레임워크 및 풍부한 프로젝트 경험을 바탕으로 한 기술적 신뢰성 확보")
                    st.markdown("• **실증된 성과**: 유사 도메인 프로젝트 성공 사례를 통한 고객 신뢰도 및 프로젝트 성공률 향상")
                
                st.markdown("")
                st.markdown("### ▲ 기회 (Opportunities)")
                
                # 기회 데이터 가공
                market_opportunity = focus.get('market', '')
                if market_opportunity and market_opportunity != 'N/A':
                    opportunity_items = []
                    
                    if '디지털' in market_opportunity or '전환' in market_opportunity:
                        opportunity_items.append("• **디지털 전환 가속화**: 정부 및 기업의 디지털 전환 정책 확산으로 인한 시장 기회 확대")
                    
                    if '접근성' in market_opportunity or '요구' in market_opportunity:
                        opportunity_items.append("• **접근성 규제 강화**: 웹 접근성 개선 의무화로 인한 새로운 시장 수요 창출")
                    
                    if '시장' in market_opportunity or '증가' in market_opportunity:
                        opportunity_items.append("• **시장 수요 증가**: 사용자 경험 중심의 UI/UX 개선 요구 증가로 인한 프로젝트 기회 확대")
                    
                    if not opportunity_items:
                        opportunity_items.append(f"• {market_opportunity}")
                    
                    for item in opportunity_items:
                        st.markdown(item)
                else:
                    st.markdown("• **디지털 전환 가속화**: 정부 및 기업의 디지털 전환 정책 확산으로 인한 시장 기회 확대")
                    st.markdown("• **접근성 규제 강화**: 웹 접근성 개선 의무화로 인한 새로운 시장 수요 창출")
                
            with col2:
                st.markdown("### ▲ 약점 (Weaknesses)")
                
                # 약점 데이터 가공
                low_fits = [f.get('requirement', '') for f in fit_table if f.get('fit_level', '').upper() in ['LOW_FIT', 'PARTIAL_FIT']]
                if low_fits:
                    weakness_items = []
                    
                    for fit in low_fits[:3]:  # 상위 3개만
                        if 'Flash' in fit or 'JSP' in fit or '레거시' in fit:
                            weakness_items.append("• **레거시 기술 스택**: Flash 기반 시스템의 현대적 웹 기술 전환 필요성")
                        elif '보안' in fit or '인증' in fit:
                            weakness_items.append("• **보안 인증 부족**: ISMS 등 보안 인증 취득을 통한 신뢰성 제고 필요")
                        elif 'AI' in fit or 'ML' in fit:
                            weakness_items.append("• **AI/ML 역량**: 차세대 기술 트렌드 대응을 위한 AI/ML 전문 역량 보강 필요")
                        else:
                            weakness_items.append(f"• **{fit}**: 해당 영역의 기술적 보완 필요")
                    
                    for item in weakness_items:
                        st.markdown(item)
                else:
                    st.markdown("• **레거시 기술 스택**: Flash 기반 시스템의 현대적 웹 기술 전환 필요성")
                    st.markdown("• **보안 인증 부족**: ISMS 등 보안 인증 취득을 통한 신뢰성 제고 필요")
                
                st.markdown("")
                st.markdown("### ▲ 위협 (Threats)")
                
                # 위협 데이터 가공
                competitor_threat = focus.get('competitor', '')
                if competitor_threat and competitor_threat != 'N/A':
                    threat_items = []
                    
                    if '경쟁사' in competitor_threat or '대응' in competitor_threat:
                        threat_items.append("• **경쟁사 기술 우위**: 대형 SI 업체들의 선진 기술력 및 대규모 프로젝트 경험 활용")
                    
                    if '차별화' in competitor_threat or '약점' in competitor_threat:
                        threat_items.append("• **차별화 포인트 부족**: 기술적 차별화 요소 부족으로 인한 가격 경쟁력 위축")
                    
                    if '시장' in competitor_threat or '포지셔닝' in competitor_threat:
                        threat_items.append("• **시장 포지셔닝**: 대형 업체 중심의 시장 구조에서 중소 SI의 시장 점유율 확대 어려움")
                    
                    if not threat_items:
                        threat_items.append(f"• {competitor_threat}")
                    
                    for item in threat_items:
                        st.markdown(item)
                else:
                    st.markdown("• **경쟁사 기술 우위**: 대형 SI 업체들의 선진 기술력 및 대규모 프로젝트 경험 활용")
                    st.markdown("• **차별화 포인트 부족**: 기술적 차별화 요소 부족으로 인한 가격 경쟁력 위축")
        else:
            st.info("SWOT 분석 데이터가 없습니다.")
        st.markdown("---")
        
        # [6] 3단계 실행 로드맵 (전략 수준)
        st.markdown("## [6] 3단계 실행 로드맵")
        roadmap = strategy_data.get('roadmap', {})
        
        if roadmap:
            col1, col2, col3 = st.columns(3)
            
            # Phase 0: Pre-Bid
            with col1:
                st.markdown("### ■ Phase 0: Pre-Bid")
                prebid = roadmap.get('phase_0_prebid', {})
                if prebid and isinstance(prebid, dict):
                    st.markdown(f"**▷ 기간:** {prebid.get('duration', 'N/A')}")
                    st.markdown(f"**▷ 목표:** {prebid.get('objective', 'N/A')}")
                    st.markdown(f"**▷ 이유:** {prebid.get('why', 'N/A')}")
                    
                    deliverables = prebid.get('key_deliverables', [])
                    if deliverables:
                        st.markdown("**■ 주요 산출물:**")
                        for d in deliverables:
                            st.markdown(f"  • {d}")
                    
                    st.markdown(f"**▶ 기대 효과:** {prebid.get('expected_outcome', 'N/A')}")
                else:
                    st.markdown("_항목 없음_")
            
            # Phase 1: PoC
            with col2:
                st.markdown("### ■ Phase 1: PoC")
                poc = roadmap.get('phase_1_poc', {})
                if poc and isinstance(poc, dict):
                    st.markdown(f"**▷ 기간:** {poc.get('duration', 'N/A')}")
                    st.markdown(f"**▷ 목표:** {poc.get('objective', 'N/A')}")
                    st.markdown(f"**▷ 이유:** {poc.get('why', 'N/A')}")
                    
                    deliverables = poc.get('key_deliverables', [])
                    if deliverables:
                        st.markdown("**■ 주요 산출물:**")
                        for d in deliverables:
                            st.markdown(f"  • {d}")
                    
                    st.markdown(f"**▶ 기대 효과:** {poc.get('expected_outcome', 'N/A')}")
                else:
                    st.markdown("_항목 없음_")
            
            # Phase 2: Proposal
            with col3:
                st.markdown("### ■ Phase 2: Proposal")
                proposal = roadmap.get('phase_2_proposal', {})
                if proposal and isinstance(proposal, dict):
                    st.markdown(f"**▷ 기간:** {proposal.get('duration', 'N/A')}")
                    st.markdown(f"**▷ 목표:** {proposal.get('objective', 'N/A')}")
                    st.markdown(f"**▷ 이유:** {proposal.get('why', 'N/A')}")
                    
                    deliverables = proposal.get('key_deliverables', [])
                    if deliverables:
                        st.markdown("**■ 주요 산출물:**")
                        for d in deliverables:
                            st.markdown(f"  • {d}")
                    
                    st.markdown(f"**▶ 기대 효과:** {proposal.get('expected_outcome', 'N/A')}")
                else:
                    st.markdown("_항목 없음_")
        else:
            st.info("로드맵 데이터가 없습니다.")
        st.markdown("---")
        
        # [7] 리스크 및 KPI
        st.markdown("## [7] 리스크 및 KPI")
        
        # 리스크
        st.markdown("### ▲ 주요 리스크")
        risks = strategy_data.get('risks', [])
        
        if risks:
            import pandas as pd
            
            # 리스크 요약 테이블
            risk_summary_data = []
            for i, risk in enumerate(risks, 1):
                if isinstance(risk, dict):
                    likelihood = risk.get('likelihood', 'medium').upper()
                    impact = risk.get('impact', 'medium').upper()
                    
                    # 리스크 레벨 계산
                    if likelihood == "HIGH" and impact == "HIGH":
                        level_emoji = "🔴"
                        level_text = "높음"
                    elif likelihood == "HIGH" or impact == "HIGH":
                        level_emoji = "🟡"
                        level_text = "중간"
                    else:
                        level_emoji = "🟢"
                        level_text = "낮음"
                    
                    risk_summary_data.append({
                        "No.": f"{risk.get('id', f'R{i}')}",
                        "레벨": f"{level_emoji} {level_text}",
                        "카테고리": risk.get('category', '-'),
                        "리스크": risk.get('risk', '리스크 항목'),
                        "가능성": likelihood,
                        "영향도": impact,
                        "대응 액션": ", ".join(risk.get('mitigation_action_ids', []) or ["-"])
                    })
            
            if risk_summary_data:
                df_risk = pd.DataFrame(risk_summary_data)
                st.dataframe(
                    df_risk,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "No.": st.column_config.TextColumn("No.", width="small"),
                        "레벨": st.column_config.TextColumn("레벨", width="small"),
                        "카테고리": st.column_config.TextColumn("카테고리", width="small"),
                        "리스크": st.column_config.TextColumn("리스크 내용", width="large"),
                        "가능성": st.column_config.TextColumn("가능성", width="small"),
                        "영향도": st.column_config.TextColumn("영향도", width="small"),
                        "대응 액션": st.column_config.TextColumn("대응 액션", width="small")
                    }
                )
                st.caption(f"※ 총 {len(risk_summary_data)}개 리스크 항목")
                
                # 상세 내용 (expander로 표시)
                st.markdown("#### ■ 리스크 상세 대응 계획")
                for i, risk in enumerate(risks, 1):
                    if isinstance(risk, dict):
                        risk_id = risk.get('id', f'R{i}')
                        risk_name = risk.get('risk', '리스크 항목')
                        
                        with st.expander(f"[{risk_id}] {risk_name}", expanded=False):
                            st.markdown(f"**▷ 리스크 전문:** {risk.get('risk', 'N/A')}")
                            st.markdown(f"**◈ Plan A (예방):** {risk.get('mitigation', 'N/A')}")
                            
                            plan_b = risk.get('plan_b', '')
                            if plan_b:
                                st.markdown(f"**◎ Plan B (대안):** {plan_b}")
                            
                            trigger = risk.get('trigger_condition', '')
                            if trigger:
                                st.markdown(f"**▸ 발동 조건:** {trigger}")
        else:
            st.info("리스크 데이터가 없습니다.")
        
        st.markdown("")
        
        # KPI
        st.markdown("### ▶ 핵심 KPI")
        kpis = strategy_data.get('kpis', [])
        
        if kpis:
            # KPI를 테이블 형식으로 표시
            import pandas as pd
            
            kpi_table_data = []
            for i, kpi in enumerate(kpis, 1):
                if isinstance(kpi, dict):
                    kpi_table_data.append({
                        "No.": i,
                        "카테고리": kpi.get('category', '-'),
                        "KPI명": kpi.get('name', 'KPI 항목'),
                        "현재값 (Baseline)": kpi.get('baseline', 'N/A'),
                        "목표값 (Target)": kpi.get('target', 'N/A'),
                        "측정 방법": kpi.get('measurement_method', '-')
                    })
                else:
                    kpi_table_data.append({
                        "No.": i,
                        "카테고리": "-",
                        "KPI명": str(kpi),
                        "현재값 (Baseline)": "-",
                        "목표값 (Target)": "-",
                        "측정 방법": "-"
                    })
            
            if kpi_table_data:
                df = pd.DataFrame(kpi_table_data)
                
                # 스타일링을 위한 함수 정의
                def highlight_improvement(row):
                    """목표값에서 개선률 추출하여 하이라이트"""
                    target = str(row['목표값 (Target)'])
                    if '향상' in target or '개선' in target or '증가' in target or '↑' in target:
                        return ['background-color: #e8f5e9'] * len(row)  # 연한 초록
                    elif '감소' in target or '절감' in target or '단축' in target or '↓' in target:
                        return ['background-color: #e3f2fd'] * len(row)  # 연한 파랑
                    else:
                        return [''] * len(row)
                
                # 테이블 표시 (스타일 적용)
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "No.": st.column_config.NumberColumn("No.", width="small"),
                        "카테고리": st.column_config.TextColumn("카테고리", width="small"),
                        "KPI명": st.column_config.TextColumn("KPI명", width="medium"),
                        "현재값 (Baseline)": st.column_config.TextColumn("현재값", width="medium"),
                        "목표값 (Target)": st.column_config.TextColumn("목표값", width="medium"),
                        "측정 방법": st.column_config.TextColumn("측정 방법", width="large")
                    }
                )
                
                st.caption(f"※ 총 {len(kpi_table_data)}개 KPI 지표")
        else:
            st.info("KPI 데이터가 없습니다.")
    
    else:
        st.warning("전략 분석 결과를 찾을 수 없습니다.")
    
    # 하단 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("← 분석 결과로 돌아가기", use_container_width=True, type="primary", key="back_bottom"):
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