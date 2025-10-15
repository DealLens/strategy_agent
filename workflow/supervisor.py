import os
import asyncio
from typing import Any, Dict

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor

# --- 개별 에이전트 import ---
from workflow.agents.rfp_parser import rfp_parser
from workflow.agents.internal_rag import internal_rag
from workflow.agents.competitor_analysis import competitor_analysis, generate_competitive_strategy
from workflow.agents.strategy_synthesizer import strategy_synthesizer_v2 as strategy_synthesizer


# ======================
# 1. 사용할 툴 정의
# ======================
tools = [rfp_parser, internal_rag, competitor_analysis, strategy_synthesizer]


# ======================
# 2. Supervisor 프롬프트
# ======================
prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "너는 전문 전략 컨설턴트 역할의 Supervisor다. "
        "분석은 반드시 **네 단계**로 수행한다:\n\n"
        "1️⃣ RFP 분석\n"
        "2️⃣ 내부 매칭\n"
        "3️⃣ 경쟁사 분석\n"
        "4️⃣ 전략 제안\n\n"
        "📌 RFP Parser / Internal RAG / Competitor Analysis는 병렬로 실행 후 결과를 합쳐 전략 분석에 사용한다.\n"
        "📌 Strategy Synthesizer(v2)는 병렬 결과물을 받아 컨설턴트 수준의 전략을 도출한다.\n"
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
        """RFP Parser, Internal RAG, Competitor Analysis 병렬 실행"""

        async def _run_tool(tool, name, params):
            """각 에이전트를 안전하게 비동기 실행"""
            try:
                result = await tool.ainvoke(params)
                print(f"[{name}] ✅ 완료")
                return name, result
            except Exception as e:
                print(f"[{name}] ❌ 실패: {e}")
                return name, {"error": str(e)}

        # ---------------------
        # Step 1️⃣ RFP Parser 실행
        # ---------------------
        pdf_path = input_data.get("pdf_path", "")
        rfp_result = await _run_tool(rfp_parser, "rfp_parser", {"pdf_path": pdf_path})
        rfp_data = rfp_result[1]

        # 요구사항 추출
        requirements = []
        if isinstance(rfp_data, dict) and "requirements" in rfp_data:
            requirements = rfp_data["requirements"][:5]  # 상위 5개만 사용
        else:
            print("⚠️ RFP 요구사항 추출 실패, 기본값 사용")
            requirements = ["요구사항 추출 실패"]

        # ---------------------
        # Step 2️⃣ 병렬 실행 (Internal RAG + Competitor Analysis)
        # ---------------------
        results = await asyncio.gather(
            _run_tool(internal_rag, "internal_rag", {"requirements": requirements}),
            _run_tool(competitor_analysis, "competitor_analysis", {"update_data": True}),
            return_exceptions=False
        )

        all_results = dict([rfp_result] + list(results))
        return all_results

    async def invoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """전체 Supervisor 파이프라인 실행"""
        print("\n🚀 [Supervisor] 전체 분석 시작...\n")

        # 1️⃣ 병렬 실행
        parallel_results = await self.run_parallel(input_data)

        # 결과 정리
        rfp_data = parallel_results.get("rfp_parser", {})
        internal_data = parallel_results.get("internal_rag", {})
        competitor_data = parallel_results.get("competitor_analysis", {})

        # ---------------------
        # Step 3️⃣ 전략 합성 (컨설턴트 수준)
        # ---------------------
        requirements = rfp_data.get("requirements", [])[:5]
        if not requirements:
            requirements = ["요구사항 추출 실패"]

        # ✅ internal_matches 구조 로그 + 보정
        internal_matches = internal_data.get("internal_matches", [])
        print("\n🧩 [DEBUG] internal_matches 전달 전 구조 확인:")
        if not internal_matches:
            print("⚠️ internal_matches 비어 있음")
        else:
            for i, m in enumerate(internal_matches, 1):
                print(f"  {i}. {m.get('requirement')} | match_score={m.get('match_score')}")

        # ✅ match_score 누락 방지용 보정
        for m in internal_matches:
            val = m.get("match_score")
            try:
                if val in [None, "", "N/A"]:
                    print(f"   ↳ {m.get('requirement')} → match_score 누락 → 0.55 기본값 적용")
                    m["match_score"] = 0.55
                else:
                    m["match_score"] = round(float(val), 2)
            except Exception:
                m["match_score"] = 0.55

        print("\n🎯 [Strategy Synthesizer v3.1] 전략 분석 시작 (상세 모드)...\n")
        
        # 경쟁사 데이터 확인
        comp_profiles = competitor_data.get("competitor_profiles", {})
        print(f"📊 [DEBUG] 경쟁사 프로필 개수: {len(comp_profiles)}")
        for company in comp_profiles.keys():
            print(f"  - {company}")
        
        # ✅ SK AX 프로필 생성
        skax_profile = {
            "company_name": "SK AX (SK㈜ C&C)",
            "core_competencies": [
                "생성형 AI 및 LLM 기반 솔루션 개발",
                "클라우드 인프라 구축 (하이브리드/프라이빗/퍼블릭)",
                "스마트 팩토리 및 MES/MCS 시스템 구축",
                "데이터 분석 플랫폼 (AccuInsight+, DataRobot AutoML)",
                "디지털 전환(DX) 컨설팅 및 통합 솔루션"
            ],
            "key_solutions": [
                "I-FACTs MCS (제조 물류 자동화)",
                "AI 코딩 어시스턴트 (생성형 AI 기반)",
                "차세대 택배/커머스 시스템 (클라우드 기반)",
                "이중화 전자패치 (IFS - 네트워크 무중단)",
                "Accu.Fabric Suite (통합 Digital Platform)"
            ],
            "industries": ["제조", "금융", "유통/물류", "공공", "반도체", "디스플레이"],
            "technical_strengths": [
                "Azure/AWS 멀티 클라우드 전문성",
                "AutoML 및 데이터 분석 자동화",
                "실시간 대용량 트래픽 처리 (오토 스케일링)",
                "보안 강화 솔루션 (프라이빗 클라우드, VDI)",
                "End-to-End 프로젝트 수행 역량"
            ]
        }
        
        # ✅ 경쟁사 대응 전략 생성 (각 경쟁사별)
        competitive_strategies = []
        if comp_profiles:
            print("\n🔥 [경쟁사 대응 전략] 생성 중...\n")
            try:
                # 경쟁사 리스트 준비
                competitors_list = []
                for company, profile in comp_profiles.items():
                    competitors_list.append({
                        "company": company,
                        "swot": profile.get("swot", {}),
                        "company_summary": profile.get("company_summary", ""),
                        "key_technologies": profile.get("key_technologies", [])
                    })
                
                # generate_competitive_strategy 호출 (동기 함수이므로 invoke 사용)
                strategy_response = generate_competitive_strategy.invoke({
                    "skax_profile": skax_profile,
                    "competitors": competitors_list
                })
                
                if isinstance(strategy_response, list):
                    competitive_strategies = strategy_response
                    print(f"✅ [경쟁사 대응 전략] {len(competitive_strategies)}개 생성 완료")
                elif isinstance(strategy_response, dict):
                    # dict인 경우 리스트로 변환
                    for company, strategies in strategy_response.items():
                        if isinstance(strategies, list):
                            competitive_strategies.extend(strategies)
                        else:
                            competitive_strategies.append(strategies)
                    print(f"✅ [경쟁사 대응 전략] {len(competitive_strategies)}개 생성 완료")
                else:
                    print(f"⚠️ [경쟁사 대응 전략] 예상치 못한 응답 형식: {type(strategy_response)}")
            except Exception as e:
                print(f"⚠️ [경쟁사 대응 전략] 생성 실패: {e}")
                competitive_strategies = []
        
        strategy_result = await strategy_synthesizer.ainvoke({
            "requirements": requirements,
            "internal_matches": internal_matches,
            "competitor_profiles": comp_profiles,
            "temperature": 0.7
        })

        # ✅ 생성된 경쟁사 대응 전략을 strategy에 통합
        if competitive_strategies and isinstance(strategy_result, dict):
            strategy_data = strategy_result.get("strategy", {})
            if isinstance(strategy_data, dict):
                # appendix.competitor_counters에 추가
                appendix = strategy_data.get("appendix", {})
                if not isinstance(appendix, dict):
                    appendix = {}
                
                # competitor_analysis에서 생성된 전략만 사용 (중복 방지)
                appendix["competitor_counters"] = competitive_strategies
                strategy_data["appendix"] = appendix
                strategy_result["strategy"] = strategy_data
                
                print(f"✅ [Supervisor] 경쟁사 대응 전략 {len(competitive_strategies)}개가 strategy에 통합됨")

        print("\n✅ [Supervisor] 전체 프로세스 완료\n")
        return {
            "rfp_parser": rfp_data,
            "internal_rag": internal_data,
            "competitor_analysis": competitor_data,
            "strategy": strategy_result,
            "skax_profile": skax_profile,
            "competitive_strategies": competitive_strategies
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

        print("\n=== 📊 최종 전략 분석 결과 ===\n")
        print(results["strategy"])

    asyncio.run(main())
