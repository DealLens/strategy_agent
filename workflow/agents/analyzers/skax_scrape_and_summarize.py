# skax_scrape_and_summarize.py
import re
import time
import hashlib
import logging
import os
import sqlite3
from urllib.parse import urljoin
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from playwright.sync_api import sync_playwright

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv("app/.env")  # app/.env 파일 로드
    print("✅ app/.env 파일 로드 완료")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않았습니다.")
except Exception as e:
    print(f"⚠️ .env 파일 로드 실패: {e}")

# RAG 관련 imports
try:
    from langchain_core.tools import tool
    from langchain_openai import AzureOpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("Warning: RAG dependencies not available. Install langchain packages for RAG functionality.")

# 로깅 설정 (기본적으로 콘솔만, 파일 로깅은 선택적)
def setup_logging(enable_file_logging: bool = False):
    """로깅 설정을 초기화"""
    handlers = [logging.StreamHandler()]
    
    if enable_file_logging:
        handlers.append(logging.FileHandler('skax_scraper.log'))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True  # 기존 설정 덮어쓰기
    )
    return logging.getLogger(__name__)

# 기본 로거 설정 (파일 로깅 없음)
logger = setup_logging(False)

@dataclass
class Config:
    """설정값들을 관리하는 클래스"""
    base_url: str = os.getenv("SKAX_BASE_URL", "https://www.skax.co.kr/case-study/storys")
    domain: str = os.getenv("SKAX_DOMAIN", "https://www.skax.co.kr")
    max_posts: int = int(os.getenv("MAX_POSTS", "200"))
    headless: bool = os.getenv("HEADLESS", "true").lower() == "true"
    csv_output: str = os.getenv("CSV_OUTPUT", "skax_case_studies.csv")
    db_output: str = os.getenv("DB_OUTPUT", "skax_case_studies.db")
    enable_file_logging: bool = os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true"

class Constants:
    """상수값들을 관리하는 클래스"""
    PAGE_LOAD_TIMEOUT = 2000
    MAX_CONTENT_LENGTH = 120000
    MIN_CONTENT_LENGTH = 200
    NETWORK_TIMEOUT = 60000
    MIN_SENTENCE_LENGTH = 10
    DEFAULT_SUMMARY_RATIO = 0.2
    DEFAULT_MAX_SENTENCES = 20

