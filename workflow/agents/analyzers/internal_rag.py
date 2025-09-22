from langchain_core.tools import tool
from ..base_agent import BaseAgent
# B. 내부지식 매칭

@tool
def match_internal_requirements(requirements: list) -> dict:
    """내부 프로젝트/솔루션과 요구사항 매칭"""
    # TODO: VectorStore/DB 검색 로직 구현
    return {
        "matches": ["프로젝트 A", "프로젝트 B"],
        "capability_gap": ["AI 역량 부족"]
    }

class InternalRAGAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are an internal RAG agent. Match requirements with internal projects.",
            tools=[match_internal_requirements]
        )

def run_internal_rag(topic: str) -> str:
    """내부 RAG 실행 함수"""
    agent = InternalRAGAgent()
    return agent.run(f"다음 주제에 대한 내부 프로젝트 매칭을 수행해줘: {topic}")

if __name__ == "__main__":
    agent = InternalRAGAgent()
    output = agent.run("요구사항 리스트를 내부 프로젝트와 매칭해줘.")
    print(output)
