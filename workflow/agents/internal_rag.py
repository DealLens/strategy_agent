import json
import os
from langchain_core.tools import tool
from typing import List, Dict, Any

# =========================
# 경로 초기화 (competitor_analysis와 동일 패턴)
# =========================
try:
    from dotenv import load_dotenv
    CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "..", ".."))
    env_path = os.path.join(PROJECT_ROOT, ".env")
    load_dotenv(env_path)
except Exception:
    PROJECT_ROOT = os.getcwd()

# 내부 데이터 경로 (유연하게 설정)
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
    요구사항별 매칭 결과 (Top-3)를 반환합니다.

    Args:
        requirements (List[str]): RFP에서 추출된 요구사항 리스트

    Returns:
        dict: {
            "internal_matches": [
                {
                    "requirement": str,
                    "matches": [
                        {"title": str, "summary": str, "url": str}
                    ]
                }
            ]
        }
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
        
        # 요구사항에서 키워드 추출 (공백, 쉼표, 괄호 등으로 분리)
        keywords = []
        for word in req.replace(',', ' ').replace('(', ' ').replace(')', ' ').split():
            word = word.strip()
            if len(word) >= 2:  # 2글자 이상만
                keywords.append(word.lower())
        
        print(f"[내부 RAG] '{req}' → 키워드: {keywords}")
        
        # 제목, 내용, summary에서 키워드 매칭
        for case in cases:
            title = case.get("title", "").lower()
            content = case.get("content", "").lower()
            summary = case.get("summary", "").lower()
            
            # 키워드 중 하나라도 매칭되면 추가
            match_score = 0
            for keyword in keywords:
                if keyword in title:
                    match_score += 3  # 제목 매칭은 가중치 높게
                elif keyword in summary:
                    match_score += 2  # 요약 매칭
                elif keyword in content:
                    match_score += 1  # 본문 매칭
            
            if match_score > 0:
                related_projects.append({
                    "title": case.get("title", "제목 없음"),
                    "summary": case.get("summary", case.get("content", "")[:300] + "..."),
                    "url": case.get("url", ""),
                    "score": match_score
                })
        
        # 점수 높은 순으로 정렬 후 Top-3만 선택
        related_projects = sorted(related_projects, key=lambda x: x.get("score", 0), reverse=True)[:3]
        
        # score 필드는 제거 (결과에는 불필요)
        for proj in related_projects:
            proj.pop("score", None)
        
        print(f"[내부 RAG] '{req}' → {len(related_projects)}개 매칭")
        if related_projects:
            for i, proj in enumerate(related_projects, 1):
                print(f"         {i}. {proj['title'][:50]}...")

        matches.append({
            "requirement": req,
            "matches": related_projects
        })

    print(f"[내부 RAG] ✅ 완료 - 총 {sum(len(m['matches']) for m in matches)}개 프로젝트 매칭\n")
    
    return {"internal_matches": matches}


# 디버깅용 실행
if __name__ == "__main__":
    sample_requirements = ["AI 성능 검증", "보안 인증"]

    # @tool 데코레이터 때문에 .invoke()로 실행해야 함
    result = internal_rag.invoke({"requirements": sample_requirements})

    print("📋 Internal RAG 결과:")
    for r in result.get("internal_matches", []):
        print(f"요구사항: {r['requirement']}")
        for m in r["matches"]:
            print(f"   - {m['title']} | {m['summary']} | {m['url']}")