# -------------------- 유틸 --------------------
def sha256_hex(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def sentence_split(text: str) -> List[str]:
    """문장을 분리하여 리스트로 반환"""
    sents = re.split(r"(?<=[\.!?])\s+", text)
    return [s.strip() for s in sents if len(s.strip()) > Constants.MIN_SENTENCE_LENGTH]

# -------------------- 카테고리 요약 --------------------
def categorized_summary(text: str, ratio: float = Constants.DEFAULT_SUMMARY_RATIO, max_sentences: int = Constants.DEFAULT_MAX_SENTENCES) -> Dict[str, List[str]]:
    """
    본문을 네 가지 카테고리로 분류해 bullet point 요약
    
    Args:
        text: 요약할 텍스트
        ratio: 요약 비율 (0.0 ~ 1.0)
        max_sentences: 최대 문장 수
        
    Returns:
        카테고리별 문장 리스트를 담은 딕셔너리
    """
    text = clean_text(text)
    sents = sentence_split(text)
    if not sents:
        return {
            "사업 환경": ["본문이 짧아 요약 불가"],
            "Win 전략": [],
            "성과": [],
            "Lessons Learned": []
        }

    def tokenize(t):
        return [w.lower() for w in re.findall(r"[A-Za-z0-9가-힣]+", t)]

    words = [w for w in tokenize(text) if len(w) > 1]
    freq = Counter(words)
    scores = []
    for i, s in enumerate(sents):
        sw = tokenize(s)
        score = sum(freq.get(w, 0) for w in sw)
        scores.append((i, s, score))

    n = min(max(6, int(len(sents) * ratio)), max_sentences)
    top = sorted(scores, key=lambda x: x[2], reverse=True)[:n]
    top_sorted = [t[1] for t in sorted(top, key=lambda x: x[0])]

    # 간단 키워드 분류
    categories = {
        "사업 환경": [],
        "Win 전략": [],
        "성과": [],
        "Lessons Learned": []
    }

    for s in top_sorted:
        low = s.lower()
        if any(k in low for k in ["문제", "과제", "환경", "배경", "도전"]):
            categories["사업 환경"].append(s)
        elif any(k in low for k in ["전략", "해결", "접근", "제안", "방법"]):
            categories["Win 전략"].append(s)
        elif any(k in low for k in ["성과", "효과", "개선", "결과", "성과물", "비용 절감", "속도"]):
            categories["성과"].append(s)
        elif any(k in low for k in ["교훈", "lesson", "배운", "개선점"]):
            categories["Lessons Learned"].append(s)
        else:
            # 기본 분류: 사업 환경
            categories["사업 환경"].append(s)

    return categories

def summary_to_text(cat_summary: Dict[str, List[str]]) -> str:
    """카테고리별 요약을 텍스트 형태로 변환"""
    lines = []
    for cat, items in cat_summary.items():
        if items:
            lines.append(f"▶ {cat}")
            for it in items:
                lines.append("- " + it)
            lines.append("")  # 카테고리 끝에 빈 줄 추가
    
    # 마지막에 구분선을 추가해서 다음 항목과 명확히 구분
    if lines:
        lines.append("=" * 50)  # 구분선 추가
        lines.append("")  # 구분선 후 빈 줄
    
    return "\n".join(lines).strip()

# -------------------- 본문 추출 --------------------
def extract_article_body_from_dom(html: str) -> str:
    """HTML에서 본문 내용을 추출"""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","noscript","header","footer","nav","aside","form","button"]):
        tag.decompose()

    candidates = [
        "article",
        "main",
        "[role='main']",
        ".content",
        ".article",
        ".article-body",
        ".post",
        ".post-content",
        ".detail",
        ".view",
        ".board-view",
    ]
    for sel in candidates:
        node = soup.select_one(sel)
        if node and node.get_text(strip=True):
            text = node.get_text(" ", strip=True)
            if len(text) > Constants.MIN_CONTENT_LENGTH:
                return clean_text(text)

    text = soup.get_text(" ", strip=True)
    return clean_text(text)

# -------------------- 링크 수집 (더보기 버튼 클릭) --------------------
def collect_post_links(page, config: Config) -> List[str]:
    """페이지에서 포스트 링크들을 수집"""
    links = set()

    while True:
        anchors = page.query_selector_all("a[href]")
        for a in anchors:
            href = a.get_attribute("href") or ""
            if "/case-study/story/" in href:
                links.add(urljoin(config.domain, href))

        btn = page.query_selector("text='더 보기'")
        if btn:
            btn.click()
            page.wait_for_timeout(Constants.PAGE_LOAD_TIMEOUT)
        else:
            break

        if len(links) >= config.max_posts:
            break

    return list(links)[:config.max_posts]

# -------------------- 메인 --------------------
def scrape_and_summarize(config: Optional[Config] = None) -> pd.DataFrame:
    """메인 스크래핑 및 요약 함수"""
    if config is None:
        config = Config()
    
    rows = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=config.headless)
            page = browser.new_page()
            
            logger.info(f"Starting scraping from {config.base_url}")
            page.goto(config.base_url, wait_until="networkidle", timeout=Constants.NETWORK_TIMEOUT)

            links = collect_post_links(page, config)
            logger.info(f"Found {len(links)} post links")

            for idx, url in enumerate(links, start=1):
                try:
                    page.goto(url, wait_until="networkidle", timeout=Constants.NETWORK_TIMEOUT)
                    html = page.content()
                    title = page.title() or ""

                    body = extract_article_body_from_dom(html)
                    body = body[:Constants.MAX_CONTENT_LENGTH]
                    
                    if not body or len(body) < Constants.MIN_CONTENT_LENGTH:
                        raise ValueError("본문 추출 실패 또는 너무 짧음")

                    cat_summary = categorized_summary(body)
                    summary_text = summary_to_text(cat_summary)

                    rows.append({
                        "title": clean_text(title),
                        "url": url,
                        "url_hash": sha256_hex(url),
                        "content": body,
                        "content_hash": sha256_hex(body),
                        "summary": summary_text,
                    })
                    logger.info(f"[{idx}/{len(links)}] Successfully processed: {url}")
                    
                except TimeoutError:
                    logger.error(f"[{idx}/{len(links)}] Timeout error: {url}")
                except ValueError as e:
                    logger.error(f"[{idx}/{len(links)}] Content error: {url} -> {e}")
                except Exception as e:
                    logger.error(f"[{idx}/{len(links)}] Unknown error: {url} -> {e}")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise

    cols = ["title", "url", "url_hash", "content", "content_hash", "summary"]
    df = pd.DataFrame(rows, columns=cols)
    logger.info(f"Scraping completed. Total rows: {len(df)}")
    return df

