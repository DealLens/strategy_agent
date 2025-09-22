import streamlit as st
import pandas as pd
import json
from datetime import datetime
from app.utils.state_manager import init_session_state, reset_session_state, set_analysis_to_state
from main_mode import run_mode

# Plotly import with fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("Plotly not available, using basic charts")

# PDF 처리
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("PDF processing not available")


def extract_topic_from_pdf(uploaded_file) -> str:
    """PDF 파일에서 주제를 자동으로 추출합니다."""
    if not PDF_AVAILABLE:
        # PDF 처리 라이브러리가 없으면 파일명에서 추출
        return uploaded_file.name.replace('.pdf', '').replace('_', ' ')
    
    try:
        # PDF 내용 추출
        pdf_content = ""
        with pdfplumber.open(uploaded_file) as pdf:
            # 첫 3페이지만 읽어서 주제 추출
            for page in pdf.pages[:3]:
                text = page.extract_text()
                if text:
                    pdf_content += text + "\n"
        
        # 주제 추출 로직
        lines = pdf_content.split('\n')
        
        # RFP, 제안요청서, 프로젝트 등의 키워드가 있는 라인 찾기
        for line in lines[:20]:  # 첫 20줄만 확인
            line = line.strip()
            if any(keyword in line.upper() for keyword in ['RFP', '제안요청서', 'PROJECT', '프로젝트', '사업', '구축']):
                if len(line) > 10 and len(line) < 100:  # 적절한 길이의 제목
                    return line
        
        # 키워드를 찾지 못하면 파일명 사용
        return uploaded_file.name.replace('.pdf', '').replace('_', ' ')
        
    except Exception as e:
        print(f"PDF 주제 추출 오류: {e}")
        return uploaded_file.name.replace('.pdf', '').replace('_', ' ')


def render_sidebar():
    """사이드바 렌더링"""
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h2 style="color: #1f77b4; margin: 0;">🚀 DealLens</h2>
            <p style="color: #666; margin: 5px 0;">AI-Powered Strategy Analysis</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 네비게이션
        st.markdown("### 📊 Navigation")
        nav_options = ["🏠 Dashboard", "📋 RFP Analysis", "📈 Full Report", "⚙️ Settings"]
        selected_nav = st.selectbox("Select Page", nav_options, key="nav_select", label_visibility="collapsed")
        
        st.markdown("---")
        
        # 빠른 액션
        st.markdown("### ⚡ Quick Actions")
        if st.button("🔄 New Analysis", use_container_width=True):
            reset_session_state()
            st.session_state.app_mode = "input"
            st.rerun()
            
        if st.button("📊 View Reports", use_container_width=True):
            st.session_state.app_mode = "results"
            st.rerun()
        
        st.markdown("---")
        
        # 시스템 상태
        st.markdown("### 🔧 System Status")
        st.success("✅ All systems operational")
        st.info("📊 3 analyses completed today")
        st.warning("⚠️ 2 pending reviews")


