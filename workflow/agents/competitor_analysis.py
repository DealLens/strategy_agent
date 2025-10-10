import os
import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.tools import tool
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
client_init_error = None

try:
    if os.getenv("AOAI_ENDPOINT") and os.getenv("AOAI_API_KEY"):
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=os.getenv("AOAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AOAI_ENDPOINT"),
        )
        print("✅ [경쟁사 분석] Azure OpenAI 클라이언트 초기화 성공")
    elif os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print("✅ [경쟁사 분석] OpenAI 클라이언트 초기화 성공")
    else:
        client_init_error = "환경 변수 미설정: AOAI_API_KEY, AOAI_ENDPOINT 또는 OPENAI_API_KEY 필요"
        print(f"⚠️ [경쟁사 분석] {client_init_error}")
        print("   AI 기반 분석 기능이 제한됩니다.")
except Exception as e:
    client_init_error = str(e)
    print(f"⚠️ [경쟁사 분석] OpenAI 클라이언트 초기화 실패: {e}")
    print("   AI 기반 분석 기능이 제한됩니다.")

# 모드/설정 토글
FAST_MODE = os.getenv("FAST_MODE", "1") == "1"
SUMMARIZE_TOPK = int(os.getenv("SUMMARIZE_TOPK", "10" if FAST_MODE else "30"))
MAX_PER_SOURCE = int(os.getenv("MAX_PER_SOURCE", "8" if FAST_MODE else "20"))
CACHE_TTL = int(os.getenv("CACHE_TTL", "600" if FAST_MODE else "0"))

# HTTP 캐시 (선택)
try:
    if CACHE_TTL > 0:
        import requests_cache
        cache_path = os.path.join(PROJECT_ROOT, "data", "http_cache")
        os.makedirs(cache_path, exist_ok=True)
        requests_cache.install_cache(cache_path, expire_after=CACHE_TTL)
except:
    pass

# 전역 세션 구성
SESSION = requests.Session()
retry_config = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.4,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD"],
)
adapter = HTTPAdapter(pool_connections=30, pool_maxsize=30, max_retries=retry_config)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko,en;q=0.9",
})


def GET(url: str, timeout=(3, 8)):
    return SESSION.get(url, timeout=timeout)

# 저장 경로
COMPANY_DIR = os.path.join(PROJECT_ROOT, "data", "company")
os.makedirs(COMPANY_DIR, exist_ok=True)

__all__ = [
    "FAST_MODE",
    "SUMMARIZE_TOPK",
    "MAX_PER_SOURCE",
    "CACHE_TTL",
    "COMPANY_DIR",
    "COMPETITORS",
    "GET",
    "crawl_daum_news",
    "crawl_naver_news",
    "crawl_google_news",
    "crawl_all_sources",
    "extract_key_technologies",
    "extract_differentiation_points",
    "generate_article_summary",
    "generate_company_summary",
    "generate_swot",
    "generate_competitive_comparison",
    "normalize_title",
    "deduplicate_articles",
    "save_articles",
    "load_articles",
    "competitor_analysis",
]

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
        response = GET(url)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "lxml")
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
        response = GET(url)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "lxml")
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
        response = GET(url)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "lxml")
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
        prompt = f"""당신은 IT 업계 전문 분석가입니다.

제목: "{title}"
회사: {company}

위 뉴스 제목을 바탕으로 다음 정보를 2-3문장으로 요약해주세요:

1. **핵심 내용**: 이 뉴스가 다루는 주요 사안
2. **사업적 의미**: {company}의 전략적 관점에서의 중요성
3. **기술/서비스**: 언급된 기술이나 서비스 영역

주의사항:
- 추측이나 가정은 피하고 제목에서 유추 가능한 내용만 서술
- 구체적이고 명확한 문장으로 작성
- {company}의 사업 영역과 연관성 중심으로 분석"""
        
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
        
        prompt = f"""당신은 IT 업계 수석 전략 컨설턴트입니다.

회사: {company}
최근 뉴스 제목들:
{news_list}

위 뉴스들을 종합 분석하여 {company}의 현재 상황을 다음 관점에서 5-7문장으로 서술해주세요:

📊 **분석 관점**:
1. **사업 동향**: 주요 프로젝트, 계약, 파트너십 동향
2. **기술 역량**: AI, 클라우드, 디지털 전환 등 핵심 기술 영역
3. **시장 위치**: 경쟁력, 시장 점유율, 브랜드 파워
4. **성장 전략**: 신규 사업, 해외 진출, M&A 등 확장 전략
5. **재무/조직**: 실적, 투자, 조직 변화

📋 **작성 가이드라인**:
- 각 문장은 구체적인 근거(뉴스 제목)를 포함
- 추측보다는 뉴스에서 확인된 사실 중심으로 서술
- 경쟁사 대비 차별화 포인트 언급
- 시장 트렌드와의 연관성 분석

예시 형식: "{company}는 [구체적 사안]을 통해 [분석 결과]를 보여주고 있으며, 이는 [시장적 의미]를 시사한다."
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
    """SWOT 분석 생성 - 다단계 fallback 전략"""
    
    # 1단계: 기본 검증
    if not client:
        return _create_fallback_swot(company, "LLM 클라이언트 초기화 실패")
    
    if not articles:
        return _create_fallback_swot(company, "뉴스 데이터 부족")
    
    # 2단계: LLM API 호출 시도
    try:
        news_list = "\n".join([f"• {a['title']}" for a in articles[:10]])
        
        prompt = f"""당신은 IT 업계 수석 전략 컨설턴트로서 SWOT 분석 전문가입니다.

