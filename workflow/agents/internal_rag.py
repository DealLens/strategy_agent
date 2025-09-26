import json
import os
from langchain_core.tools import tool
from typing import List, Dict, Any

# 내부 데이터 경로 (환경에 맞게 수정 가능)
DATA_PATH = r"C:\GIT\strategy_agent\data\internal\skax_case_studies.json"


@tool
def internal_rag(requirements: List[str]) -> Dict[str, Any]:
    """
    내부 데이터(skax_case_studies.json)를 불러와
    요구사항별 매칭 결과를 반환합니다.

    Args:
        requirements (List[str]): RFP에서 추출된 요구사항 리스트

    Returns:
        dict: {
            "internal_matches": [
                {"requirement": str, "related": [프로젝트명 리스트]}
            ]
        }
    """
    # 데이터 파일 확인
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
                related_projects.append(case.get("title", "제목 없음"))
        matches.append({
            "requirement": req,
            "related": related_projects
        })

    return {"internal_matches": matches}


# 단독 실행 디버깅용
if __name__ == "__main__":
    sample_requirements = ["AI 성능 검증", "보안 인증", "SLA 99.9%"]
    result = internal_rag.run(sample_requirements)
    print("📋 Internal RAG 결과:")
    for r in result.get("internal_matches", []):
        print(f"- {r['requirement']}: {r.get('related', [])}")
