"""
AI 통합 테스트 스크립트
각 agent가 AI를 제대로 사용하는지 확인
"""
import os
from dotenv import load_dotenv

print("=" * 60)
print("AI 통합 테스트 시작")
print("=" * 60)

# 환경변수 로드
load_dotenv()

# 1. API 키 확인
print("\n[1] API 키 확인")
print("-" * 60)

AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT")
AOAI_API_KEY = os.getenv("AOAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if AOAI_API_KEY and AOAI_ENDPOINT:
    print(f"✅ Azure OpenAI 설정됨")
    print(f"   Endpoint: {AOAI_ENDPOINT[:50]}...")
    print(f"   API Key: {'*' * 20}")
elif OPENAI_API_KEY:
    print(f"✅ OpenAI 설정됨")
    print(f"   API Key: {'*' * 20}")
else:
    print("❌ API 키가 설정되지 않았습니다!")
    print("   .env 파일에 다음 중 하나를 설정해주세요:")
    print("   - AOAI_ENDPOINT, AOAI_API_KEY (Azure)")
    print("   - OPENAI_API_KEY (OpenAI)")
    print("\n중단합니다.")
    exit(1)

# 2. LLM 클라이언트 초기화 테스트
print("\n[2] LLM 클라이언트 초기화 테스트")
print("-" * 60)

try:
    if AOAI_API_KEY and AOAI_ENDPOINT:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            api_key=AOAI_API_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=AOAI_ENDPOINT,
        )
        print("✅ Azure OpenAI 클라이언트 초기화 성공")
    elif OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI 클라이언트 초기화 성공")
except Exception as e:
    print(f"❌ 클라이언트 초기화 실패: {e}")
    exit(1)

# 3. 간단한 AI 호출 테스트
print("\n[3] AI 호출 테스트")
print("-" * 60)

try:
    model = os.getenv("AOAI_DEPLOY_GPT4O", "gpt-4o")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Hello, are you working? Reply with 'Yes' only."}],
        temperature=0,
        max_tokens=10
    )
    result = response.choices[0].message.content.strip()
    print(f"✅ AI 응답 성공: {result}")
except Exception as e:
    print(f"❌ AI 호출 실패: {e}")
    exit(1)

# 4. Agent별 LLM 초기화 확인
print("\n[4] Agent별 LLM 초기화 확인")
print("-" * 60)

agent_files = [
    ("RFP Parser", "workflow/agents/rfp_parser.py"),
    ("Strategy Synthesizer", "workflow/agents/strategy_synthesizer.py"),
    ("Reporter", "workflow/agents/reporter.py"),
]

for agent_name, file_path in agent_files:
    try:
        # 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # LLM 초기화 코드 확인
        has_llm_init = "client = None" in content and "AzureOpenAI" in content
        has_ai_function = "client.chat.completions.create" in content
        
        if has_llm_init and has_ai_function:
            print(f"✅ {agent_name}: LLM 통합 완료")
        elif has_llm_init:
            print(f"⚠️  {agent_name}: LLM 초기화만 있고 사용 코드 없음")
        else:
            print(f"❌ {agent_name}: LLM 통합 안됨")
    except Exception as e:
        print(f"❌ {agent_name}: 확인 실패 ({e})")

# 5. 실제 Agent 테스트
print("\n[5] 실제 Agent 테스트")
print("-" * 60)

# Strategy Synthesizer 테스트
print("\n테스트 1: Strategy Synthesizer")
try:
    from workflow.agents.strategy_synthesizer import strategy_synthesizer
    
    test_data = {
        "requirements": ["AI 성능 검증", "클라우드 인프라", "보안 인증"],
        "internal_matches": [
            {"requirement": "AI 성능 검증", "matches": [{"title": "AI 프로젝트 A", "summary": "테스트"}]},
            {"requirement": "보안 인증", "matches": []}
        ],
        "competitor_profiles": {
            "삼성SDS": {"swot": {"S": ["브랜드"], "W": ["비용"]}},
        }
    }
    
    result = strategy_synthesizer.invoke(test_data)
    strategy = result.get("strategy", {})
    
    if strategy.get("summary"):
        print("✅ AI 요약 생성됨:")
        print(f"   {strategy['summary'][:100]}...")
    else:
        print("❌ AI 요약이 없음 (기본 모드로 작동)")
        
except Exception as e:
    print(f"❌ 테스트 실패: {e}")

# Reporter 테스트
print("\n테스트 2: Reporter")
try:
    from workflow.agents.reporter import reporter
    
    test_data = {
        "data": {
            "requirements": ["AI 성능 검증", "클라우드"],
            "evaluation": ["기술 70%", "가격 30%"],
            "risks": ["일정 지연 가능성"],
            "internal_matches": [],
            "competitor_profiles": {},
            "strategy": {"summary": "테스트 전략", "actions": ["액션1"]}
        }
    }
    
    result = reporter.invoke(test_data)
    deal_brief = result.get("deal_brief", "")
    
    if "프로젝트 개요" in deal_brief or "Deal Brief" in deal_brief:
        print("✅ AI 보고서 생성됨:")
        print(f"   {deal_brief[:200]}...")
    else:
        print("❌ AI 보고서가 없음 (기본 모드로 작동)")
        
except Exception as e:
    print(f"❌ 테스트 실패: {e}")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)
print("\n만약 ❌가 있다면:")
print("1. .env 파일에 API 키가 올바르게 설정되어 있는지 확인")
print("2. Azure OpenAI라면 AOAI_ENDPOINT, AOAI_API_KEY, AOAI_DEPLOY_GPT4O 확인")
print("3. OpenAI라면 OPENAI_API_KEY 확인")
print("4. 모델 이름이 올바른지 확인 (gpt-4o, gpt-4o-mini 등)")

