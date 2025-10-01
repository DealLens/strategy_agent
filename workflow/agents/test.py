import streamlit as st
from competitor_analysis import crawl_and_save, competitor_analysis

st.set_page_config(page_title="경쟁사 뉴스 분석", page_icon="📰", layout="wide")

st.title("📰 경쟁사 뉴스 크롤링 & 분석")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 회사명 입력
    company_input = st.text_input(
        "회사명 입력 (쉼표로 구분)", 
        value="LG CNS, 삼성SDS",
        help="예: LG CNS, 삼성SDS, KT"
    )
    
    # 크롤링 설정
    max_articles = st.slider(
        "각 소스당 크롤링할 기사 수 (다음+네이버+구글)", 
        min_value=5, 
        max_value=30, 
        value=20,
        step=5,
        help="각 소스에서 수집할 기사 수 (총 수집량 = 3 × 이 값)"
    )
    
    threshold = st.slider(
        "중복 판단 기준 (유사도)", 
        min_value=0.7, 
        max_value=1.0, 
        value=0.9,
        step=0.05,
        help="1에 가까울수록 엄격하게 중복 판단"
    )

# 회사명 리스트 생성
companies = [c.strip() for c in company_input.split(",") if c.strip()]

# 메인 영역
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🔍 뉴스 크롤링")
    
    if st.button("📊 크롤링 실행", type="primary", use_container_width=True):
        if not companies:
            st.warning("회사명을 입력하세요.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, company in enumerate(companies):
                status_text.text(f"'{company}' 크롤링 중...")
                
                with st.spinner(f"'{company}' 뉴스 수집 중..."):
                    crawl_and_save(company, max_articles=max_articles, threshold=threshold)
                
                progress_bar.progress((i + 1) / len(companies))
            
            status_text.text("✅ 크롤링 완료!")
            st.success(f"{len(companies)}개 회사 크롤링 완료!")
            st.balloons()

with col2:
    st.subheader("📈 분석 실행")
    
    if st.button("🎯 분석 실행", type="secondary", use_container_width=True):
        with st.spinner("분석 중..."):
            result = competitor_analysis.invoke({"companies": None})
            profiles = result.get("competitor_profiles", {})
        
        if not profiles:
            st.warning("분석할 데이터가 없습니다. 먼저 크롤링을 실행하세요.")
        else:
            st.success(f"✅ {len(profiles)}개 회사 분석 완료!")

# 구분선
st.divider()

# 분석 결과 표시
st.subheader("📊 분석 결과")

# 분석 실행 (자동)
if companies:
    with st.spinner("데이터 로딩 중..."):
        result = competitor_analysis.invoke({"companies": None})
        profiles = result.get("competitor_profiles", {})
    
    if profiles:
        # 탭으로 회사별 결과 표시
        tabs = st.tabs(list(profiles.keys()))
        
        for tab, (comp, prof) in zip(tabs, profiles.items()):
            with tab:
                st.markdown(f"### {comp}")
                
                # 최근 뉴스
                recent_news = prof.get("recent_news", [])
                if recent_news:
                    st.markdown(f"**📰 최근 뉴스 ({len(recent_news)}건)**")
                    
                    for i, news in enumerate(recent_news, 1):
                        with st.expander(f"{i}. {news.get('title', 'N/A')[:100]}..."):
                            col_a, col_b = st.columns([1, 3])
                            
                            with col_a:
                                st.markdown(f"**출처:** {news.get('source', 'N/A')}")
                                st.markdown(f"**날짜:** {news.get('crawled_at', 'N/A')[:10]}")
                            
                            with col_b:
                                if news.get('summary'):
                                    st.info(f"**💡 AI 요약:**\n\n{news['summary']}")
                                
                                if news.get('description'):
                                    st.markdown(f"**📝 내용:** {news['description']}")
                                
                                if news.get('url'):
                                    st.markdown(f"[🔗 원문 보기]({news['url']})")
                
                # SWOT 분석
                swot = prof.get("swot", {})
                if any(swot.values()):
                    st.markdown("**📋 SWOT 분석**")
                    
                    swot_col1, swot_col2 = st.columns(2)
                    
                    with swot_col1:
                        st.success(f"**💪 Strengths (강점)**\n\n{swot.get('S', 'TBD')}")
                        st.info(f"**🎯 Opportunities (기회)**\n\n{swot.get('O', 'TBD')}")
                    
                    with swot_col2:
                        st.warning(f"**⚠️ Weaknesses (약점)**\n\n{swot.get('W', 'TBD')}")
                        st.error(f"**🚨 Threats (위협)**\n\n{swot.get('T', 'TBD')}")
                
                # 요약 통계
                summaries = prof.get("summaries", [])
                if summaries:
                    st.markdown(f"**📊 통계**")
                    st.metric("AI 요약 생성", f"{len(summaries)}건")
    else:
        st.info("💡 왼쪽 사이드바에서 회사명을 입력하고 '크롤링 실행' 버튼을 클릭하세요.")
else:
    st.info("💡 왼쪽 사이드바에서 회사명을 입력하세요.")

# 푸터
st.divider()
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 20px;'>
        <p>🤖 Powered by Azure OpenAI | 📊 데이터 출처: 다음 뉴스, 네이버 뉴스</p>
    </div>
    """,
    unsafe_allow_html=True
)
