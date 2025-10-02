"""
경쟁사 뉴스 크롤러 - Streamlit 앱
실행: streamlit run app.py
"""
import streamlit as st
import sys
import os
import json
from datetime import datetime

# 현재 디렉토리를 path에 추가
sys.path.insert(0, os.path.dirname(__file__))

# 페이지 설정
st.set_page_config(page_title="경쟁사 뉴스 크롤러", page_icon="🔍", layout="wide")

# CSS 스타일
st.markdown("""
<style>
    .main-header {font-size: 2.5rem; font-weight: bold; color: #1f77b4;}
    .success-box {padding: 1rem; background-color: #d4edda; border-radius: 0.5rem; margin: 1rem 0;}
    .info-box {padding: 1rem; background-color: #d1ecf1; border-radius: 0.5rem; margin: 1rem 0;}
</style>
""", unsafe_allow_html=True)

# 타이틀
st.markdown('<p class="main-header">🔍 경쟁사 뉴스 크롤러</p>', unsafe_allow_html=True)
st.markdown("---")

# 환경 확인
try:
    from competitor_analysis import (
        competitor_analysis,
        COMPANY_DIR,
        client,
        crawl_all_sources,
        normalize_title,
        deduplicate_articles,
        save_articles,
        load_articles,
        extract_key_technologies,
        extract_differentiation_points,
    )
    env_ok = True
except Exception as e:
    st.error(f"❌ 모듈 로드 실패: {e}")
    st.stop()

# 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 환경 정보
    st.subheader("📊 환경 상태")
    st.metric("데이터 경로", "✓" if COMPANY_DIR else "✗")
    st.metric("OpenAI", "✓" if client else "✗")
    
    if COMPANY_DIR and os.path.isdir(COMPANY_DIR):
        json_files = [f for f in os.listdir(COMPANY_DIR) if f.endswith('.json')]
        st.metric("저장된 회사", len(json_files))
    
    st.markdown("---")
    
    # 크롤링 옵션
    st.subheader("🔧 크롤링 옵션")
    max_articles = st.slider("최대 기사 수", 5, 50, 20)
    threshold = st.slider("중복 제거 임계값", 0.7, 1.0, 0.9, 0.05)

# 메인 영역
tab1, tab2, tab3 = st.tabs(["🚀 크롤링 실행", "📊 분석 결과", "💾 저장된 파일"])

