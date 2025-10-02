"""
빠른 LLM 통합 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

def quick_test():
    print("🚀 빠른 LLM 통합 테스트")
    print("=" * 40)
    
    # 1. 기본 LLM 클라이언트 테스트
    try:
        from utils.llm_client import get_llm_client, is_llm_available, call_llm
        print("✅ LLM 클라이언트 임포트: 성공")
        
        available = is_llm_available()
        print(f"✅ LLM 사용 가능: {'예' if available else '아니오'}")
        
        if available:
            response = call_llm("안녕하세요!", temperature=0.3)
            print(f"✅ LLM 호출: {'성공' if response else '실패'}")
            
    except Exception as e:
        print(f"❌ LLM 클라이언트 오류: {e}")
        return
    
    # 2. RFP Parser 테스트
    try:
        from workflow.agents.rfp_parser import _apply_smart_fallback_single
        result = _apply_smart_fallback_single(
            ["Python 개발", "목차 작성", "보안 강화", "제출 일정"], 
            "requirements"
        )
        print(f"✅ RFP Parser fallback: {len(result)}개 항목")
        
    except Exception as e:
        print(f"❌ RFP Parser 오류: {e}")
    
    # 3. Strategy Synthesizer 테스트
    try:
        from workflow.agents.strategy_synthesizer import _validate_strategy_data
        test_data = {
            "summary": "테스트",
            "actions": ["액션1"],
            "swot": {"S": "강점", "W": "약점", "O": "기회", "T": "위협"},
            "differentiation": ["차별화1"]
        }
        valid = _validate_strategy_data(test_data)
        print(f"✅ Strategy Synthesizer 검증: {'통과' if valid else '실패'}")
        
    except Exception as e:
        print(f"❌ Strategy Synthesizer 오류: {e}")
    
    # 4. Competitor Analysis 테스트
    try:
        from workflow.agents.competitor_analysis import _validate_swot_data
        test_swot = {"S": ["강점1"], "W": ["약점1"], "O": ["기회1"], "T": ["위협1"]}
        valid = _validate_swot_data(test_swot)
        print(f"✅ Competitor Analysis 검증: {'통과' if valid else '실패'}")
        
    except Exception as e:
        print(f"❌ Competitor Analysis 오류: {e}")
    
    # 5. 파싱 함수 테스트
    try:
        from utils.llm_client import parse_list_response, parse_json_response
        
        # 리스트 파싱
        list_result = parse_list_response("- 항목1\n- 항목2\n- 항목3")
        print(f"✅ 리스트 파싱: {len(list_result)}개 항목")
        
        # JSON 파싱
        json_result = parse_json_response('{"test": "value"}')
        print(f"✅ JSON 파싱: {'성공' if json_result else '실패'}")
        
    except Exception as e:
        print(f"❌ 파싱 함수 오류: {e}")
    
    print("\n🎯 테스트 완료!")

if __name__ == "__main__":
    quick_test()
