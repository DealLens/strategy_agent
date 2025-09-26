from langchain_core.tools import tool
from typing import List, Dict, Any, Optional


@tool
def strategy_synthesizer(
    requirements: List[str],   # ✅ 필수: RFP에서 직접 추출 (개발언어, 요구사항 등)
    internal_matches: Optional[List[Dict[str, Any]]] = None,   # 선택
    competitor_profiles: Optional[Dict[str, Any]] = None       # 선택
) -> dict:
    """
    내부 매칭 + 경쟁사 분석을 종합해 전략을 도출합니다.

    Args:
        requirements (List[str]): RFP에서 직접 추출된 요구사항/개발언어
        internal_matches (Optional[List[Dict]]): 내부 역량 매칭 결과 (없으면 빈 리스트)
        competitor_profiles (Optional[Dict]): 경쟁사 SWOT 분석 결과 (없으면 빈 dict)

    Returns:
        dict: {
            "strategy": {
                "actions": [...],          # 갭 보완책
                "swot": {...},             # 당사 SWOT
                "differentiation": [...]   # 차별화 포인트
            }
        }
    """

    internal_matches = internal_matches or []
    competitor_profiles = competitor_profiles or {}

    # 1. 갭 분석 → 보완책(Action Plan)
    actions = []
    for match in internal_matches:
        req = match.get("requirement")
        related = match.get("related", [])
        if not related:
            actions.append(f"{req}: 외부 파트너십 확보 필요")
        else:
            actions.append(f"{req}: 내부 역량으로 대응 가능")

    if not actions:
        actions = ["내부 매칭 데이터 부족 → 보완책 제안 불가"]

    # 2. 당사 SWOT (샘플, 필요시 개선 가능)
    swot = {
        "S": "내부 AI 연구 경험 풍부",
        "W": "전문 인력 일부 부족",
        "O": "공공 AI 프로젝트 증가",
        "T": "대기업의 가격 경쟁 압박"
    }

    # 3. 경쟁사 대비 차별화 포인트
    differentiation = []
    for comp, profile in competitor_profiles.items():
        swot_comp = profile.get("swot", {})
        if "W" in swot_comp and "가격 경쟁력 부족" in swot_comp["W"]:
            differentiation.append(f"{comp} 대비 가격 경쟁 우위 확보 가능")
        if "S" in swot_comp and "브랜드" in swot_comp["S"]:
            differentiation.append(f"{comp}는 브랜드 강점 → 우리는 기술 차별화 강조 필요")

    if not differentiation:
        differentiation = ["경쟁사 데이터 부족 → 차별화 포인트 도출 불가"]

    return {
        "strategy": {
            "actions": actions[:5],
            "swot": swot,
            "differentiation": differentiation[:5]
        }
    }


# 디버깅용 실행
if __name__ == "__main__":
    dummy_requirements = ["AI 성능 검증", "보안 인증", "개발언어: Python"]
    dummy_internal_matches = [
        {"requirement": "AI 성능 검증", "related": ["프로젝트 A"]},
        {"requirement": "보안 인증", "related": []}
    ]
    dummy_competitors = {
        "삼성 SDS": {"swot": {"S": "브랜드", "W": "가격 경쟁력 부족"}},
        "LG CNS": {"swot": {"S": "SI 경험", "W": "민첩성 부족"}}
    }

    result = strategy_synthesizer.invoke({
        "requirements": dummy_requirements,
        # internal_matches, competitor_profiles는 안 줘도 OK
    })
    print("🎯 전략 합성 결과:")
    print(result)
