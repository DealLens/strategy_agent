import os
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv가 없어도 환경변수는 사용 가능

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
        "당신은 **수석 전략 컨설턴트**로서 RFP 기반 입찰 전략 수립을 담당합니다.\n"
        "분석은 **체계적인 5단계 프로세스**로 수행하며, 각 단계별로 구체적인 산출물을 생성합니다:\n\n"
        
        "🎯 **1단계: RFP 심층 분석**\n"
        "   → rfp_parser 도구로 PDF 문서에서 다음 정보를 추출:\n"
        "     • 핵심 요구사항 (기술적/비기술적 요구사항 구분)\n"
        "     • 평가기준 및 가중치 (기술/가격/사업수행능력 등)\n"
        "     • 제출 서류 및 일정\n"
        "     • 잠재적 리스크 요소\n"
        "   → 각 항목을 **우선순위별로 분류**하고 **구체적인 기준** 명시\n\n"
        
        "🔍 **2단계: 내부 역량 매칭**\n"
        "   → internal_rag 도구로 요구사항별 내부 사례 검색:\n"
        "     • 각 요구사항당 **Top-3 유사 프로젝트** 식별\n"
        "     • **매칭도 점수**와 함께 구체적인 사례 설명\n"
        "     • 기술 스택, 프로젝트 규모, 성과 지표 포함\n"
        "     • 갭 분석: 부족한 역량과 보완 방안 제시\n\n"
        
        "⚔️ **3단계: 경쟁사 전략적 분석** (핵심 단계)\n"
        "   → competitor_analysis(update_data=True) 호출로 3사 실시간 분석:\n"
        "     • **삼성SDS, LG CNS, 현대오토에버** 최신 동향 파악\n"
        "     • 각사의 company_summary 기반 **핵심 역량** 도출\n"
        "     • SWOT 분석으로 **경쟁 우위/약점** 식별\n"
        "     • **차별화 포인트** 도출: 우리 vs 경쟁사 비교\n"
        "     • **가격 경쟁력, 기술력, 브랜드력** 등 다각도 분석\n\n"
        
        "⚠️ **4단계: 리스크 시나리오 분석**\n"
        "   → 다음 관점에서 **구체적인 위험 시나리오** 작성:\n"
        "     • **기술적 리스크**: 요구사항 대비 역량 부족\n"
        "     • **경쟁 리스크**: 경쟁사 강점 대비 우리 약점\n"
        "     • **사업 리스크**: 일정, 예산, 리소스 제약\n"
        "     • **계약 리스크**: 조건, 책임, 보증 등\n"
        "   → 각 리스크별 **발생 확률, 영향도, 대응 방안** 제시\n\n"
        
        "🚀 **5단계: 차별화 전략 수립**\n"
        "   → 다음 요소를 종합하여 **구체적인 전략** 도출:\n"
        "     • **우리 강점** + **경쟁사 약점** = 차별화 기회\n"
        "     • **내부 매칭 결과** 기반 신뢰성 확보 방안\n"
        "     • **가격 전략**: 프리미엄 vs 경쟁력 가격\n"
        "     • **제안 구성**: 기술 제안 + 사업 제안 + 차별화 요소\n"
        "     • **실행 계획**: 단계별 마일스톤과 성공 지표\n\n"
        
        "📋 **출력 형식 가이드라인**:\n"
        "   • 각 단계별로 **명확한 제목**과 **핵심 내용** 구분\n"
        "   • **근거 기반** 분석: 구체적인 데이터와 출처 명시\n"
        "   • **실행 가능한** 제안: 추상적이지 않고 구체적인 방안\n"
        "   • **우선순위** 명시: High/Medium/Low 또는 1-5점 척도\n"
        "   • **시각적 구분**: 이모지와 불릿 포인트 활용\n\n"
        
        "🎯 **품질 관리**:\n"
        "   • 각 도구 호출 후 **결과 검증**: 필요한 정보가 모두 포함되었는지 확인\n"
        "   • **일관성 체크**: 단계간 논리적 연결성 확보\n"
        "   • **완성도 점검**: RFP 요구사항 대비 충분한 분석 여부\n"
        "   • **최대 3회 재시도**: 품질 미달 시 동일 도구 재호출 가능\n\n"
        
        "💡 **성공 기준**:\n"
        "   → 고객이 **즉시 실행 가능한** 구체적인 전략 제시\n"
        "   → 경쟁사 대비 **명확한 차별화 포인트** 도출\n"
        "   → **리스크 대응 방안**까지 포함한 완성도 높은 제안서"
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
        print("✅ [Supervisor] Azure OpenAI 초기화 성공")
        print(f"   - Endpoint: {AOAI_ENDPOINT}")
        print(f"   - Deployment: {AOAI_DEPLOY_GPT4O}")
    elif OPENAI_API_KEY:
        # OpenAI
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model="gpt-4o-mini",
            temperature=0.2
        )
        print("✅ [Supervisor] OpenAI 초기화 성공")
    else:
        print("⚠️ [Supervisor] API 키가 설정되지 않았습니다.")
        print("   필요한 환경 변수:")
        print("   - Azure OpenAI: AOAI_API_KEY, AOAI_ENDPOINT")
        print("   - 또는 OpenAI: OPENAI_API_KEY")
        print("   더미 모드로 동작합니다.")
        llm = None
except Exception as e:
    print(f"⚠️ [Supervisor] LLM 초기화 실패: {e}")
    print("   환경 변수를 확인해주세요:")
    print("   - AOAI_API_KEY, AOAI_ENDPOINT (Azure)")
    print("   - OPENAI_API_KEY (OpenAI)")
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
