from langchain_core.tools import tool

@tool
def strategy_synthesizer(data: dict) -> dict:
    """
    내부 매칭 + 경쟁사 분석을 종합해 전략을 도출합니다.
    
    Args:
        data (dict): Supervisor가 모은 A~C 단계 결과
            {
                "requirements": [...],
                "internal_matches": [...],
                "competitor_profiles": {...}
            }
    
    Returns:
        dict: {
            "strategy": {
                "actions": [...],  # 갭 보완책
                "swot": {...},     # 당사 SWOT
                "differentiation": [...]  # 경쟁사 대비 차별화 포인트
            }
        }
    """

    requirements = data.get("requirements", [])
    internal_matches = data.get("internal_matches", [])
    competitors = data.get("competitor_profiles", {})

    # 1. 갭 분석 → 보완책(Action Plan) (샘플 로직)
    actions = []
    for match in internal_matches:
        req = match.get("requirement")
        related = match.get("related", [])
        if not related:  # 매칭 실패 → 갭 존재
            actions.append(f"{req}: 외부 파트너십 확보 필요")
        else:
            actions.append(f"{req}: 내부 역량으로 대응 가능")

    if not actions:
        actions = ["추가 데이터 필요"]

    # 2. 당사 SWOT (샘플 값)
    swot = {
        "S": "내부 AI 연구 경험 풍부",
        "W": "전문 인력 일부 부족",
        "O": "공공 AI 프로젝트 증가",
        "T": "대기업의 가격 경쟁 압박"
    }

    # 3. 경쟁사 대비 차별화 포인트 (샘플 로직)
    differentiation = []
    for comp, profile in competitors.items():
        swot_comp = profile.get("swot", {})
        if "W" in swot_comp and "가격 경쟁력 부족" in swot_comp["W"]:
            differentiation.append(f"{comp} 대비 가격 경쟁 우위 확보 가능")
        if "S" in swot_comp and "브랜드" in swot_comp["S"]:
            differentiation.append(f"{comp}는 브랜드 강점 → 우리는 기술 차별화 강조 필요")

    if not differentiation:
        differentiation = ["차별화 포인트 도출 불가 - 데이터 부족"]

    return {
        "strategy": {
            "actions": actions[:5],
            "swot": swot,
            "differentiation": differentiation[:5]
        }
    }


# 디버깅 / 단독 실행용
if __name__ == "__main__":
    dummy_data = {
        "requirements": ["AI 성능 검증", "보안 인증"],
        "internal_matches": [
            {"requirement": "AI 성능 검증", "related": ["프로젝트 A"]},
            {"requirement": "보안 인증", "related": []}
        ],
        "competitor_profiles": {
            "삼성 SDS": {"swot": {"S": "브랜드", "W": "가격 경쟁력 부족"}},
            "LG CNS": {"swot": {"S": "SI 경험", "W": "민첩성 부족"}}
        }
    }

    result = strategy_synthesizer.run(dummy_data)  # @tool 은 run()으로 실행 가능
    print("🎯 전략 합성 결과:")
    print(result)