def save_to_csv(df: pd.DataFrame, config: Config) -> None:
    """CSV 파일로 저장"""
    try:
        df.to_csv(config.csv_output, index=False, encoding="utf-8-sig")
        logger.info(f"Saved {len(df)} rows to CSV: {config.csv_output}")
    except Exception as e:
        logger.error(f"CSV save failed: {e}")
        raise

def save_to_database(df: pd.DataFrame, config: Config) -> None:
    """데이터베이스로 저장 (중복 제거 포함)"""
    engine = None
    try:
        engine = create_engine(f"sqlite:///{config.db_output}")
        
        # 기존 데이터의 해시값들을 가져와서 중복 제거
        try:
            existing_hashes = pd.read_sql("SELECT url_hash FROM cases", engine)['url_hash'].tolist()
            df_filtered = df[~df['url_hash'].isin(existing_hashes)]
            logger.info(f"Filtered {len(df) - len(df_filtered)} duplicate rows")
        except Exception:
            # 테이블이 없거나 오류가 발생한 경우 전체 데이터 저장
            df_filtered = df
            logger.info("No existing data found, saving all rows")
        
        if not df_filtered.empty:
            df_filtered.to_sql("cases", engine, if_exists="append", index=False)
            logger.info(f"Saved {len(df_filtered)} new rows to database: {config.db_output}")
        else:
            logger.info("No new data to save to database")
            
    except Exception as e:
        logger.error(f"Database save failed: {e}")
        raise
    finally:
        if engine:
            engine.dispose()

def save_outputs(df: pd.DataFrame, config: Optional[Config] = None) -> None:
    """결과를 CSV와 데이터베이스에 저장"""
    if config is None:
        config = Config()
        
    if df.empty:
        logger.warning("No data to save. Skipping CSV/DB save.")
        return

    save_to_csv(df, config)
    save_to_database(df, config)

# -------------------- RAG 기능 --------------------
def load_skax_data(db_path: str = "skax_case_studies.db") -> pd.DataFrame:
    """SKAX 케이스 스터디 데이터를 데이터베이스에서 로드"""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM cases", conn)
        conn.close()
        return df
    except Exception as e:
        logger.error(f"데이터베이스 로드 실패: {e}")
        return pd.DataFrame()

def create_vector_store(df: pd.DataFrame) -> Optional[FAISS]:
    """케이스 스터디 데이터로 벡터 스토어 생성"""
    if not RAG_AVAILABLE:
        logger.warning("RAG 기능을 사용하려면 langchain 패키지가 필요합니다.")
        return None
        
    if df.empty:
        logger.warning("데이터가 없어서 벡터 스토어를 생성할 수 없습니다.")
        return None
    
    try:
        # 텍스트 분할기 설정
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Azure OpenAI 임베딩 모델 초기화
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=os.getenv("AOAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"),
            azure_endpoint=os.getenv("AOAI_ENDPOINT"),
            api_key=os.getenv("AOAI_API_KEY"),
            api_version=os.getenv("AOAI_API_VERSION", "2024-05-01-preview")
        )
        logger.info("Azure OpenAI 임베딩 모델 사용")
        
        # 문서 생성 (제목 + 요약 + 본문 일부)
        documents = []
        for _, row in df.iterrows():
            # 제목과 요약을 결합하여 검색 가능한 텍스트 생성
            text = f"제목: {row['title']}\n\n요약:\n{row['summary']}\n\n본문: {row['content'][:2000]}"
            docs = text_splitter.create_documents([text])
            documents.extend(docs)
        
        # 벡터 스토어 생성
        vector_store = FAISS.from_documents(documents, embeddings)
        logger.info(f"벡터 스토어 생성 완료: {len(documents)}개 문서")
        return vector_store
        
    except Exception as e:
        logger.error(f"벡터 스토어 생성 실패: {e}")
        return None

