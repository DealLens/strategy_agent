import os
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

from workflow.agents.rfp_parser import rfp_parser
from workflow.agents.internal_rag import internal_rag
from workflow.agents.competitor_analysis import competitor_analysis
from workflow.agents.strategy_synthesizer import strategy_synthesizer
from workflow.agents.reporter import reporter

tools = [rfp_parser, internal_rag, competitor_analysis, strategy_synthesizer, reporter]

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 Supervisor야. "
        "RFP 분석 → 내부매칭 → 경쟁사 분석 → 전략 → 리포트 순서로 진행해. "
        "품질이 부족하면 같은 툴을 다시 호출할 수도 있지만, 최대 3회까지만 반복 가능해."
    ),
    ("placeholder", "{chat_history}"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}")
])

# 환경변수에서 불러오기
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
AOAI_DEPLOY_GPT4O = os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2024-05-01-preview")

# OpenAI API 키도 확인
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# API 키가 있는지 확인하고 적절한 LLM 초기화
try:
    if AOAI_API_KEY and AOAI_ENDPOINT:
        # Azure OpenAI 사용
        llm = AzureChatOpenAI(
            azure_endpoint=AOAI_ENDPOINT,
            azure_deployment=AOAI_DEPLOY_GPT4O,
            api_version=AOAI_API_VERSION,
            api_key=AOAI_API_KEY,
        )
        print("✅ Azure OpenAI 사용")
    elif OPENAI_API_KEY:
        # OpenAI 사용
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.1
        )
        print("✅ OpenAI 사용")
    else:
        # API 키가 없는 경우 더미 LLM 사용
        print("⚠️ API 키가 없어서 더미 모드로 동작합니다")
        llm = None
except Exception as e:
    print(f"⚠️ LLM 초기화 실패: {e}")
    print("더미 모드로 동작합니다")
    llm = None

# LLM이 있는 경우에만 agent 생성
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
    # 더미 모드에서는 간단한 더미 supervisor 생성
    class DummySupervisor:
        def __init__(self):
            self.tools = tools
            
        def invoke(self, input_data):
            return {
                "output": "⚠️ API 키가 설정되지 않아 더미 모드로 동작합니다. 실제 분석을 위해서는 API 키를 설정해주세요.",
                "intermediate_steps": []
            }
    
    supervisor = DummySupervisor()