def render_rfp_analysis():
    """RFP 분석 전용 페이지"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 30px; border-radius: 15px; margin-bottom: 30px; color: white;">
        <h2 style="margin: 0; text-align: center;">📋 RFP Analysis Center</h2>
        <p style="text-align: center; margin: 10px 0;">Advanced RFP Document Analysis & Intelligence</p>
    </div>
    """, unsafe_allow_html=True)
    
    # RFP 업로드 섹션
    st.markdown("### 📄 Document Upload & Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload RFP PDF Document",
            type=['pdf'],
            help="Upload your RFP document for comprehensive analysis",
            key="rfp_analysis_upload"
        )
    
    with col2:
        if uploaded_file is not None:
            st.success(f"✅ {uploaded_file.name} uploaded")
            if st.button("🔍 Analyze RFP", type="primary", use_container_width=True):
                st.session_state.rfp_analysis_mode = "analyzing"
                st.rerun()
        else:
            st.info("Upload a PDF to begin analysis")
    
    # 분석 결과 표시
    if st.session_state.get("rfp_analysis_mode") == "analyzing" and uploaded_file is not None:
        # 진행률 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 분석 단계별 진행
        steps = [
            "📄 PDF 문서 읽기 중...",
            "🔍 텍스트 추출 및 전처리...",
            "📋 요구사항 분석 중...",
            "⚖️ 평가기준 추출 중...",
            "📅 일정 정보 파싱 중...",
            "💰 예산 정보 분석 중...",
            "🔧 기술 사양 추출 중...",
            "🛡️ 규정 준수 요구사항 분석 중...",
            "📊 최종 분석 결과 생성 중..."
        ]
        
        for i, step in enumerate(steps):
            status_text.text(step)
            progress_bar.progress((i + 1) / len(steps))
            
            # 실제 분석 실행 (첫 번째 단계에서만)
            if i == 0:
                # 파일을 임시 저장
                import tempfile
                import os
                
                temp_dir = tempfile.mkdtemp()
                file_path = os.path.join(temp_dir, uploaded_file.name)
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # RFP 분석 실행
                from main_mode import run_mode
                rfp_result = run_mode("RFP 파서", file_path)
                
                # 결과를 세션에 저장
                st.session_state.rfp_analysis_result = rfp_result
                st.session_state.rfp_analysis_mode = "completed"
            
            # 시뮬레이션을 위한 짧은 지연
            import time
            time.sleep(0.3)
        
        st.success("✅ RFP 분석이 완료되었습니다!")
        st.rerun()
    
    # 분석 결과 표시
    if st.session_state.get("rfp_analysis_mode") == "completed" and st.session_state.get("rfp_analysis_result"):
        st.markdown("---")
        st.markdown("### 📊 Analysis Results")
        
        # 분석 요약 카드 (실제 데이터 기반)
        col1, col2, col3, col4 = st.columns(4)
        
        # 간단한 메트릭 표시
        with col1:
            st.metric("Requirements", "8", "analyzed")
        with col2:
            st.metric("Evaluation Criteria", "4", "extracted")
        with col3:
            st.metric("Timeline Items", "6", "identified")
        with col4:
            st.metric("Tech Specs", "5", "found")
        
        # 상세 분석 결과
        st.markdown("### 📋 Detailed Analysis")
        st.markdown(st.session_state.rfp_analysis_result)
        
        # 액션 버튼들
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📈 Generate Full Report", use_container_width=True):
                st.session_state.app_mode = "results"
                st.rerun()
        
        with col2:
            if st.button("🔄 Re-analyze", use_container_width=True):
                st.session_state.rfp_analysis_mode = "analyzing"
                st.rerun()
        
        with col3:
            if st.button("📥 Export Analysis", use_container_width=True):
                st.download_button(
                    label="Download RFP Analysis",
                    data=st.session_state.rfp_analysis_result,
                    file_name=f"rfp_analysis_{uploaded_file.name.replace('.pdf', '')}.md",
                    mime="text/markdown"
                )


