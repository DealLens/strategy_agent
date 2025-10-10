"""Import 테스트 스크립트"""

try:
    print("1. supervisor import 시도...")
    from workflow.supervisor import ParallelSupervisor, llm
    print("   ✅ supervisor import 성공")
    
    print("\n2. 개별 에이전트 import 시도...")
    from workflow.agents.rfp_parser import rfp_parser
    print("   ✅ rfp_parser import 성공")
    
    from workflow.agents.internal_rag import internal_rag
    print("   ✅ internal_rag import 성공")
    
    from workflow.agents.competitor_analysis import competitor_analysis
    print("   ✅ competitor_analysis import 성공")
    
    from workflow.agents.strategy_synthesizer import strategy_synthesizer_v2
    print("   ✅ strategy_synthesizer import 성공")
    
    print("\n3. LLM 클라이언트 import 시도...")
    from utils.llm_client import get_llm_client, is_llm_available
    print("   ✅ llm_client import 성공")
    
    print("\n✅ 모든 import 성공!")
    print(f"   LLM 사용 가능: {is_llm_available()}")
    
except Exception as e:
    print(f"\n❌ Import 실패: {e}")
    import traceback
    traceback.print_exc()

