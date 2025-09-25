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
AOAI_DEPLOY_GPT4O = os.getenv("AOAI_DEPLOY_GPT4O")
AOAI_API_VERSION = os.getenv("AOAI_API_VERSION", "2024-05-01-preview")

llm = AzureChatOpenAI(
    azure_endpoint=AOAI_ENDPOINT,
    azure_deployment=AOAI_DEPLOY_GPT4O,
    api_version=AOAI_API_VERSION,
    api_key=AOAI_API_KEY,
)

agent = create_tool_calling_agent(llm, tools, prompt)

supervisor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=15,
    handle_parsing_errors=True
)
