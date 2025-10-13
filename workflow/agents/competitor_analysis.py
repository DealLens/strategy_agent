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
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except:
    PROJECT_ROOT = os.getcwd()

# =========================
# 통합 LLM 클라이언트 사용
# =========================
# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.llm_client import get_llm_client, is_llm_available, call_llm, parse_json_response

llm_client = get_llm_client()

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
    """개별 기사 요약 (구체적 정보 추출)"""
    if not is_llm_available() or not title:
        return ""
    
    try:
        prompt = f"""
{company}의 뉴스 제목: "{title}"

이 뉴스를 분석하여 다음 정보를 포함한 2-3문장 요약을 작성하라:
- 구체적인 기술명/제품명/서비스명
- 사업 규모, 금액, 수치 (있다면)
- 핵심 성과나 특징

예시: "LG CNS가 자체 개발한 생성형 AI 플랫폼 'EXAONE'을 공개. 한국어 처리 정확도 95%로 업계 최고 수준. 공공/금융 분야 12개 프로젝트에 적용 예정"

요약:"""
        
        result = call_llm(prompt, temperature=0.3, max_tokens=200, use_secondary=True)
        return result.strip() if result else ""
    except:
        return ""


def generate_company_summary(company: str, articles: List[Dict]) -> str:
    """기업 전체 종합 서머리 (구체적 정보 포함)"""
    if not is_llm_available() or not articles:
        return f"{company}의 최근 활동 정보가 부족합니다."
    
    try:
        # 제목 + 요약 함께 제공
        news_details = []
        for i, a in enumerate(articles[:10], 1):
            title = a.get('title', '')
            summary = a.get('summary', '')
            
            if summary and len(summary) > 10:
                summary_short = summary[:150] + "..." if len(summary) > 150 else summary
                news_details.append(f"{i}. {title}\n   → {summary_short}")
            else:
                news_details.append(f"{i}. {title}")
        
        news_text = "\n\n".join(news_details)
        
        prompt = f"""
{company}의 최근 뉴스와 활동:

{news_text}

위 내용을 분석하여 {company}의 현황을 다음 관점에서 5-7문장으로 요약하라:

1. 핵심 사업 분야 및 주력 기술/솔루션 (구체적 제품명 포함)
2. 최근 성과 및 프로젝트 (규모, 수치 포함)
3. 기술 경쟁력 및 차별화 포인트
4. 시장 위치 및 경쟁 상황

⚠️ 추상적 표현 금지. 구체적인 기술명, 제품명, 수치를 반드시 포함하라.
"""
        
        result = call_llm(prompt, temperature=0.3, max_tokens=800, use_secondary=True)
        return result or f"{company}는 다양한 IT 서비스 분야에서 활동 중입니다."
    except:
        return f"{company}는 다양한 IT 서비스 분야에서 활동 중입니다."


