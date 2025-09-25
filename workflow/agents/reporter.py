from langchain_core.tools import tool

@tool
def reporter(data: dict) -> dict:
    """
    최종 보고서 요약 및 브리핑을 생성합니다.
    
    Args:
        data (dict): Supervisor가 모은 A~D 단계 결과
            {
                "requirements": [...],
                "evaluation": [...],
                "risks": [...],
                "internal_matches": [...],
                "competitor_profiles": {...},
                "strategy": {...}
            }
    
    Returns:
        dict: {
            "deal_brief": str,   # 1~2p 요약 브리핑
            "sections": dict     # 상세 섹션 (요구사항/리스크/전략/경쟁사)
        }
    """

    requirements = data.get("requirements", [])
    evaluation = data.get("evaluation", [])
    risks = data.get("risks", [])
    internal_matches = data.get("internal_matches", [])
    competitors = data.get("competitor_profiles", {})
    strategy = data.get("strategy", {})

    # 간단 브리핑 (Deal Brief)
    deal_brief = f"""
    📋 요구사항: {len(requirements)}개
    🛡️ 평가 기준: {len(evaluation)}개
    ⚠️ 리스크 후보: {len(risks)}개
    🔍 내부 매칭: {len(internal_matches)}개
    🏢 경쟁사 분석: {len(competitors)}개
    🎯 전략 요약: {strategy.get('actions', [])}
    """

    # 상세 섹션
    sections = {
        "요구사항": requirements[:5],
        "평가기준": evaluation[:5],
        "리스크": risks[:5],
        "내부매칭": internal_matches[:3],
        "경쟁사": {k: v.get("swot", {}) for k, v in competitors.items()},
        "전략": strategy
    }

    return {
        "deal_brief": deal_brief.strip(),
        "sections": sections
    }


# 단독 실행 디버깅용
if __name__ == "__main__":
    dummy_data = {
        "requirements": ["AI 성능 검증", "보안 인증"],
        "evaluation": ["기술 80%", "가격 20%"],
        "risks": ["보안 요구 불명확"],
        "internal_matches": [{"requirement": "AI 성능 검증", "related": ["프로젝트 A"]}],
        "competitor_profiles": {
            "삼성 SDS": {"swot": {"S": "브랜드", "W": "비용"}}
        },
        "strategy": {"actions": ["PoC 제안", "파트너 협력"], "swot": {"S": "AI 역량"}}
    }

    result = reporter.run(dummy_data)  # @tool 은 run()으로 실행 가능
    print("📋 Deal Brief:\n", result["deal_brief"])
    print("📑 상세 섹션:\n", result["sections"])