# ===== 탭 1: 크롤링 실행 =====
with tab1:
    st.subheader("📰 뉴스 크롤링 (전체 회사)")
    
    # 크롤링 대상 회사
    target_companies = ["현대오토에버", "삼성SDS", "LG CNS"]
    
    st.info(f"🏢 **크롤링 대상**: {', '.join(target_companies)} (총 {len(target_companies)}개 회사)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("##### 📊 크롤링 정보")
        st.metric("대상 회사 수", len(target_companies))
        st.metric("회사당 최대 기사", max_articles)
    
    with col2:
        st.markdown("##### 크롤링 소스")
        st.info("✓ 다음 뉴스\n\n✓ 네이버 뉴스\n\n✓ 구글 뉴스")
    
    st.markdown("---")
    
    # 크롤링 실행
    if st.button("🚀 전체 크롤링 시작", type="primary", use_container_width=True):

        total_progress = st.progress(0)
        overall_status = st.empty()
        log_container = st.container()
        all_results = {}

        previous_counts = {
            company: len(load_articles(company))
            for company in target_companies
        }

        overall_status.markdown("**🚀 전체 크롤링 실행 중...**")
        total_progress.progress(10)

        with st.spinner("크롤링 및 분석 실행 중..."):
            result = competitor_analysis.invoke({"update_data": True})
            profiles = result.get('competitor_profiles', {})

        st.session_state['last_profiles'] = profiles
        total_progress.progress(60)

        for idx, company_name in enumerate(target_companies, 1):
            articles = load_articles(company_name)
            new_count = len(articles) - previous_counts.get(company_name, 0)
            progress_value = int(60 + (idx / len(target_companies)) * 40)
            total_progress.progress(min(progress_value, 100))
            overall_status.markdown(f"**🏁 {company_name} 처리 완료 (총 {len(articles)}건)**")

            with log_container:
                st.markdown(f"### 🏢 {company_name}")
                if new_count > 0:
                    st.success(f"✅ {company_name} 완료! 신규 **{new_count}건** / 총 **{len(articles)}건**")
                else:
                    st.info(f"ℹ️ {company_name}: 신규 기사 없음 (총 {len(articles)}건)")

                profile = profiles.get(company_name)
                if profile:
                    key_techs = profile.get('key_technologies', [])
                    if key_techs:
                        st.caption(f"핵심 기술: {', '.join(key_techs)}")
                st.markdown("---")

            all_results[company_name] = {
                'new': max(new_count, 0),
                'total': len(articles),
                'articles': articles[:3] if articles else [],
            }

        total_progress.progress(100)
        overall_status.markdown("**✅ 전체 크롤링 완료!**")

        st.markdown("## 📊 전체 크롤링 결과")
        summary_cols = st.columns(len(target_companies))
        for idx, company in enumerate(target_companies):
            if company in all_results:
                with summary_cols[idx]:
                    st.metric(
                        company,
                        f"{all_results[company]['new']}건",
                        f"총 {all_results[company]['total']}건"
                    )

        st.session_state['last_crawl_all'] = {
            'results': all_results,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    
    # 마지막 크롤링 결과 표시
    if 'last_crawl_all' in st.session_state:
        st.markdown("---")
        last = st.session_state['last_crawl_all']
        total_new = sum(r['new'] for r in last['results'].values())
        st.info(f"📌 마지막 전체 크롤링: ({last['timestamp']}) - 총 신규 {total_new}개 기사")

# ===== 탭 2: 분석 결과 =====
with tab2:
    st.subheader("📊 경쟁사 분석 결과")
    
    if st.button("🔄 분석 실행", type="primary"):
        with st.spinner("분석 중..."):
            try:
                result = competitor_analysis.invoke({"update_data": False})
                profiles = result.get('competitor_profiles', {})

                if not profiles:
                    st.warning("분석할 데이터가 없습니다. 먼저 크롤링을 실행하세요.")
                else:
                    st.success(f"✓ **{len(profiles)}개** 회사 분석 완료")
                    st.session_state['last_profiles'] = profiles

                    for company, data in profiles.items():
                        with st.expander(f"🏢 {company}", expanded=True):
                            col1, col2 = st.columns([2, 1])

                            with col1:
                                st.markdown("##### 📰 최신 뉴스")
                                news = data.get('recent_news', [])
                                for idx, item in enumerate(news[:5], 1):
                                    st.markdown(f"**{idx}.** {item.get('title', 'N/A')}")
                                    st.caption(f"출처: {item.get('source', 'N/A')}")
                                    if item.get('summary'):
                                        st.info(item['summary'])
                                    st.markdown("---")

                            with col2:
                                st.markdown("##### 📊 통계")
                                st.metric("뉴스 수", len(news))
                                st.metric("요약 수", len([n for n in news if n.get('summary')]))
                                st.markdown("##### 🎯 SWOT")
                                swot = data.get('swot', {})
                                for key, value in swot.items():
                                    st.text(f"{key}: {value}")

            except Exception as e:
                st.error(f"❌ 분석 실패: {e}")
                import traceback
                with st.expander("오류 상세"):
                    st.code(traceback.format_exc())

# ===== 탭 3: 저장된 파일 =====
with tab3:
    st.subheader("💾 저장된 데이터 파일")
    
    if COMPANY_DIR and os.path.isdir(COMPANY_DIR):
        json_files = sorted(
            [f for f in os.listdir(COMPANY_DIR) if f.endswith('.json')],
            key=lambda x: os.path.getmtime(os.path.join(COMPANY_DIR, x)),
            reverse=True
        )

        if json_files:
            st.info(f"📁 저장 경로: `{COMPANY_DIR}`")

            for json_file in json_files:
                file_path = os.path.join(COMPANY_DIR, json_file)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    file_size = os.path.getsize(file_path) / 1024
                    mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))

                    with st.expander(f"📄 {json_file} ({len(data)}개 기사, {file_size:.1f} KB)"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric("기사 수", len(data))
                            st.metric("파일 크기", f"{file_size:.1f} KB")
                            st.text(f"수정: {mod_time.strftime('%Y-%m-%d %H:%M')}")

                        with col2:
                            json_str = json.dumps(data, ensure_ascii=False, indent=2)
                            st.download_button(
                                label="📥 JSON 다운로드",
                                data=json_str,
                                file_name=json_file,
                                mime="application/json",
                                key=f"download_{json_file}"
                            )

                        st.markdown("##### 최신 기사 (3개)")
                        for idx, article in enumerate(data[:3], 1):
                            st.markdown(f"**{idx}.** {article.get('title', 'N/A')}")
                            st.caption(f"{article.get('source', 'N/A')} | {article.get('crawled_at', 'N/A')[:10]}")

                except Exception as e:
                    st.error(f"파일 읽기 실패: {json_file} - {e}")
        else:
            st.info("저장된 파일이 없습니다. 크롤링을 먼저 실행하세요.")
    else:
        st.warning("데이터 디렉토리가 설정되지 않았습니다.")

# Footer
st.markdown("---")
st.caption("🔍 Competitor Analysis Crawler | 실행: `streamlit run app.py`")