회사: {company}
분석 대상 뉴스:
{news_list}

위 뉴스들을 바탕으로 {company}의 전략적 SWOT 분석을 수행해주세요.

📊 **SWOT 분석 가이드라인**:

**강점(Strengths)**: 
- 기술적 우위, 브랜드 파워, 시장 지위, 인력 역량
- 경쟁사 대비 차별화된 강점

**약점(Weaknesses)**:
- 기술적 한계, 시장 점유율 부족, 조직적 제약
- 경쟁사 대비 취약한 영역

**기회(Opportunities)**:
- 신규 시장, 정책 변화, 기술 트렌드, 파트너십 기회
- 성장 가능성이 있는 영역

**위협(Threats)**:
- 경쟁 심화, 기술 변화, 규제 강화, 시장 축소
- 위험 요소들

📋 **출력 형식** (JSON):
{{
  "S": ["강점1 (근거: 뉴스 제목)", "강점2 (근거: 뉴스 제목)", ...],
  "W": ["약점1 (근거: 뉴스 제목)", "약점2 (근거: 뉴스 제목)", ...],
  "O": ["기회1 (근거: 뉴스 제목)", "기회2 (근거: 뉴스 제목)", ...],
  "T": ["위협1 (근거: 뉴스 제목)", "위협2 (근거: 뉴스 제목)", ...]
}}

