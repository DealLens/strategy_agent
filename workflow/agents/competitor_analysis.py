import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from glob import glob


# --- 설정: 경로 우선순위 ---
# 1) 환경변수 COMPETITOR_DIR
# 2) Windows 절대경로 (사용자 요청)
# 3) 프로젝트 상대경로 ./data/company
DEFAULT_DIRS = [
    os.getenv("COMPETITOR_DIR"),
    r"C:\GIT\strategy_agent\data\company",
    os.path.join(os.getcwd(), "data", "company"),
]
COMPANY_DIR = next((d for d in DEFAULT_DIRS if d and os.path.isdir(d)), None)


# --- 유틸들 ---

def _safe_parse_dt(dt_str: str) -> Optional[datetime]:
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except Exception:
            continue
    # 마지막 시도: fromisoformat
    try:
        return datetime.fromisoformat(dt_str.replace("Z", ""))
    except Exception:
        return None


def _canonical_company_name(file_path: str, record_company: Optional[str]) -> str:
    # 파일명 기반 기본 회사명
    base = os.path.splitext(os.path.basename(file_path))[0]
    base = base.replace("_", " ").replace("-", " ").strip()

    # 레코드가 회사명 주면 우선 사용
    cand = (record_company or "").strip()
    if cand:
        return cand

    # 파일명 특수 매핑(선호 표기)
    mapping = {
        "samsung_sds": "삼성 SDS",
        "lgcns": "LG CNS",
        "lgu": "LG유플러스",
        "posco_dx": "포스코DX",
        "kt": "KT",
        "hyundai": "현대오토에버",
        "kakaoenterprise": "카카오엔터프라이즈",
        "naver_cloud": "네이버클라우드",
        "cj_olive": "CJ 올리브네트웍스",
        "skax": "SK AX",
    }
    return mapping.get(base.lower(), base)


PROJECT_KEYWORDS = [
    "수주", "계약", "프로젝트", "구축", "도입", "시범사업", "PoC", "플랫폼", "출시", "오픈", "고도화"
]

STRENGTH_KEYWORDS = {
    "AI/ML": ["AI", "인공지능", "머신러닝", "LLM", "Agent", "RAG"],
    "클라우드": ["클라우드", "Cloud", "PaaS", "IaaS", "SaaS", "컨테이너", "쿠버네티스", "Kubernetes"],
    "데이터/빅데이터": ["데이터", "빅데이터", "DWH", "데이터레이크", "Lakehouse", "ETL", "파이프라인"],
    "보안/인증": ["보안", "ISMS", "ISO27001", "인증", "제로트러스트", "암호화"],
    "공공/국방": ["공공", "정부", "지자체", "국방", "행안부", "조달"],
    "제조/스마트팩토리": ["제조", "스마트팩토리", "MES", "설비", "품질", "공정"],
    "모빌리티/자동차": ["모빌리티", "자동차", "자율주행", "차량", "교통", "ITS"],
    "금융": ["금융", "은행", "보험", "카드"],
    "헬스케어": ["의료", "헬스케어", "병원", "EMR"],
    "SI/통합": ["SI", "통합", "레거시", "ERP", "SAP", "전사", "대규모"],
    "브랜드/규모": ["브랜드", "대기업", "글로벌", "레퍼런스", "대규모", "대형"],
}

WEAKNESS_HINTS = {
    "가격 경쟁": ["가격 인상", "원가", "고가", "가격 경쟁력 부족"],
    "민첩성": ["느리", "민첩성 부족", "의사결정 지연", "관료적"],
    "인력": ["인력 부족", "채용 난항", "이직률", "역량 부족"],
    "보안/리스크": ["보안 사고", "침해", "유출", "법적 분쟁"],
}

OPPORTUNITY_HINTS = ["공공 사업 확대", "디지털 전환", "AI 투자 증가", "클라우드 전환", "규제 완화"]
THREAT_HINTS = ["빅테크 진입", "가격 경쟁 심화", "규제 강화", "경기 둔화", "수주 지연"]


def _extract_projects_and_strengths(item: Dict[str, Any]) -> (bool, Dict[str, int]):
    """프로젝트성 기사 여부와 강점점수 부분집계."""
    text = " ".join([
        str(item.get("title", "")),
        str(item.get("description", "")),
        str(item.get("summary", "")),
    ])
    is_project = any(k in text for k in PROJECT_KEYWORDS)

    # 강점 점수
    local_score = {}
    for label, kws in STRENGTH_KEYWORDS.items():
        score = sum(text.count(kw) for kw in kws)
        if score:
            local_score[label] = local_score.get(label, 0) + score

    return is_project, local_score


def _to_recent_list(records: List[Dict[str, Any]], topn: int = 5) -> List[Dict[str, Any]]:
    def norm(r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": r.get("title"),
            "url": r.get("url"),
            "source": r.get("source"),
            "crawled_at": r.get("crawled_at"),
        }

    recs = []
    for r in records:
        dt = _safe_parse_dt(r.get("crawled_at", ""))
        recs.append((dt or datetime.min, r))
    recs.sort(key=lambda x: x[0], reverse=True)
    return [norm(r) for _, r in recs[:topn]]


