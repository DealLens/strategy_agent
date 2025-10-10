import json
import os
from langchain_core.tools import tool
from typing import List, Dict, Any

# =========================
# 경로 초기화
# =========================
try:
    from dotenv import load_dotenv
    CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "..", ".."))
    env_path = os.path.join(PROJECT_ROOT, ".env")
    load_dotenv(env_path)
except Exception:
    PROJECT_ROOT = os.getcwd()

# 내부 데이터 경로
DEFAULT_INTERNAL_DIRS = [
    os.getenv("INTERNAL_DATA_DIR"),
    os.path.join(PROJECT_ROOT, "data", "internal"),
    r"C:\GIT\strategy_agent\data\internal",
    os.path.join(os.getcwd(), "data", "internal"),
]

INTERNAL_DATA_DIR = next((d for d in DEFAULT_INTERNAL_DIRS if d and os.path.isdir(d)), None)
if not INTERNAL_DATA_DIR:
    INTERNAL_DATA_DIR = DEFAULT_INTERNAL_DIRS[1]
    os.makedirs(INTERNAL_DATA_DIR, exist_ok=True)

DATA_PATH = os.path.join(INTERNAL_DATA_DIR, "skax_case_studies.json")

print(f"[내부 데이터] 경로: {DATA_PATH}")
print(f"[내부 데이터] 파일 존재: {os.path.exists(DATA_PATH)}")


@tool
def internal_rag(requirements: List[str]) -> Dict[str, Any]:
    """
    내부 데이터(skax_case_studies.json)를 불러와
    요구사항별 매칭 결과 및 적합도 점수를 반환합니다.
    """
    print(f"\n[내부 RAG] 시작 - 요구사항 {len(requirements)}개")
    print(f"[내부 RAG] 데이터 경로: {DATA_PATH}")
    
    if not os.path.exists(DATA_PATH):
        error_msg = f"데이터 파일을 찾을 수 없음: {DATA_PATH}"
        print(f"[내부 RAG] ❌ {error_msg}")
        return {"error": error_msg}

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            cases = json.load(f)
        print(f"[내부 RAG] ✅ 데이터 로드 성공 - 총 {len(cases)}개 케이스")
    except Exception as e:
        error_msg = f"데이터 로드 실패: {str(e)}"
        print(f"[내부 RAG] ❌ {error_msg}")
        return {"error": error_msg}

    matches = []
    for req in requirements:
        related_projects = []
        total_score = 0  # 총합
        max_possible = 0  # 최대 점수 계산용 (키워드 수 × 3)

        # 키워드 추출
        keywords = []
        for word in req.replace(',', ' ').replace('(', ' ').replace(')', ' ').split():
            word = word.strip()
            if len(word) >= 2:
                keywords.append(word.lower())

        print(f"[내부 RAG] '{req}' → 키워드: {keywords}")

        # 매칭 스코어 계산
        for case in cases:
            title = case.get("title", "").lower()
            content = case.get("content", "").lower()
            summary = case.get("summary", "").lower()

            match_score = 0
            for keyword in keywords:
                if keyword in title:
                    match_score += 3
                elif keyword in summary:
                    match_score += 2
                elif keyword in content:
                    match_score += 1

            if match_score > 0:
                related_projects.append({
                    "title": case.get("title", "제목 없음"),
                    "summary": case.get("summary", case.get("content", "")[:300] + "..."),
                    "url": case.get("url", ""),
                    "score": match_score
                })
                total_score += match_score
            max_possible += len(keywords) * 3  # 각 문서별 잠재 점수

        # 점수 정규화
        if max_possible > 0:
            normalized_score = min(round(total_score / max_possible, 2), 1.0)
        else:
            normalized_score = 0.0

        # 상위 3개만 남기기
        related_projects = sorted(related_projects, key=lambda x: x.get("score", 0), reverse=True)[:3]
        for proj in related_projects:
            proj.pop("score", None)

        print(f"[내부 RAG] '{req}' → {len(related_projects)}개 매칭, 적합도={normalized_score}")

        matches.append({
            "requirement": req,
            "match_score": normalized_score,  # ✅ 핵심 추가
            "matches": related_projects
        })

    print(f"[내부 RAG] ✅ 완료 - 총 {sum(len(m['matches']) for m in matches)}개 매칭\n")
    return {"internal_matches": matches}


# 디버깅용
if __name__ == "__main__":
    sample_requirements = ["AI 성능 검증", "보안 인증"]

    result = internal_rag.invoke({"requirements": sample_requirements})

    print("📋 Internal RAG 결과:")
    for r in result.get("internal_matches", []):
        print(f"요구사항: {r['requirement']} | 적합도: {r['match_score']}")
        for m in r["matches"]:
            print(f"   - {m['title']} | {m['summary'][:60]}...")