⚠️ **주의사항**:
- 각 요소별 최대 5개까지만 제시
- 모든 요소에 근거가 되는 뉴스 제목을 괄호 안에 명시
- 뉴스에서 확인되지 않은 추측은 포함하지 마세요
- 구체적이고 실행 가능한 분석을 제공하세요"""
        
        model = os.getenv("AOAI_DEPLOY_GPT4O_MINI", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        result = response.choices[0].message.content.strip()
        
        # JSON 추출 및 검증
        import re
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            swot_data = json.loads(json_match.group())
            # 3단계: 결과 검증
            if _validate_swot_structure(swot_data):
                return swot_data
            else:
                return _create_fallback_swot(company, "LLM 응답 형식 오류")
        
    except Exception as e:
        # 4단계: 예외 발생 시 로깅
        print(f"[SWOT 분석 실패] {company}: {str(e)}")
    
    # 5단계: 최종 fallback
    return _create_fallback_swot(company, "LLM API 호출 실패")


def _create_fallback_swot(company: str, error_reason: str) -> Dict[str, List[str]]:
    """투명한 fallback SWOT 생성 - 기존 데이터 우선 활용"""
    
    # 1단계: 기존 저장된 데이터 확인
    existing_swot = _load_existing_swot(company)
    if existing_swot:
        existing_swot["_fallback"] = True
        existing_swot["_error"] = f"{error_reason} (기존 데이터 사용)"
        existing_swot["_timestamp"] = datetime.now().isoformat()
        return existing_swot
    
    # 2단계: 도메인별 기본 템플릿 활용
    domain_swot = _get_domain_based_swot(company)
    if domain_swot:
        domain_swot["_fallback"] = True
        domain_swot["_error"] = f"{error_reason} (도메인 템플릿 사용)"
        domain_swot["_timestamp"] = datetime.now().isoformat()
        return domain_swot
    
    # 3단계: 최종 투명한 fallback
    return {
        "S": [f"{company} SWOT 분석 불가 - {error_reason}"],
        "W": [f"{company} SWOT 분석 불가 - {error_reason}"],
        "O": [f"{company} SWOT 분석 불가 - {error_reason}"],
        "T": [f"{company} SWOT 분석 불가 - {error_reason}"],
        "_fallback": True,
        "_error": error_reason,
        "_timestamp": datetime.now().isoformat()
    }


def _load_existing_swot(company: str) -> Optional[Dict[str, List[str]]]:
    """기존 저장된 SWOT 데이터 로드"""
    try:
        file_path = os.path.join(COMPANY_DIR, f"{company.lower().replace(' ', '_')}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 최근 분석 결과에서 SWOT 추출
                if isinstance(data, list) and len(data) > 0:
                    latest = data[-1]  # 가장 최근 데이터
                    if "swot" in latest and _validate_swot_structure(latest["swot"]):
                        return latest["swot"]
    except:
        pass
    return None


def _get_domain_based_swot(company: str) -> Optional[Dict[str, List[str]]]:
    """회사명 기반 도메인 템플릿 SWOT"""
    company_lower = company.lower()
    
    # IT 서비스 회사 공통 템플릿
    if any(keyword in company_lower for keyword in ["sds", "cns", "오토에버", "c&c"]):
        return {
            "S": ["IT 인프라 구축 경험", "대기업 그룹 지원"],
            "W": ["높은 프로젝트 비용", "복잡한 의사결정 구조"],
            "O": ["디지털 전환 수요 증가", "AI/클라우드 시장 확대"],
            "T": ["중소기업의 가격 경쟁", "글로벌 IT 기업 진출"]
        }
    
    return None


def _validate_swot_structure(swot_data: Dict) -> bool:
    """SWOT 데이터 구조 검증"""
    required_keys = ["S", "W", "O", "T"]
    
    if not isinstance(swot_data, dict):
        return False
    
    for key in required_keys:
        if key not in swot_data:
            return False
        if not isinstance(swot_data[key], list):
            return False
        if len(swot_data[key]) == 0:
            return False
    
    return True


def generate_competitive_comparison(profiles: Dict[str, Dict]) -> str:
    """경쟁사 간 비교 분석"""
    if not client or len(profiles) < 2:
        return ""
    
    try:
        companies_info = []
        for company, data in profiles.items():
            companies_info.append(f"{company}:\n- {data.get('company_summary', '')[:200]}")
        
        combined = "\n\n".join(companies_info)
        
        prompt = f"""당신은 IT 업계 수석 전략 컨설턴트로서 경쟁 분석 전문가입니다.

분석 대상: 3개 주요 IT 서비스 기업
{combined}

위 3개 기업의 요약을 바탕으로 **경쟁 분석 보고서**를 작성해주세요.

📊 **분석 관점**:
1. **기술 역량**: AI, 클라우드, 디지털 전환 등 핵심 기술 영역별 비교
2. **시장 포지션**: 브랜드 파워, 시장 점유율, 고객 기반
3. **사업 전략**: 주요 프로젝트, 파트너십, 확장 전략
4. **경쟁 우위**: 각 기업의 차별화 포인트와 강점
5. **약점 분석**: 상대적 취약점과 개선 필요 영역

📋 **작성 가이드라인**:
- 각 기업별로 **명확한 차별화 포인트** 제시
- **상대적 비교**: "A사는 B사 대비 ~한 강점을 가짐" 형식
- **구체적 근거**: 각 분석의 근거가 되는 요약 내용 인용
- **실행 가능한 인사이트**: 단순 나열이 아닌 전략적 시사점

출력 형식:
**삼성SDS**: [차별화 포인트 및 강점 분석]
**LG CNS**: [차별화 포인트 및 강점 분석]  
**현대오토에버**: [차별화 포인트 및 강점 분석]
**종합 비교**: [3사 간 상대적 우위/약점 종합 분석]

