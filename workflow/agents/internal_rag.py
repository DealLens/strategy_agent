import json
import os
from langchain_core.tools import tool
from typing import List, Dict, Any

# 내부 데이터 경로
DATA_PATH = r"C:\GIT\strategy_agent\data\internal\skax_case_studies.json"


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
    if not os.path.exists(DATA_PATH):
        return {"error": f"데이터 파일을 찾을 수 없음: {DATA_PATH}"}

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            cases = json.load(f)
    except Exception as e:
        return {"error": f"데이터 로드 실패: {str(e)}"}

    matches = []
    for req in requirements:
        related_projects = []
        for case in cases:
            capabilities = case.get("capabilities", [])
            if any(req.lower() in cap.lower() for cap in capabilities):
                related_projects.append({
                    "title": case.get("title", "제목 없음"),
                    "summary": case.get("summary", case.get("content", "")[:150] + "..."),
                    "url": case.get("url", "")
                })
        # 🔹 Top-3만 선택
        related_projects = related_projects[:3]

        matches.append({
            "requirement": req,
            "matches": related_projects
        })

    return {"internal_matches": matches}


# 디버깅용 실행
if __name__ == "__main__":
    sample_requirements = ["AI 성능 검증", "보안 인증"]
    # @tool 데코레이터 때문에 .invoke()를 사용해야 함
    result = internal_rag.invoke({"requirements": sample_requirements})
    print("📋 Internal RAG 결과:")
    for r in result.get("internal_matches", []):
        print(f"요구사항: {r['requirement']}")
        for m in r["matches"]:
            print(f"   - {m['title']} | {m['summary']} | {m['url']}")
