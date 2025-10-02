import os
import asyncio
from typing import Any, Dict

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

# --- 개별 에이전트 import ---
from workflow.agents.rfp_parser import rfp_parser
from workflow.agents.internal_rag import internal_rag
from workflow.agents.competitor_analysis import competitor_analysis
from workflow.agents.strategy_synthesizer import strategy_synthesizer
from workflow.agents.reporter import reporter


# ======================
# 1. 사용할 툴 정의
# ======================
tools = [rfp_parser, internal_rag, competitor_analysis, strategy_synthesizer, reporter]


# ======================
# 2. Supervisor 프롬프트
# ======================
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 전문 전략 컨설턴트 역할의 Supervisor다. "
        "분석은 반드시 **다섯 단계**로 수행한다:\n\n"
        "1️⃣ RFP 분석\n"
        "2️⃣ 내부 매칭\n"
        "3️⃣ 경쟁사 분석\n"
        "4️⃣ 리스크 분석\n"
        "5️⃣ 전략 제안\n\n"
        "📌 RFP Parser / Internal RAG / Competitor Analysis는 병렬로 실행 후 결과를 합쳐 전략 분석에 사용한다.\n"
        "📌 Strategy Synthesizer는 병렬 결과물을 받아 종합 전략을 만든다.\n"
        "📌 Reporter는 최종 결과를 보고서 스타일로 작성한다.\n"
    ),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])


# ======================
# 3. LLM 초기화
# ======================
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_DEPLOY_GPT4O = os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2024-05-01-preview")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = None
try:
    if AOAI_API_KEY and AOAI_ENDPOINT:
        llm = AzureChatOpenAI(
            azure_endpoint=AOAI_ENDPOINT,
            azure_deployment=AOAI_DEPLOY_GPT4O,
            api_version=AOAI_API_VERSION,
            api_key=AOAI_API_KEY,
            temperature=0.2,
        )
        print("✅ Azure OpenAI 사용")
    elif OPENAI_API_KEY:
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.2,
        )
        print("✅ OpenAI 사용")
    else:
        print("⚠️ API 키 없음 → 더미 모드 동작")
except Exception as e:
    print(f"⚠️ LLM 초기화 실패: {e}")


# ======================
# 4. 병렬 Supervisor 정의
# ======================
class ParallelSupervisor:
    def __init__(self, llm):
        self.llm = llm

    async def run_parallel(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """RFP Parser, Internal RAG, Competitor Analysis를 병렬 실행"""

        async def _run_tool(tool, name, params):
            try:
                result = await tool.ainvoke(params)
                return name, result
            except Exception as e:
                return name, {"error": str(e)}

        # 각 툴에 맞는 파라미터 준비
        pdf_path = input_data.get("pdf_path", "")
        
        # RFP Parser 실행
        rfp_result = await _run_tool(rfp_parser, "rfp_parser", {"pdf_path": pdf_path})
        
        # RFP 결과에서 요구사항 추출
        rfp_data = rfp_result[1]
        requirements = []
        if isinstance(rfp_data, dict) and "requirements" in rfp_data:
            requirements = rfp_data["requirements"][:5]  # 상위 5개만
        
        # Internal RAG와 Competitor Analysis는 병렬 실행
        results = await asyncio.gather(
            _run_tool(internal_rag, "internal_rag", {"requirements": requirements}),
            _run_tool(competitor_analysis, "competitor_analysis", {"update_data": False}),
            return_exceptions=False
        )

        # 결과 합치기
        all_results = dict([rfp_result] + list(results))
        return all_results

    async def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # 1. 병렬 실행
        parallel_results = await self.run_parallel(input_data)

        # 2. 결과에서 필요한 데이터 추출
        rfp_data = parallel_results.get("rfp_parser", {})
        internal_data = parallel_results.get("internal_rag", {})
        competitor_data = parallel_results.get("competitor_analysis", {})
        
        # requirements 추출 (RFP Parser 결과에서)
        requirements = rfp_data.get("requirements", [])
        if isinstance(requirements, list) and requirements:
            # 텍스트만 추출 (상위 5개)
            requirements = requirements[:5]
        else:
            requirements = ["요구사항 추출 실패"]
        
        # 3. 전략 합성 (순차) - 올바른 파라미터 형식
        strategy_result = await strategy_synthesizer.ainvoke({
            "requirements": requirements,
            "internal_matches": internal_data.get("internal_matches", []),
            "competitor_profiles": competitor_data.get("competitor_profiles", {})
        })

        # 4. 리포터 실행 (순차) - 모든 데이터를 하나의 dict로
        report_data = {
            "requirements": rfp_data.get("requirements", []),
            "evaluation": rfp_data.get("evaluation", []),
            "risks": rfp_data.get("risks", []),
            "internal_matches": internal_data.get("internal_matches", []),
            "competitor_profiles": competitor_data.get("competitor_profiles", {}),
            "strategy": strategy_result.get("strategy", {})
        }
        
        report_result = await reporter.ainvoke({"data": report_data})

        return {
            "rfp_parser": rfp_data,
            "internal_rag": internal_data,
            "competitor_analysis": competitor_data,
            "strategy": strategy_result,
            "report": report_result
        }


# ======================
# 5. 실행 예시
# ======================
if __name__ == "__main__":
    supervisor = ParallelSupervisor(llm)

    async def main():
        input_data = {
            "pdf_path": "data/samples/RFP_finance.pdf",
            "user_input": "이번 공공 RFP에 대한 전략 분석을 생성해줘."
        }
        results = await supervisor.invoke(input_data)

        print("\n=== 최종 보고서 ===\n")
        print(results["report"])

    asyncio.run(main())
