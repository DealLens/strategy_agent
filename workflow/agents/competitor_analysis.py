import os
import time
import json
import math
import requests
from requests.adapters import HTTPAdapter, Retry
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from glob import glob
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.tools import tool
from openai import OpenAI

# =========================
# 0) 환경/클라이언트 초기화
# =========================
try:
    from dotenv import load_dotenv
    CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "..", ".."))
    env_path = os.path.join(PROJECT_ROOT, ".env")
    load_dotenv(env_path)
    print(f"[ENV] .env loaded: {os.path.exists(env_path)} -> {env_path}")
except Exception:
    pass

# OpenAI / Azure OpenAI
client = None
try:
    aoai_endpoint = os.getenv("AOAI_ENDPOINT")
    aoai_api_key = os.getenv("AOAI_API_KEY")
    if aoai_endpoint and aoai_api_key:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=aoai_api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=aoai_endpoint,
        )
        print("[OK] Azure OpenAI client ready")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            client = OpenAI(api_key=api_key)
            print("[OK] OpenAI client ready")
        else:
            print("[WARN] No API key for OpenAI/AzureOpenAI -> summaries disabled")
except Exception as e:
    print(f"[ERR] OpenAI client init failed: {e}")
    client = None

# 저장 디렉토리
DEFAULT_DIRS = [
    os.getenv("COMPETITOR_DIR"),
    os.path.join(PROJECT_ROOT, "data", "company"),
    r"C:\GIT\strategy_agent\data\company",
    os.path.join(os.getcwd(), "data", "company"),
]
COMPANY_DIR = next((d for d in DEFAULT_DIRS if d and os.path.isdir(d)), None)
if not COMPANY_DIR:
    COMPANY_DIR = DEFAULT_DIRS[1]
    os.makedirs(COMPANY_DIR, exist_ok=True)

# =========================
# 1) 검색어 alias
# =========================
KEYWORD_ALIASES = {
    "현대오토에버": ["현대오토에버", "현대 오토에버", "Hyundai AutoEver", "Hyundai Autoever", "현대오토에버(주)", "(주)현대오토에버"],
    "현대 오토에버": ["현대오토에버", "현대 오토에버", "Hyundai AutoEver", "Hyundai Autoever", "현대오토에버(주)", "(주)현대오토에버"],
    "삼성SDS": ["삼성SDS", "삼성 SDS", "Samsung SDS"],
    "LG CNS": ["LG CNS", "엘지 CNS", "엘지씨엔에스", "LGCNS", "lg cns"],
}


def get_queries_for_company(company: str) -> List[str]:
    name = company.strip()
    if name in KEYWORD_ALIASES:
        return list(dict.fromkeys(KEYWORD_ALIASES[name]))
    cands = [name]
    if " " in name:
        cands.append(name.replace(" ", ""))
    return list(dict.fromkeys(cands))

# =========================
# 2) 공통 유틸
# =========================
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SESSION = requests.Session()
retry_strategy = Retry(total=3, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504])
SESSION.mount("https://", HTTPAdapter(max_retries=retry_strategy))
SESSION.mount("http://", HTTPAdapter(max_retries=retry_strategy))
SESSION.headers.update(UA)

def fetch_article_content(url: str, timeout: float = 7.0) -> str:
    try:
        res = SESSION.get(url, timeout=timeout)
        if res.status_code != 200:
            return ""
        soup = BeautifulSoup(res.text, "html.parser")
        paragraphs = [p.get_text(strip=True) for p in soup.select("p")]
        return " ".join(paragraphs)[:5000]
    except Exception:
        return ""

