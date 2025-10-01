import os
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

from workflow.agents.rfp_parser import rfp_parser
from workflow.agents.internal_rag import internal_rag
from workflow.agents.competitor_analysis import competitor_analysis
from workflow.agents.strategy_synthesizer import strategy_synthesizer
from workflow.agents.reporter import reporter

# 사용할 툴들
tools = [rfp_parser, internal_rag, competitor_analysis, strategy_synthesizer, reporter]

# 🔹 Supervisor 프롬프트 강화
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 전문 전략 컨설턴트 역할의 Supervisor다. "
        "분석은 반드시 **다섯 단계**로 수행한다:\n"
        "1) RFP 분석 → 요구사항과 평가기준을 **문단 단위**로 상세히 정리\n"
        "2) 내부 매칭 → 각 요구사항당 내부 유사사업 Top-3를 찾아 **사례별 설명**과 함께 제시\n"
        "3) 경쟁사 분석 → 삼성 SDS, LG CNS, 현대 오토에버를 대상으로 SWOT 분석을 수행하고, "
        "최근 프로젝트·뉴스를 인용하여 근거 기반으로 작성\n"
        "4) 리스크 → 단순 나열이 아니라 **위험 시나리오 + 영향도**를 문단으로 작성\n"
        "5) 전략 제안 → 최소 3개 이상의 actionable 전략을 문장 단위로 제시하고, 내부/경쟁사 비교를 근거로 활용\n\n"
        "⚠️ 품질이 부족하면 같은 툴을 다시 호출할 수 있으나, 최대 3회까지만 반복 가능하다.\n"
        "⚠️ 결과물은 반드시 보고서 스타일로 풍부하게 작성한다."
    ),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# --- 환경변수에서 불러오기 ---
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_DEPLOY_GPT4O = os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2024-05-01-preview")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- LLM 초기화 ---
try:
    if AOAI_API_KEY and AOAI_ENDPOINT:
        # Azure OpenAI
        llm = AzureChatOpenAI(
            azure_endpoint=AOAI_ENDPOINT,
            azure_deployment=AOAI_DEPLOY_GPT4O,
            api_version=AOAI_API_VERSION,
            api_key=AOAI_API_KEY,
            temperature=0.2,
        )
        print("✅ Azure OpenAI 사용")
    elif OPENAI_API_KEY:
        # OpenAI
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.2
        )
        print("✅ OpenAI 사용")
    else:
        print("⚠️ API 키가 없어서 더미 모드로 동작합니다")
        llm = None
except Exception as e:
    print(f"⚠️ LLM 초기화 실패: {e}")
    llm = None

# --- AgentExecutor or Dummy ---
if llm:
    agent = create_tool_calling_agent(llm, tools, prompt)
    supervisor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        max_iterations=15,
        handle_parsing_errors=True
    )
else:
    class DummySupervisor:
        def __init__(self):
            self.tools = tools
        def invoke(self, input_data):
            return {
                "output": "⚠️ API 키가 설정되지 않아 더미 모드로 동작합니다. 실제 분석을 위해서는 API 키를 설정해주세요.",
                "intermediate_steps": []
            }
    supervisor = DummySupervisor()