def generate_swot(company: str, articles: List[Dict]) -> Dict[str, List[str]]:
    """SWOT 분석 생성 (뉴스 제목 + 요약 활용, 구체적 분석)"""
    if not is_llm_available() or not articles:
        return {"S": ["정보 부족"], "W": ["정보 부족"], "O": ["정보 부족"], "T": ["정보 부족"]}
    
    try:
        # 뉴스 제목 + 요약을 함께 제공 (최대 15개)
        news_details = []
        for i, a in enumerate(articles[:15], 1):
            title = a.get('title', '제목 없음')
            summary = a.get('summary', '')
            
            # 요약이 있으면 제목 + 요약, 없으면 제목만
            if summary and len(summary) > 10:
                # 요약을 200자로 제한
                summary_short = summary[:200] + "..." if len(summary) > 200 else summary
                news_details.append(f"{i}. {title}\n   📄 {summary_short}")
            else:
                news_details.append(f"{i}. {title}")
        
        news_text = "\n\n".join(news_details)
        
        prompt = f"""
너는 IT 업계 전문 분석가다.
{company}의 최근 뉴스와 활동 내용을 분석하여 상세한 SWOT 분석을 수행하라.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[{company} 최근 뉴스 및 활동]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{news_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 SWOT 분석 작성 가이드:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

위 뉴스에서 실제로 언급된 내용을 기반으로 구체적으로 작성하라:

✅ S (Strengths - 강점): 4-6개
   - 실제 기술명, 제품명, 솔루션명 명시
   - 사업 규모, 매출, 시장 점유율 등 수치 포함
   - 예: "Brightics AI 플랫폼으로 데이터 분석 시장 점유율 35%"
   
✅ W (Weaknesses - 약점): 3-5개
   - 구체적인 문제점 (비용, 속도, 인력, 기술 한계 등)
   - 예: "클라우드 구축 비용이 경쟁사 대비 25% 높음"
   
✅ O (Opportunities - 기회): 3-5개
   - 시장 트렌드, 정부 정책, 산업 변화
   - 예: "AI 규제 강화로 보안 솔루션 수요 급증"
   
✅ T (Threats - 위협): 3-5개
   - 경쟁 상황, 시장 변화, 리스크
   - 예: "네이버클라우드의 공격적 가격 정책"

⚠️ 중요:
- 추상적 표현 금지 (예: "우수한 기술력" ❌ → "GPT-4 기반 AI 챗봇 정확도 92%" ✅)
- 반드시 위 뉴스에서 언급된 실제 내용 활용
- 기술명/제품명/사업명을 구체적으로 명시

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
출력 형식 (JSON만 반환):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
  "S": [
    "구체적 강점 1 (기술명/제품명 포함)",
    "구체적 강점 2 (수치 포함)",
    "구체적 강점 3",
    "구체적 강점 4"
  ],
  "W": [
    "구체적 약점 1 (수치/비교 포함)",
    "구체적 약점 2",
    "구체적 약점 3"
  ],
  "O": [
    "구체적 기회 1 (시장/트렌드)",
    "구체적 기회 2",
    "구체적 기회 3"
  ],
  "T": [
    "구체적 위협 1 (경쟁사/리스크)",
    "구체적 위협 2",
    "구체적 위협 3"
  ]
}}

지금 즉시 위 형식의 JSON만 생성하라!
"""
        
        result = call_llm(prompt, temperature=0.4, max_tokens=3000, use_secondary=True)
        
        if result:
            # 개선된 JSON 파싱 로직 사용
            swot_data = parse_json_response(result)
            if swot_data and _validate_swot_data(swot_data):
                print(f"  ✅ {company} SWOT: S={len(swot_data.get('S', []))}개, W={len(swot_data.get('W', []))}개, O={len(swot_data.get('O', []))}개, T={len(swot_data.get('T', []))}개")
                return swot_data
    except Exception as e:
        print(f"  ⚠️ {company} SWOT 생성 실패: {e}")
    
    # Fallback
    return {
        "S": ["프로젝트 수주 역량", "기술 인프라"],
        "W": ["높은 비용"],
        "O": ["디지털 전환 수요"],
        "T": ["경쟁 심화"]
    }


def _validate_swot_data(data: Dict[str, Any]) -> bool:
    """SWOT 데이터 유효성 검증"""
    required_keys = ["S", "W", "O", "T"]
    return all(key in data and isinstance(data[key], list) for key in required_keys)


def generate_competitive_comparison(profiles: Dict[str, Dict]) -> str:
    """경쟁사 간 비교 분석"""
    if not is_llm_available() or len(profiles) < 2:
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
        
        result = call_llm(prompt, temperature=0.3, use_secondary=True)
        return result or ""
    except:
        return ""