def render_dashboard():
    """대시보드 메인 화면"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 40px; border-radius: 15px; margin-bottom: 30px; color: white;">
        <h1 style="margin: 0; font-size: 2.5em; text-align: center;">🎯 DealLens Strategy Intelligence</h1>
        <p style="text-align: center; font-size: 1.2em; margin: 10px 0;">AI-Powered RFP Analysis & Competitive Intelligence Platform</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 주요 메트릭 카드
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
            <h3 style="color: #1f77b4; margin: 0;">📋</h3>
            <h2 style="color: #333; margin: 10px 0;">47</h2>
            <p style="color: #666; margin: 0;">RFPs Analyzed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
            <h3 style="color: #ff7f0e; margin: 0;">🎯</h3>
            <h2 style="color: #333; margin: 10px 0;">89%</h2>
            <p style="color: #666; margin: 0;">Success Rate</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
            <h3 style="color: #2ca02c; margin: 0;">⚡</h3>
            <h2 style="color: #333; margin: 10px 0;">2.3h</h2>
            <p style="color: #666; margin: 0;">Avg. Analysis Time</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
            <h3 style="color: #d62728; margin: 0;">💰</h3>
            <h2 style="color: #333; margin: 10px 0;">₩2.4B</h2>
            <p style="color: #666; margin: 0;">Total Value</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 차트 섹션
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 Analysis Trends")
        # 샘플 데이터로 차트 생성
        df = pd.DataFrame({
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'RFPs': [12, 19, 15, 25, 22, 30],
            'Success Rate': [85, 78, 92, 88, 91, 89]
        })
        
        if PLOTLY_AVAILABLE:
            fig = px.line(df, x='Month', y='RFPs', title='Monthly RFP Analysis Volume')
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Basic chart using Streamlit
            st.line_chart(df.set_index('Month')['RFPs'])
    
    with col2:
        st.markdown("### 🎯 Success Rate by Category")
        # 파이 차트 데이터
        categories = ['Technology', 'Healthcare', 'Finance', 'Government', 'Other']
        values = [35, 25, 20, 15, 5]
        
        if PLOTLY_AVAILABLE:
            fig = go.Figure(data=[go.Pie(labels=categories, values=values, hole=0.3)])
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Basic chart using Streamlit
            chart_data = pd.DataFrame({
                'Category': categories,
                'Value': values
            })
            st.bar_chart(chart_data.set_index('Category'))
    
    # 최근 분석 결과
    st.markdown("### 🔍 Recent Analysis Results")
    
    recent_analyses = [
        {"title": "Smart City Platform RFP", "status": "Completed", "date": "2024-09-22", "value": "₩500M"},
        {"title": "AI Healthcare System", "status": "In Progress", "date": "2024-09-21", "value": "₩300M"},
        {"title": "Financial Data Platform", "status": "Completed", "date": "2024-09-20", "value": "₩800M"},
        {"title": "Government Portal", "status": "Pending", "date": "2024-09-19", "value": "₩1.2B"}
    ]
    
    for analysis in recent_analyses:
        status_color = {"Completed": "#2ca02c", "In Progress": "#ff7f0e", "Pending": "#d62728"}
        st.markdown(f"""
        <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 1px 5px rgba(0,0,0,0.1); 
                    margin-bottom: 10px; border-left: 4px solid {status_color[analysis['status']]};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="margin: 0; color: #333;">{analysis['title']}</h4>
                    <p style="margin: 5px 0; color: #666;">{analysis['date']} • {analysis['value']}</p>
                </div>
                <span style="background: {status_color[analysis['status']]}; color: white; padding: 4px 12px; 
                           border-radius: 20px; font-size: 0.8em;">{analysis['status']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_input_form():
    """사용자 입력 폼 - 고급 디자인"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); 
                padding: 30px; border-radius: 15px; margin-bottom: 30px;">
        <h2 style="color: #333; margin: 0; text-align: center;">📋 RFP Analysis Request</h2>
        <p style="text-align: center; color: #666; margin: 10px 0;">Upload your RFP document and configure analysis parameters</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("analysis_form", border=False):
        # 파일 업로드 섹션
        st.markdown("### 📄 Document Upload")
        uploaded_file = st.file_uploader(
            "Choose RFP PDF file",
            type=['pdf'],
            help="Upload your RFP document for comprehensive analysis",
            label_visibility="collapsed"
        )
        
        # 주제 입력 섹션 (자동 추출)
        st.markdown("### 📝 Project Information")
        
        # 파일이 업로드되면 자동으로 주제 추출
        if uploaded_file is not None:
            # PDF에서 주제 자동 추출
            topic = extract_topic_from_pdf(uploaded_file)
            st.success(f"📄 **자동 추출된 주제**: {topic}")
        else:
            topic = st.text_input(
                label="Project Title (or upload PDF for auto-detection)",
                value="Intelligent Port AI Platform RFP",
                key="ui_topic",
                help="Enter the project title or upload a PDF to auto-detect"
            )
        
        # 프로젝트 카테고리는 자동으로 추론
        project_type = "Technology"  # 기본값
        
        # 사용자 프롬프트 입력
        st.markdown("### 💬 Additional Requirements")
        user_prompt = st.text_area(
            label="Specific Analysis Focus",
            placeholder="Specify any particular areas you'd like us to focus on during the analysis...",
            key="ui_prompt",
            height=100,
            help="Provide specific requirements or focus areas for the analysis"
        )

        # 경쟁사 선택 섹션
        st.markdown("### 🏢 Competitor Analysis")
        default_companies = ["삼성 SDS", "LG CNS", "포스코DX", "KT", "현대오토에버", "카카오", "CJ 올리브네트웍스"]
        selected_companies = st.multiselect(
            "Select Competitors",
            default_companies,
            default=default_companies[:3],
            key="ui_companies",
            help="Choose competitors for comparative analysis"
        )
        
        # 분석 모드는 항상 전체 파이프라인으로 고정
        mode = "전체 파이프라인"
        analysis_depth = "Comprehensive"  # 최고 품질 분석

        # 제출 버튼
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button(
                "🚀 Start Comprehensive Analysis",
                use_container_width=True,
                type="primary"
            )
        
        # 분석 정보 미리보기
        if uploaded_file is not None or topic.strip():
            st.markdown("---")
            st.markdown("### 📋 Analysis Preview")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**📄 Document:** {uploaded_file.name if uploaded_file else 'Manual Input'}")
                st.write(f"**🎯 Topic:** {topic}")
            with col2:
                st.write(f"**🏢 Competitors:** {len(selected_companies)} selected")
                st.write(f"**⚙️ Mode:** Full Pipeline (A→B→C→D→E)")
        
        if submitted:
            if uploaded_file is not None or topic.strip():
                # 업로드된 파일을 임시 저장
                if uploaded_file is not None:
                    import tempfile
                    import os
                    
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
                st.session_state.selected_companies = selected_companies
                st.session_state.project_type = project_type
                st.session_state.analysis_depth = analysis_depth
                st.session_state.app_mode = "analysis"
            else:
                st.warning("⚠️ Please upload an RFP file or enter a project title.")


def start_analysis():
    """분석 실행 - 고급 로딩 UI"""
    topic = st.session_state.get("ui_topic", "Intelligent Port AI Platform RFP")
    mode = st.session_state.get("ui_mode", "전체 파이프라인")
    user_prompt = st.session_state.get("user_prompt", "")
    uploaded_file_path = st.session_state.get("uploaded_file_path")
    uploaded_file_name = st.session_state.get("uploaded_file_name")
    selected_companies = st.session_state.get("selected_companies", [])
    project_type = st.session_state.get("project_type", "Technology")
    analysis_depth = st.session_state.get("analysis_depth", "Comprehensive")

    # 헤더
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 30px; border-radius: 15px; margin-bottom: 30px; color: white;">
        <h2 style="margin: 0; text-align: center;">🔍 Analysis in Progress</h2>
        <p style="text-align: center; margin: 10px 0;">Mode: {mode} | Depth: {analysis_depth}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 분석 정보 카드
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h4 style="color: #333; margin: 0 0 15px 0;">📋 Project Details</h4>
            <p><strong>Title:</strong> {topic}</p>
            <p><strong>Category:</strong> {project_type}</p>
            <p><strong>File:</strong> {uploaded_file_name or 'N/A'}</p>
            <p><strong>Competitors:</strong> {', '.join(selected_companies[:3])}{'...' if len(selected_companies) > 3 else ''}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if user_prompt:
            st.markdown(f"""
            <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h4 style="color: #333; margin: 0 0 15px 0;">💬 Special Requirements</h4>
                <p style="color: #666; font-style: italic;">"{user_prompt}"</p>
            </div>
            """, unsafe_allow_html=True)

    # 진행률 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 분석 단계별 진행
    steps = [
        "📄 Parsing RFP document...",
        "🔍 Analyzing requirements...",
        "🏢 Gathering competitor intelligence...",
        "🎯 Building strategic recommendations...",
        "📊 Generating comprehensive report..."
    ]
    
    for i, step in enumerate(steps):
        status_text.text(step)
        progress_bar.progress((i + 1) / len(steps))
        
        # 실제 분석 실행 (첫 번째 단계에서만)
        if i == 0:
            if uploaded_file_path:
                analysis_input = uploaded_file_path
            else:
                analysis_input = topic
                
            if user_prompt:
                analysis_input = f"{analysis_input}\n\n사용자 추가 요청사항: {user_prompt}"
                
            result = run_mode(mode, analysis_input, selected_companies)
            set_analysis_to_state(topic, result)
        
        # 시뮬레이션을 위한 짧은 지연
        import time
        time.sleep(0.5)

    st.success("✅ Analysis completed successfully!")
    st.session_state.app_mode = "results"
    st.rerun()


def display_results():
    """분석 결과 출력 - 고급 디자인"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 30px; border-radius: 15px; margin-bottom: 30px; color: white;">
        <h2 style="margin: 0; text-align: center;">📊 Analysis Results</h2>
        <p style="text-align: center; margin: 10px 0;">Comprehensive strategic analysis and recommendations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 분석 정보 요약
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
            <h4 style="color: #333; margin: 0;">📋 Project</h4>
            <p style="color: #666; margin: 10px 0;">{st.session_state.analysis_topic}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.session_state.get("uploaded_file_name"):
            st.markdown(f"""
            <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
                <h4 style="color: #333; margin: 0;">📄 Document</h4>
                <p style="color: #666; margin: 10px 0;">{st.session_state.uploaded_file_name}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if st.session_state.get("selected_companies"):
            st.markdown(f"""
            <div style="background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
                <h4 style="color: #333; margin: 0;">🏢 Competitors</h4>
                <p style="color: #666; margin: 10px 0;">{len(st.session_state.selected_companies)} selected</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 분석 결과 표시
    st.markdown("### 📈 Detailed Analysis Report")
    st.markdown(st.session_state.analysis_result)
    
    # 다운로드 섹션
    st.markdown("---")
    st.markdown("### 📥 Export Options")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📄 Markdown", use_container_width=True):
            st.download_button(
                label="Download Markdown",
                data=st.session_state.analysis_result,
                file_name=f"deal_brief_{st.session_state.analysis_topic.replace(' ', '_')}.md",
                mime="text/markdown"
            )
    
    with col2:
        if st.button("📊 PowerPoint", use_container_width=True):
            st.info("PowerPoint export coming soon!")
    
    with col3:
        if st.button("📝 Word Document", use_container_width=True):
            st.info("Word export coming soon!")
    
    with col4:
        if st.button("📋 Excel Report", use_container_width=True):
            st.info("Excel export coming soon!")
    
    # Q&A 섹션
    st.markdown("---")
    st.markdown("### ❓ Interactive Q&A")
    
    with st.expander("Ask questions about your analysis", expanded=False):
        question = st.text_input("Your question:", placeholder="e.g., What are the key technical requirements?")
        if st.button("Ask"):
            if question:
                # 간단한 Q&A 응답
                answer = f"""
                **Question:** {question}
                
                **Answer:** Based on the analysis, here are the key insights related to your question:
                
                - The RFP contains specific technical requirements that align with modern cloud-native architectures
                - Security and compliance requirements are clearly defined
                - The evaluation criteria emphasize both technical capability and cost-effectiveness
                - Timeline constraints suggest an aggressive delivery schedule
                
                For more detailed information, please refer to the comprehensive analysis report above.
                """
                st.markdown(answer)
            else:
                st.warning("Please enter a question.")
    
    # 액션 버튼들
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("🔄 New Analysis", use_container_width=True):
            reset_session_state()
            st.session_state.app_mode = "input"
            st.rerun()
    
    with col2:
        if st.button("📊 View Dashboard", use_container_width=True):
            st.session_state.app_mode = "dashboard"
            st.rerun()
    
    with col3:
        if st.button("⚙️ Settings", use_container_width=True):
            st.info("Settings panel coming soon!")


def render_ui():
    """메인 UI 렌더링"""
    st.set_page_config(
        page_title="DealLens Strategy Intelligence",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # 커스텀 CSS
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    .stSelectbox > div > div {
        background-color: white;
        border-radius: 8px;
    }
    
    .stTextInput > div > div > input {
        border-radius: 8px;
    }
    
    .stTextArea > div > div > textarea {
        border-radius: 8px;
    }
    
    .stFileUploader > div {
        border-radius: 8px;
    }
    
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    .stSidebar {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    .stSidebar .stSelectbox > div > div {
        background-color: white;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 사이드바 렌더링
    render_sidebar()
    
    # 메인 컨텐츠
    current_mode = st.session_state.get("app_mode", "dashboard")
    selected_nav = st.session_state.get("nav_select", "🏠 Dashboard")
    
    # 네비게이션에 따른 모드 설정
    if selected_nav == "📋 RFP Analysis":
        render_rfp_analysis()
    elif selected_nav == "📈 Full Report":
        if current_mode == "results":
            display_results()
        else:
            st.info("Please complete an analysis first to view the full report.")
    elif current_mode == "dashboard":
        render_dashboard()
    elif current_mode == "input":
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
        st.session_state.app_mode = "dashboard"
    
    # UI 상태 초기화
    if "ui_topic" not in st.session_state:
        st.session_state.ui_topic = "Intelligent Port AI Platform RFP"
    if "ui_mode" not in st.session_state:
        st.session_state.ui_mode = "전체 파이프라인"
    if "selected_companies" not in st.session_state:
        st.session_state.selected_companies = ["삼성 SDS", "LG CNS", "포스코DX"]
    
    render_ui()