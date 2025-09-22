from typing import Dict, Any, List
from langchain_core.tools import tool
from ..base_agent import BaseAgent


 # E. 리포팅 (Q&A 포함)
@tool
def generate_report(all_results: List[Dict[str, Any]]) -> str:
    """최종 보고서 생성"""
    # 여기서 all_results는 [{"title": "...", "content": "..."}] 같은 구조를 가정
    summaries = []
    for r in all_results:
        title = r.get("title", "제목 없음")
        summaries.append(f"- {title}")
    return "최종 보고서\n" + "\n".join(summaries)

class ReporterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are a reporting agent. Summarize results and generate final report.",
            tools=[generate_report]
        )

if __name__ == "__main__":
    agent = ReporterAgent()
    sample_results = [
        {"title": "스마트시티 RFP 분석", "content": "보안 및 클라우드 요구사항 포함"},
        {"title": "경쟁사 분석", "content": "삼성SDS, LG CNS 주요 강점 도출"}
    ]
    output = agent.run(str(sample_results))
    print(output)