@tool
def generate_competitive_strategy(skax_profile: dict, competitors: list) -> list:
    """
    자사 및 경쟁사 데이터를 기반으로 대응 전략 생성 (각 경쟁사별 2개씩: 강점 대응 + 약점 활용)
    
    반환 형식: [{"company": "경쟁사명", "counter": "대응전략"}, ...]
    """
    
    # 경쟁사 SWOT을 구조화된 텍스트로 변환
    competitors_text = []
    for comp in competitors:
        company = comp.get("company", "")
        swot = comp.get("swot", {})
        
        s_list = swot.get("S", [])
        w_list = swot.get("W", [])
        
        comp_text = f"""
[{company}]
강점(S):
{chr(10).join([f"  - {s}" for s in s_list[:5]])}

약점(W):
{chr(10).join([f"  - {w}" for w in w_list[:5]])}
"""
        competitors_text.append(comp_text)
    
    competitors_str = "\n".join(competitors_text)
    
    prompt = f"""
🚨🚨🚨 CRITICAL: 각 경쟁사당 정확히 2개씩 (강점 대응 1개 + 약점 활용 1개) 총 6개 전략을 반드시 생성하라! 🚨🚨🚨

너는 SK AX의 전략 컨설턴트다.
아래 자사 역량과 경쟁사 SWOT을 분석하여 각 경쟁사별 대응전략 2개씩을 작성하라.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SK AX 핵심 역량]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 생성형 AI 및 LLM 솔루션 (AI 코딩 어시스턴트)
• 클라우드 인프라 구축 (하이브리드/프라이빗/퍼블릭)
• 스마트 팩토리 (I-FACTs MCS)
• 데이터 분석 플랫폼 (AccuInsight+, DataRobot AutoML)
• 네트워크 이중화 (이중화 전자패치 IFS)
• End-to-End 프로젝트 수행

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[경쟁사 SWOT 분석]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{competitors_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 작성 규칙 (반드시 준수!)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣ 각 경쟁사당 정확히 2개 작성:
   - 첫 번째: "💪 강점 대응:" 으로 시작 (경쟁사의 강점에 대한 대응)
   - 두 번째: "⚠️ 약점 활용:" 으로 시작 (경쟁사의 약점을 활용한 차별화)

2️⃣ 각 전략은 2-3문장으로 구성:
   - 경쟁사의 실제 강점/약점 명시
   - SK AX의 구체적 솔루션명 활용
   - 정량적 수치 포함 (예: 30% 절감, 40% 향상)

3️⃣ 반드시 위 SWOT의 실제 내용 기반으로 작성

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
출력 형식 예시:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[
  {{
    "company": "삼성SDS",
    "counter": "💪 강점 대응: 삼성SDS의 Brightics AI 플랫폼 데이터 분석 역량 → SK AX는 AccuInsight+와 DataRobot AutoML 통합으로 모델 개발 자동화율 45% 향상 + 분석 시간 50% 단축하여 대응. 중소기업 시장에서 접근성과 비용 효율성으로 차별화."
  }},
  {{
    "company": "삼성SDS",
    "counter": "⚠️ 약점 활용: 삼성SDS의 높은 초기 구축 비용과 복잡한 의사결정 구조 → SK AX는 하이브리드 클라우드로 초기 투자 35% 절감 + 신속한 의사결정으로 프로젝트 착수 기간 40% 단축. 유연한 과금 모델로 중견기업 공략."
  }},
  {{
    "company": "LG CNS",
    "counter": "💪 강점 대응: (위 SWOT의 LG CNS 강점 기반으로 구체적 작성)"
  }},
  {{
    "company": "LG CNS",
    "counter": "⚠️ 약점 활용: (위 SWOT의 LG CNS 약점 기반으로 구체적 작성)"
  }},
  {{
    "company": "현대오토에버",
    "counter": "💪 강점 대응: (위 SWOT의 현대오토에버 강점 기반으로 구체적 작성)"
  }},
  {{
    "company": "현대오토에버",
    "counter": "⚠️ 약점 활용: (위 SWOT의 현대오토에버 약점 기반으로 구체적 작성)"
  }}
]

🚨 주의: 순수 JSON 배열만 출력! 설명/마크다운 제외!
🚨 필수: 총 6개 항목 (각 경쟁사당 2개씩)!
"""
    
    print(f"  🔥 경쟁사 대응 전략 생성 중... (경쟁사: {len(competitors)}개)")
    response = call_llm(prompt, temperature=0.6, max_tokens=5000)
    
    # 디버깅: LLM 응답 확인
    if not response:
        print(f"    ❌ LLM 응답 없음!")
        return []
    
    print(f"    📝 LLM 응답 길이: {len(response)} 문자")
    print(f"    📝 LLM 응답 미리보기: {response[:200]}...")
    
    parsed = parse_json_response(response)
    
    if not parsed:
        print(f"    ❌ JSON 파싱 실패!")
        print(f"    원본 응답:\n{response[:500]}...")
        return []
    
    print(f"    ✅ JSON 파싱 성공, 타입: {type(parsed)}")
    if isinstance(parsed, list):
        print(f"    ✅ 파싱된 항목 수: {len(parsed)}")
    
    # 유효한 경쟁사 리스트
    valid_companies = {comp.get("company", "") for comp in competitors}
    
    # 형식 검증 및 보정
    result = []
    
    if isinstance(parsed, list):
        print(f"    🔍 검증 시작: {len(parsed)}개 항목 검사")
        for i, item in enumerate(parsed, 1):
            print(f"      [{i}] 검사 중...")
            
            if not isinstance(item, dict):
                print(f"        ❌ dict가 아님: {type(item)}")
                continue
                
            company = item.get("company", "")
            counter = item.get("counter", "")
            
            print(f"        company: '{company[:30]}...' ({len(company)}자)")
            print(f"        counter: '{counter[:50]}...' ({len(counter)}자)")
            
            # 검증: 키 이름이 값으로 들어간 경우 제거
            if company.lower() in ["company", "counter", "경쟁사", "경쟁사명"]:
                print(f"        ❌ 무효한 company명: '{company}'")
                continue
            
            # 검증: counter가 너무 짧거나 메타데이터인 경우
            if len(counter) < 20:  # 최소 20자
                print(f"        ❌ 전략이 너무 짧음: {len(counter)}자 < 20자")
                continue
            
            # 검증: company가 실제 경쟁사 목록에 있는지
            if valid_companies and company not in valid_companies:
                print(f"        ⚠️ 알 수 없는 경쟁사: '{company}'")
                print(f"        유효한 경쟁사: {valid_companies}")
                # 그래도 추가 (오타 가능성)
            
            print(f"        ✅ 통과!")
            result.append({"company": company, "counter": counter})
    
    elif isinstance(parsed, dict):
        print(f"    🔍 dict 형식 감지, 변환 시작...")
        # dict를 list로 변환
        for company, strategies in parsed.items():
            print(f"      키: '{company}'")
            
            # 키가 메타데이터인 경우 스킵
            if company.lower() in ["company", "counter", "경쟁사"]:
                print(f"        ❌ 메타데이터 키 스킵")
                continue
                
            if isinstance(strategies, list):
                print(f"        strategies는 list: {len(strategies)}개")
                for strategy in strategies:
                    if isinstance(strategy, str) and len(strategy) >= 20:
                        result.append({"company": company, "counter": strategy})
                        print(f"          ✅ 추가: {strategy[:50]}...")
            else:
                strategy_text = str(strategies)
                print(f"        strategies는 {type(strategies)}: {len(strategy_text)}자")
                if len(strategy_text) >= 20:
                    result.append({"company": company, "counter": strategy_text})
                    print(f"          ✅ 추가: {strategy_text[:50]}...")
    
    else:
        print(f"    ❌ 예상치 못한 응답 형식: {type(parsed)}")
    
    # 각 경쟁사당 개수 확인
    company_counts = {}
    for item in result:
        company = item.get("company", "")
        company_counts[company] = company_counts.get(company, 0) + 1
    
    print(f"  ✅ 생성된 전략: {len(result)}개")
    for company, count in company_counts.items():
        emoji = "✅" if count >= 2 else "⚠️"
        print(f"    {emoji} {company}: {count}개")
    
    # 경고: 각 경쟁사당 2개 미만인 경우
    for company in valid_companies:
        if company_counts.get(company, 0) < 2:
            print(f"    ⚠️⚠️ {company}에 대한 전략이 {company_counts.get(company, 0)}개만 생성됨 (2개 필요)")
    
    return result


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
