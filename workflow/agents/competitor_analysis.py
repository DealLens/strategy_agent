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
    try:
        return datetime.fromisoformat(dt_str.replace("Z", ""))
    except Exception:
        return None


def _canonical_company_name(file_path: str, record_company: Optional[str]) -> str:
    base = os.path.splitext(os.path.basename(file_path))[0]
    base = base.replace("_", " ").replace("-", " ").strip()

    cand = (record_company or "").strip()
    if cand:
        return cand

    mapping = {
        "samsung_sds": "삼성 SDS",
        "lgcns": "LG CNS",
        "hyundai": "현대오토에버",
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
    text = " ".join([
        str(item.get("title", "")),
        str(item.get("description", "")),
        str(item.get("summary", "")),
    ])
    is_project = any(k in text for k in PROJECT_KEYWORDS)

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
    S = " · ".join(strengths[:3]) if strengths else "레퍼런스 기반 강점 파악 필요"

    W_hits = []
    all_text = " ".join(news_texts)
    for w_label, kws in WEAKNESS_HINTS.items():
        if any(kw in all_text for kw in kws):
            W_hits.append(w_label)
    W = " · ".join(W_hits) if W_hits else "민첩성/가격/인력 측면의 잠재 리스크"

    O = " · ".join(OPPORTUNITY_HINTS[:3])
    T = " · ".join(THREAT_HINTS[:3])

    return {"S": S, "W": W, "O": O, "T": T}


# --- 메인 툴 ---

@tool
def competitor_analysis(companies: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    삼성 SDS / LG CNS / 현대오토에버 3사만 분석.
    """
    if not COMPANY_DIR:
        return {"competitor_profiles": {}, "error": "company 데이터 디렉토리를 찾을 수 없습니다."}

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

        items = data if isinstance(data, list) else data.get("items", [])
        if not isinstance(items, list):
            continue

        for item in items:
            comp_name = _canonical_company_name(path, item.get("company"))

            # ✅ 3사만 필터링
            if comp_name not in companies:
                continue

            p = profiles.setdefault(comp_name, {
                "strengths": [],
                "recent_projects_raw": [],
                "recent_news_raw": [],
            })

            is_project, local_score = _extract_projects_and_strengths(item)
            if is_project:
                p["recent_projects_raw"].append(item)
            p["recent_news_raw"].append(item)

            score_map = p.setdefault("_strength_score", {})
            for k, v in local_score.items():
                score_map[k] = score_map.get(k, 0) + v

    # 후처리
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
    result = competitor_analysis()  # 기본값: 삼성/LG/현대 3사
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