각 기업별 2-3문장, 종합 비교 2-3문장으로 총 8-12문장 분량으로 작성해주세요."""
        
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
def normalize_title(text: str) -> str:
    return re.sub(r"\W+", "", (text or "").lower())


def deduplicate_articles(articles: List[Dict], existing: List[Dict], threshold: float = 0.92) -> List[Dict]:
    """빠른 중복 제거 (유사도는 후보에만 적용)"""
    seen_titles = {normalize_title(a.get("title", "")) for a in existing}
    seen_urls = {a.get("url", "") for a in existing}
    uniques = []
    candidates = []

    for article in articles:
        title = article.get("title", "")
        t_norm = normalize_title(title)
        url = article.get("url", "")

        if not t_norm:
            continue
        if t_norm in seen_titles:
            continue
        if url and url in seen_urls:
            continue

        if len(t_norm) > 20:
            uniques.append(article)
            seen_titles.add(t_norm)
            if url:
                seen_urls.add(url)
        else:
            candidates.append(article)

    if candidates:
        from difflib import SequenceMatcher

        existing_titles = [a.get("title", "") for a in existing] + [u.get("title", "") for u in uniques]
        for article in candidates:
            title = article.get("title", "")
            if not title:
                continue
            if any(SequenceMatcher(None, title, e_title).ratio() >= threshold for e_title in existing_titles):
                continue
            uniques.append(article)
            existing_titles.append(title)

    return uniques


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
    new_articles = deduplicate_articles(articles, existing)
    
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
    def process_company(company: str, update_data_local: bool) -> Dict[str, Any]:
        print(f"  → {company}")
        articles = []

        if update_data_local:
            crawled = crawl_all_sources(company, max_per_source=MAX_PER_SOURCE, use_parallel=True)
            print(f"    → 총 {len(crawled)}개 수집")

            existing_articles = load_articles(company)
            existing_map = {normalize_title(a.get("title", "")): a for a in existing_articles}

            to_summarize = []
            summarized = []

            for article in crawled:
                title_key = normalize_title(article.get("title", ""))
                existing = existing_map.get(title_key)
                if existing and existing.get("summary"):
                    article["summary"] = existing.get("summary")
                    summarized.append(article)
                else:
                    to_summarize.append(article)

            if to_summarize and client:
                limit = min(len(to_summarize), SUMMARIZE_TOPK)
                need_summary = to_summarize[:limit]
                remaining = to_summarize[limit:]

                def add_summary(article):
                    article["summary"] = generate_article_summary(article["title"], company)
                    return article

                with ThreadPoolExecutor(max_workers=4) as executor:
                    summarized.extend(executor.map(add_summary, need_summary))

                summarized.extend(remaining)
            else:
                summarized.extend(to_summarize)

            articles = summarized
            save_articles(company, articles)
        else:
            print("    → 이전 저장 데이터 사용")
            articles = load_articles(company)

        if not articles:
            print(f"  ⚠️ {company}: 데이터 없음")
            return {}

        swot = generate_swot(company, articles)
        recent_news = [{
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "source": article.get("source", ""),
            "summary": article.get("summary", "")
        } for article in articles[:5]]

        profile = {
            "recent_news": recent_news,
            "company_summary": generate_company_summary(company, articles),
            "swot": swot,
            "key_technologies": extract_key_technologies(articles),
            "differentiation_points": extract_differentiation_points(company, swot),
            "total_articles": len(articles)
        }

        print(f"  ✅ {company}: {len(articles)}개 기사 분석 완료")
        return profile

    if update_data:
        print("[1/3] 최신 뉴스 크롤링 (다음/네이버/구글, 병렬 처리)...")
    else:
        print("[1/3] 기존 데이터 사용 (크롤링 스킵)")

    print("\n[2/3] 데이터 분석 중...")
    profiles = {}

    with ThreadPoolExecutor(max_workers=len(COMPETITORS)) as executor:
        futures = {
            executor.submit(process_company, company, update_data): company
            for company in COMPETITORS
        }

        for future in as_completed(futures):
            company = futures[future]
            try:
                profile = future.result()
                if profile:
                    profiles[company] = profile
            except Exception as exc:
                print(f"  ⚠️ {company}: 처리 실패 ({exc})")
    
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
