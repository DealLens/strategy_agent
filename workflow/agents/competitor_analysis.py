import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from langchain_core.tools import tool

# =========================
# 초기화
# =========================
try:
    from dotenv import load_dotenv
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except:
    PROJECT_ROOT = os.getcwd()

# OpenAI 클라이언트
client = None
try:
    if os.getenv("AOAI_ENDPOINT") and os.getenv("AOAI_API_KEY"):
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=os.getenv("AOAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AOAI_ENDPOINT"),
        )
    elif os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except:
    pass

# 저장 경로
COMPANY_DIR = os.path.join(PROJECT_ROOT, "data", "company")
os.makedirs(COMPANY_DIR, exist_ok=True)

# 3사 고정
COMPETITORS = ["삼성SDS", "LG CNS", "현대오토에버"]

# =========================
# 크롤링 (다음/네이버/구글)
# =========================
def crawl_daum_news(company: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """다음 뉴스 크롤링"""
    try:
        query = company.replace(" ", "+")
        url = f"https://search.daum.net/search?w=news&q={query}"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        
        for link in soup.select("a[href*='v.daum.net']")[:max_results]:
            title = link.get("title") or link.get_text(strip=True)
            href = link.get("href", "")
            
            if title and href and "v.daum.net" in href:
                articles.append({
                    "title": title,
                    "url": href,
                    "company": company,
                    "source": "다음 뉴스",
                    "crawled_at": datetime.now().isoformat()
                })
        
        return articles
    except:
        return []


def crawl_naver_news(company: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """네이버 뉴스 크롤링"""
    try:
        query = company.replace(" ", "+")
        url = f"https://search.naver.com/search.naver?where=news&query={query}"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        
        # 네이버 뉴스 링크 찾기
        for link in soup.select("a.news_tit, a[href*='news.naver']")[:max_results]:
            title = link.get("title") or link.get_text(strip=True)
            href = link.get("href", "")
            
            if title and href and "news.naver.com" in href:
                articles.append({
                    "title": title,
                    "url": href,
                    "company": company,
                    "source": "네이버 뉴스",
                    "crawled_at": datetime.now().isoformat()
                })
                
                if len(articles) >= max_results:
                    break
        
        return articles
    except:
        return []


def crawl_google_news(company: str, max_results: int = 20) -> List[Dict[str, Any]]:
    """구글 뉴스 크롤링"""
    try:
        query = company.replace(" ", "+")
        url = f"https://www.google.com/search?q={query}&tbm=nws&hl=ko"
        
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        articles = []
        
        for card in soup.select("div.SoaBEf, div.dbsr")[:max_results]:
            link = card.find("a", href=True)
            if not link:
                continue
                
            title_tag = card.find("div", class_="n0jPhd") or card.find("div", class_="JheGif")
            title = title_tag.get_text(strip=True) if title_tag else link.get_text(strip=True)
            
            if title and len(title) > 10:
                articles.append({
                    "title": title,
                    "url": link["href"],
                    "company": company,
                    "source": "구글 뉴스",
                    "crawled_at": datetime.now().isoformat()
                })
        
        return articles
    except:
        return []


def crawl_all_sources(company: str, max_per_source: int = 15, use_parallel: bool = True) -> List[Dict[str, Any]]:
    """3개 소스 모두 크롤링 (병렬 처리 옵션)"""
    
    if use_parallel:
        # 병렬 처리
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        all_articles = []
        tasks = [
            ("다음", crawl_daum_news),
            ("네이버", crawl_naver_news),
            ("구글", crawl_google_news)
        ]
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(func, company, max_per_source): name for name, func in tasks}
            
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                    print(f"    - {source_name}: {len(articles)}개")
                except Exception as e:
                    print(f"    - {source_name}: 실패 ({e})")
        
        return all_articles
    else:
        # 순차 처리
        all_articles = []
        
        print(f"    - 다음 크롤링...", end=" ")
        daum = crawl_daum_news(company, max_per_source)
        all_articles.extend(daum)
        print(f"{len(daum)}개")
        
        print(f"    - 네이버 크롤링...", end=" ")
        naver = crawl_naver_news(company, max_per_source)
        all_articles.extend(naver)
        print(f"{len(naver)}개")
        
        print(f"    - 구글 크롤링...", end=" ")
        google = crawl_google_news(company, max_per_source)
        all_articles.extend(google)
        print(f"{len(google)}개")
        
        return all_articles


# =========================
# 키워드 및 기술 분석
# =========================
def extract_key_technologies(articles: List[Dict]) -> List[str]:
    """핵심 기술 키워드 추출"""
    tech_keywords = {
        'AI/ML': ['ai', '인공지능', '머신러닝', '딥러닝', 'llm', 'gpt'],
        '클라우드': ['클라우드', 'cloud', 'aws', 'azure', 'gcp'],
        '보안': ['보안', 'security', '암호화', '방화벽'],
        '데이터': ['빅데이터', '데이터', 'data', '분석', 'analytics'],
        'IoT': ['iot', '사물인터넷', '센서'],
        '블록체인': ['블록체인', 'blockchain', 'nft', 'web3'],
        '5G': ['5g', '6g', '통신망'],
        'DX': ['디지털전환', 'dx', '디지털 혁신']
    }
    
    tech_count = {}
    for article in articles:
        text = (article.get("title", "") + " " + article.get("summary", "")).lower()
        
        for tech, keywords in tech_keywords.items():
            if any(kw in text for kw in keywords):
                tech_count[tech] = tech_count.get(tech, 0) + 1
    
    # 상위 5개 기술
    sorted_techs = sorted(tech_count.items(), key=lambda x: x[1], reverse=True)
    return [tech for tech, _ in sorted_techs[:5]]


def extract_differentiation_points(company: str, swot: Dict) -> List[str]:
    """차별화 포인트 도출"""
    points = []
    
    strengths = swot.get("S", [])
    weaknesses = swot.get("W", [])
    
    # 강점 기반
    for s in strengths[:3]:
        points.append(f"✓ {s}")
    
    # 약점의 반대를 우리 강점으로
    weakness_counters = {
        "비용": "경쟁력 있는 가격 정책",
        "의사결정": "신속한 의사결정 체계",
        "인력": "전문 인력 보유",
        "규모": "유연한 프로젝트 대응"
    }
    
    for w in weaknesses:
        for key, counter in weakness_counters.items():
            if key in w.lower():
                points.append(f"⚡ 우리 강점: {counter}")
                break
    
    return points[:5]


# =========================
# LLM 서머리 생성
# =========================
def generate_article_summary(title: str, company: str) -> str:
    """개별 기사 요약"""
    if not client or not title:
        return ""
    
    try:
        prompt = f"{company} 관련 뉴스 제목: '{title}'\n이 뉴스의 핵심을 2-3문장으로 요약해주세요."
        
        model = os.getenv("AOAI_DEPLOY_GPT4O_MINI", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except:
        return ""


def generate_company_summary(company: str, articles: List[Dict]) -> str:
    """기업 전체 종합 서머리"""
    if not client or not articles:
        return f"{company}의 최근 활동 정보가 부족합니다."
    
    try:
        news_list = "\n".join([f"• {a['title']}" for a in articles[:10]])
        
        prompt = f"""
{company}의 최근 뉴스 제목들입니다:
{news_list}

이를 바탕으로 {company}의 현재 사업 동향, 기술 역량, 시장 위치를 
전략 컨설턴트 관점에서 5-7문장으로 종합 요약해주세요.
"""
        
        model = os.getenv("AOAI_DEPLOY_GPT4O_MINI", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except:
        return f"{company}는 다양한 IT 서비스 분야에서 활동 중입니다."


def generate_swot(company: str, articles: List[Dict]) -> Dict[str, List[str]]:
    """SWOT 분석 생성"""
    if not client or not articles:
        return {"S": ["정보 부족"], "W": ["정보 부족"], "O": ["정보 부족"], "T": ["정보 부족"]}
    
    try:
        news_list = "\n".join([f"• {a['title']}" for a in articles[:10]])
        
        prompt = f"""
{company}의 최근 뉴스:
{news_list}

위 뉴스를 바탕으로 SWOT 분석을 수행하고, 다음 JSON 형식으로 답변해주세요:
{{
  "S": ["강점1", "강점2"],
  "W": ["약점1", "약점2"],
  "O": ["기회1", "기회2"],
  "T": ["위협1", "위협2"]
}}
"""
        
        model = os.getenv("AOAI_DEPLOY_GPT4O_MINI", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        result = response.choices[0].message.content.strip()
        
        # JSON 추출
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    # Fallback
    return {
        "S": ["프로젝트 수주 역량", "기술 인프라"],
        "W": ["높은 비용"],
        "O": ["디지털 전환 수요"],
        "T": ["경쟁 심화"]
    }


def generate_competitive_comparison(profiles: Dict[str, Dict]) -> str:
    """경쟁사 간 비교 분석"""
    if not client or len(profiles) < 2:
        return ""
    
    try:
        companies_info = []
        for company, data in profiles.items():
            companies_info.append(f"{company}:\n- {data.get('company_summary', '')[:200]}")
        
        combined = "\n\n".join(companies_info)
        
        prompt = f"""
다음은 3개 경쟁사의 요약입니다:

{combined}

이들을 비교하여 각 회사의 차별화 포인트와 경쟁 우위를 3-4문장으로 요약해주세요.
"""
        
        model = os.getenv("AOAI_DEPLOY_GPT4O_MINI", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        return response.choices[0].message.content.strip()
    except:
        return ""


# =========================
# 데이터 저장/로드
# =========================
def deduplicate_articles(articles: List[Dict], existing: List[Dict], threshold: float = 0.85) -> List[Dict]:
    """고급 중복 제거 (유사도 기반)"""
    from difflib import SequenceMatcher
    
    existing_titles = [a.get("title", "") for a in existing]
    new_articles = []
    
    for article in articles:
        title = article.get("title", "")
        if not title:
            continue
        
        # 유사도 체크
        is_duplicate = False
        for existing_title in existing_titles:
            similarity = SequenceMatcher(None, title, existing_title).ratio()
            if similarity >= threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            new_articles.append(article)
            existing_titles.append(title)
    
    return new_articles


def save_articles(company: str, articles: List[Dict]):
    """JSON 파일에 저장"""
    file_path = os.path.join(COMPANY_DIR, f"{company.lower().replace(' ', '_')}.json")
    
    # 기존 데이터 로드
    existing = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except:
            pass
    
    # 고급 중복 제거 (유사도 기반)
    new_articles = deduplicate_articles(articles, existing, threshold=0.85)
    
    # 합치고 저장
    combined = new_articles + existing
    combined = sorted(combined, key=lambda x: x.get("crawled_at", ""), reverse=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(combined[:100], f, ensure_ascii=False, indent=2)  # 최신 100개만 보관
    
    # 상태 저장
    state_path = os.path.join(COMPANY_DIR, f"{company.lower().replace(' ', '_')}_state.json")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"last_crawled_at": datetime.now().isoformat()}, f, indent=2)
    
    print(f"  ✅ {company}: 신규 {len(new_articles)}개 저장 (총 {len(combined)}개)")


def load_articles(company: str) -> List[Dict]:
    """JSON 파일에서 로드"""
    file_path = os.path.join(COMPANY_DIR, f"{company.lower().replace(' ', '_')}.json")
    
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []


# =========================
# 메인 도구
# =========================
@tool
def competitor_analysis(update_data: bool = True) -> Dict[str, Any]:
    """
    3대 경쟁사(삼성SDS, LG CNS, 현대오토에버)의 최신 데이터를 수집하고 종합 분석합니다.
    
    Args:
        update_data: True면 최신 뉴스 크롤링 (기본값)
    
    Returns:
        각 경쟁사의 company_summary, swot, recent_news 포함
    """
    print(f"\n{'='*60}")
    print(f"경쟁사 분석 시작 (3사)")
    print(f"{'='*60}\n")
    
    # 1) 데이터 수집 (병렬 처리)
    if update_data:
        print("[1/3] 최신 뉴스 크롤링 (다음/네이버/구글, 병렬 처리)...")
        for company in COMPETITORS:
            print(f"  → {company}")
            articles = crawl_all_sources(company, max_per_source=15, use_parallel=True)
            
            print(f"    → 총 {len(articles)}개 수집, 요약 생성 중...", end=" ")
            
            # 요약 생성 (병렬)
            from concurrent.futures import ThreadPoolExecutor
            
            def add_summary(article):
                article["summary"] = generate_article_summary(article["title"], company)
                return article
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                articles = list(executor.map(add_summary, articles))
            
            summarized_count = sum(1 for a in articles if a.get('summary'))
            print(f"{summarized_count}개 완료")
            
            save_articles(company, articles)
    else:
        print("[1/3] 기존 데이터 사용 (크롤링 스킵)")
    
    # 2) 분석
    print("\n[2/3] 데이터 분석 중...")
    profiles = {}
    
    for company in COMPETITORS:
        articles = load_articles(company)
        
        if not articles:
            print(f"  ⚠️ {company}: 데이터 없음")
            continue
        
        # SWOT 생성
        swot = generate_swot(company, articles)
        
        # 최신 뉴스 5개 (링크 포함)
        recent_news = []
        for article in articles[:5]:
            recent_news.append({
                "title": article.get("title", ""),
                "url": article.get("url", ""),  # 🆕 링크 포함
                "source": article.get("source", ""),
                "summary": article.get("summary", "")
            })
        
        profiles[company] = {
            "recent_news": recent_news,
            "company_summary": generate_company_summary(company, articles),
            "swot": swot,
            "key_technologies": extract_key_technologies(articles),  # 🆕 기술 분석
            "differentiation_points": extract_differentiation_points(company, swot),  # 🆕 차별화 포인트
            "total_articles": len(articles)
        }
        
        print(f"  ✅ {company}: {len(articles)}개 기사 분석 완료")
    
    # 3) 경쟁 분석 요약
    print("\n[3/3] 경쟁 분석 요약 생성...")
    if len(profiles) >= 2:
        comparison_summary = generate_competitive_comparison(profiles)
        print(f"  ✅ 경쟁 분석 완료")
    
    print(f"\n{'='*60}")
    print(f"경쟁사 분석 완료: {len(profiles)}/{len(COMPETITORS)}개 기업")
    print(f"{'='*60}\n")
    
    return {"competitor_profiles": profiles}


# =========================
# 직접 실행
# =========================
if __name__ == "__main__":
    result = competitor_analysis.invoke({"update_data": True})
    profiles = result.get("competitor_profiles", {})
    
    for company, data in profiles.items():
        print(f"\n[{company}]")
        print(f"종합: {data.get('company_summary', '')[:150]}...")
        print(f"SWOT-S: {', '.join(data.get('swot', {}).get('S', []))}")
