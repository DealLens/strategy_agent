from langchain_core.tools import tool
from .base_agent import BaseAgent

# Tool 정의
@tool
def parse_rfp(pdf_path: str) -> dict:
    """RFP PDF를 파싱하여 요구사항 및 리스크 반환"""
    # 실제 PDF 파싱 로직은 추후 구현
    return {
        "requirements": ["클라우드 전환", "개인정보 암호화"],
        "risks": ["라이선스 이슈", "납기 불명확"]
    }

# RFP Parser Agent
class RFPParserAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            system_prompt="You are an RFP parsing agent. Extract requirements and risks.",
            tools=[parse_rfp]
        )

if __name__ == "__main__":
    agent = RFPParserAgent()
    output = agent.run("이 PDF를 분석해줘: sample.pdf")
    print(output)