def _rank_strengths(score: Dict[str, int], topn: int = 5) -> List[str]:
    if not score:
        return []
    ranked = sorted(score.items(), key=lambda x: x[1], reverse=True)[:topn]
    return [k for k, _ in ranked]


def _generate_swot(strengths: List[str], news_texts: List[str]) -> Dict[str, str]:
    # S: 상위 강점 2~3개를 문장화
    S = " · ".join(strengths[:3]) if strengths else "레퍼런스 기반 강점 파악 필요"

    # W: 뉴스 텍스트에 약점 힌트가 보이면 반영
    W_hits = []
    all_text = " ".join(news_texts)
    for w_label, kws in WEAKNESS_HINTS.items():
        if any(kw in all_text for kw in kws):
            W_hits.append(w_label)
    W = " · ".join(W_hits) if W_hits else "민첩성/가격/인력 측면의 잠재 리스크"

    # O/T: 고정 힌트(필요시 뉴스 기반 강화 가능)
    O = " · ".join(OPPORTUNITY_HINTS[:3])
    T = " · ".join(THREAT_HINTS[:3])

    return {"S": S, "W": W, "O": O, "T": T}


# --- 메인 툴 ---

@tool
def competitor_analysis(companies: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    data/company/*.json 크롤링 결과를 취합하여
    경쟁사별 강점/최근 프로젝트/최근 뉴스/자동 SWOT을 생성합니다.

    Args:
        companies (Optional[List[str]]): 특정 회사들만 필터링하고 싶을 때 사용.
                                         None이면 디렉토리 모든 파일 사용.

    Returns:
        dict: {
          "competitor_profiles": {
            "<회사명>": {
              "strengths": [..],
              "recent_projects": [ {title,url,source,crawled_at}, ... ],
              "recent_news":     [ {title,url,source,crawled_at}, ... ],
              "swot": {"S": str, "W": str, "O": str, "T": str}
            }, ...
          }
        }
    """
    if not COMPANY_DIR:
        return {"competitor_profiles": {}, "error": "company 데이터 디렉토리를 찾을 수 없습니다."}

    json_files = glob(os.path.join(COMPANY_DIR, "*.json"))
    if not json_files:
        return {"competitor_profiles": {}, "error": f"JSON 파일이 없습니다: {COMPANY_DIR}"}

    profiles: Dict[str, Dict[str, Any]] = {}

    for path in json_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            # 파일 단위 에러는 스킵하고 계속
            continue

        # 파일 내부가 리스트/딕셔너리 양쪽 모두 대응
        items = data if isinstance(data, list) else data.get("items", [])
        if not isinstance(items, list):
            continue

        # 파일명 또는 레코드에서 회사명 추출
        for item in items:
            comp_name = _canonical_company_name(path, item.get("company"))
            if companies and comp_name not in companies:
                continue

            # 프로필 초기화
            p = profiles.setdefault(comp_name, {
                "strengths": [],
                "recent_projects_raw": [],
                "recent_news_raw": [],
            })

            # 프로젝트성 기사 여부 + 강점 점수 반영
            is_project, local_score = _extract_projects_and_strengths(item)
            if is_project:
                p["recent_projects_raw"].append(item)
            p["recent_news_raw"].append(item)

            # 강점 점수 누적
            score_map = p.setdefault("_strength_score", {})
            for k, v in local_score.items():
                score_map[k] = score_map.get(k, 0) + v

    # 후처리: 상위 강점/뉴스 정렬/프로젝트 정렬/SWOT 생성
    for comp, p in profiles.items():
        strengths = _rank_strengths(p.get("_strength_score", {}), topn=5)
        news = _to_recent_list(p.get("recent_news_raw", []), topn=5)
        projects = _to_recent_list(p.get("recent_projects_raw", []), topn=5)

        news_texts = [str(x.get("title", "")) for x in p.get("recent_news_raw", [])]
        swot = _generate_swot(strengths, news_texts)

        profiles[comp] = {
            "strengths": strengths,
            "recent_projects": projects,
            "recent_news": news,
            "swot": swot,
        }

    return {"competitor_profiles": profiles}


# --- 단독 실행 디버깅 ---
if __name__ == "__main__":
    # 특정 회사만 보고 싶으면 리스트로 전달: ["삼성 SDS", "LG CNS"]
    result = competitor_analysis.invoke({})
    profiles = result.get("competitor_profiles", {})

    print(f"총 {len(profiles)}개 회사 정리")
    for name, prof in profiles.items():
        print(f"\n== {name} ==")
        print("강점:", ", ".join(prof.get("strengths", [])) or "-")
        print("최근 프로젝트:")
        for r in prof.get("recent_projects", []):
            print(" -", r.get("title"))
        print("최근 뉴스:")
        for r in prof.get("recent_news", []):
            print(" -", r.get("title"))
        print("SWOT:", prof.get("swot"))