def summarize_with_openai(text: str, company: str) -> str:
    if not client or not text.strip():
        return ""
    prompt = f"""
아래는 {company} 관련 기사 내용입니다.
핵심만 3~4문장으로, 한국어로 전문가에게 제공할 수 있는 톤으로 요약해 주세요.

기사:
{text}
"""
    try:
        model_name = os.getenv("AOAI_DEPLOY_GPT4O_MINI", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[SUM ERR] {str(e)[:120]}")
        return ""

def deduplicate_by_title(
    articles: List[Dict[str, Any]], existing_titles: List[str], threshold: float = 0.9
) -> List[Dict[str, Any]]:
    out = []
    for it in articles:
        t = (it.get("title") or "").strip()
        if not t:
            continue
        if any(SequenceMatcher(None, t, old).ratio() >= threshold for old in existing_titles):
            continue
        out.append(it)
        existing_titles.append(t)
    return out


def load_existing_articles(path: str) -> List[Dict[str, Any]]:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_articles(path: str, items: List[Dict[str, Any]]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _slugify_company(company: str) -> str:
    return company.lower().replace(" ", "_")



def _state_file_path(company: str) -> str:
    return os.path.join(COMPANY_DIR, f"{_slugify_company(company)}_state.json")


def load_crawl_state(company: str) -> Dict[str, Any]:
    path = _state_file_path(company)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_crawl_state(company: str, state: Dict[str, Any]):
    path = _state_file_path(company)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] failed to persist state for {company}: {e}")

# =========================
# 3) 소스별 크롤러 (단일 쿼리)
# =========================
def crawl_daum(query: str, max_articles: int = 20) -> List[Dict[str, Any]]:
    url = f"https://search.daum.net/search?w=news&q={query}"
    try:
        res = SESSION.get(url, timeout=10)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.text, "html.parser")
        items = []
        for a in soup.select("a[href*='v.daum.net']")[:max_articles]:
            href = a.get("href", "")
            if not href or "v.daum.net" not in href:
                continue
            title = a.get("title") or a.get_text(strip=True)
            if title:
                items.append({"title": title, "url": href, "source": "다음 뉴스"})
        return items
    except Exception:
        return []

def crawl_naver(query: str, max_articles: int = 20) -> List[Dict[str, Any]]:
    url = f"https://search.naver.com/search.naver?where=news&query={query}"
    try:
        res = SESSION.get(url, timeout=10)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.text, "html.parser")
        items = []
        for selector in ["a.news_tit", "a[href*='news.naver']"]:
            links = soup.select(selector)
            if not links:
                continue
            for a in links[:max_articles]:
                href = a.get("href", "")
                if not href or "news.naver.com" not in href:
                    continue
                title = a.get("title") or a.get_text(strip=True)
                if title:
                    items.append({"title": title, "url": href, "source": "네이버 뉴스"})
                if len(items) >= max_articles:
                    break
            if items:
                break
        return items
    except Exception:
        return []

def _normalize_google_href(href: str) -> str:
    if not href:
        return ""
    if href.startswith("/url?"):
        qs = parse_qs(urlparse(href).query)
        return qs.get("q", [""])[0]
    return href

def crawl_google(query: str, max_articles: int = 20, pages: int = 5) -> List[Dict[str, Any]]:
    news_domains = [
        'news.', '.news', 'naver.com', 'daum.net',
        'chosun.com', 'joins.com', 'donga.com', 'mk.co.kr',
        'hankyung.com', 'khan.co.kr', 'hani.co.kr', 'sedaily.com',
        'etnews.com', 'zdnet.co.kr', 'inews24.com', 'dt.co.kr',
        'news1.kr', 'newsis.com', 'yna.co.kr', 'yonhapnews.co.kr',
        'einfomax.co.kr', 'newstomato.com', 'fnnews.com', 'biz.chosun.com',
        'nate.com', 'heraldcorp.com', 'edaily.co.kr'
    ]

    items, seen = [], set()
    for page in range(pages):
        if len(items) >= max_articles:
            break
        start = page * 10
        url = f"https://www.google.com/search?q={query}&tbm=nws&hl=ko&start={start}"
        try:
            res = SESSION.get(url, timeout=10)
            if res.status_code != 200:
                continue
            text_lower = res.text.lower()
            if "captcha" in text_lower or "unusual traffic" in text_lower:
                print("[WARN] Google blocked (captcha)")
                break
            soup = BeautifulSoup(res.text, "html.parser")
            # 핵심 뉴스 카드 선택
            cards = soup.select("div.SoaBEf") or soup.select("div.dbsr") or []
            for card in cards:
                if len(items) >= max_articles:
                    break
                link_tag = card.find("a", href=True)
                if not link_tag:
                    continue
                href = _normalize_google_href(link_tag.get("href"))
                if not href:
                    continue
                if not any(domain in href.lower() for domain in news_domains):
                    continue
                if href in seen:
                    continue
                title_tag = card.find("div", class_="n0jPhd") or card.find("div", class_="JheGif")
                title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)
                if not title or len(title) < 8:
                    continue
                seen.add(href)
                items.append({"title": title, "url": href, "source": "구글 뉴스"})
        except Exception:
            continue
        # 페이지 간 대기 (차단 방지)
        time.sleep(0.6)
    return items

