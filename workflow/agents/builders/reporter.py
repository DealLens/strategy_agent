from langchain_core.tools import tool
from ..base_agent import BaseAgent

@tool
def generate_report(all_results: dict) -> str:
    """최종 보고서 생성"""
    # TODO: Streamlit 시각화 / PDF 변환 등 연결
    return "최종 보고서가 생성되었습니다."

class ReporterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are a reporting agent. Summarize results and generate final report.",
            tools=[generate_report]
        )

if __name__ == "__main__":
    agent = ReporterAgent()
    output = agent.run("최종 결과를 보고서로 만들어줘.")
    print(output)
