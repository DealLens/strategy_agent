from typing import List, Dict, Any
from langchain_core.tools import tool
from ..base_agent import BaseAgent


@tool
def build_strategy(
    requirements: List[str],
    capability_gap: List[str],
    swot: Dict[str, Any]
) -> Dict[str, Any]:
    """
    SWOT 통합 및 보완 전략 수립
    requirements: 요구사항 리스트
    capability_gap: 내부 역량 격차 리스트
    swot: 경쟁사 분석 결과 (strengths, weaknesses, opportunities, threats 포함)
    return: 최종 SWOT 및 추천 전략 dict
    """
    # TODO: LLM 기반 통합 분석 로직 추가
    return {
        "strengths": ["AI 인력 보유"],
        "weaknesses": ["보안 인증 부족"],
        "opportunities": ["공공 시장 확대"],
        "threats": ["대기업 경쟁 심화"],
        "recommendations": ["보안 인증 확보", "파트너십 확대"]
    }


class StrategyBuilderAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt=(
                "You are a strategy builder agent. "
                "Integrate RFP requirements, internal capability gaps, "
                "and competitor SWOT to propose business strategies."
            ),
            tools=[build_strategy]
        )


if __name__ == "__main__":
    # 에이전트 실행 테스트
    agent = StrategyBuilderAgent()
    
    # 예시 입력
    sample_requirements = ["보안 인증", "클라우드 아키텍처", "데이터 통합"]
    sample_gaps = ["보안 인증 부족"]
    sample_swot = {
        "strengths": ["AI 인력 보유"],
        "weaknesses": ["보안 인증 부족"],
        "opportunities": ["공공 시장 확대"],
        "threats": ["대기업 경쟁 심화"]
    }

    # 툴 직접 실행
    result = build_strategy(sample_requirements, sample_gaps, sample_swot)
    print("🔹 build_strategy 결과:", result)

    # 에이전트 실행
    output = agent.run("요구사항과 경쟁사 분석을 기반으로 전략을 세워줘.")
    print("🔹 StrategyBuilderAgent 결과:", output)