# =========================
# 4) 배치 실행 헬퍼
# =========================
def batched(seq: List[Any], size: int) -> List[List[Any]]:
    for i in range(0, len(seq), size):
        yield seq[i:i+size]

def run_crawl_tasks_in_batches(
    tasks: List[Tuple[str, str, int]],
    max_workers: int = 6,
    batch_size: int = 9,
    pause: float = 1.5,
) -> List[Dict[str, Any]]:
    """
    tasks: [(source, query, max_articles), ...]
    source in {"daum","naver","google"}
    """
    results: List[Dict[str, Any]] = []

    def _worker(source: str, query: str, limit: int) -> List[Dict[str, Any]]:
        if source == "daum":
            return crawl_daum(query, limit)
        if source == "naver":
            return crawl_naver(query, limit)
        if source == "google":
            return crawl_google(query, limit)
        return []

    for batch in batched(tasks, batch_size):
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_worker, s, q, m): (s, q) for (s, q, m) in batch}
            for fut in as_completed(futs):
                try:
                    items = fut.result() or []
                    results.extend(items)
                except Exception:
                    pass
        if pause > 0:
            time.sleep(pause)
    return results

def summarize_many_in_batches(
    items: List[Dict[str, Any]],
    company: str,
    max_workers: int = 4,
    batch_size: int = 8,
    pause: float = 2.0,
):
    """
    items: 각 item에 'description'(원문 일부)과 'summary'를 채워 넣음
    """
    if not client:
        for it in items:
            it["summary"] = ""
        return

    def _worker(text: str) -> str:
        return summarize_with_openai(text, company)

    targets = [(i, it) for i, it in enumerate(items) if (it.get("description") or "").strip()]

    for batch in batched(targets, batch_size):
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(_worker, it["description"]): idx for idx, it in batch}
            for fut in as_completed(futs):
                idx = futs[fut]
                try:
                    items[idx]["summary"] = fut.result() or ""
                except Exception:
                    items[idx]["summary"] = ""
        if pause > 0:
            time.sleep(pause)

