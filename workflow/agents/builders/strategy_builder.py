from langchain_core.tools import tool
from ..base_agent import BaseAgent

@tool
def build_strategy(requirements: list, capability_gap: list, swot: dict) -> dict:
    """SWOT 통합 및 보완 전략 수립"""
    # TODO: LLM 기반 통합 분석 로직
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
            system_prompt="You are a strategy builder agent. Integrate SWOT and propose recommendations.",
            tools=[build_strategy]
        )

if __name__ == "__main__":
    agent = StrategyBuilderAgent()
    output = agent.run("요구사항과 경쟁사 분석을 기반으로 전략을 세워줘.")
    print(output)