def search_cases(query: str, vector_store: FAISS, k: int = 5) -> List[Dict]:
    """케이스 스터디 검색"""
    try:
        # 유사도 검색
        docs = vector_store.similarity_search(query, k=k)
        
        matches = []
        for doc in docs:
            # 문서에서 제목 추출
            content = doc.page_content
            if "제목:" in content:
                title = content.split("제목:")[1].split("\n")[0].strip()
                matches.append({
                    "title": title,
                    "content": content[:500] + "..." if len(content) > 500 else content
                })
        
        return matches
        
    except Exception as e:
        logger.error(f"검색 중 오류 발생: {e}")
        return []

def run_rag_demo(vector_store: FAISS, df: pd.DataFrame):
    """RAG 데모 실행"""
    if not RAG_AVAILABLE or vector_store is None:
        logger.warning("RAG 기능을 사용할 수 없습니다.")
        return
    
    logger.info("=" * 60)
    logger.info("🔍 RAG 검색 데모 시작")
    logger.info("=" * 60)
    
    # 테스트 쿼리들
    test_queries = [
        "데이터 보안 강화 솔루션이 필요해요",
        "ESG 관리 시스템 구축",
        "브랜드 통합 관리 시스템",
        "VDI 가상 데스크톱 인프라"
    ]
    
    for query in test_queries:
        logger.info(f"\n🔍 검색 쿼리: {query}")
        logger.info("-" * 50)
        
        matches = search_cases(query, vector_store)
        
        logger.info(f"📊 총 케이스 수: {len(df)}")
        logger.info(f"🎯 매칭된 케이스: {len(matches)}개")
        
        for i, match in enumerate(matches, 1):
            logger.info(f"\n{i}. {match['title']}")
            logger.info(f"   내용: {match['content'][:200]}...")
        
        logger.info("\n" + "="*60)

def main():
    """메인 실행 함수"""
    try:
        config = Config()
        
        # 설정에 따라 로깅 재설정
        global logger
        logger = setup_logging(config.enable_file_logging)
        
        logger.info("Starting SKAX case study scraper")
        
        # 1단계: 스크래핑 및 저장
        df = scrape_and_summarize(config)
        save_outputs(df, config)
        
        logger.info("Scraping and saving completed successfully")
        
        # 2단계: RAG 기능 실행
        if RAG_AVAILABLE and not df.empty:
            logger.info("Starting RAG functionality...")
            
            # 데이터 로드
            df_loaded = load_skax_data(config.db_output)
            if not df_loaded.empty:
                # 벡터 스토어 생성
                vector_store = create_vector_store(df_loaded)
                
                if vector_store:
                    # RAG 데모 실행
                    run_rag_demo(vector_store, df_loaded)
                    logger.info("RAG demo completed successfully")
                else:
                    logger.warning("벡터 스토어 생성 실패로 RAG 기능을 건너뜁니다.")
            else:
                logger.warning("데이터 로드 실패로 RAG 기능을 건너뜁니다.")
        else:
            if not RAG_AVAILABLE:
                logger.info("RAG dependencies not available. Skipping RAG functionality.")
            else:
                logger.info("No data available for RAG functionality.")
        
        logger.info("All processes completed successfully!")
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        raise

if __name__ == "__main__":
    main()