# =========================
# 5) 통합 크롤러 (병렬+배치)
# =========================
def crawl_and_save(
    company: str,
    max_articles: int = 20,
    threshold: float = 0.9,
    crawl_workers: int = 6,
    crawl_batch_size: int = 9,
    crawl_pause: float = 1.0,
    fetch_workers: int = 8,
    summary_workers: int = 4,
    summary_batch_size: int = 8,
    summary_pause: float = 1.5,
) -> List[Dict[str, Any]]:
    """
    전체 파이프라인(크롤링→중복제거→본문수집→요약→저장) 병렬/배치 구성 + 증분 업데이트.
    """
    file_path = os.path.join(COMPANY_DIR, f"{_slugify_company(company)}.json")
    existing = load_existing_articles(file_path)
    existing_titles = [a.get("title", "") for a in existing]

    state = load_crawl_state(company)
    last_crawled_iso = state.get("last_crawled_at")
    last_crawled_dt = None
    if last_crawled_iso:
        try:
            last_crawled_dt = datetime.fromisoformat(last_crawled_iso)
        except Exception:
            last_crawled_dt = None

    queries = get_queries_for_company(company)
    print(f"\n[CRAWL] {company} → queries={queries}")

    task_list: List[Tuple[str, str, int]] = []
    for q in queries:
        task_list += [("daum", q, max_articles), ("naver", q, max_articles), ("google", q, max_articles)]

    candidates = run_crawl_tasks_in_batches(
        tasks=task_list,
        max_workers=crawl_workers,
        batch_size=crawl_batch_size,
        pause=crawl_pause,
    )
    for it in candidates:
        it["company"] = company
    print(f"[CRAWL] candidates={len(candidates)}")

    new_articles = deduplicate_by_title(candidates, existing_titles, threshold)

    if last_crawled_dt:
        filtered = []
        for item in new_articles:
            ts_str = item.get("published_at") or item.get("crawled_at")
            if not ts_str:
                filtered.append(item)
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
            except Exception:
                filtered.append(item)
                continue
            if ts > last_crawled_dt:
                filtered.append(item)
        if len(filtered) != len(new_articles):
            print(f"[CRAWL] filtered by last_crawled_at -> {len(filtered)}/{len(new_articles)}")
        new_articles = filtered

    if not new_articles:
        print("[CRAWL] 신규 기사 없음")
        return existing
    print(f"[CRAWL] dedup -> new={len(new_articles)}")

    urls = [it["url"] for it in new_articles]
    print("[FETCH] fetching contents (parallel)...")
    url_to_content: Dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=fetch_workers) as ex:
        futs = {ex.submit(fetch_article_content, u): u for u in urls}
        for fut in as_completed(futs):
            u = futs[fut]
            try:
                url_to_content[u] = fut.result() or ""
            except Exception:
                url_to_content[u] = ""
    collected = sum(1 for c in url_to_content.values() if c)
    print(f"[FETCH] collected={collected}/{len(new_articles)}")

    now_iso = datetime.now().isoformat()
    for it in new_articles:
        content = url_to_content.get(it["url"], "")
        it["description"] = content[:200] if content else ""
        it["summary"] = ""
        it["crawled_at"] = now_iso

    print("[SUM] summarizing (parallel + batch)...")
    summarize_many_in_batches(
        new_articles, company,
        max_workers=summary_workers,
        batch_size=summary_batch_size,
        pause=summary_pause,
    )
    sum_count = sum(1 for it in new_articles if it.get("summary"))
    print(f"[SUM] done -> {sum_count}/{len(new_articles)}")

    combined = new_articles + existing
    combined.sort(key=lambda x: x.get("crawled_at", ""), reverse=True)
    save_articles(file_path, combined)
    print(f"[SAVE] {file_path} | new={len(new_articles)} total={len(combined)}")

    save_crawl_state(company, {"last_crawled_at": now_iso})
    print(f"[STATE] last_crawled_at updated -> {now_iso}")

    return combined

# =========================
# 6) 분석 도구
# =========================
@tool
def competitor_analysis(companies: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    경쟁사 뉴스 JSON 데이터를 읽어 최신 뉴스/요약과 SWOT(placeholder)을 제공합니다.
    
    Args:
        companies: 분석할 회사 리스트(없으면 폴더 내 전체)
    
    Returns:
        {"competitor_profiles": { 회사명: { "recent_news": [...], "summaries": [...], "swot": {...} } }}
    """
    if not COMPANY_DIR:
        return {"competitor_profiles": {}, "error": "COMPANY_DIR 없음"}

    # ✅ 기본값: 3사만
    if not companies:
        companies = ["삼성 SDS", "LG CNS", "현대오토에버"]

    json_files = glob(os.path.join(COMPANY_DIR, "*.json"))
    if not json_files:
        return {"competitor_profiles": {}, "error": f"JSON 파일이 없습니다: {COMPANY_DIR}"}

    profiles: Dict[str, Dict[str, Any]] = {}
    for path in json_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        for item in data:
            comp = item.get("company")
            if not comp:
                continue
            if companies and comp not in companies:
                continue
            p = profiles.setdefault(comp, {
                "recent_news": [],
                "summaries": [],
                "swot": {"S": "TBD", "W": "TBD", "O": "TBD", "T": "TBD"},
            })
            p["recent_news"].append(item)
            if item.get("summary"):
                p["summaries"].append(item["summary"])

    for comp in profiles:
        profiles[comp]["recent_news"] = profiles[comp]["recent_news"][:5]

    return {"competitor_profiles": profiles}

# =========================
# 7) 단독 실행
# =========================
if __name__ == "__main__":
    companies = ["삼성SDS", "LG CNS", "현대오토에버"]
    for c in companies:
        crawl_and_save(
            c,
            max_articles=20,
            threshold=0.9,
            crawl_workers=6,
            crawl_batch_size=9,
            crawl_pause=1.0,
            fetch_workers=8,
            summary_workers=4,
            summary_batch_size=8,
            summary_pause=1.5,
        )

    result = competitor_analysis.invoke({})
    print("companies analyzed:", list(result.get("competitor_profiles", {}).keys()))
